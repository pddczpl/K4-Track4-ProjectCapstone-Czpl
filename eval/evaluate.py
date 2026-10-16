"""
ĐÁNH GIÁ ĐỊNH LƯỢNG & ĐO LƯỜNG (Quantitative Evaluation & Benchmarking)
======================================================================
Mục đích:
- Thực hiện bài kiểm tra "1 số đo" bắt buộc theo tiêu chí Bằng chứng (10 điểm).
- Chạy đối đầu: KHÔNG LỌC (Raw Pinhole) vs CÓ LỌC (Kalman Filter).
- Đo MAE / RMSE khoảng cách theo từng dải cự ly thực tế:
  + Dải 5 - 10m (Vùng bám đuôi nguy hiểm / cận va chạm)
  + Dải 10 - 20m (Vùng khoảng cách trung bình / chú ý)
  + Dải 20 - 40m (Vùng khoảng cách xa / an toàn)
- Đo sai số TTC (Time-To-Collision) và độ trễ pipeline (mean, p50, p95, FPS).
- Xuất:
  + results/metrics.json
  + results/distance_comparison.png
  + results/error_by_range.png
  + results/ttc_comparison.png
  + results/latency_breakdown.png
  + results/demo_backup.mp4 (video đã render sẵn có HUD để dự phòng demo)
"""

import json
import os
import sys
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.pipeline import FollowingDistancePipeline


def run_pipeline_on_video(video_path: str, use_kalman: bool, hfov_deg: float = 50.0, record_video_out: str = None):
    pipeline = FollowingDistancePipeline(use_kalman=use_kalman, hfov_deg=hfov_deg, confidence_threshold=0.25)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = None
    if record_video_out:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(record_video_out, fourcc, fps, (w, h))

    records = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t_s = frame_idx / fps
        annotated, targets, stats = pipeline.process_frame(frame, timestamp_s=t_s)

        if writer is not None:
            writer.write(annotated)

        pri = stats.get("primary_target")
        if pri:
            records.append({
                "frame": frame_idx,
                "timestamp_s": t_s,
                "z_raw_m": pri["z_raw_m"],
                "z_est_m": pri["z_est_m"],
                "vz_est_mps": pri["vz_est_mps"],
                "sigma_z_m": pri["sigma_z_m"],
                "ttc_s": pri["ttc_s"],
                "alert_level": pri["alert_level"],
                "is_uncertain": pri["is_uncertain"]
            })
        else:
            records.append({
                "frame": frame_idx,
                "timestamp_s": t_s,
                "z_raw_m": np.nan,
                "z_est_m": np.nan,
                "vz_est_mps": np.nan,
                "sigma_z_m": np.nan,
                "ttc_s": np.nan,
                "alert_level": "UNKNOWN",
                "is_uncertain": True
            })

        frame_idx += 1

    cap.release()
    if writer is not None:
        writer.release()

    timing_stats = pipeline.timing.get_stats()
    return pd.DataFrame(records), timing_stats


