"""
BỘ MÔ PHỎNG TỔNG HỢP (Synthetic Simulation Generator)
====================================================
Cấu hình chuẩn:
- Camera ADAS hướng trước VinFast VF8 / VF9 (VinFast ADAS Forward-Looking Camera):
  + Độ phân giải: 1280x720, 30 FPS, độ dài 10 giây (300 frames)
  + HFOV = 50.0 độ => Tiêu cự f = (1280/2) / tan(25 deg) = 1372.5 pixel
  + Chiều cao gắn camera kính lái: h_cam = 1.30m
  + Đường chân trời y_horizon = 360 pixel
- Xe mục tiêu (VinFast VF e34 / VF8):
  + Chiều rộng vật lý W_true = 1.80m, chiều cao thân xe H_true = 1.08m
- Quỹ đạo khoảng cách Z(t) bao quát đầy đủ 3 dải cự ly kiểm chuẩn:
  + Dải 20 - 40m: từ 30.0m giảm xuống 20.0m (v_rel = -3.3 m/s)
  + Dải 10 - 20m: từ 20.0m giảm xuống 10.0m (v_rel = -5.0 m/s)
  + Dải 5 - 10m: từ 10.0m giảm xuống 6.5m (bám đuôi nguy hiểm / phanh khẩn cấp)
  + Pha giữ cự ly 6.5m và tăng tốc tách khoảng cách an toàn trở lại 14.0m
"""

import math
import os
import cv2
import numpy as np
import pandas as pd


