import numpy as np
import pytest
from src.pipeline import FollowingDistancePipeline


def test_pipeline_smoke_test():
    pipeline = FollowingDistancePipeline(use_kalman=True)
    # Create a synthetic 720p frame
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Process single frame
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
