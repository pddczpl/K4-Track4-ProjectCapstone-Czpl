"""
Trụ cột: BẤT ĐỊNH (Uncertainty)
=============================
Mục đích:
- Khắc phục hiện tượng nhiễu giật (bounding box jitter) và đo khoảng cách thô bị rung lắc giữa các frame.
- Tự viết bộ lọc Kalman (NumPy thuần) với trạng thái x = [Z, vZ]^T:
  + Z: Khoảng cách dọc (m)
  + vZ: Vận tốc tương đối dọc (m/s), vZ < 0 nghĩa là hai xe đang tiến lại gần nhau.
- Tính toán Thời gian va chạm: TTC = Z / (-vZ) (khi vZ < -0.1 m/s).
- Mô hình phương sai đo động R(Z):
  + Theo lý thuyết truyền sai số từ Pinhole: delta_Z = (Z^2 / (f * W)) * delta_w_px.
  + Do đó phương sai đo R không cố định mà tăng theo bậc 4 của khoảng cách Z!
  + Xe càng ở xa, Kalman càng ít tin vào phép đo tức thời, ưu tiên quán tính dự đoán.
- Xuất độ bất định sigma_Z = sqrt(P[0,0]) và dải tin cậy 95% [Z - 1.96*sigma, Z + 1.96*sigma].
- Quy tắc "Nghi ngờ" (Rule of Suspicion):
  + Khi sigma_Z quá lớn (sigma_Z / Z > 0.25) hoặc bước nhảy đo (residual) vượt ngưỡng chi-square (Mahalanobis gate),
    hệ thống hạ cấp cảnh báo xuống mức "KHÔNG CHẮC CHẮN / NGHI NGỜ", ngăn chặn phanh gấp oan uổng (false alarms).
"""

from typing import Dict, Optional, Tuple
import numpy as np


