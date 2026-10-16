"""
Trụ cột: HÌNH HỌC (Geometry)
===========================
Mục đích:
- Ước lượng khoảng cách vật lý Z (mét) từ camera đơn (monocular vision) dựa trên mô hình Pinhole Camera.
- Triển khai 2 phương án tính toán hình học:
  1. Phương án A (Width Prior): Z = f * W_real / w_px
     - Dựa trên chiều rộng chuẩn của xe theo phân loại COCO (car ~ 1.8m, truck ~ 2.5m, bus ~ 2.5m, motorcycle ~ 0.8m).
  2. Phương án B (Ground Plane / Vanishing Line): Z = f * h_cam / (y_bottom - y_horizon)
     - Dựa trên chiều cao lắp đặt camera h_cam (~1.3m) và vị trí điểm tiếp đất của bánh xe so với đường chân trời.
- So sánh 2 phương án & Lý do chọn:
  + Phương án B cực kỳ nhạy cảm với dao động nhún (pitch) của xe khi phanh/tăng tốc và địa hình mấp mô.
    Khi khoảng cách xa (Z > 25m), (y_bottom - y_horizon) chỉ còn vài pixel; sai số 1 pixel làm Z nhảy 5–15 mét!
  + Phương án A ổn định hơn nhiều trước dao động cao độ và góc dốc của mặt đường.
  + Quyết định thiết kế: Chọn Phương án A làm bộ ước lượng chính, dùng Phương án B để kiểm tra tính hợp lý (sanity check).
- Hiệu chuẩn tiêu cự f:
  + Tính f từ trường nhìn ngang (HFOV): f = W_img / (2 * tan(HFOV / 2)).
  + Hỗ trợ cấu hình camera chuẩn VinFast VF8 / VF e34 (HFOV ~ 90°-120°).
- Phân tích độ nhạy (Sensitivity Analysis):
  + dZ / dW_real = Z / W_real
  + dZ / df = Z / f
  + dZ / dw_px = -Z / w_px
  => Sai số tương đối: delta_Z / Z = delta_f / f + delta_W / W - delta_w_px / w_px
"""

import math
from typing import Dict, Tuple, Optional


# Kích thước vật lý giả định trung bình theo lớp (mét)
VEHICLE_CLASS_PRIORS: Dict[str, float] = {
    "car": 1.80,         # Xe con VinFast VF5 (1.72m), VF e34 (1.77m), VF8 (1.93m) -> tb 1.80m
    "truck": 2.50,       # Xe tải chở hàng trung bình ~ 2.4 - 2.55m
    "bus": 2.55,         # Xe buýt đô thị / VinBus ~ 2.55m
    "motorcycle": 0.80,  # Xe máy / xe máy điện VinFast Feliz/Klara/Klara S ~ 0.75 - 0.80m
}


class PinholeGeometry:
    """Mô hình hình học Pinhole ước lượng khoảng cách và phân tích độ nhạy."""
    def __init__(
        self,
        image_width: int = 1280,
        image_height: int = 720,
        hfov_deg: float = 90.0,
        camera_height_m: float = 1.30,
        horizon_ratio: float = 0.50,
        focal_length_px: Optional[float] = None,
    ):
        self.image_width = image_width
        self.image_height = image_height
        self.hfov_deg = hfov_deg
        self.camera_height_m = camera_height_m
        self.horizon_y = image_height * horizon_ratio

        if focal_length_px is not None and focal_length_px > 0:
            self.focal_length_px = float(focal_length_px)
        else:
            self.focal_length_px = self.calculate_focal_length(image_width, hfov_deg)

    @staticmethod
    def calculate_focal_length(image_width: int, hfov_deg: float) -> float:
        """
        Tính tiêu cự f (pixel) từ độ rộng ảnh và Horizontal Field of View (HFOV).
        f = (W / 2) / tan(HFOV / 2)
        """
        half_fov_rad = math.radians(hfov_deg / 2.0)
        return float((image_width / 2.0) / math.tan(half_fov_rad))

    def estimate_distance_width(
        self,
        box_w_px: float,
        class_name: str = "car",
        custom_width_m: Optional[float] = None
    ) -> float:
        """
        Phương án A: Z = f * W_real / w_px
        """
        if box_w_px <= 1.0:
            return 100.0  # Tránh chia cho 0, khoảng cách coi như vô cực xa
        w_real = custom_width_m if custom_width_m is not None else VEHICLE_CLASS_PRIORS.get(class_name, 1.80)
        z = (self.focal_length_px * w_real) / box_w_px
        return max(0.5, float(z))

    def estimate_distance_ground(
        self,
        box_y_bottom_px: float,
    ) -> float:
        """
        Phương án B: Z = f * h_cam / (y_bottom - y_horizon)
        Áp dụng khi xe nằm trên mặt phẳng đường phía dưới đường chân trời.
        """
        delta_y = box_y_bottom_px - self.horizon_y
        if delta_y <= 2.0:
            return 100.0  # Gần hoặc vượt đường chân trời
        z = (self.focal_length_px * self.camera_height_m) / delta_y
        return max(0.5, float(z))

    def estimate_distance_hybrid(
        self,
        box: Tuple[float, float, float, float],
        class_name: str = "car",
        custom_width_m: Optional[float] = None
    ) -> Tuple[float, float, float]:
        """
        Tính cả 2 phương án và trả về (z_width, z_ground, z_chosen).
        z_chosen được chọn là z_width vì độ ổn định cao hơn,
        đồng thời tính độ lệch giữa 2 phương án.
        """
        x1, y1, x2, y2 = box
        w_px = max(1.0, x2 - x1)
        z_w = self.estimate_distance_width(w_px, class_name, custom_width_m)
        z_g = self.estimate_distance_ground(y2)
        return z_w, z_g, z_w

    def sensitivity_analysis(
        self,
        z: float,
        w_real: float,
        delta_w_real_percent: float = 0.10,
        delta_f_percent: float = 0.05,
        delta_box_px: float = 2.0,
        w_px: float = 80.0
    ) -> Dict[str, float]:
        """
        Phân tích độ nhạy của Z theo sai lệch tham số đầu vào.
        """
        dz_df = z / self.focal_length_px
        dz_dw_real = z / w_real
        dz_dw_px = -z / max(1.0, w_px)

        error_due_to_w = abs(dz_dw_real * (w_real * delta_w_real_percent))
        error_due_to_f = abs(dz_df * (self.focal_length_px * delta_f_percent))
        error_due_to_box = abs(dz_dw_px * delta_box_px)

        return {
            "Z_nominal_m": z,
            "error_due_to_width_prior_m": error_due_to_w,
            "error_due_to_focal_calib_m": error_due_to_f,
            "error_due_to_box_jitter_m": error_due_to_box,
            "total_estimated_sigma_m": math.sqrt(error_due_to_w**2 + error_due_to_f**2 + error_due_to_box**2)
        }
