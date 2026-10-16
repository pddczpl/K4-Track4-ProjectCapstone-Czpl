import math
import numpy as np
import pytest
from src.kalman import VehicleKalmanFilter, MultiTargetKalmanManager


def test_kalman_ttc_calculation():
    kf = VehicleKalmanFilter(initial_z=20.0, initial_vz=-5.0)
    z_est, vz_est, sigma_z, ttc, is_uncertain = kf.get_state()
    # Z = 20, vz = -5 -> TTC = 20 / 5 = 4.0s
    assert math.isclose(ttc, 4.0, rel_tol=1e-2)

    # When moving away (vz > 0), TTC should be infinite
    kf.x[1, 0] = 2.0
    _, _, _, ttc_away, _ = kf.get_state()
    assert math.isinf(ttc_away)


def test_kalman_filters_noise():
    # Simulate true Z decreasing from 35m at 20 Hz (dt = 0.05s)
    np.random.seed(42)
    dt = 0.05
    true_vz = -3.0
    true_z = 35.0
    kf = VehicleKalmanFilter(initial_z=35.0, initial_vz=0.0)

    raw_errors = []
    kalman_errors = []

    for i in range(60):
        true_z += true_vz * dt
        z_measured = true_z + np.random.normal(0, 1.5)
        kf.predict(dt)
        z_est, vz_est, sigma_z = kf.update(z_measured)

        if i >= 20:  # After initial adaptation period
            raw_errors.append(abs(z_measured - true_z))
            kalman_errors.append(abs(z_est - true_z))

    mean_raw_err = np.mean(raw_errors)
    mean_kf_err = np.mean(kalman_errors)
    assert mean_kf_err < mean_raw_err, f"Kalman error {mean_kf_err} should be less than raw error {mean_raw_err}"



def test_rule_of_suspicion_on_outlier():
    # An abrupt 15m jump should trigger suspicion flag
    kf = VehicleKalmanFilter(initial_z=15.0)
    # Run a few steady steps
    for _ in range(5):
        kf.predict(0.033)
        kf.update(15.0)

    # Sudden outlier
    kf.predict(0.033)
    z_est, vz_est, sigma_z = kf.update(35.0)
    assert kf.is_uncertain is True, "Outlier jump should trigger suspicion"


def test_multi_target_manager():
    mgr = MultiTargetKalmanManager()
    dt = 0.033
    mgr.predict_all(dt)
    z1, v1, sig1, ttc1, unc1 = mgr.update_or_create(track_id=1, z_measured=25.0, dt=dt)
    z2, v2, sig2, ttc2, unc2 = mgr.update_or_create(track_id=2, z_measured=12.0, dt=dt)

    assert 1 in mgr.filters
    assert 2 in mgr.filters
    assert math.isclose(z1, 25.0, abs_tol=3.0)
    assert math.isclose(z2, 12.0, abs_tol=3.0)

    # Test track removal on missed frames
    for _ in range(20):
        mgr.mark_missed(active_track_ids={1})  # track 2 is missing
    assert 2 not in mgr.filters
    assert 1 in mgr.filters