def evaluate_simulation():
    os.makedirs("results", exist_ok=True)
    sim_video = "sim/synthetic_dashcam.mp4"
    gt_csv = "sim/ground_truth.csv"

    from sim.generate_sim import generate_synthetic_dataset
    print("1. Đang sinh lại dữ liệu mô phỏng với cấu hình VinFast ADAS Camera (HFOV=50 deg)...")
    generate_synthetic_dataset(output_video_path=sim_video, output_csv_path=gt_csv, hfov_deg=50.0)

    df_gt = pd.read_csv(gt_csv)

    print("2. Đang chạy pipeline CÓ LỌC (Kalman)...")
    backup_video_path = "results/demo_backup.mp4"
    df_kalman, timing_kalman = run_pipeline_on_video(sim_video, use_kalman=True, hfov_deg=50.0, record_video_out=backup_video_path)

    print("3. Đang chạy pipeline KHÔNG LỌC (Raw Pinhole)...")
    df_raw, timing_raw = run_pipeline_on_video(sim_video, use_kalman=False, hfov_deg=50.0)

    # Ghép dữ liệu đánh giá
    df_eval = pd.merge(df_gt, df_kalman, on="frame", suffixes=("_gt", "_kf"))
    df_eval = pd.merge(df_eval, df_raw[["frame", "z_raw_m"]], on="frame")

    # Loại bỏ các frame không detect được nếu có
    valid = df_eval.dropna(subset=["z_est_m", "z_raw_m_y"])
    valid = valid.rename(columns={"z_raw_m_y": "z_raw_val", "z_est_m": "z_kf_val"})

    z_true = valid["z_true_m"].values
    z_raw = valid["z_raw_val"].values
    z_kf = valid["z_kf_val"].values
    sigma_kf = valid["sigma_z_m"].values

    # Tính toán sai số
    err_raw = np.abs(z_raw - z_true)
    err_kf = np.abs(z_kf - z_true)

    # MAE & RMSE tổng
    mae_raw = float(np.mean(err_raw))
    rmse_raw = float(np.sqrt(np.mean((z_raw - z_true)**2)))

    mae_kf = float(np.mean(err_kf))
    rmse_kf = float(np.sqrt(np.mean((z_kf - z_true)**2)))

    # Phân dải khoảng cách: 5-10m, 10-20m, 20-40m
    range_bins = {
        "range_5_10m": (z_true >= 5.0) & (z_true < 10.0),
        "range_10_20m": (z_true >= 10.0) & (z_true < 20.0),
        "range_20_40m": (z_true >= 20.0) & (z_true <= 40.0),
    }

    metrics_by_range = {}
    for r_name, mask in range_bins.items():
        count = int(np.sum(mask))
        if count > 0:
            m_raw = err_raw[mask]
            m_kf = err_kf[mask]
            raw_m = float(np.mean(m_raw))
            kf_m = float(np.mean(m_kf))
            imp = float(((raw_m - kf_m) / raw_m) * 100.0) if raw_m > 0 else 0.0
            metrics_by_range[r_name] = {
                "num_samples": count,
                "raw_mae_m": round(raw_m, 3),
                "raw_rmse_m": round(float(np.sqrt(np.mean(m_raw**2))), 3),
                "kalman_mae_m": round(kf_m, 3),
                "kalman_rmse_m": round(float(np.sqrt(np.mean(m_kf**2))), 3),
                "mae_improvement_percent": round(imp, 1)
            }
        else:
            metrics_by_range[r_name] = {
                "num_samples": 0,
                "raw_mae_m": 0.0,
                "raw_rmse_m": 0.0,
                "kalman_mae_m": 0.0,
                "kalman_rmse_m": 0.0,
                "mae_improvement_percent": 0.0
            }

    # Đánh giá TTC trên các frame có vZ < -0.5 m/s
    ttc_mask = (valid["vz_true_mps"] < -0.5) & (valid["ttc_true_s"] < 20.0) & (valid["ttc_s"] < 30.0)
    if np.sum(ttc_mask) > 0:
        ttc_true = valid.loc[ttc_mask, "ttc_true_s"].values
        ttc_kf = valid.loc[ttc_mask, "ttc_s"].values
        ttc_mae = float(np.mean(np.abs(ttc_kf - ttc_true)))
        ttc_rmse = float(np.sqrt(np.mean((ttc_kf - ttc_true)**2)))
    else:
        ttc_mae, ttc_rmse = 0.0, 0.0

    # Tỉ lệ giảm phương sai (Variance Reduction)
    var_raw = float(np.var(z_raw - z_true))
    var_kf = float(np.var(z_kf - z_true))
    var_reduction_pct = float(((var_raw - var_kf) / var_raw) * 100.0) if var_raw > 0 else 0.0

    results = {
        "overall": {
            "total_frames_evaluated": len(valid),
            "detection_rate_percent": round((len(valid) / len(df_gt)) * 100.0, 1),
            "raw_mae_m": round(mae_raw, 3),
            "raw_rmse_m": round(rmse_raw, 3),
            "kalman_mae_m": round(mae_kf, 3),
            "kalman_rmse_m": round(rmse_kf, 3),
            "mae_improvement_percent": round(((mae_raw - mae_kf) / mae_raw) * 100.0, 1),
            "variance_reduction_percent": round(var_reduction_pct, 1),
            "ttc_mae_s": round(ttc_mae, 2),
            "ttc_rmse_s": round(ttc_rmse, 2),
        },
        "by_distance_range": metrics_by_range,
        "timing_latency": {
            "fps": round(timing_kalman["fps"], 1),
            "latency_mean_ms": round(timing_kalman["latency_mean_ms"], 2),
            "latency_p50_ms": round(timing_kalman["latency_p50_ms"], 2),
            "latency_p95_ms": round(timing_kalman["latency_p95_ms"], 2),
            "stage_breakdown_ms": {
                "track": round(timing_kalman.get("stage_track_mean_ms", 0.0), 2),
                "geometry_kalman": round(timing_kalman.get("stage_geometry_kalman_mean_ms", 0.0), 2),
                "render": round(timing_kalman.get("stage_render_mean_ms", 0.0), 2),
            }
        }
    }

    with open("results/metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Đã lưu kết quả đo lường: results/metrics.json")

    # VẼ CÁC BIỂU ĐỒ BẰNG CHỨNG
    # 1. Biểu đồ Z(t): Ground Truth vs Raw vs Kalman + Confidence ribbon
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    t_axis = valid["timestamp_s_gt"].values
    ax.plot(t_axis, z_true, "k--", label="Ground Truth Z (m)", linewidth=2.2)
    ax.plot(t_axis, z_raw, color="#c83538", alpha=0.45, label="Raw Pinhole (không lọc)", linewidth=1.2)
    ax.plot(t_axis, z_kf, color="#2e548a", label="Kalman Filtered [Z, vZ]", linewidth=2.0)
    ax.fill_between(
        t_axis,
        z_kf - 1.96 * sigma_kf,
        z_kf + 1.96 * sigma_kf,
        color="#2e548a",
        alpha=0.18,
        label="Dải bất định 95% (±1.96σ)"
    )
    ax.axhline(8.0, color="red", linestyle=":", alpha=0.7, label="Ngưỡng NGUY HIỂM (8m)")
    ax.axhline(15.0, color="orange", linestyle=":", alpha=0.7, label="Ngưỡng CHÚ Ý (15m)")
    ax.set_title("So sánh Khoảng cách: Ground Truth vs Không lọc vs Kalman Filter", fontsize=13, fontweight="bold")
    ax.set_xlabel("Thời gian (giây)", fontsize=11)
    ax.set_ylabel("Khoảng cách dọc Z (mét)", fontsize=11)
    ax.set_ylim(0, 35)
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    fig.savefig("results/distance_comparison.png")
    plt.close(fig)

    # 2. Biểu đồ Sai số MAE/RMSE theo từng dải cự ly
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ranges = ["5-10m\n(Nguy hiểm)", "10-20m\n(Chú ý)", "20-40m\n(Xa/An toàn)"]
    keys = ["range_5_10m", "range_10_20m", "range_20_40m"]
    raw_maes = [metrics_by_range.get(k, {}).get("raw_mae_m", 0.0) for k in keys]
    kf_maes = [metrics_by_range.get(k, {}).get("kalman_mae_m", 0.0) for k in keys]
    raw_rmses = [metrics_by_range.get(k, {}).get("raw_rmse_m", 0.0) for k in keys]
    kf_rmses = [metrics_by_range.get(k, {}).get("kalman_rmse_m", 0.0) for k in keys]

    x = np.arange(len(ranges))
    width = 0.20
    ax.bar(x - 1.5*width, raw_maes, width, label="Raw MAE", color="#f0777a")
    ax.bar(x - 0.5*width, kf_maes, width, label="Kalman MAE", color="#2e548a")
    ax.bar(x + 0.5*width, raw_rmses, width, label="Raw RMSE", color="#c83538")
    ax.bar(x + 1.5*width, kf_rmses, width, label="Kalman RMSE", color="#1a3355")

    ax.set_title("Sai số Ước lượng Khoảng cách theo Dải Cự ly (MAE & RMSE)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Sai số (mét)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(ranges, fontsize=10)
    ax.legend(loc="upper left")
    plt.tight_layout()
    fig.savefig("results/error_by_range.png")
    plt.close(fig)

    # 3. Biểu đồ TTC ước lượng trong pha phanh gấp
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    t_braking = valid.loc[ttc_mask, "timestamp_s_gt"].values
    ttc_gt_val = valid.loc[ttc_mask, "ttc_true_s"].values
    ttc_kf_val = valid.loc[ttc_mask, "ttc_s"].values
    if len(t_braking) > 0:
        ax.plot(t_braking, ttc_gt_val, "k--", label="TTC Ground Truth (s)", linewidth=2.0)
        ax.plot(t_braking, ttc_kf_val, color="#c83538", label="TTC ước lượng từ Kalman (s)", linewidth=1.8)
        ax.axhline(2.0, color="red", linestyle=":", label="Ngưỡng Va chạm Khẩn cấp (< 2.0s)")
        ax.set_title("Độ chính xác Ước lượng Thời gian Va chạm (TTC)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Thời gian (giây)", fontsize=10)
        ax.set_ylabel("TTC (giây)", fontsize=10)
        ax.set_ylim(0, 10)
        ax.legend(loc="upper right")
    plt.tight_layout()
    fig.savefig("results/ttc_comparison.png")
    plt.close(fig)

    # 4. Biểu đồ Phân rã độ trễ (Latency Breakdown)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    stages = ["Track (Detect+ByteTrack)", "Geometry & Kalman", "Render HUD"]
    latencies = [
        timing_kalman.get("stage_track_mean_ms", 0.0),
        timing_kalman.get("stage_geometry_kalman_mean_ms", 0.0),
        timing_kalman.get("stage_render_mean_ms", 0.0)
    ]
    colors = ["#2e548a", "#5fc79a", "#e8a838"]
    bars = ax.barh(stages, latencies, color=colors)
    ax.set_xlabel("Độ trễ trung bình (ms)", fontsize=10)
    ax.set_title(f"Phân rã Độ trễ Từng Tầng (Tổng p50: {timing_kalman['latency_p50_ms']:.1f}ms)", fontsize=11, fontweight="bold")
    for bar in bars:
        w_val = bar.get_width()
        ax.text(w_val + 0.3, bar.get_y() + bar.get_height()/2.0, f"{w_val:.1f} ms", va="center", fontsize=9)
    ax.set_xlim(0, max(latencies) * 1.25 + 2)
    plt.tight_layout()
    fig.savefig("results/latency_breakdown.png")
    plt.close(fig)

    print("Đã hoàn tất đánh giá và xuất kết quả vào results/")
    return results


if __name__ == "__main__":
    evaluate_simulation()
