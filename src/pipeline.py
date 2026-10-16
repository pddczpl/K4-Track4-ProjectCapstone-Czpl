"""
HỆ THỐNG PIPELINE TỔNG HỢP (Perception & Safety Pipeline)
=========================================================
Kết nối các trụ cột:
1. Học (YOLOv8)
2. Biểu diễn (ByteTrack ID & Box)
3. Hình học (Pinhole Model Z_w & Z_g, co giãn tiêu cự động theo độ phân giải)
4. Bất định (Kalman Filter [Z, vZ], sigma_Z, Rule of Suspicion)
5. Thời gian (Đo trễ từng tầng, p50/p95, true dt)

Cải tiến độ vững & logic an toàn:
- Co giãn tiêu cự f tự động khi độ phân giải video thay đổi (1280, 1920, 720p).
- Hành lang làn đường xe chủ (Ego-lane Corridor): Chỉ phát hiện xe dẫn đường trong hành lang,
  loại trừ xe làn bên, không fallback lấy xe gần nhất bất kỳ để tránh báo động giả.
- Tính toán TTC công bằng ở cả nhánh Kalman và nhánh đo thô (dùng sai phân có lọc trượt).
- Gom ngưỡng cảnh báo vào lớp AlertConfig có docstring cơ sở vật lý.
- Bộ ghi nhận sự kiện bám đuôi nguy hiểm (Tailgating Event Logger) xuất results/events.csv.
"""

from collections import deque
from dataclasses import dataclass
import os
import time
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
import pandas as pd

from src.geometry import PinholeGeometry, VEHICLE_CLASS_PRIORS
from src.kalman import MultiTargetKalmanManager
from src.timing import PipelineTiming
from src.track import VehicleTracker


@dataclass
class AlertConfig:
    """
    Cấu hình ngưỡng cảnh báo an toàn & cơ sở động học:
    - danger_ttc_s (2.0s): Thời gian phản xạ tài xế (0.8-1.2s) cộng trễ kích hoạt phanh (0.3s)
      cần tối thiểu ~1.8-2.0s để không đâm đuôi xe trước khi xe trước phanh khẩn cấp.
    - danger_dist_m (8.0m): Vùng đệm tối thiểu khi di chuyển ở dải tốc độ đô thị.
    - warning_ttc_s (3.5s): Ngưỡng cảnh báo sớm theo khuyến nghị ADAS Euro NCAP.
    - warning_dist_m (15.0m): Khoảng cách an toàn tiêu chuẩn trong lưu thông đô thị.
    - min_closing_speed_mps (-0.15 m/s ~ 0.5 km/h): Ngưỡng kích hoạt tiến lại gần (closing speed).
      Nếu xe đi cùng tốc độ hoặc đang giãn khoảng cách (vz >= -0.15), TTC = vô cực (an toàn).
    - min_event_duration_s (1.0s): Thời gian duy trì liên tục tối thiểu để xác nhận là 1 sự kiện bám đuôi nguy hiểm,
      loại trừ các trường hợp detector nhảy box trong 1-2 khung hình.
    """
    danger_ttc_s: float = 2.0
    danger_dist_m: float = 8.0
    warning_ttc_s: float = 3.5
    warning_dist_m: float = 15.0
    min_closing_speed_mps: float = -0.15
    min_event_duration_s: float = 1.0


def is_in_ego_corridor(
    box: Tuple[float, float, float, float],
    img_w: int,
    img_h: int,
    horizon_y: float,
    top_ratio: float = 0.16,
    bottom_ratio: float = 0.38
) -> bool:
    """
    Kiểm tra điểm tiếp đất của xe có nằm trong hành lang hình thang trước xe chủ hay không.
    Loại bỏ hoàn toàn các xe chạy ở làn bên trái / làn bên phải.
    """
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2.0
    y_contact = y2

    # Tỷ lệ từ đường chân trời xuống đáy ảnh [0, 1]
    scale = (y_contact - horizon_y) / max(1.0, (img_h - horizon_y))
    scale = np.clip(scale, 0.0, 1.0)

    half_w = img_w * (top_ratio + scale * (bottom_ratio - top_ratio))
    lane_center_x = img_w * 0.50

    return bool(abs(cx - lane_center_x) <= half_w)


