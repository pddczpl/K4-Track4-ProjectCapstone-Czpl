"""
TẠO VÀ CHẠY CA LỖI QUA PIPELINE THỰC TẾ (Real Pipeline Failure Case)
===================================================================
Mục đích:
- Thay thế phân tích số học tĩnh bằng việc CHẠY THẬT qua FollowingDistancePipeline
  (YOLOv8 + ByteTrack + Pinhole + Kalman Filter).
- Kịch bản thực nghiệm:
  + Xe mục tiêu chạy ở cự ly Z_true = 12.0m (cần cảnh báo CHÚ Ý).
  + Khung 0 - 20: Xe không bị che khuất, pipeline nhận diện chuẩn.
  + Khung 20 - 50: Rào chắn / vật cản che khuất 40% bề rộng xe từ bên trái.
  + Chạy pipeline kiểm tra:
    * Bounding box YOLO nhận diện thay đổi thế nào?
    * Z ước lượng nhảy bao nhiêu mét?
    * Cờ `is_uncertain` trong Kalman có được kích hoạt không?
    * Trễ bao nhiêu khung hình trước khi phát hiện bất thường?
- Khảo sát độ nhạy theo tỷ lệ che khuất (10%, 20%, 30%, 40%).
- Cập nhật results/failure_case.png và results/failure_case_analysis.json.
"""

import json
import math
import os
import sys
from typing import Tuple, List, Dict, Any, Optional
import cv2
import numpy as np

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.pipeline import FollowingDistancePipeline


