"""
ĐÁNH GIÁ ĐỘ BỀN VỮNG TRONG ĐIỀU KIỆN STRESS (Stress Benchmark)
=============================================================
Mục đích:
- Giải quyết triệt để vấn đề "đánh giá vòng tròn" (circular evaluation) của mô phỏng lý tưởng.
- Đưa vào 5 loại sai lệch thực tế giữa thế giới thực và giả định của mô hình:
  1. Sai lệch chiều rộng xe thật (W_true lệch so với prior 1.80m: 1.65m, 1.95m, xe tải 2.30m)
  2. Sai số hiệu chuẩn tiêu cự camera f (+5%, +10%)
  3. Dao động góc nhún xe / đường chân trời (pitch vibration +-15px)
  4. Nhiễu rung viền box của detector (+-3px) và rớt khung hình (1-3 frames drop)
  5. Hiện tượng che khuất nhẹ (15% bề rộng thân xe)
- Xuất:
  + results/metrics_stress.json
  + results/stress_benchmark.png
"""

import json
import math
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.geometry import PinholeGeometry
from src.kalman import VehicleKalmanFilter


def run_stress_benchmarks(random_seed: int = 42):
    np.random.seed(random_seed)
    os.makedirs("results", exist_ok=True)

    dt = 1.0 / 30.0
    num_frames = 300
    # Quỹ đạo Z thực tế từ 30m -> 6.5m -> 14.5m
    z_true = np.zeros(num_frames)
    for i in range(num_frames):
        t = i * dt
        if t < 3.0:
            z_true[i] = 30.0 - (10.0 / 3.0) * t
        elif t < 5.5:
            z_true[i] = 20.0 - (10.0 / 2.5) * (t - 3.0)
        elif t < 7.0:
            z_true[i] = 10.0 - (3.5 / 1.5) * (t - 5.5)
        elif t < 8.2:
            z_true[i] = 6.50
        else:
            z_true[i] = 6.50 + (8.0 / 1.8) * (t - 8.2)

    f_true = 1372.5
    w_assumed_car = 1.80

    scenarios = {
        "ideal_baseline": {
            "name": "Mô phỏng lý tưởng (Ideal)",
            "w_true": 1.80,
            "f_est": f_true,
            "box_jitter_sigma": 1.0,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.0
        },
        "stress_small_car_1.65m": {
            "name": "Xe cỡ nhỏ (W=1.65m vs prior 1.80m)",
            "w_true": 1.65,
            "f_est": f_true,
            "box_jitter_sigma": 1.5,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.0
        },
        "stress_large_suv_1.95m": {
            "name": "Xe SUV lớn (W=1.95m vs prior 1.80m)",
            "w_true": 1.95,
            "f_est": f_true,
            "box_jitter_sigma": 1.5,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.0
        },
        "stress_focal_error_plus5pct": {
            "name": "Sai lệch tiêu cự f (+5%)",
            "w_true": 1.80,
            "f_est": f_true * 1.05,
            "box_jitter_sigma": 1.5,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.0
        },
        "stress_focal_error_plus10pct": {
            "name": "Sai lệch tiêu cự f (+10%)",
            "w_true": 1.80,
            "f_est": f_true * 1.10,
            "box_jitter_sigma": 1.5,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.0
        },
        "stress_pitch_vibration_15px": {
            "name": "Nhún xe / rung kính lái (+-15px pitch)",
            "w_true": 1.80,
            "f_est": f_true,
            "box_jitter_sigma": 2.5,
            "pitch_shift_px": 15.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.0
        },
        "stress_detector_jitter_and_drops": {
            "name": "Nhiễu box detector (+-3px) & rớt 3% frames",
            "w_true": 1.80,
            "f_est": f_true,
            "box_jitter_sigma": 3.0,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.03,
            "occlusion_ratio": 0.0
        },
        "stress_mild_occlusion_15pct": {
            "name": "Che khuất nhẹ 15% bề rộng thân xe",
            "w_true": 1.80,
            "f_est": f_true,
            "box_jitter_sigma": 2.0,
            "pitch_shift_px": 0.0,
            "drop_rate": 0.0,
            "occlusion_ratio": 0.15
        }
    }

    benchmark_results = {}

    for s_key, s_cfg in scenarios.items():
        w_real = s_cfg["w_true"]
        f_est = s_cfg["f_est"]
        jitter = s_cfg["box_jitter_sigma"]
        drop_rate = s_cfg["drop_rate"]
        occl = s_cfg["occlusion_ratio"]

        geom = PinholeGeometry(focal_length_px=f_est)
        kf = VehicleKalmanFilter(initial_z=z_true[0], focal_length_px=f_est, vehicle_width_m=w_assumed_car)

        raw_errors = []
        kf_errors = []
        valid_frames = 0

        for i in range(num_frames):
            # Khung hình có bị rớt không
            if drop_rate > 0 and np.random.rand() < drop_rate:
                continue

            z_actual = z_true[i]
            # Chiều rộng pixel thực trên cảm biến
            w_px_true = (f_true * w_real) / z_actual
            # Áp dụng che khuất và nhiễu jitter detector
            w_px_observed = w_px_true * (1.0 - occl) + np.random.normal(0, jitter)
            w_px_observed = max(5.0, w_px_observed)

            # Ước lượng Pinhole dùng prior giả định (1.80m)
            z_raw = geom.estimate_distance_width(w_px_observed, class_name="car", custom_width_m=w_assumed_car)

            kf.predict(dt)
            z_kf, vz_kf, sig_kf = kf.update(z_raw)

            raw_errors.append(abs(z_raw - z_actual))
            kf_errors.append(abs(z_kf - z_actual))
            valid_frames += 1

        raw_mae = float(np.mean(raw_errors))
        kf_mae = float(np.mean(kf_errors))
        raw_rmse = float(np.sqrt(np.mean(np.array(raw_errors)**2)))
        kf_rmse = float(np.sqrt(np.mean(np.array(kf_errors)**2)))
        var_raw = float(np.var(raw_errors))
        var_kf = float(np.var(kf_errors))
        var_red = float(((var_raw - var_kf) / var_raw) * 100.0) if var_raw > 0 else 0.0

        benchmark_results[s_key] = {
            "name": s_cfg["name"],
            "valid_frames": valid_frames,
            "raw_mae_m": round(raw_mae, 3),
            "raw_rmse_m": round(raw_rmse, 3),
            "kalman_mae_m": round(kf_mae, 3),
            "kalman_rmse_m": round(kf_rmse, 3),
            "variance_reduction_percent": round(var_red, 1),
            "relative_error_percent": round(((kf_mae) / np.mean(z_true)) * 100.0, 1)
        }

    # Xuất file JSON
    out_json = "results/metrics_stress.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2, ensure_ascii=False)
    print(f"Đã lưu kết quả stress benchmark vào {out_json}")

    # Vẽ biểu đồ so sánh MAE giữa các điều kiện Stress
    names = [s["name"] for s in benchmark_results.values()]
    raw_vals = [s["raw_mae_m"] for s in benchmark_results.values()]
    kf_vals = [s["kalman_mae_m"] for s in benchmark_results.values()]

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    y_pos = np.arange(len(names))
    height = 0.35

    ax.barh(y_pos - height/2, raw_vals, height, label="Raw Pinhole MAE", color="#c83538", alpha=0.85)
    ax.barh(y_pos + height/2, kf_vals, height, label="Kalman Filter MAE", color="#2e548a", alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Sai số tuyệt đối trung bình MAE (mét)", fontsize=10)
    ax.set_title("Độ Bền Vững của Hệ Thống Dưới Các Sai Lệch Thực Tế (Stress Benchmark)", fontsize=12, fontweight="bold")
    ax.legend(loc="lower right")

    for i in range(len(names)):
        ax.text(raw_vals[i] + 0.05, i - height/2, f"{raw_vals[i]:.2f}m", va="center", fontsize=8)
        ax.text(kf_vals[i] + 0.05, i + height/2, f"{kf_vals[i]:.2f}m", va="center", fontsize=8)

    ax.set_xlim(0, max(max(raw_vals), max(kf_vals)) * 1.25)
    plt.tight_layout()
    fig.savefig("results/stress_benchmark.png")
    plt.close(fig)
    print("Đã tạo biểu đồ results/stress_benchmark.png")

    return benchmark_results


if __name__ == "__main__":
    run_stress_benchmarks()