class VehicleKalmanFilter:
    """
    Bộ lọc Kalman tuyến tính 1D chuyển động liên tục cho khoảng cách Z và vận tốc tương đối vZ.
    State: x = [Z, vZ]^T
    """
    def __init__(
        self,
        initial_z: float,
        initial_vz: float = 0.0,
        process_noise_accel: float = 3.0,  # Gia tốc tương đối cực đại giả định (m/s^2)
        box_pixel_noise_sigma: float = 2.0, # Độ rung của box do detector (pixel)
        focal_length_px: float = 640.0,
        vehicle_width_m: float = 1.80,
    ):
        self.x = np.array([[float(initial_z)], [float(initial_vz)]], dtype=np.float64)
        # Ma trận hiệp phương sai ban đầu
        self.P = np.array([
            [4.0, 0.0],
            [0.0, 9.0]
        ], dtype=np.float64)

        self.q_var = process_noise_accel ** 2
        self.box_noise_sigma = box_pixel_noise_sigma
        self.focal_length_px = focal_length_px
        self.vehicle_width_m = vehicle_width_m

        self.H = np.array([[1.0, 0.0]], dtype=np.float64)
        self.last_residual: float = 0.0
        self.is_uncertain: bool = False
        self.age: int = 1
        self.missed_frames: int = 0

    def predict(self, dt: float) -> None:
        """
        Bước Dự đoán (Prediction step) với dt thực tế:
        x_pred = F * x
        P_pred = F * P * F^T + Q
        """
        dt = max(0.001, float(dt))
        F = np.array([
            [1.0, dt],
            [0.0, 1.0]
        ], dtype=np.float64)

        # Mô hình nhiễu quá trình Continuous White Noise Acceleration (CWNA)
        Q = np.array([
            [0.25 * (dt ** 4), 0.5 * (dt ** 3)],
            [0.5 * (dt ** 3), dt ** 2]
        ], dtype=np.float64) * self.q_var

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        self.age += 1

    def compute_measurement_noise(self, z_measured: float) -> float:
        """
        Tính phương sai đo động R(Z) dựa trên truyền sai số quang học Pinhole:
        sigma_Z = (Z^2 / (f * W_real)) * sigma_pixel
        """
        z_safe = max(1.0, z_measured)
        sigma_z_optical = (z_safe ** 2 / (self.focal_length_px * self.vehicle_width_m)) * self.box_noise_sigma
        # R tối thiểu 0.2 m^2 để tránh overconfident khi xe rất gần
        r_var = max(0.20, sigma_z_optical ** 2)
        return float(r_var)

    def update(self, z_measured: float) -> Tuple[float, float, float]:
        """
        Bước Cập nhật (Update step) với kiểm tra gating / quy tắc nghi ngờ.
        Trả về (Z_est, vZ_est, sigma_Z).
        """
        R_val = self.compute_measurement_noise(z_measured)
        R = np.array([[R_val]], dtype=np.float64)

        # Innovation / Residual: y = z - H * x
        y = np.array([[z_measured]], dtype=np.float64) - (self.H @ self.x)
        self.last_residual = float(y[0, 0])

        # Innovation covariance: S = H * P * H^T + R
        S = self.H @ self.P @ self.H.T + R
        S_inv = 1.0 / S[0, 0]

        # Mahalanobis distance squared (kiểm định chi-square 1 bậc tự do, ngưỡng 9.0 ~ 3 sigma)
        mahalanobis_sq = (self.last_residual ** 2) * S_inv
        if mahalanobis_sq > 9.0 and self.age > 3:
            # Đo đạc dị biệt (outlier) do che khuất hoặc detector nhảy box
            # Tăng nhiễu đo để giảm ảnh hưởng của outlier
            R *= 4.0
            S = self.H @ self.P @ self.H.T + R
            S_inv = 1.0 / S[0, 0]
            self.is_uncertain = True
        else:
            self.is_uncertain = False

        # Kalman gain: K = P * H^T * S^-1
        K = self.P @ self.H.T * S_inv

        # Trạng thái cập nhật: x = x + K * y
        self.x = self.x + K @ y

        # Cập nhật hiệp phương sai Joseph form: P = (I - K*H)*P*(I - K*H)^T + K*R*K^T để ổn định số
        I = np.eye(2, dtype=np.float64)
        IKH = I - K @ self.H
        self.P = IKH @ self.P @ IKH.T + K @ R @ K.T

        # Giữ Z vật lý luôn dương
        if self.x[0, 0] < 0.2:
            self.x[0, 0] = 0.2

        sigma_z = float(np.sqrt(max(0.001, self.P[0, 0])))
        rel_uncertainty = sigma_z / max(1.0, float(self.x[0, 0]))
        if rel_uncertainty > 0.25 or sigma_z > 3.5:
            self.is_uncertain = True

        self.missed_frames = 0
        return float(self.x[0, 0]), float(self.x[1, 0]), sigma_z

    def get_state(self) -> Tuple[float, float, float, float, bool]:
        """
        Trả về (Z_est, vZ_est, sigma_Z, TTC, is_uncertain).
        """
        z_est = float(self.x[0, 0])
        vz_est = float(self.x[1, 0])
        sigma_z = float(np.sqrt(max(0.001, self.P[0, 0])))

        # Tính TTC = Z / (-vZ)
        if vz_est < -0.15:  # Đang tiến lại gần (closing speed > 0.15 m/s ~ 0.5 km/h)
            ttc = z_est / (-vz_est)
        else:
            ttc = float("inf")

        return z_est, vz_est, sigma_z, ttc, self.is_uncertain


class MultiTargetKalmanManager:
    """Quản lý các bộ lọc Kalman theo ID theo dõi từ ByteTrack."""
    def __init__(
        self,
        focal_length_px: float = 640.0,
        vehicle_width_m: float = 1.80,
        max_missed_frames: int = 15,
    ):
        self.focal_length_px = focal_length_px
        self.vehicle_width_m = vehicle_width_m
        self.max_missed_frames = max_missed_frames
        self.filters: Dict[int, VehicleKalmanFilter] = {}

    def predict_all(self, dt: float) -> None:
        for kf in self.filters.values():
            kf.predict(dt)

    def update_or_create(
        self,
        track_id: int,
        z_measured: float,
        dt: float,
        class_name: str = "car",
        custom_width_m: Optional[float] = None
    ) -> Tuple[float, float, float, float, bool]:
        w_real = custom_width_m if custom_width_m is not None else self.vehicle_width_m

        if track_id not in self.filters:
            kf = VehicleKalmanFilter(
                initial_z=z_measured,
                initial_vz=0.0,
                focal_length_px=self.focal_length_px,
                vehicle_width_m=w_real,
            )
            self.filters[track_id] = kf
        else:
            kf = self.filters[track_id]
            kf.vehicle_width_m = w_real
            kf.focal_length_px = self.focal_length_px

        kf.update(z_measured)
        return kf.get_state()

    def mark_missed(self, active_track_ids: set) -> None:
        to_delete = []
        for tid, kf in self.filters.items():
            if tid not in active_track_ids:
                kf.missed_frames += 1
                if kf.missed_frames > self.max_missed_frames:
                    to_delete.append(tid)
        for tid in to_delete:
            del self.filters[tid]

    def clear(self) -> None:
        self.filters.clear()
