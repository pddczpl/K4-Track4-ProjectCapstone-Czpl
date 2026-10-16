"""Exercise a bundled video with the real Ultralytics + geometry + Kalman pipeline."""
from pathlib import Path

import cv2
import numpy as np

from src.pipeline import FollowingDistancePipeline

ROOT = Path(__file__).resolve().parents[1]


def test_real_pipeline_reads_bundled_sim_video():
    video = ROOT / "sim" / "synthetic_dashcam.mp4"
    assert video.is_file(), "Demo video must be included in the repository"
    cap = cv2.VideoCapture(str(video))
    try:
        assert cap.isOpened(), "OpenCV must be able to decode the bundled MP4 on the test runner"
        pipeline = FollowingDistancePipeline(hfov_deg=50.0, use_kalman=True, device="cpu")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        for i in range(3):
            ok, frame = cap.read()
            assert ok
            annotated, targets, stats = pipeline.process_frame(frame, timestamp_s=i / fps)
            assert annotated.shape == frame.shape
            assert isinstance(targets, list)
            assert np.isfinite(stats["latency_p50_ms"])
    finally:
        cap.release()
