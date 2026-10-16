import pytest
from eval.check_docs import check_documentation_consistency


def test_documentation_metrics_consistency():
    """Kiểm tra tự động: PITCH.md và IMPACT.md phải khớp 100% với metrics.json và impact_calc.py."""
    is_valid = check_documentation_consistency()
    assert is_valid is True, "Số liệu trong PITCH.md hoặc IMPACT.md không khớp với kết quả đo lường!"
