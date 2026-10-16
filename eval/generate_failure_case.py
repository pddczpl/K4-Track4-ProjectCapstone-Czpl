"""
TẠO VÀ PHÂN TÍCH CA LỖI CÓ CHỦ ĐÍCH (Deliberate Failure Case Analysis)
====================================================================
Mục đích:
- Thực hiện bài kiểm tra "1 ca lỗi" bắt buộc theo tiêu chí Bằng chứng (10 điểm).
- Mô phỏng trường hợp hệ thống mắc sai số nghiêm trọng:
  Hiện tượng CHE KHUẤT MỘT PHẦN (Partial Occlusion) do dải phân cách / xe máy tạt đầu.
- Cơ chế gây lỗi:
  + Khoảng cách thực Z_true = 12.0m, kích thước xe W_real = 1.80m, f = 1372.5 px => w_px_true = 205 px.
  + Dải phân cách / xe máy che mất 40% thân xe phía bên trái => Bounding box phát hiện chỉ rộng w_px = 123 px.
  + Công thức Pinhole tính khoảng cách: Z_est = f * W_real / w_px = 1372.5 * 1.8 / 123 = 20.08m!
  + Sai số tuyệt đối: +8.08m (+67.4%).
  + Hậu quả an toàn: Xe thực tế đang ở cự ly nguy hiểm/chú ý (12m), nhưng hệ thống tưởng xe ở xa (20m, an toàn) => BỎ SÓT CẢNH BÁO.
- Cơ chế giảm thiểu của hệ thống:
  + Quy tắc Nghi ngờ (Rule of Suspicion) trong Kalman Filter: phát hiện residual Mahalanobis nhảy đột ngột,
    bật cờ `is_uncertain`, chuyển nhãn sang "KHÔNG CHẮC CHẮN", không phát tín hiệu an toàn giả tạo.
- Giới hạn của phương pháp:
  + Pinhole monocular giả định nhìn thấy trọn vẹn 100% bề rộng xe.
  + Không thể phân biệt được xe bị che khuất với xe nhỏ hơn nếu chỉ dùng 1 camera đơn không có cảm biến độ sâu (radar/LiDAR/stereo).
"""

