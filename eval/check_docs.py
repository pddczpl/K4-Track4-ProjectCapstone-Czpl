"""
Kiểm tra số liệu trong PITCH.md, IMPACT.md và dữ liệu thực nghiệm.
Kiểm tra theo ngữ cảnh ô bảng (không chỉ tìm chuỗi số rời rạc).
Không tuyên bố kiểm chứng tính đúng của bản thân phép đo.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.impact_calc import calculate_impact


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _numbers(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", text)]


def _assert_num(cell: str, expected: float, label: str, errors: list[str]) -> None:
    values = _numbers(cell)
    if len(values) != 1 or abs(values[0] - float(expected)) > 0.0001:
        errors.append(f"{label}: expected {expected}, found {cell!r}")


def check_documentation_consistency() -> bool:
    errors: list[str] = []
    try:
        metrics = json.loads(_read("results/metrics.json"))
        failure = json.loads(_read("results/failure_case_analysis.json"))
        pitch = _read("PITCH.md")
        impact = _read("IMPACT.md")
        guide = _read("README_DEMO.md")
    except (OSError, ValueError, KeyError) as exc:
        print(f"[FAIL] Missing or invalid documentation source: {exc}")
        return False

    ov = metrics["overall"]
    ranges = metrics["by_distance_range"]
    # Bảng đo trong PITCH.md phải có đúng sample count và từng ô MAE/RMSE.
    expected_rows = [
        ("Toàn bộ hành trình", ov["total_frames_evaluated"], ov),
        ("5 – 10m", ranges["range_5_10m"]["num_samples"], ranges["range_5_10m"]),
        ("10 – 20m", ranges["range_10_20m"]["num_samples"], ranges["range_10_20m"]),
        ("20 – 40m", ranges["range_20_40m"]["num_samples"], ranges["range_20_40m"]),
    ]
    lines = [line for line in pitch.splitlines() if line.strip().startswith("|")]
    for name, samples, expected in expected_rows:
        found = [line for line in lines if name in line]
        if len(found) != 1:
            errors.append(f"PITCH.md: expected one metrics table row for {name}, got {len(found)}")
            continue
        cells = [cell.strip().replace("**", "") for cell in found[0].split("|")[1:-1]]
        if len(cells) != 8:
            errors.append(f"PITCH.md row {name}: expected 8 cells, got {len(cells)}")
            continue
        for cell_index, expected_value, col_name in [
            (1, samples, "number of samples"),
            (2, ov["detection_rate_percent"], "detection rate"),
            (3, expected["raw_mae_m"], "raw MAE"),
            (4, expected["raw_rmse_m"], "raw RMSE"),
            (5, expected["kalman_mae_m"], "Kalman MAE"),
            (6, expected["kalman_rmse_m"], "Kalman RMSE"),
        ]:
            _assert_num(cells[cell_index], expected_value, f"{name}/{col_name}", errors)

    lat = metrics["timing_latency"]
    for value, pattern_label in [
        (lat["fps"], "FPS"),
        (lat["latency_p50_ms"], "p50"),
        (lat["latency_p95_ms"], "p95"),
        (ov["ttc_mae_s"], "TTC MAE"),
        (ov["ttc_rmse_s"], "TTC RMSE"),
    ]:
        number = str(value)
        if number not in pitch:
            errors.append(f"PITCH.md missing {pattern_label}={number}")

    # Những giá trị TTC trước đây không có file benchmark hỗ trợ.
    for unsupported in ["11.77", "7.47", "3.80"]:
        if unsupported in pitch:
            errors.append(f"PITCH.md still asserts unverified TTC result {unsupported}")

    # Phân biệt phép tính Pinhole giả định với quan sát thực từ YOLO.
    after = failure["pipeline_execution_results"]["average_estimated_z_after_occlusion_m"]
    if f"{after:.2f}m" not in pitch:
        errors.append(f"PITCH.md missing observed post-occlusion Z={after:.2f}m")
    if "phân tích độ nhạy" not in pitch.lower():
        errors.append("PITCH.md must distinguish occlusion sensitivity model from observed pipeline")

    # Bản JSON trong tài liệu IMPACT.md phải khớp từng field với hàm tính, không chỉ token rời.
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", impact)
    if not match:
        errors.append("IMPACT.md missing generated scenario JSON block")
    else:
        try:
            documented_impact = json.loads(match.group(1))
            calculated_impact = calculate_impact()
            if documented_impact != calculated_impact:
                errors.append("IMPACT.md scenario JSON differs from eval/impact_calc.py output")
            for scenario in calculated_impact.values():
                amount = str(scenario["total_benefit_billion_vnd"])
                if amount not in pitch:
                    errors.append(f"PITCH.md missing scenario impact total {amount} billion VND")
        except json.JSONDecodeError as exc:
            errors.append(f"IMPACT.md malformed scenario JSON: {exc}")

    if "GIẢ ĐỊNH" not in impact or "streamlit run app/main.py" not in guide:
        errors.append("Impact assumptions or demo command are missing")

    if errors:
        for err in errors:
            print("[FAIL]", err)
        return False
    print("[PASS] Checked PITCH.md metrics table, TTC claims, occlusion evidence, "
          "IMPACT.md scenario JSON and demo guide against source results.")
    return True


if __name__ == "__main__":
    sys.exit(0 if check_documentation_consistency() else 1)
