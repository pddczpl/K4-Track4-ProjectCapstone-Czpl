"""
HỆ THỐNG PIPELINE TỔNG HỢP (Perception & Safety Pipeline)
=========================================================
Kết nối các trụ cột:
1. Học (YOLOv8)
2. Biểu diễn (ByteTrack ID & Box)
3. Hình học (Pinhole Model Z_w & Z_g)
4. Bất định (Kalman Filter [Z, vZ], sigma_Z, Rule of Suspicion)
5. Thời gian (Đo trễ từng tầng, p50/p95, true dt)
"""

import time
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

from src.geometry import PinholeGeometry, VEHICLE_CLASS_PRIORS
from src.kalman import MultiTargetKalmanManager
from src.timing import PipelineTiming
from src.track import VehicleTracker


class FollowingDistancePipeline:
    """Pipeline cảnh báo khoảng cách an toàn và thời gian va chạm cho xe VinFast."""
    def __init__(
        self,
        hfov_deg: float = 90.0,
        focal_length_px: Optional[float] = None,
        camera_height_m: float = 1.30,
        vehicle_width_m: float = 1.80,
        confidence_threshold: float = 0.35,
        use_kalman: bool = True,
        device: str = "cpu"
    ):
        self.use_kalman = use_kalman
        self.timing = PipelineTiming()
        self.tracker = VehicleTracker(confidence_threshold=confidence_threshold, device=device)
        self.geometry = PinholeGeometry(
            hfov_deg=hfov_deg,
            camera_height_m=camera_height_m,
            focal_length_px=focal_length_px
        )
        self.kalman_manager = MultiTargetKalmanManager(
            focal_length_px=self.geometry.focal_length_px,
            vehicle_width_m=vehicle_width_m
        )
        self.history_records: List[Dict[str, Any]] = []

    def set_parameters(
        self,
        hfov_deg: Optional[float] = None,
        focal_length_px: Optional[float] = None,
        vehicle_width_m: Optional[float] = None,
        use_kalman: Optional[bool] = None,
    ) -> None:
        if use_kalman is not None:
            self.use_kalman = use_kalman
        if focal_length_px is not None and focal_length_px > 0:
            self.geometry.focal_length_px = float(focal_length_px)
            self.kalman_manager.focal_length_px = float(focal_length_px)
        elif hfov_deg is not None:
            self.geometry.hfov_deg = hfov_deg
            fl = self.geometry.calculate_focal_length(self.geometry.image_width, hfov_deg)
            self.geometry.focal_length_px = fl
            self.kalman_manager.focal_length_px = fl

        if vehicle_width_m is not None:
            self.kalman_manager.vehicle_width_m = vehicle_width_m

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp_s: Optional[float] = None
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Xử lý 1 khung hình:
        1. Đo timestamp & true dt
        2. Nhận diện & theo dõi (Detect + Track)
        3. Ước lượng hình học Pinhole
        4. Lọc Kalman & tính TTC, độ bất định
        5. Phân loại mức cảnh báo
        6. Render giao diện HUD
        """
        t_start = time.perf_counter()
        h, w = frame.shape[:2]
        self.geometry.image_width = w
        self.geometry.image_height = h
        self.geometry.horizon_y = h * 0.50

        # Cập nhật dt thực tế
        dt = self.timing.update_timestamp(timestamp_s)

        # Bước 1: Track (Detect + ByteTrack)
        t_track_start = time.perf_counter()
        tracks = self.tracker.track(frame)
        t_track_end = time.perf_counter()
        self.timing.record_stage("track", (t_track_end - t_track_start) * 1000.0)

        # Bước 2: Hình học & Kalman
        t_geom_start = time.perf_counter()
        if self.use_kalman:
            self.kalman_manager.predict_all(dt)

        active_track_ids = set()
        frame_results = []
        primary_target = None
        min_distance = 999.0

        for trk in tracks:
            tid = trk["track_id"]
            box = trk["box"]
            cls_name = trk["class_name"]
            active_track_ids.add(tid)

            x1, y1, x2, y2 = box
            w_px = max(1.0, x2 - x1)

            # Tính khoảng cách thô Pinhole
            z_raw = self.geometry.estimate_distance_width(w_px, cls_name)
            z_ground = self.geometry.estimate_distance_ground(y2)

            if self.use_kalman:
                z_est, vz_est, sigma_z, ttc, is_uncertain = self.kalman_manager.update_or_create(
                    track_id=tid,
                    z_measured=z_raw,
                    dt=dt,
                    class_name=cls_name
                )
            else:
                z_est = z_raw
                vz_est = 0.0
                sigma_z = 0.0
                ttc = float("inf")
                is_uncertain = False

            # Phân loại mức cảnh báo an toàn
            # 1. Nguy hiểm: TTC < 2.0s HOẶC khoảng cách Z < 8m (khi đang di chuyển)
            # 2. Chú ý: 2.0s <= TTC < 3.5s HOẶC 8m <= Z < 15m
            # 3. An toàn: TTC >= 3.5s VÀ Z >= 15m
            # 4. Nghi ngờ: khi is_uncertain = True (box nhảy, sigma_Z lớn)
            if is_uncertain:
                alert_level = "KHÔNG CHẮC CHẮN"
                alert_color = (180, 180, 180)  # Xám
            elif (ttc < 2.0 and vz_est < -0.2) or (z_est < 8.0):
                alert_level = "NGUY HIỂM"
                alert_color = (40, 40, 235)    # Đỏ (BGR)
            elif (ttc < 3.5 and vz_est < -0.2) or (z_est < 15.0):
                alert_level = "CHÚ Ý"
                alert_color = (0, 215, 255)    # Vàng cam (BGR)
            else:
                alert_level = "AN TOÀN"
                alert_color = (50, 205, 50)    # Xanh lục (BGR)

            target_info = {
                "track_id": tid,
                "class_name": cls_name,
                "box": box,
                "z_raw_m": z_raw,
                "z_est_m": z_est,
                "z_ground_m": z_ground,
                "vz_est_mps": vz_est,
                "vz_est_kmh": vz_est * 3.6,
                "sigma_z_m": sigma_z,
                "ttc_s": ttc,
                "is_uncertain": is_uncertain,
                "alert_level": alert_level,
                "alert_color": alert_color,
                "dt_s": dt,
                "timestamp_s": timestamp_s or time.perf_counter()
            }
            frame_results.append(target_info)

            # Chọn mục tiêu chính (xe ở gần nhất trong làn)
            box_center_x = (x1 + x2) / 2.0
            # Nằm trong vùng giữa khung hình (30% - 70% width)
            if 0.25 * w <= box_center_x <= 0.75 * w:
                if z_est < min_distance:
                    min_distance = z_est
                    primary_target = target_info

        if self.use_kalman:
            self.kalman_manager.mark_missed(active_track_ids)

        t_geom_end = time.perf_counter()
        self.timing.record_stage("geometry_kalman", (t_geom_end - t_geom_start) * 1000.0)

        # Nếu không có xe nào ở giữa làn, lấy xe gần nhất bất kỳ
        if primary_target is None and frame_results:
            primary_target = min(frame_results, key=lambda x: x["z_est_m"])

        # Bước 3: Render HUD trực quan
        t_rend_start = time.perf_counter()
        annotated_frame = self.render_hud(frame, frame_results, primary_target)
        t_rend_end = time.perf_counter()
        self.timing.record_stage("render", (t_rend_end - t_rend_start) * 1000.0)

        # Tổng thời gian
        t_total_ms = (time.perf_counter() - t_start) * 1000.0
        self.timing.record_total(t_total_ms)

        stats = self.timing.get_stats()
        stats["num_vehicles"] = len(frame_results)
        stats["primary_target"] = primary_target

        # Lưu lịch sử
        if primary_target:
            rec = {
                "frame": self.timing.frame_count,
                "timestamp_s": primary_target["timestamp_s"],
                "track_id": primary_target["track_id"],
                "z_raw_m": primary_target["z_raw_m"],
                "z_est_m": primary_target["z_est_m"],
                "vz_est_kmh": primary_target["vz_est_kmh"],
                "sigma_z_m": primary_target["sigma_z_m"],
                "ttc_s": primary_target["ttc_s"],
                "alert_level": primary_target["alert_level"],
                "is_uncertain": primary_target["is_uncertain"]
            }
            self.history_records.append(rec)

        return annotated_frame, frame_results, stats

    def render_hud(
        self,
        frame: np.ndarray,
        targets: List[Dict[str, Any]],
        primary_target: Optional[Dict[str, Any]]
    ) -> np.ndarray:
        """Vẽ bounding box, khoảng cách, dải sigma, TTC và thanh trạng thái lên ảnh."""
        out = frame.copy()
        h, w = out.shape[:2]

        # 1. Vẽ các phương tiện
        for trk in targets:
            x1, y1, x2, y2 = map(int, trk["box"])
            color = trk["alert_color"]
            is_pri = (primary_target is not None and trk["track_id"] == primary_target["track_id"])
            thickness = 3 if is_pri else 2

            # Bounding box
            cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)

            # Label nền mờ
            z_text = f"Z: {trk['z_est_m']:.1f}m"
            if self.use_kalman and trk["sigma_z_m"] > 0:
                z_text += f" (±{1.96*trk['sigma_z_m']:.1f}m)"

            ttc_val = trk["ttc_s"]
            ttc_text = f"TTC: {ttc_val:.1f}s" if ttc_val < 30.0 else "TTC: --"
            label = f"#{trk['track_id']} {trk['class_name']} | {z_text} | {ttc_text}"

            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x1, max(0, y1 - 22)), (x1 + lw + 6, max(0, y1)), color, -1)
            cv2.putText(out, label, (x1 + 3, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

            # Nếu là mục tiêu chính, vẽ thêm vạch ngắm khoảng cách
            if is_pri:
                cv2.circle(out, (int((x1 + x2) / 2), y2), 6, color, -1)
                cv2.line(out, (int(w / 2), h - 10), (int((x1 + x2) / 2), y2), color, 2, cv2.LINE_AA)

        # 2. Thanh thông báo HUD trên cùng (Top Banner)
        banner_h = 56
        overlay = out.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (20, 25, 35), -1)
        cv2.addWeighted(overlay, 0.85, out, 0.15, 0, out)

        # Tiêu đề bên trái
        cv2.putText(out, "VINFAST SAFETY ASSISTANT | GSM FLEET", (14, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        mode_str = "Kalman: ON [Z, vZ]" if self.use_kalman else "Kalman: OFF (Raw)"
        cv2.putText(out, f"Mode: {mode_str} | f={self.geometry.focal_length_px:.0f}px", (14, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 195, 225), 1, cv2.LINE_AA)

        # Trạng thái mục tiêu chính bên phải
        if primary_target:
            al = primary_target["alert_level"]
            col = primary_target["alert_color"]
            z_m = primary_target["z_est_m"]
            ttc_s = primary_target["ttc_s"]
            ttc_str = f"{ttc_s:.1f}s" if ttc_s < 30.0 else "--"

            alert_badge = f"[{al}] DIST: {z_m:.1f}m | TTC: {ttc_str}"
            (bw, bh), _ = cv2.getTextSize(alert_badge, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.rectangle(out, (w - bw - 24, 8), (w - 10, 48), col, -1)
            cv2.putText(out, alert_badge, (w - bw - 18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2, cv2.LINE_AA)
        else:
            no_target_str = "[AN TOÀN] Không có xe phía trước"
            (bw, bh), _ = cv2.getTextSize(no_target_str, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.putText(out, no_target_str, (w - bw - 20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 1, cv2.LINE_AA)

        return out

    def reset(self) -> None:
        self.tracker.reset()
        self.kalman_manager.clear()
        self.history_records.clear()
        self.timing = PipelineTiming()
