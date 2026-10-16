"""
TÍNH TOÁN TÁC ĐỘNG ĐỘI XE THEO 3 KỊCH BẢN (Impact Calculator)
===========================================================
Công thức:
  Delta_accidents = N_vehicles * N_events_per_year * P_crash_given_event * P_prevention
  Direct_savings = Delta_accidents * Cost_per_crash
  Downtime_days = Delta_accidents * Days_downtime_per_crash
  Downtime_savings = Downtime_days * Revenue_per_day
  Total_benefit = Direct_savings + Downtime_savings
"""

import json
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


SCENARIOS = {
    "conservative": {
        "name": "Thận trọng (Conservative)",
        "num_vehicles": 10000,
        "tailgating_events_per_vehicle_year": 200,
        "prob_crash_given_event": 0.00010,  # 1 va chạm trên 10.000 lần bám đuôi sát
        "prevention_rate": 0.15,            # Cảnh báo giúp tài xế né được 15%
        "cost_per_crash_vnd": 15000000,     # 15 triệu VNĐ/vụ va chạm đuôi nhẹ
        "downtime_days_per_crash": 2.0,
        "revenue_per_day_vnd": 1000000,
    },
    "base": {
        "name": "Cơ sở (Base Case)",
        "num_vehicles": 30000,
        "tailgating_events_per_vehicle_year": 350,
        "prob_crash_given_event": 0.00015,  # 1.5 va chạm trên 10.000 lần
        "prevention_rate": 0.25,            # Cảnh báo giúp tài xế né được 25%
        "cost_per_crash_vnd": 20000000,     # 20 triệu VNĐ/vụ
        "downtime_days_per_crash": 3.0,
        "revenue_per_day_vnd": 1200000,
    },
    "optimistic": {
        "name": "Lạc quan (Optimistic)",
        "num_vehicles": 50000,
        "tailgating_events_per_vehicle_year": 500,
        "prob_crash_given_event": 0.00020,  # 2 va chạm trên 10.000 lần
        "prevention_rate": 0.35,            # Cảnh báo giúp tài xế né được 35%
        "cost_per_crash_vnd": 25000000,     # 25 triệu VNĐ/vụ
        "downtime_days_per_crash": 3.5,
        "revenue_per_day_vnd": 1300000,
    }
}


def calculate_impact():
    results = {}
    for key, sc in SCENARIOS.items():
        n_veh = sc["num_vehicles"]
        n_ev = sc["tailgating_events_per_vehicle_year"]
        p_crash = sc["prob_crash_given_event"]
        p_prev = sc["prevention_rate"]
        c_crash = sc["cost_per_crash_vnd"]
        d_down = sc["downtime_days_per_crash"]
        rev_day = sc["revenue_per_day_vnd"]

        # Số vụ va chạm đuôi xe giảm được
        prevented_accidents = n_veh * n_ev * p_crash * p_prev
        prevented_accidents_rounded = round(prevented_accidents, 1)

        # Tiết kiệm chi phí sửa chữa / bảo hiểm trực tiếp
        direct_savings_vnd = prevented_accidents * c_crash
        direct_savings_bil = direct_savings_vnd / 1e9

        # Ngày nằm xưởng tiết kiệm được
        downtime_days = prevented_accidents * d_down
        downtime_days_rounded = round(downtime_days, 1)

        # Doanh thu giữ lại từ việc giảm nằm xưởng
        downtime_savings_vnd = downtime_days * rev_day
        downtime_savings_bil = downtime_savings_vnd / 1e9

        # Tổng giá trị kinh tế ước tính
        total_benefit_vnd = direct_savings_vnd + downtime_savings_vnd
        total_benefit_bil = total_benefit_vnd / 1e9

        results[key] = {
            "name": sc["name"],
            "num_vehicles": n_veh,
            "tailgating_events_per_vehicle_year": n_ev,
            "prob_crash_given_event": p_crash,
            "prevention_rate_percent": round(p_prev * 100, 1),
            "prevented_accidents_per_year": prevented_accidents_rounded,
            "cost_per_crash_million_vnd": round(c_crash / 1e6, 1),
            "direct_repair_savings_billion_vnd": round(direct_savings_bil, 2),
            "downtime_days_saved": downtime_days_rounded,
            "downtime_revenue_saved_billion_vnd": round(downtime_savings_bil, 2),
            "total_benefit_billion_vnd": round(total_benefit_bil, 2)
        }

    return results


if __name__ == "__main__":
    res = calculate_impact()
    print(json.dumps(res, indent=2, ensure_ascii=False))