import json
import os
import sys
import cv2
import matplotlib.pyplot as plt
import numpy as np

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def generate_failure_case_artifact():
    os.makedirs("results", exist_ok=True)

    # Dựng ảnh đối sánh
    h, w = 720, 1280
    frame_normal = np.zeros((h, w, 3), dtype=np.uint8)
    frame_occluded = np.zeros((h, w, 3), dtype=np.uint8)

    # Load car template
    template = cv2.imread("sim/car_template.png")
    aspect = template.shape[0] / template.shape[1]

    # Tham số
    f = 1372.5
    W_real = 1.80
    z_true = 12.0
    w_true_px = int(round(f * W_real / z_true))  # ~206 px
    h_true_px = int(round(w_true_px * aspect))   # ~124 px
    y_b = int(round(360 + f * 1.30 / z_true))    # ~508 px
    y_t = y_b - h_true_px
    x_c = 640
    x_l = x_c - w_true_px // 2

    # Vẽ nền đường
    for frame in [frame_normal, frame_occluded]:
        frame[:360, :] = 180
        frame[360:, :] = 65
        pts = np.array([[590, 360], [690, 360], [1150, 720], [130, 720]], np.int32)
        cv2.fillPoly(frame, [pts], (80, 80, 85))

    # Dán xe vào frame normal
    car_res = cv2.resize(template, (w_true_px, h_true_px))
    frame_normal[y_t:y_b, x_l:x_l+w_true_px] = car_res
    # Bounding box chuẩn (xanh lá)
    cv2.rectangle(frame_normal, (x_l, y_t), (x_l+w_true_px, y_b), (50, 205, 50), 3)
    cv2.putText(frame_normal, f"KHONG BI CHE KHUAT: w={w_true_px}px -> Z_est=12.0m [DUNG]", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 205, 50), 2, cv2.LINE_AA)

    # Frame occluded: dán xe, rồi vẽ chướng ngại vật che 40% bên trái
    frame_occluded[y_t:y_b, x_l:x_l+w_true_px] = car_res.copy()
    occlusion_w = int(w_true_px * 0.40)
    # Rào chắn che khuất
    barrier_pts = np.array([
        [x_l - 15, y_b + 20],
        [x_l + occlusion_w, y_t - 10],
        [x_l + occlusion_w + 10, y_b + 20]
    ], np.int32)
    cv2.fillPoly(frame_occluded, [barrier_pts], (20, 100, 220)) # Rào chắn màu cam

    # Box bị detector nhận diện thiếu (chỉ nhận phần nhìn thấy)
    detected_x1 = x_l + occlusion_w
    detected_w = w_true_px - occlusion_w
    detected_z = (f * W_real) / detected_w
    cv2.rectangle(frame_occluded, (detected_x1, y_t), (x_l+w_true_px, y_b), (40, 40, 235), 3)
    cv2.putText(frame_occluded, f"BI CHE KHUAT 40%: w_det={detected_w}px -> Z_est={detected_z:.1f}m [SAI +{detected_z-z_true:.1f}m!]",
                (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (40, 40, 235), 2, cv2.LINE_AA)

    # Ghép 2 ảnh cạnh nhau
    combined = np.hstack([frame_normal, frame_occluded])
    cv2.imwrite("results/failure_case.png", combined)

    # Lưu phân tích định lượng chi tiết
    analysis = {
        "failure_case_id": "ERR_01_PARTIAL_OCCLUSION",
        "description": "Hiện tượng che khuất một phần (Partial Occlusion) do rào chắn/xe máy dẫn đến sai số ước lượng khoảng cách pinhole nghiêm trọng.",
        "parameters": {
            "ground_truth_distance_m": z_true,
            "ground_truth_vehicle_width_m": W_real,
            "camera_focal_length_px": f,
            "true_bounding_box_width_px": w_true_px,
            "occlusion_ratio_percent": 40.0,
            "detected_bounding_box_width_px": detected_w,
            "estimated_distance_m": round(detected_z, 2),
            "absolute_error_m": round(detected_z - z_true, 2),
            "relative_error_percent": round(((detected_z - z_true) / z_true) * 100.0, 1)
        },
        "safety_risk": "Nguy cơ cao bỏ sót cảnh báo khoảng cách: Xe đang ở khoảng cách chú ý (12.0m) nhưng hệ thống ước lượng nhầm thành an toàn (20.1m).",
        "mitigation_mechanism": "Bộ lọc Kalman tích hợp Quy tắc Nghi ngờ (Rule of Suspicion): khi kích thước box sụt giảm đột biến >30% giữa 2 frame liên tiếp, Kalman gán cờ is_uncertain = True, chuyển cảnh báo sang 'KHÔNG CHẮC CHẮN' thay vì phát báo động an toàn giả tạo.",
        "system_limitations": [
            "Mô hình Pinhole đơn mắt (monocular) phụ thuộc chặt chẽ vào giả định nhìn thấy 100% viền bao quanh thân xe.",
            "Tại giao thông đô thị Việt Nam (tắc đường, xe máy lấn làn), tần suất che khuất có thể đạt 15-25% thời gian di chuyển.",
            "Đường mở rộng thực tế cần kết hợp camera stereo hoặc cảm biến Radar dải milimet (radar 77GHz của xe VinFast VF8) để đo độ sâu độc lập khi bị che khuất."
        ]
    }

    with open("results/failure_case_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print("Đã tạo ca lỗi có chủ đích: results/failure_case.png và results/failure_case_analysis.json")


if __name__ == "__main__":
    generate_failure_case_artifact()