def generate_synthetic_dataset(
    output_video_path: str = "sim/synthetic_dashcam.mp4",
    output_csv_path: str = "sim/ground_truth.csv",
    num_frames: int = 300,
    fps: float = 30.0,
    width: int = 1280,
    height: int = 720,
    hfov_deg: float = 50.0,  # VinFast ADAS Forward Camera profile
    camera_height_m: float = 1.30,
    vehicle_width_m: float = 1.80,
) -> None:
    focal_length_px = (width / 2.0) / math.tan(math.radians(hfov_deg / 2.0))
    horizon_y = height / 2.0
    cx = width / 2.0

    template_path = "sim/car_template.png"
    if os.path.exists(template_path):
        car_sprite = cv2.imread(template_path)
    else:
        car_sprite = np.full((100, 160, 3), (30, 40, 180), dtype=np.uint8)

    aspect_ratio = car_sprite.shape[0] / car_sprite.shape[1]  # ~0.60

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_video = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    dt = 1.0 / fps
    records = []

    # Quỹ đạo Z(t)
    z_trajectory = np.zeros(num_frames)
    for i in range(num_frames):
        t = i * dt
        if t < 3.0:
            # 30.0m -> 20.0m (dải 20-40m)
            z_trajectory[i] = 30.0 - (10.0 / 3.0) * t
        elif t < 5.5:
            # 20.0m -> 10.0m (dải 10-20m)
            z_trajectory[i] = 20.0 - (10.0 / 2.5) * (t - 3.0)
        elif t < 7.0:
            # 10.0m -> 6.5m (dải 5-10m, bám đuôi nguy hiểm)
            z_trajectory[i] = 10.0 - (3.5 / 1.5) * (t - 5.5)
        elif t < 8.2:
            # 6.5m giữ cự ly
            z_trajectory[i] = 6.50
        else:
            # 6.5m -> 14.5m (tăng tốc tách an toàn)
            z_trajectory[i] = 6.50 + (8.0 / 1.8) * (t - 8.2)

    # Vận tốc tương đối thực tế
    vz_true = np.gradient(z_trajectory, dt)

    for i in range(num_frames):
        t = i * dt
        z_t = float(z_trajectory[i])
        vz_t = float(vz_true[i])

        if vz_t < -0.15:
            ttc_t = z_t / (-vz_t)
        else:
            ttc_t = float("inf")

        box_w = (focal_length_px * vehicle_width_m) / z_t
        box_h = box_w * aspect_ratio

        y_bottom = horizon_y + (focal_length_px * camera_height_m) / z_t
        y_top = y_bottom - box_h

        # Lắc lư ngang thực tế
        center_x = cx + math.sin(t * 1.8) * (180.0 / z_t)
        x_left = center_x - box_w / 2.0
        x_right = center_x + box_w / 2.0

        # Dựng nền
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Bầu trời
        for y in range(int(horizon_y)):
            sky_val = int(175 + (y / horizon_y) * 45)
            frame[y, :] = (sky_val, sky_val - 15, 215)

        # Mặt đường
        for y in range(int(horizon_y), height):
            road_val = int(60 + ((y - horizon_y) / (height - horizon_y)) * 25)
            frame[y, :] = (road_val, road_val, road_val)

        # Làn đường perspective
        road_poly = np.array([
            [int(cx - 40), int(horizon_y)],
            [int(cx + 40), int(horizon_y)],
            [width - 120, height],
            [120, height]
        ], np.int32)
        cv2.fillPoly(frame, [road_poly], (78, 78, 82))

        # Vạch đứt trắng giữa làn
        offset = (int(t * 220)) % 60
        for y_dash in range(int(horizon_y) + offset, height, 60):
            scale = (y_dash - horizon_y) / (height - horizon_y)
            dash_w = max(2, int(scale * 12))
            dash_h = max(6, int(scale * 30))
            cv2.rectangle(frame, (int(cx - dash_w / 2), y_dash), (int(cx + dash_w / 2), y_dash + dash_h), (245, 245, 245), -1)

        # Vạch biên vàng
        cv2.line(frame, (int(cx - 40), int(horizon_y)), (140, height), (0, 215, 255), 4, cv2.LINE_AA)
        cv2.line(frame, (int(cx + 40), int(horizon_y)), (width - 140, height), (0, 215, 255), 4, cv2.LINE_AA)

        # Dán bóng xe và xe
        bw = max(10, int(round(box_w)))
        bh = max(10, int(round(box_h)))
        x1 = int(round(x_left))
        y1 = int(round(y_top))
        x2 = x1 + bw
        y2 = y1 + bh

        # Bóng xe dưới gầm
        cv2.ellipse(frame, (int(round(center_x)), y2 + 2), (bw // 2 + 4, max(2, bh // 8)), 0, 0, 360, (25, 25, 25), -1)

        # Dán xe
        resized_car = cv2.resize(car_sprite, (bw, bh), interpolation=cv2.INTER_LINEAR)
        paste_x1 = max(0, x1)
        paste_y1 = max(0, y1)
        paste_x2 = min(width, x2)
        paste_y2 = min(height, y2)

        src_x1 = paste_x1 - x1
        src_y1 = paste_y1 - y1
        src_x2 = src_x1 + (paste_x2 - paste_x1)
        src_y2 = src_y1 + (paste_y2 - paste_y1)

        if paste_x2 > paste_x1 and paste_y2 > paste_y1:
            frame[paste_y1:paste_y2, paste_x1:paste_x2] = resized_car[src_y1:src_y2, src_x1:src_x2]

        # Nhiễu cảm biến thực tế
        illum = 1.0 + 0.05 * math.sin(t * 3.0)
        frame = np.clip(frame.astype(np.float32) * illum, 0, 255).astype(np.uint8)

        noise = np.random.normal(0, 2.5, frame.shape).astype(np.float32)
        frame = np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        out_video.write(frame)

        records.append({
            "frame": i,
            "timestamp_s": round(t, 4),
            "z_true_m": round(z_t, 3),
            "vz_true_mps": round(vz_t, 3),
            "ttc_true_s": round(ttc_t, 2) if not math.isinf(ttc_t) else 999.0,
            "gt_x1": max(0, x1),
            "gt_y1": max(0, y1),
            "gt_x2": min(width, x2),
            "gt_y2": min(height, y2),
            "gt_w_px": round(box_w, 2),
            "gt_h_px": round(box_h, 2),
        })

    out_video.release()
    df = pd.DataFrame(records)
    df.to_csv(output_csv_path, index=False)
    print(f"Generated synthetic simulation: {output_video_path} (HFOV={hfov_deg} deg, f={focal_length_px:.1f}px)")


if __name__ == "__main__":
    generate_synthetic_dataset()