class FollowingDistancePipeline:
    """Pipeline cảnh báo khoảng cách an toàn và thời gian va chạm cho xe VinFast."""
    def __init__(
        self,
        hfov_deg: float = 90.0,
        focal_length_px: Optional[float] = None,
        camera_height_m: float = 1.30,
        vehicle_width_m: float = 1.80,
        horizon_ratio: float = 0.50,
        confidence_threshold: float = 0.25,
        use_kalman: bool = True,
        alert_config: Optional[AlertConfig] = None,
        device: str = "cpu"
    ):
        self.use_kalman = use_kalman
        self.alert_config = alert_config if alert_config is not None else AlertConfig()
        self.timing = PipelineTiming()
        self.tracker = VehicleTracker(confidence_threshold=confidence_threshold, device=device)
        self.geometry = PinholeGeometry(
            hfov_deg=hfov_deg,
            camera_height_m=camera_height_m,
            horizon_ratio=horizon_ratio,
            focal_length_px=focal_length_px
        )
        self.kalman_manager = MultiTargetKalmanManager(
            focal_length_px=self.geometry.focal_length_px,
            vehicle_width_m=vehicle_width_m
        )
        self.history_records: List[Dict[str, Any]] = []

        # Bộ đệm để tính đạo hàm sai phân cho đo thô (để so sánh TTC công bằng)
        self._raw_history: Dict[int, deque] = {}

        # Bộ đếm và quản lý sự kiện bám đuôi nguy hiểm
        self.tailgating_events: List[Dict[str, Any]] = []
        self._current_event: Optional[Dict[str, Any]] = None

    def set_parameters(
        self,
        hfov_deg: Optional[float] = None,
        focal_length_px: Optional[float] = None,
        vehicle_width_m: Optional[float] = None,
        horizon_ratio: Optional[float] = None,
        use_kalman: Optional[bool] = None,
    ) -> None:
        if use_kalman is not None:
            self.use_kalman = use_kalman
        if horizon_ratio is not None:
            self.geometry.horizon_ratio = horizon_ratio
            self.geometry.horizon_y = self.geometry.image_height * horizon_ratio
        if focal_length_px is not None and focal_length_px > 0:
            self.geometry._fixed_focal_length_ref = float(focal_length_px)
            self.geometry.update_resolution(self.geometry.image_width, self.geometry.image_height)
            self.kalman_manager.focal_length_px = self.geometry.focal_length_px
        elif hfov_deg is not None:
            self.geometry.hfov_deg = hfov_deg
            self.geometry._fixed_focal_length_ref = None
            self.geometry.update_resolution(self.geometry.image_width, self.geometry.image_height)
            self.kalman_manager.focal_length_px = self.geometry.focal_length_px

        if vehicle_width_m is not None:
            self.kalman_manager.vehicle_width_m = vehicle_width_m

    def _estimate_raw_velocity_and_ttc(self, tid: int, z_raw: float, t_s: float) -> Tuple[float, float]:
        """Tính vận tốc tương đối và TTC cho nhánh đo thô bằng sai phân có làm mượt."""
        if tid not in self._raw_history:
            self._raw_history[tid] = deque(maxlen=5)

        dq = self._raw_history[tid]
        dq.append((t_s, z_raw))

        if len(dq) < 2:
            return 0.0, float("inf")

        # Lấy sai phân giữa đầu và cuối bộ đệm
        t_first, z_first = dq[0]
        t_last, z_last = dq[-1]
        dt = t_last - t_first
        if dt <= 0.001:
            return 0.0, float("inf")

        vz_raw = (z_last - z_first) / dt

        if vz_raw < self.alert_config.min_closing_speed_mps:
            ttc_raw = z_raw / (-vz_raw)
            if ttc_raw > 100.0:
                ttc_raw = float("inf")
        else:
            ttc_raw = float("inf")

        return float(vz_raw), float(ttc_raw)

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp_s: Optional[float] = None
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Xử lý 1 khung hình với đầy đủ logic kiểm tra hành lang và co giãn tiêu cự.
        """
        t_start = time.perf_counter()
        h, w = frame.shape[:2]

        # Cập nhật tiêu cự tự động theo kích thước khung hình thật
        self.geometry.update_resolution(w, h)
        self.kalman_manager.focal_length_px = self.geometry.focal_length_px

        t_curr = timestamp_s if timestamp_s is not None else time.perf_counter()
        dt = self.timing.update_timestamp(t_curr)

        # 1. Phát hiện & Theo dõi (ByteTrack)
        t_track_start = time.perf_counter()
        tracks = self.tracker.track(frame)
        t_track_end = time.perf_counter()
        self.timing.record_stage("track", (t_track_end - t_track_start) * 1000.0)

        # 2. Hình học & Kalman
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

            # Ước lượng khoảng cách thô Pinhole
            z_raw = self.geometry.estimate_distance_width(w_px, cls_name)
            z_ground = self.geometry.estimate_distance_ground(y2)

            # Kiểm tra xem xe có nằm trong hành lang làn đường trước xe chủ không
            in_corridor = is_in_ego_corridor(box, w, h, self.geometry.horizon_y)

            if self.use_kalman:
                z_est, vz_est, sigma_z, ttc, is_uncertain = self.kalman_manager.update_or_create(
                    track_id=tid,
                    z_measured=z_raw,
                    dt=dt,
                    class_name=cls_name
                )
            else:
                vz_est, ttc = self._estimate_raw_velocity_and_ttc(tid, z_raw, t_curr)
                z_est = z_raw
                sigma_z = 0.0
                is_uncertain = False

            # Phân loại mức cảnh báo an toàn dựa trên AlertConfig
            cfg = self.alert_config
            if is_uncertain:
                alert_level = "KHÔNG CHẮC CHẮN"
                alert_color = (180, 180, 180)  # Xám
            elif (ttc < cfg.danger_ttc_s and vz_est < cfg.min_closing_speed_mps) or (z_est < cfg.danger_dist_m):
                alert_level = "NGUY HIỂM"
                alert_color = (40, 40, 235)    # Đỏ (BGR)
            elif (ttc < cfg.warning_ttc_s and vz_est < cfg.min_closing_speed_mps) or (z_est < cfg.warning_dist_m):
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
                "is_in_corridor": in_corridor,
                "alert_level": alert_level,
                "alert_color": alert_color,
                "dt_s": dt,
                "timestamp_s": t_curr
            }
            frame_results.append(target_info)

            # CHỈ CHỌN XE DẪN ĐƯỜNG NẰM TRONG HÀNH LANG (EGO CORRIDOR)
            # TUYỆT ĐỐI KHÔNG FALLBACK LẤY XE LÀN BÊN
            if in_corridor and z_est < min_distance:
                min_distance = z_est
                primary_target = target_info

        if self.use_kalman:
            self.kalman_manager.mark_missed(active_track_ids)

        t_geom_end = time.perf_counter()
        self.timing.record_stage("geometry_kalman", (t_geom_end - t_geom_start) * 1000.0)

        # 3. Quản lý sự kiện bám đuôi nguy hiểm (Tailgating Event Tracking)
        self._update_tailgating_events(primary_target, t_curr)

        # 4. Render HUD trực quan
        t_rend_start = time.perf_counter()
        annotated_frame = self.render_hud(frame, frame_results, primary_target)
        t_rend_end = time.perf_counter()
        self.timing.record_stage("render", (t_rend_end - t_rend_start) * 1000.0)

        # Đo tổng thời gian
        t_total_ms = (time.perf_counter() - t_start) * 1000.0
        self.timing.record_total(t_total_ms)

        stats = self.timing.get_stats()
        stats["num_vehicles"] = len(frame_results)
        stats["primary_target"] = primary_target
        stats["total_dangerous_events"] = len(self.tailgating_events)

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

    def _update_tailgating_events(self, primary_target: Optional[Dict[str, Any]], t_curr: float) -> None:
        """Gộp các khung hình nguy hiểm liên tiếp thành 1 sự kiện bám đuôi."""
        cfg = self.alert_config
        is_danger = (primary_target is not None and primary_target["alert_level"] == "NGUY HIỂM")

        if is_danger:
            z = primary_target["z_est_m"]
            ttc = primary_target["ttc_s"]
            vz = primary_target["vz_est_kmh"]
            tid = primary_target["track_id"]

            if self._current_event is None:
                self._current_event = {
                    "event_id": len(self.tailgating_events) + 1,
                    "track_id": tid,
                    "start_time_s": round(t_curr, 2),
                    "end_time_s": round(t_curr, 2),
                    "duration_s": 0.0,
                    "min_z_m": round(z, 2),
                    "min_ttc_s": round(ttc, 2),
                    "max_closing_speed_kmh": round(abs(vz), 1),
                    "frame_count": 1
                }
            else:
                ev = self._current_event
                ev["end_time_s"] = round(t_curr, 2)
                ev["duration_s"] = round(t_curr - ev["start_time_s"], 2)
                ev["min_z_m"] = min(ev["min_z_m"], round(z, 2))
                ev["min_ttc_s"] = min(ev["min_ttc_s"], round(ttc, 2))
                ev["max_closing_speed_kmh"] = max(ev["max_closing_speed_kmh"], round(abs(vz), 1))
                ev["frame_count"] += 1
        else:
            if self._current_event is not None:
                ev = self._current_event
                if ev["duration_s"] >= cfg.min_event_duration_s or ev["frame_count"] >= 15:
                    self.tailgating_events.append(ev)
                self._current_event = None

    def export_events_csv(self, output_path: str = "results/events.csv") -> Optional[str]:
        """Xuất danh sách sự kiện bám đuôi nguy hiểm ra file CSV."""
        if not self.tailgating_events and self._current_event is not None:
            if self._current_event["duration_s"] >= self.alert_config.min_event_duration_s:
                self.tailgating_events.append(self._current_event)

        if not self.tailgating_events:
            return None

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_ev = pd.DataFrame(self.tailgating_events)
        df_ev.to_csv(output_path, index=False)
        return output_path

    def render_hud(
        self,
        frame: np.ndarray,
        targets: List[Dict[str, Any]],
        primary_target: Optional[Dict[str, Any]]
    ) -> np.ndarray:
        """Vẽ bounding box, hành lang ego-corridor, khoảng cách, TTC và thanh trạng thái."""
        out = frame.copy()
        h, w = out.shape[:2]

        # 1. Vẽ ranh giới hành lang Ego-lane Corridor mờ
        corridor_overlay = out.copy()
        hy = int(self.geometry.horizon_y)
        p1 = (int(w * (0.50 - 0.16)), hy)
        p2 = (int(w * (0.50 + 0.16)), hy)
        p3 = (int(w * (0.50 + 0.38)), h)
        p4 = (int(w * (0.50 - 0.38)), h)
        corridor_poly = np.array([p1, p2, p3, p4], np.int32)
        cv2.polylines(corridor_overlay, [corridor_poly], True, (0, 200, 255), 1, cv2.LINE_AA)
        cv2.addWeighted(corridor_overlay, 0.4, out, 0.6, 0, out)

        # 2. Vẽ các phương tiện
        for trk in targets:
            x1, y1, x2, y2 = map(int, trk["box"])
            is_pri = (primary_target is not None and trk["track_id"] == primary_target["track_id"])
            in_corridor = trk["is_in_corridor"]

            if not in_corridor:
                # Xe làn bên cạnh: vẽ màu xám trung tính, không cảnh báo
                cv2.rectangle(out, (x1, y1), (x2, y2), (130, 130, 130), 1)
                lbl = f"#{trk['track_id']} [LÀN BÊN]"
                cv2.putText(out, lbl, (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
                continue

            color = trk["alert_color"]
            thickness = 3 if is_pri else 2
            cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)

            z_text = f"Z: {trk['z_est_m']:.1f}m"
            if self.use_kalman and trk["sigma_z_m"] > 0:
                z_text += f" (±{1.96*trk['sigma_z_m']:.1f}m)"

            ttc_val = trk["ttc_s"]
            ttc_text = f"TTC: {ttc_val:.1f}s" if ttc_val < 30.0 else "TTC: --"
            label = f"#{trk['track_id']} {trk['class_name']} | {z_text} | {ttc_text}"

            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(out, (x1, max(0, y1 - 20)), (x1 + lw + 4, max(0, y1)), color, -1)
            cv2.putText(out, label, (x1 + 2, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            if is_pri:
                cv2.circle(out, (int((x1 + x2) / 2), y2), 5, color, -1)
                cv2.line(out, (int(w / 2), h - 10), (int((x1 + x2) / 2), y2), color, 2, cv2.LINE_AA)

        # 3. Top Banner HUD
        banner_h = 56
        overlay = out.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (20, 25, 35), -1)
        cv2.addWeighted(overlay, 0.85, out, 0.15, 0, out)

        cv2.putText(out, "VINFAST SAFETY ASSISTANT | GSM FLEET", (14, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        mode_str = "Kalman: ON [Z, vZ]" if self.use_kalman else "Kalman: OFF (Raw Diff)"
        cv2.putText(out, f"Mode: {mode_str} | f={self.geometry.focal_length_px:.0f}px | Res: {w}x{h}", (14, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 195, 225), 1, cv2.LINE_AA)

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
            no_target_str = "[AN TOÀN] Không có xe phía trước trong làn"
            (bw, bh), _ = cv2.getTextSize(no_target_str, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.putText(out, no_target_str, (w - bw - 20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 100), 1, cv2.LINE_AA)

        return out

    def reset(self) -> None:
        self.tracker.reset()
        self.kalman_manager.clear()
        self.history_records.clear()
        self._raw_history.clear()
        self.tailgating_events.clear()
        self._current_event = None
        self.timing = PipelineTiming()
