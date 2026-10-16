import math
import pytest
from src.geometry import PinholeGeometry, VEHICLE_CLASS_PRIORS


def test_focal_length_from_hfov():
    # 90 degrees HFOV, width = 1280
    # f = (1280 / 2) / tan(45 deg) = 640 / 1.0 = 640.0
    f = PinholeGeometry.calculate_focal_length(1280, 90.0)
    assert math.isclose(f, 640.0, rel_tol=1e-3)


def test_distance_width_calculation():
    # Given f = 640, W_real = 1.8m, w_px = 64 -> Z = 640 * 1.8 / 64 = 18.0m
    geom = PinholeGeometry(focal_length_px=640.0)
    z = geom.estimate_distance_width(box_w_px=64.0, class_name="car")
    assert math.isclose(z, 18.0, rel_tol=1e-3)

    # Truck with W_real = 2.5m, w_px = 100 -> Z = 640 * 2.5 / 100 = 16.0m
    z_truck = geom.estimate_distance_width(box_w_px=100.0, class_name="truck")
    assert math.isclose(z_truck, 16.0, rel_tol=1e-3)


def test_ground_distance_calculation():
    # Given f = 640, h_cam = 1.30m, horizon_y = 360, box_y_bottom = 400
    # delta_y = 400 - 360 = 40 px
    # Z = 640 * 1.30 / 40 = 20.8m
    geom = PinholeGeometry(image_height=720, horizon_ratio=0.5, camera_height_m=1.30, focal_length_px=640.0)
    z_g = geom.estimate_distance_ground(box_y_bottom_px=400.0)
    assert math.isclose(z_g, 20.8, rel_tol=1e-3)


def test_sensitivity_analysis():
    geom = PinholeGeometry(focal_length_px=640.0)
    res = geom.sensitivity_analysis(z=20.0, w_real=1.80, delta_w_real_percent=0.10)
    # 10% variation in width at 20m should produce ~ 2.0m variation
    assert math.isclose(res["error_due_to_width_prior_m"], 2.0, rel_tol=1e-2)