def build_synthetic_scene(
    z_true: float = 12.0,
    occlusion_ratio: float = 0.0,
    width: int = 1280,
    height: int = 720,
    hfov_deg: float = 50.0,
    camera_height_m: float = 1.30,
    vehicle_width_m: float = 1.80,
    template_path: str = "sim/car_template.png"
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    focal_length_px = (width / 2.0) / math.tan(math.radians(hfov_deg / 2.0))
    horizon_y = height / 2.0
    cx = width / 2.0

    car_sprite = cv2.imread(template_path)
    aspect = car_sprite.shape[0] / car_sprite.shape[1]

    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Bầu trời
    for y in range(int(horizon_y)):
        s_val = int(175 + (y / horizon_y) * 45)
        frame[y, :] = (s_val, s_val - 15, 215)
    # Đường nhựa
    for y in range(int(horizon_y), height):
        r_val = int(60 + ((y - horizon_y) / (height - horizon_y)) * 25)
        frame[y, :] = (r_val, r_val, r_val)

    # Làn đường
    road_poly = np.array([
        [int(cx - 40), int(horizon_y)],
        [int(cx + 40), int(horizon_y)],
        [width - 120, height],
        [120, height]
    ], np.int32)
    cv2.fillPoly(frame, [road_poly], (78, 78, 82))

    # Kích thước pixel xe
    bw = int(round((focal_length_px * vehicle_width_m) / z_true))
    bh = int(round(bw * aspect))
    y_bottom = int(round(horizon_y + (focal_length_px * camera_height_m) / z_true))
    y_top = y_bottom - bh
    x_left = int(round(cx - bw / 2.0))

    # Dán bóng xe
    cv2.ellipse(frame, (int(round(cx)), y_bottom + 2), (bw // 2 + 4, max(2, bh // 8)), 0, 0, 360, (25, 25, 25), -1)

    # Dán xe
    resized_car = cv2.resize(car_sprite, (bw, bh), interpolation=cv2.INTER_LINEAR)
    frame[y_top:y_bottom, x_left:x_left+bw] = resized_car

    # Dán vật cản che khuất nếu có
    if occlusion_ratio > 0.0:
        occ_w = int(round(bw * occlusion_ratio))
        # Rào chắn màu cam / dải phân cách che góc bên trái xe
        barrier_poly = np.array([
            [x_left - 10, y_bottom + 15],
            [x_left + occ_w, y_top - 5],
            [x_left + occ_w + 12, y_bottom + 15]
        ], np.int32)
        cv2.fillPoly(frame, [barrier_poly], (25, 110, 225))

    return frame, (x_left, y_top, x_left + bw, y_bottom)


def run_real_pipeline_failure_case():
    os.makedirs("results", exist_ok=True)
    pipeline = FollowingDistancePipeline(hfov_deg=50.0, confidence_threshold=0.20, use_kalman=True)

    z_true = 12.0
    total_frames = 50
    occlusion_start_frame = 20
    occlusion_ratio = 0.40

    frame_logs = []
    normal_annotated = None
    occluded_annotated = None

    print("Đang chạy 50 frames qua FollowingDistancePipeline thực tế...")
    for f_idx in range(total_frames):
        t_s = f_idx * 0.0333
        is_occluded = (f_idx >= occlusion_start_frame)
        curr_occ = occlusion_ratio if is_occluded else 0.0

        frame, true_box = build_synthetic_scene(z_true=z_true, occlusion_ratio=curr_occ)
        annotated, targets, stats = pipeline.process_frame(frame, timestamp_s=t_s)

        pri = stats.get("primary_target")
        if pri:
            log_item = {
                "frame": f_idx,
                "is_occluded": is_occluded,
                "detected": True,
                "z_raw_m": round(pri["z_raw_m"], 2),
                "z_est_m": round(pri["z_est_m"], 2),
                "sigma_z_m": round(pri["sigma_z_m"], 2),
                "vz_est_kmh": round(pri["vz_est_kmh"], 1),
                "ttc_s": round(pri["ttc_s"], 1) if pri["ttc_s"] < 99 else 999.0,
                "is_uncertain": pri["is_uncertain"],
                "alert_level": pri["alert_level"]
            }
        else:
            log_item = {
                "frame": f_idx,
                "is_occluded": is_occluded,
                "detected": False,
                "z_raw_m": None,
                "z_est_m": None,
                "sigma_z_m": None,
                "vz_est_kmh": None,
                "ttc_s": None,
                "is_uncertain": True,
                "alert_level": "KHÔNG NHẬN DIỆN"
            }
        frame_logs.append(log_item)

        if f_idx == 15:
            normal_annotated = annotated.copy()
        elif f_idx == 35:
            occluded_annotated = annotated.copy()

    # Lưu ảnh đối sánh kết quả thực
    if normal_annotated is not None and occluded_annotated is not None:
        combined = np.hstack([normal_annotated, occluded_annotated])
        cv2.imwrite("results/failure_case.png", combined)
        print("Đã lưu results/failure_case.png từ pipeline thực tế.")

    # Khảo sát độ nhạy theo các tỷ lệ che khuất (10%, 20%, 30%, 40%)
    sensitivity_results = {}
    f_val = 1372.5
    w_true_m = 1.80
    w_true_px = (f_val * w_true_m) / z_true  # ~205.88 px

    for occ_pct in [10.0, 20.0, 30.0, 40.0]:
        occ_frac = occ_pct / 100.0
        w_obs_px = w_true_px * (1.0 - occ_frac)
        z_est_calc = (f_val * w_true_m) / w_obs_px
        err_m = z_est_calc - z_true
        err_pct = (err_m / z_true) * 100.0
        sensitivity_results[f"occlusion_{int(occ_pct)}pct"] = {
            "occlusion_ratio_percent": occ_pct,
            "detected_width_px": round(w_obs_px, 1),
            "estimated_distance_m": round(z_est_calc, 2),
            "absolute_error_m": round(err_m, 2),
            "relative_error_percent": round(err_pct, 1)
        }

    # Phân tích sự kích hoạt của cơ chế nghi ngờ trong Kalman
    occ_frames_data = [item for item in frame_logs if item["is_occluded"]]
    uncertain_triggers = [item["frame"] for item in occ_frames_data if item["is_uncertain"]]
    first_trigger_frame = uncertain_triggers[0] if uncertain_triggers else None
    trigger_delay_frames = (first_trigger_frame - occlusion_start_frame) if first_trigger_frame is not None else None

    # Lấy giá trị ước lượng trung bình sau khi bị che
    z_est_after_occl = [item["z_est_m"] for item in occ_frames_data if item["z_est_m"] is not None]
    avg_z_occluded = float(np.mean(z_est_after_occl)) if z_est_after_occl else None

    analysis_report = {
        "failure_case_id": "ERR_01_PARTIAL_OCCLUSION_PIPELINE_RUN",
        "tested_with_actual_pipeline": True,
        "detector_model": "yolov8n.pt",
        "tracker": "ByteTrack",
        "filter": "VehicleKalmanFilter",
        "scenario_setup": {
            "ground_truth_distance_m": z_true,
            "true_vehicle_width_m": w_true_m,
            "camera_focal_length_px": f_val,
            "unoccluded_box_width_px": round(w_true_px, 1),
            "occlusion_ratio_tested_percent": 40.0,
            "occlusion_start_frame": occlusion_start_frame,
            "total_frames_run": total_frames
        },
        "pipeline_execution_results": {
            "average_estimated_z_before_occlusion_m": round(float(np.mean([x["z_est_m"] for x in frame_logs[:occlusion_start_frame] if x["z_est_m"]])), 2),
            "average_estimated_z_after_occlusion_m": round(avg_z_occluded, 2) if avg_z_occluded else None,
            "absolute_overestimation_error_m": round(avg_z_occluded - z_true, 2) if avg_z_occluded else None,
            "relative_overestimation_error_percent": round(((avg_z_occluded - z_true) / z_true) * 100.0, 1) if avg_z_occluded else None,
            "suspicion_mechanism_triggered": (len(uncertain_triggers) > 0),
            "first_trigger_frame": first_trigger_frame,
            "detection_delay_frames": trigger_delay_frames,
            "final_alert_level_during_occlusion": occ_frames_data[-1]["alert_level"] if occ_frames_data else None
        },
        "sensitivity_by_occlusion_ratio": sensitivity_results,
        "root_cause_analysis": (
            "Phân tích độ nhạy giả định: nếu box YOLO thu hẹp 40% từ ~206px còn ~123px, "
            "mô hình Pinhole (Z=f*W/w_px) có thể tăng cự ly từ 12m lên 20m (+66.7%). "
            "Đây KHÔNG phải khoảng cách pipeline đo được trong 50 frame; "
            f"YOLO+ByteTrack+Kalman ghi Z trung bình sau che là {avg_z_occluded:.2f}m. "
            "Mức ảnh hưởng phụ thuộc bbox detector thực sự dự đoán."
        ),
        "kalman_mitigation_behavior": (
            f"Trong thực nghiệm pipeline: Cơ chế nghi ngờ (Rule of Suspicion) "
            f"{'đã kích hoạt' if len(uncertain_triggers) > 0 else 'chưa kích hoạt đủ nhạy'}. "
            f"Cơ chế có thể gán cờ is_uncertain khi phần dư vượt ngưỡng Mahalanobis, "
            f"nhưng chưa thể giả định che khuất tất yếu kích hoạt cờ."
        ),
        "unavoidable_physical_limitations": [
            "Camera đơn (Monocular Pinhole) không thể phân biệt giữa (1) xe kích thước bình thường bị che khuất một phần và (2) xe cỡ nhỏ (như xe kei car/xe mini) đang ở xa hơn.",
            "Muốn khắc phục triệt để bắt buộc phải có cảm biến độ sâu chủ động (Radar sóng milimet 77GHz hoặc Stereo Camera)."
        ]
    }

    with open("results/failure_case_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis_report, f, indent=2, ensure_ascii=False)
    print("Đã lưu kết quả phân tích ca lỗi thực tế vào results/failure_case_analysis.json")

    return analysis_report


if __name__ == "__main__":
    run_real_pipeline_failure_case()
