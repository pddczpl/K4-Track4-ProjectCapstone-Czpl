# BÁO CÁO TÁC ĐỘNG & ĐỘ HỮU ÍCH (IMPACT REPORT)
## Kịch bản Giả định: Trợ lý Giám sát Bám đuôi & Va chạm Đội xe Dịch vụ GSM (Xanh SM)

> [!CAUTION]
> **Tuyên bố Miễn trừ & Bản quyền:**
> Báo cáo này là một nghiên cứu độc lập phục vụ đồ án Capstone Vin Perception Hackathon (Track 4). **Tác giả không đại diện, không sở hữu và không làm việc cho Công ty Cổ phần Di chuyển Xanh và Thông minh (GSM), VinFast hay Tập đoàn Vingroup.** Mọi số liệu tính toán dưới đây là **MÔ HÌNH ƯỚC LƯỢNG KỊCH BẢN GIẢ ĐỊNH**, không phải số liệu thống kê nội bộ hay cam kết kinh doanh.

---

### 1. Người dùng Cụ thể & Nỗi đau Thực tế

#### Người dùng chính (Primary Target User)
- **Nhân viên Giám sát & Quản trị Rủi ro Đội xe GSM (Fleet Safety & Risk Auditor):**
  + Nhiệm vụ: Hàng ngày/hàng tuần xem xét, đánh giá hồ sơ vận hành của đội xe taxi điện tại các thành phố lớn để phát hiện các tài xế có thói quen lái xe rủi ro (thường xuyên bám đuôi cự ly $< 8$m hoặc $TTC < 2.0$s ở tốc độ cao) nhằm lên danh sách đào tạo lại hoặc cảnh báo nội bộ.
  + Nỗi đau: Một đội xe hàng chục nghìn chiếc tạo ra hàng triệu giờ video hành trình mỗi ngày. Hiện tại không thể xem thủ công; đội an toàn chỉ xem lại video **sau khi sự cố va chạm đã xảy ra**.

#### Người dùng phụ (Secondary User)
- Tài xế taxi công nghệ / người lái xe dịch vụ cá nhân nhận cảnh báo thị giác/âm thanh thời gian thực trên màn hình buồng lái.

---

### 2. Mô hình Ước lượng Tác động Kinh tế (3 Kịch bản Giả định)

#### Công thức tính toán tác động hợp lý:
$$\Delta_{\text{va\_chạm}} = N_{\text{xe}} \times N_{\text{sự\_kiện\_bám\_đuôi/năm}} \times P(\text{va chạm} \mid \text{sự kiện}) \times Tỷ\_lệ\_ngăn\_ngừa$$
$$\text{Tiết kiệm sửa chữa} = \Delta_{\text{va\_chạm}} \times \text{Chi phí/vụ}$$
$$\text{Giảm ngày nằm xưởng} = \Delta_{\text{va\_chạm}} \times \text{Số ngày nằm xưởng/vụ}$$
$$\text{Doanh thu giữ lại} = \text{Giảm ngày nằm xưởng} \times \text{Doanh thu/ngày}$$
$$\text{Tổng giá trị thặng dư} = \text{Tiết kiệm sửa chữa} + \text{Doanh thu giữ lại}$$

#### Bảng thông số đầu vào và tình trạng nguồn kiểm chứng:

