# HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG DEMO (QUICKSTART GUIDE)
## VinFast Following-Distance & Collision-Time Assistant — GSM Fleet Safety

> [!TIP]
> **Chạy toàn bộ ứng dụng chỉ bằng 1 câu lệnh duy nhất:**
> ```bash
> streamlit run app/main.py
> ```

---

### 1. Cài đặt Môi trường (Nếu chạy lần đầu)
Mở PowerShell tại thư mục dự án:
```powershell
pip install -r requirements.txt
```

---

### 2. Các Lệnh Thực thi Chính

| Tác vụ | Lệnh thực thi | Mô tả kết quả |
| :--- | :--- | :--- |
| **Chạy Giao diện Demo Trực tiếp** | `streamlit run app/main.py` | Mở ứng dụng web tương tác tiếng Việt, chọn video có sẵn hoặc upload video bất kỳ do giám khảo đưa ra. |
| **Chạy Toàn bộ Unit Test** | `python -m pytest tests/` | Chạy 10 bài test kiểm chuẩn hình học Pinhole, lọc Kalman và pipeline (100% PASS). |
| **Sinh Video Mô phỏng Ground Truth** | `python sim/generate_sim.py` | Tạo `sim/synthetic_dashcam.mp4` và `sim/ground_truth.csv`. |
| **Chạy Đánh giá Đo lường Định lượng** | `python eval/evaluate.py` | So sánh Raw vs Kalman, xuất `results/metrics.json`, các biểu đồ `.png` và `results/demo_backup.mp4`. |
| **Tạo & Phân tích Ca lỗi có chủ đích** | `python eval/generate_failure_case.py` | Tạo ảnh đối sánh `results/failure_case.png` và file phân tích `results/failure_case_analysis.json`. |

---

### 3. Kịch bản Thao tác Demo Nhanh trước Ban Giám khảo (Trong 4 Phút)
1. **Bước 1:** Khởi chạy `streamlit run app/main.py`.
2. **Bước 2:** Trên thanh Sidebar bên trái:
   - Chọn nguồn video: *"🧪 Video Mô phỏng Kiểm chuẩn"* $\to$ Bấm **"▶️ Chạy Video"** để xem xe phanh gấp và mức cảnh báo chuyển sang Đỏ (NGUY HIỂM) khi $TTC < 2.0s$.
   - Bật/tắt toggle *"Bật Bộ lọc Kalman"* để cho Giám khảo thấy rõ tác dụng triệt tiêu nhiễu giật và dải bất định $\pm 1.96\sigma$.
3. **Bước 3:** Nhận video do Giám khảo đưa ra:
   - Chuyển sang nguồn *"📤 Tải lên Video bất kỳ"* $\to$ Tải tệp MP4 của Giám khảo $\to$ Bấm chạy và phân tích trực tiếp.
4. **Bước 4 (Dự phòng):** Nếu thiết bị gặp sự cố hiển thị, chọn nguồn *"📼 Video Dự phòng Render sẵn"* để chiếu ngay video `results/demo_backup.mp4` đã có đầy đủ telemetry HUD.

---

### 4. Cấu trúc Thư mục Dự án

```
├── app/
│   └── main.py                 # Ứng dụng Streamlit tiếng Việt
├── src/
│   ├── detect.py               # Trụ cột Học (YOLOv8n pretrained trên COCO)
│   ├── track.py                # Trụ cột Biểu diễn (ByteTrack & Fallback ID)
│   ├── geometry.py             # Trụ cột Hình học (Pinhole Model Z_w & Z_g, độ nhạy)
│   ├── kalman.py               # Trụ cột Bất định (Kalman Filter [Z, vZ], sigma, nghi ngờ)
│   ├── timing.py               # Trụ cột Thời gian (Đo trễ từng tầng, p50/p95, true dt)
│   └── pipeline.py             # Pipeline tổng hợp nhận thức và telemetry HUD
├── sim/
│   ├── generate_sim.py         # Sinh video mô phỏng + ground_truth.csv
│   ├── synthetic_dashcam.mp4   # Video mô phỏng xe VinFast
│   └── ground_truth.csv        # Dữ liệu chân lý mặt đất tuyệt đối
├── eval/
│   ├── evaluate.py             # Chạy benchmark Raw vs Kalman, xuất metrics & plots
│   └── generate_failure_case.py# Tạo và phân tích ca lỗi che khuất
├── data/
│   ├── sample_dashcam.mp4      # Clip dashcam thực tế đường cao tốc (MIT License)
│   └── vinfast_vfe34_rear.png  # Ảnh xe VinFast VF e34 (CC BY-SA 4.0)
├── results/
│   ├── metrics.json            # Bảng số đo MAE/RMSE theo 3 dải cự ly & độ trễ
│   ├── distance_comparison.png # Biểu đồ quỹ đạo Z(t) kèm dải tin cậy 95%
│   ├── error_by_range.png      # Biểu đồ sai số theo dải cự ly
│   ├── ttc_comparison.png      # Biểu đồ thời gian va chạm TTC
│   ├── latency_breakdown.png   # Phân rã độ trễ từng tầng (FPS: 46.5)
│   ├── failure_case.png        # Ảnh ca lỗi che khuất 40%
│   ├── failure_case_analysis.json # Phân tích nguyên nhân gốc & giới hạn
│   └── demo_backup.mp4         # Video dự phòng đã render đầy đủ HUD
├── tests/
│   ├── test_geometry.py        # Kiểm thử mô hình hình học Pinhole
│   ├── test_kalman.py          # Kiểm thử bộ lọc Kalman & quy tắc nghi ngờ
│   └── test_pipeline.py        # Kiểm thử tích hợp toàn bộ pipeline
├── requirements.txt            # Danh mục thư viện Python
├── IMPACT.md                   # Phân tích tác động kinh tế đội xe GSM (15.3 tỷ/năm)
├── PITCH.md                    # Kịch bản thuyết trình 10', 10 câu hỏi Q&A, checklist
├── DATA.md                     # Nguồn gốc dữ liệu & cam kết an toàn
└── README_DEMO.md              # Tài liệu khởi chạy nhanh này
```
