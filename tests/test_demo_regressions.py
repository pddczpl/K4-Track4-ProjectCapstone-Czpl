"""Regression checks for the actual Streamlit controls and safety-assistant event logic."""
import ast
import inspect
import math
from pathlib import Path

import cv2
import numpy as np

from src.pipeline import FollowingDistancePipeline


ROOT = Path(__file__).resolve().parents[1]


class FakeTracker:
    def __init__(self, objects=None):
        self.objects = objects or []

    def track(self, frame):
        return list(self.objects)

    def reset(self):
        pass


def _make_pipeline(monkeypatch, **kwargs):
    monkeypatch.setattr("src.pipeline.VehicleTracker", lambda **unused: FakeTracker())
    return FollowingDistancePipeline(**kwargs)


def _dangerous_target(track_id=1):
    return {
        "track_id": track_id,
        "z_est_m": 6.0,
        "ttc_s": 1.5,
        "vz_est_kmh": -20.0,
        "alert_level": "NGUY HIỂM",
    }


def test_streamlit_constructor_matches_pipeline_signature():
    """Catch the exact error where app/main.py used kwargs absent from pipeline.__init__."""
    app = ast.parse((ROOT / "app/main.py").read_text(encoding="utf-8"))
    valid_kwargs = set(inspect.signature(FollowingDistancePipeline).parameters)
    constructor_calls = [
        node for node in ast.walk(app) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "FollowingDistancePipeline"
    ]
    assert constructor_calls
    for call in constructor_calls:
        used_kwargs = {kw.arg for kw in call.keywords}
        assert used_kwargs <= valid_kwargs, f"Unsupported Streamlit pipeline kwargs: {used_kwargs - valid_kwargs}"
    # Pipeline must own corridor drawing; the old app called a non-existent draw_ego_corridor().
    assert not any(isinstance(node, ast.Attribute) and node.attr == "draw_ego_corridor"
                   for node in ast.walk(app))


def test_car_width_setting_changes_distance(monkeypatch):
    pipe = _make_pipeline(monkeypatch, hfov_deg=90.0, use_kalman=False)
    pipe.tracker = FakeTracker([{
        "track_id": 1, "box": (590, 320, 690, 500),
        "class_name": "car", "confidence": 0.9,
    }])
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    _, objects, _ = pipe.process_frame(frame, timestamp_s=0.0)
    assert math.isclose(objects[0]["z_raw_m"], 11.52, abs_tol=0.01)
    pipe.set_parameters(vehicle_width_m=2.0)
    _, objects, _ = pipe.process_frame(frame, timestamp_s=0.033)
    assert math.isclose(objects[0]["z_raw_m"], 12.8, abs_tol=0.01)


def test_event_requires_real_elapsed_seconds(monkeypatch):
    pipe = _make_pipeline(monkeypatch)
    for frame in range(16):
        pipe._update_tailgating_events(_dangerous_target(), frame / 30)
    pipe._update_tailgating_events(None, 16 / 30)
    assert pipe.get_tailgating_events() == [], "16 frames (~0.5s) must not count as 1s tailgating"

    for frame in range(36):
        pipe._update_tailgating_events(_dangerous_target(), 3.0 + frame / 30)
    pipe._update_tailgating_events(None, 4.3)
    assert len(pipe.get_tailgating_events()) == 1
    assert pipe.get_tailgating_events()[0]["duration_s"] >= 1.0


def test_event_is_split_when_vehicle_identity_changes(monkeypatch):
    pipe = _make_pipeline(monkeypatch)
    for i in range(40):
        pipe._update_tailgating_events(_dangerous_target(1), i * 0.0333)
    for i in range(40):
        pipe._update_tailgating_events(_dangerous_target(2), 2.0 + i * 0.0333)
    pipe._update_tailgating_events(None, 4.0)
    events = pipe.get_tailgating_events()
    assert len(events) == 2
    assert [ev["track_id"] for ev in events] == [1, 2]


def test_export_does_not_reuse_old_event_file(monkeypatch, tmp_path):
    pipe = _make_pipeline(monkeypatch)
    path = tmp_path / "events.csv"
    path.write_text("stale", encoding="utf-8")
    assert pipe.export_events_csv(str(path)) is None
    assert pipe.get_tailgating_events() == []


def test_streamlit_can_click_run_video_without_attribute_error(monkeypatch):
    """Run Streamlit's actual button flow with a 3-frame fake capture (no webcam required)."""
    from streamlit.testing.v1 import AppTest

    class FakeCapture:
        count = 0

        def __init__(self, source):
            self.count = 0

        def isOpened(self):
            return True

        def get(self, attr):
            if attr == cv2.CAP_PROP_FPS:
                return 30.0
            if attr == cv2.CAP_PROP_FRAME_COUNT:
                return 3
            return 0

        def read(self):
            if self.count >= 3:
                return False, None
            self.count += 1
            return True, np.zeros((720, 1280, 3), dtype=np.uint8)

        def release(self):
            pass

    class DemoPipeline:
        def __init__(self, **kwargs):
            assert "show_ego_corridor" in kwargs
            self.tailgating_events = []

        def process_frame(self, frame, timestamp_s=None):
            return frame, [], {
                "primary_target": None, "fps": 30.0, "latency_p50_ms": 33.3,
            }

        def get_tailgating_events(self):
            return []

        def export_events_csv(self, output_path):
            return None

    monkeypatch.setattr(cv2, "VideoCapture", FakeCapture)
    monkeypatch.setattr("src.pipeline.FollowingDistancePipeline", DemoPipeline)

    at = AppTest.from_file(str(ROOT / "app/main.py"), default_timeout=30).run()
    assert not at.exception
    at.sidebar.button[0].click().run()
    assert not at.exception, [exc.message for exc in at.exception]
    assert len(at.success) > 0