| Thông số | Kịch bản Thận trọng | Kịch bản Cơ sở (Base) | Kịch bản Lạc quan | Tình trạng Nguồn kiểm chứng |
| :--- | :---: | :---: | :---: | :--- |
| **Quy mô đội xe ô tô điện ($N_{\text{xe}}$)** | 10.000 xe | 30.000 xe | 50.000 xe | **CÓ NGUỒN:** Báo chí đưa tin quy mô toàn hệ thống Xanh SM đạt trên 100.000 xe (gồm ô tô & xe máy điện) trong giai đoạn 2024-2025 ([CafeF.vn](https://cafef.vn), [TuoiTre.vn](https://tuoitre.vn), truy cập 16/10/2026). Số lượng ô tô ước tính 30.000–50.000 xe. |
| **Sự kiện bám đuôi nguy hiểm / xe / năm** | 200 lần | 350 lần | 500 lần | **GIẢ ĐỊNH — chưa có nguồn kiểm chứng** (Ước lượng tài xế đô thị gặp 1–2 lần bám sát mỗi ngày làm việc). |
| **Xác suất va chạm khi bám đuôi sát ($P$)** | 0.00010 (0.010%) | 0.00015 (0.015%) | 0.00020 (0.020%) | **GIẢ ĐỊNH — chưa có nguồn kiểm chứng** (Trung bình 10.000 lần bám sát có 1.5 lần xảy ra va chạm quệt đuôi). |
| **Tỷ lệ cảnh báo ngăn ngừa được va chạm** | 15.0% | 25.0% | 35.0% | **GIẢ ĐỊNH — chưa có nguồn kiểm chứng** (Phụ thuộc thời gian phản xạ của tài xế khi nhận cảnh báo). |
| **Chi phí sửa chữa trung bình 1 vụ va chạm** | 15.0 triệu VNĐ | 20.0 triệu VNĐ | 25.0 triệu VNĐ | **GIẢ ĐỊNH — chưa có nguồn kiểm chứng** (Ước tính chi phí gò sơn cản sau, thay cảm biến/đèn hậu xe điện). |
| **Số ngày xe nằm xưởng sửa chữa / vụ** | 2.0 ngày | 3.0 ngày | 3.5 ngày | **GIẢ ĐỊNH — chưa có nguồn kiểm chứng** |
| **Doanh thu khai thác trung bình / xe / ngày** | 1.0 triệu VNĐ | 1.2 triệu VNĐ | 1.3 triệu VNĐ | **GIẢ ĐỊNH — chưa có nguồn kiểm chứng** |

---

### 3. Kết quả Tính toán Cụ thể (Sinh từ `eval/impact_calc.py`)

Dưới đây là kết quả tính toán tự động từ script `eval/impact_calc.py`:

```json
{
  "conservative": {
    "name": "Thận trọng (Conservative)",
    "num_vehicles": 10000,
    "tailgating_events_per_vehicle_year": 200,
    "prob_crash_given_event": 0.0001,
    "prevention_rate_percent": 15.0,
    "prevented_accidents_per_year": 30.0,
    "cost_per_crash_million_vnd": 15.0,
    "direct_repair_savings_billion_vnd": 0.45,
    "downtime_days_saved": 60.0,
    "downtime_revenue_saved_billion_vnd": 0.06,
    "total_benefit_billion_vnd": 0.51
  },
  "base": {
    "name": "Cơ sở (Base Case)",
    "num_vehicles": 30000,
    "tailgating_events_per_vehicle_year": 350,
    "prob_crash_given_event": 0.00015,
    "prevention_rate_percent": 25.0,
    "prevented_accidents_per_year": 393.7,
    "cost_per_crash_million_vnd": 20.0,
    "direct_repair_savings_billion_vnd": 7.87,
    "downtime_days_saved": 1181.2,
    "downtime_revenue_saved_billion_vnd": 1.42,
    "total_benefit_billion_vnd": 9.29
  },
  "optimistic": {
    "name": "Lạc quan (Optimistic)",
    "num_vehicles": 50000,
    "tailgating_events_per_vehicle_year": 500,
    "prob_crash_given_event": 0.0002,
    "prevention_rate_percent": 35.0,
    "prevented_accidents_per_year": 1750.0,
    "cost_per_crash_million_vnd": 25.0,
    "direct_repair_savings_billion_vnd": 43.75,
    "downtime_days_saved": 6125.0,
    "downtime_revenue_saved_billion_vnd": 7.96,
    "total_benefit_billion_vnd": 51.71
  }
}
```

#### Tóm lược kết quả 3 kịch bản:
1. **Kịch bản Thận trọng:** Giảm **30 vụ va chạm/năm**, tiết kiệm chi phí sửa chữa **0.45 tỷ VNĐ**, giảm 60 ngày xe nằm xưởng (**0.06 tỷ VNĐ** doanh thu), tổng giá trị **0.51 tỷ VNĐ/năm**.
2. **Kịch bản Cơ sở (Base Case khuyến nghị):** Giảm **~394 vụ va chạm/năm** trên 30.000 xe, tiết kiệm chi phí sửa chữa **7.87 tỷ VNĐ/năm**, giữ lại **1.42 tỷ VNĐ** từ 1.181 ngày công khai thác xe, tổng giá trị ước tính **~9.29 tỷ VNĐ/năm**.
3. **Kịch bản Lạc quan:** Giảm **1.750 vụ va chạm/năm**, tổng giá trị ước tính **51.71 tỷ VNĐ/năm**.

---

### 4. Rủi ro Triển khai Thực tế & Thách thức Kỹ thuật

1. **Báo động giả khi xe ở làn bên cạnh hoặc xe máy tạt đầu:**
   - Trong điều kiện giao thông đông đúc tại Việt Nam, xe máy liên tục điền vào khoảng trống hoặc xe làn bên di chuyển sát vạch. Nếu chỉ xét khoảng cách gần nhất, hệ thống sẽ phát cảnh báo liên tục gây ức chế cho tài xế. Cần giải pháp hành lang làn đường (ego-corridor) để giới hạn vùng cảnh báo.
2. **Khác biệt về hiệu chuẩn camera giữa các xe:**
   - Góc đặt camera dashcam gắn kính lái không cố định (tài xế tự dán lệch 3–5 độ, vị trí cao thấp khác nhau giữa VF5 và VF8). Sai lệch góc tilt 2 độ có thể làm đường chân trời lệch 25 pixel, phá vỡ ước lượng tiếp đất.
3. **Quyền riêng tư (Privacy & Data Protection):**
   - Video dashcam chứa khuôn mặt người đi đường, biển số xe khác và lộ trình cá nhân của hành khách. Nếu truyền video thô về server sẽ vi phạm nghiêm trọng quy định bảo vệ dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP). Giải pháp bắt buộc: chỉ xử lý on-device tại biên (edge compute) và chỉ gửi sự kiện telemetry dạng số ($Z$, TTC, thời điểm).
4. **Trách nhiệm pháp lý (Legal Liability):**
   - Đây chỉ là hệ thống hỗ trợ cảnh báo (Advisory Assistant), không can thiệp vào chân phanh tự động (AEB). Trách nhiệm điều khiển xe thuộc hoàn toàn về tài xế.
5. **Khoảng cách giữa Mô phỏng và Thực tế (Reality Gap):**
   - Bộ dữ liệu mô phỏng hiện tại dùng cùng mô hình Pinhole với thuật toán ước lượng. Do đó, các kết quả MAE trong phòng lab chưa chứng minh được độ chính xác khi ra đường thật có mưa bão, sương mù, mặt đường lồi lõm hoặc ban đêm ánh đèn pha lóa kính.
