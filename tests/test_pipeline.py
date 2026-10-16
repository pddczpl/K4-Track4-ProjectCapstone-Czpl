import math
import cv2
import numpy as np
import pytest
from src.pipeline import FollowingDistancePipeline, is_in_ego_corridor, AlertConfig


def test_pipeline_smoke_test():
    pipeline = FollowingDistancePipeline(use_kalman=True)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    annotated, targets, stats = pipeline.process_frame(frame, timestamp_s=0.0)

    assert annotated.shape == (720, 1280, 3)
    assert isinstance(targets, list)
    assert "fps" in stats
    assert "latency_p50_ms" in stats
    assert "latency_p95_ms" in stats


def test_pipeline_parameter_update():
    pipeline = FollowingDistancePipeline(hfov_deg=90.0)
    assert round(pipeline.geometry.focal_length_px) == 640

    pipeline.set_parameters(hfov_deg=60.0)
    assert pipeline.geometry.focal_length_px > 640


def test_resolution_invariance_1280_vs_1920():
    """Kiểm tra tính bất biến độ phân giải: Cùng cảnh ở 1280x720 và 1920x1080 phải ra Z sai khác < 5%."""
    # Scene: HFOV = 90 deg, car width = 1.8m, distance = 15m
    # At 1280px: f1 = 640px -> w_px1 = 640 * 1.8 / 15 = 76.8 px
    # At 1920px: f2 = 960px -> w_px2 = 960 * 1.8 / 15 = 115.2 px
    pipe1280 = FollowingDistancePipeline(hfov_deg=90.0)
    pipe1920 = FollowingDistancePipeline(hfov_deg=90.0)

    frame1280 = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame1920 = np.zeros((1080, 1920, 3), dtype=np.uint8)

    pipe1280.geometry.update_resolution(1280, 720)
    pipe1920.geometry.update_resolution(1920, 1080)

    z1 = pipe1280.geometry.estimate_distance_width(box_w_px=76.8, class_name="car")
    z2 = pipe1920.geometry.estimate_distance_width(box_w_px=115.2, class_name="car")

    assert math.isclose(z1, 15.0, rel_tol=1e-3)
    assert math.isclose(z2, 15.0, rel_tol=1e-3)
    assert abs(z1 - z2) / z1 < 0.05, f"Z1 ({z1}) và Z2 ({z2}) phải sai khác < 5%"


def test_adjacent_lane_exclusion():
    """Xe ở làn bên cạnh (ngoài hành lang ego-corridor) không được chọn làm xe dẫn đường."""
    # Khung hình 1280x720, horizon = 360
    # Xe A: Nằm giữa làn (cx = 640, y2 = 500) -> Trong hành lang
    box_ego = (590, 420, 690, 500)
    assert is_in_ego_corridor(box_ego, 1280, 720, 360.0) is True

    # Xe B: Làn bên phải (x1 = 1000, x2 = 1120, cx = 1060, y2 = 500) -> Ngoài hành lang
    box_adj = (1000, 420, 1120, 500)
    assert is_in_ego_corridor(box_adj, 1280, 720, 360.0) is False


def test_ttc_guard_moving_away():
    """Khi xe phía trước giãn cự ly hoặc chạy cùng tốc độ (vz >= -0.15), TTC phải là vô cực."""
    pipeline = FollowingDistancePipeline(use_kalman=True)
    # Target tiến lại gần
    z1, v1, sig1, ttc_closing, _ = pipeline.kalman_manager.update_or_create(1, 15.0, 0.1)
    pipeline.kalman_manager.filters[1].x[1, 0] = -3.0  # closing speed 3 m/s
    _, _, _, ttc_c, _ = pipeline.kalman_manager.filters[1].get_state()
    assert ttc_c < 10.0

    # Target giãn ra (vz > 0)
    pipeline.kalman_manager.filters[1].x[1, 0] = 2.0  # moving away
    _, _, _, ttc_away, _ = pipeline.kalman_manager.filters[1].get_state()
    assert math.isinf(ttc_away)


def test_tailgating_event_logging():
    """Trạng thái NGUY HIỂM duy trì liên tục >= 1.0 giây phải ghi nhận một sự kiện bám đuôi."""
    pipeline = FollowingDistancePipeline(use_kalman=True)
    pipeline.alert_config.min_event_duration_s = 0.5  # 0.5s for fast test

    # Giả lập 20 khung hình ở trạng thái nguy hiểm (Z = 6.0m, dt = 0.033s -> ~0.66s)
    for i in range(25):
        t_s = i * 0.033
        target = {
            "track_id": 1,
            "z_est_m": 6.0,
            "ttc_s": 1.5,
            "vz_est_kmh": -20.0,
            "alert_level": "NGUY HIỂM"
        }
        pipeline._update_tailgating_events(target, t_s)

    # Khung hình kết thúc nguy hiểm
    pipeline._update_tailgating_events(None, 26 * 0.033)

    assert len(pipeline.tailgating_events) == 1
    ev = pipeline.tailgating_events[0]
    assert ev["min_z_m"] == 6.0
    assert ev["min_ttc_s"] == 1.5
    assert ev["duration_s"] >= 0.5
