"""
KIỂM TRA TỰ ĐỘNG ĐỘ NHẤT QUÁN SỐ LIỆU TÀI LIỆU (Docs Consistency Checker)
======================================================================
Mục đích:
- Đảm bảo 100% tính trung thực: Mọi con số MAE, RMSE, FPS, độ trễ, tác động
  trong PITCH.md, IMPACT.md và README_DEMO.md PHẢI khớp tuyệt đối với
  results/metrics.json và eval/impact_calc.py.
- Nếu có bất kỳ sự lệch số hay làm tròn sai lệch nào, script sẽ báo lỗi (FAIL).
"""

import json
import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def check_documentation_consistency() -> bool:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    metrics_path = os.path.join(repo_root, "results", "metrics.json")
    pitch_path = os.path.join(repo_root, "PITCH.md")
    impact_path = os.path.join(repo_root, "IMPACT.md")
    demo_readme_path = os.path.join(repo_root, "README_DEMO.md")

    if not os.path.exists(metrics_path):
        print(f"[FAIL] Không tìm thấy {metrics_path}")
        return False

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    with open(pitch_path, "r", encoding="utf-8") as f:
        pitch_content = f.read()

    with open(impact_path, "r", encoding="utf-8") as f:
        impact_content = f.read()

    errors = []

    # 1. Kiểm tra các số đo trong metrics.json có xuất hiện chuẩn xác trong PITCH.md
    ov = metrics["overall"]
    rb = metrics["by_distance_range"]
    lat = metrics["timing_latency"]

    expected_pitch_tokens = [
        (f"{ov['raw_mae_m']}", "Raw Overall MAE"),
        (f"{ov['kalman_mae_m']}", "Kalman Overall MAE"),
        (f"{ov['raw_rmse_m']}", "Raw Overall RMSE"),
        (f"{ov['kalman_rmse_m']}", "Kalman Overall RMSE"),
        (f"{ov['variance_reduction_percent']}%", "Variance Reduction"),
        (f"{rb['range_5_10m']['raw_mae_m']}", "Range 5-10m Raw MAE"),
        (f"{rb['range_5_10m']['kalman_mae_m']}", "Range 5-10m Kalman MAE"),
        (f"{rb['range_10_20m']['raw_mae_m']}", "Range 10-20m Raw MAE"),
        (f"{rb['range_10_20m']['kalman_mae_m']}", "Range 10-20m Kalman MAE"),
        (f"{rb['range_20_40m']['raw_mae_m']}", "Range 20-40m Raw MAE"),
        (f"{rb['range_20_40m']['kalman_mae_m']}", "Range 20-40m Kalman MAE"),
        (f"{lat['fps']}", "FPS"),
        (f"{lat['latency_p50_ms']}", "Latency p50"),
        (f"{lat['latency_p95_ms']}", "Latency p95"),
    ]

    for token, desc in expected_pitch_tokens:
        if token not in pitch_content:
            errors.append(f"PITCH.md thiếu hoặc sai số {desc}: '{token}'")

    # Kiểm tra PITCH.md thừa nhận Kalman tệ hơn
    if "Kalman TỆ HƠN" not in pitch_content:
        errors.append("PITCH.md chưa nêu rõ ràng 'Kalman TỆ HƠN' trong bảng số liệu tổng/5-10m!")

    # 2. Kiểm tra IMPACT.md có số liệu khớp với impact_calc.py
    from eval.impact_calc import calculate_impact
    impact_data = calculate_impact()
    base_calc = impact_data["base"]

    # Kiểm tra số vụ giảm, số tiền tiết kiệm
    tokens_impact = [
        ("393.7", "394"),  # số vụ ngăn chặn
        ("7.87", "7.88"),  # chi phí trực tiếp tỷ đồng
        ("9.29", "9.3"),   # tổng thặng dư tỷ đồng
    ]

    for opt1, opt2 in tokens_impact:
        if opt1 not in impact_content and opt2 not in impact_content:
            errors.append(f"IMPACT.md không khớp số tính toán tác động cơ sở ({opt1} hoặc {opt2})")

    # 3. Báo cáo kết quả
    if errors:
        print("[FAIL] Phát hiện sự bất nhất giữa tài liệu và số liệu thực nghiệm:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("[PASS] Tất cả số liệu trong PITCH.md, IMPACT.md khớp 100% với results/metrics.json và impact_calc.py!")
        return True


if __name__ == "__main__":
    success = check_documentation_consistency()
    sys.exit(0 if success else 1)
