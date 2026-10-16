# DỮ LIỆU & NGUỒN GỐC PHÁP LÝ (DATA PROVENANCE & LICENSING)
## VinFast Following-Distance & Collision-Time Assistant

> [!IMPORTANT]
> **Cam kết an toàn dữ liệu (Data Ethics Compliance):** Toàn bộ dự án tuân thủ nghiêm ngặt quy định bảo mật:
> - KHÔNG sử dụng bất kỳ dữ liệu cá nhân nào của bệnh nhân, sinh viên, khách hàng hay tài xế ngoài đời thực.
> - Sử dụng clip lái xe công khai có giấy phép nguồn mở tương thích thương mại và dữ liệu mô phỏng tổng hợp (synthetic ground truth).

---

### 1. Dữ liệu Video Thực tế (Real Dashcam Video)

#### Tệp tin: `data/sample_dashcam.mp4`
- **Nguồn:** Dự án Mã nguồn mở Xe tự hành Udacity (Udacity Self-Driving Car Nanodegree Program - LaneLines P1).
- **Kho lưu trữ:** `https://github.com/udacity/CarND-LaneLines-P1/blob/master/test_videos/solidWhiteRight.mp4`
- **Giấy phép bản quyền (License):** MIT License (Tự do sử dụng, chỉnh sửa, phân phối trong nghiên cứu và thương mại).
- **Thông số kỹ thuật:**
  + Độ phân giải: $960 \times 540$ pixel
  + Tốc độ khung hình: $25.0$ FPS
  + Thời lượng: $8.8$ giây ($221$ khung hình)
  + Bối cảnh: Xe di chuyển trên đường cao tốc ban ngày, có xe con phía trước ở các cự ly biến thiên từ $11.9$m đến $42.3$m, vạch kẻ đường chuẩn và xe tải ở làn lân cận.
- **Mốc tham chiếu vật lý kiểm chứng ngoài đời (Real-world reference markers):**
  + Chiều dài vạch đứt trắng cao tốc: tiêu chuẩn quốc tế DOT/AASHTO là $10\text{ feet} \approx 3.05\text{m}$, khoảng cách giữa 2 vạch đứt là $30\text{ feet} \approx 9.14\text{m}$.
  + Chiều rộng xe con trung bình (sedan/SUV): $1.75\text{m} - 1.85\text{m}$ (trùng khớp giá trị giả định tiên nghiệm $W_{\text{real}} = 1.80\text{m}$).
  + Biển số xe tiêu chuẩn: $520 \times 110\text{ mm}$ (dài) hoặc $330 \times 165\text{ mm}$ (vuông).

---

### 2. Dữ liệu Hình ảnh Xe VinFast (VinFast Vehicle Template)

#### Tệp tin: `data/vinfast_vfe34_rear.png` & `sim/vinfast_sprite.png`
- **Tên tác phẩm:** *VinFast VFe34 rear view.png*
- **Tác giả:** Tuannh.286
- **Nguồn phát hành:** Wikimedia Commons (`https://commons.wikimedia.org/wiki/File:VinFast_VFe34_rear_view.png`)
- **Giấy phép bản quyền (License):** Creative Commons Attribution-Share Alike 4.0 International (CC BY-SA 4.0).
- **Thông số kích thước thực tế theo công bố nhà sản xuất VinFast:**
  + Mẫu xe: VinFast VF e34 (C-segment Electric Crossover)
  + Chiều rộng toàn bộ (Width): $1.768\text{m}$ (xấp xỉ $1.77\text{m}$)
  + Chiều cao toàn bộ (Height): $1.613\text{m}$
  + Chiều dài cơ sở (Wheelbase): $2.610\text{m}$
  + Trọng lượng không tải: $1.490\text{ kg}$

---

### 3. Dữ liệu Mô phỏng Tổng hợp Kiểm chuẩn (Synthetic Simulation Ground Truth)

#### Tệp tin: `sim/synthetic_dashcam.mp4` & `sim/ground_truth.csv`
- **Tạo bởi:** Thuật toán dựng hình toán học OpenCV thuần (`sim/generate_sim.py`).
- **Mục đích:** Cung cấp Ground Truth $Z(t)$ và $\text{TTC}(t)$ tuyệt đối chính xác để đo đạc sai số MAE / RMSE định lượng mà không bị sai lệch bởi lỗi gán nhãn thủ công (human annotation bias).
- **Cấu hình mô hình quang học:**
  + Độ phân giải: $1280 \times 720$ pixel, $30.0$ FPS, $300$ khung hình ($10.0$ giây).
  + Góc mở camera (HFOV): $50.0^\circ$ (cấu hình chuẩn cụm camera ADAS hướng trước của VinFast VF8 / VF9).
  + Tiêu cự tính toán: $f = \frac{1280 / 2}{\tan(25^\circ)} \approx 1372.5$ pixel.
  + Chiều cao đặt camera: $h_{\text{cam}} = 1.30\text{m}$ trên kính lái.
  + Đường chân trời: $y_{\text{horizon}} = 360$ pixel.
- **Các trường dữ liệu trong `ground_truth.csv`:**
  1. `frame`: Thứ tự khung hình ($0 \to 299$).
  2. `timestamp_s`: Thời điểm vật lý chính xác theo giây (bước nhảy $\Delta t = 0.0333$s).
  3. `z_true_m`: Khoảng cách dọc thực tế từ mặt phẳng camera tới đuôi xe mục tiêu (mét).
  4. `vz_true_mps`: Vận tốc tương đối dọc thực tế ($dZ/dt$, mét/giây).
  5. `ttc_true_s`: Thời gian va chạm lý thuyết ($Z / (-v_Z)$, giây).
  6. `gt_x1, gt_y1, gt_x2, gt_y2`: Tọa độ hộp bao bounding box pixel lý thuyết theo hình chiếu phối cảnh Pinhole.
  7. `gt_w_px, gt_h_px`: Chiều rộng và chiều cao pixel lý thuyết.

---

### 4. Quyền Riêng Tư & Xử Lý Dữ Liệu Bên Thứ Ba (Privacy & Anonymization)
- **Bản chất video đường phố (Dashcam):** Video ghi hình thực tế khi tham gia giao thông tiềm ẩn khả năng xuất hiện biển kiểm soát xe cơ giới và khuôn mặt người đi đường.
- **Hiện trạng trong tập dữ liệu thử nghiệm:**
  + Video `data/sample_dashcam.mp4` được trích từ tập dữ liệu nghiên cứu công khai của Udacity trên đường cao tốc nước ngoài; góc quay rộng, các phương tiện khác ở khoảng cách xa (>12m), không zoom cận cảnh danh tính cá nhân.
- **Biện pháp kỹ thuật bắt buộc khi triển khai thương mại (Nghị định 13/2023/NĐ-CP):**
  + Khi tích hợp trên đội xe GSM / Xanh SM thực tế tại Việt Nam, luồng video dashcam trước khi lưu trữ đám mây hoặc truyền về trung tâm điều hành bắt buộc phải đi qua module làm mờ tự động (auto-blurring) biển số và nhận diện khuôn mặt người tham gia giao thông.
  + Toàn bộ phép tính cự ly $Z$ và TTC được thực hiện hoàn toàn tại biên (Edge / On-device) trên frame bộ nhớ RAM mà không cần gửi hình ảnh thô chưa che giấu về máy chủ trung tâm.

---

### 5. Nguồn Gốc Bản Quyền Hình Ảnh Xe & Phương Án Dự Phòng (Vehicle Asset Rights)
- **Ảnh mẫu `data/vinfast_vfe34_rear.png`:**
  + Xuất xứ: Ảnh chụp đuôi xe VinFast VF e34 tại sự kiện công cộng, đăng tải trên Wikimedia Commons bởi tác giả `Tuannh.286` dưới giấy phép CC BY-SA 4.0.
  + Mục đích: Sử dụng trong nghiên cứu khoa học, mô phỏng thuật toán thị giác máy tính và giáo dục kỹ thuật (Fair Use / Academic Demonstration).
- **Rủi ro sở hữu trí tuệ thương hiệu (Trademark / Industrial Design):**
  + Kiểu dáng công nghiệp và logo chữ V của VinFast thuộc quyền sở hữu của Tập đoàn Vingroup / Công ty CP Sản xuất & Kinh doanh VinFast.
  + Trong môi trường sản xuất thương mại nếu không có thỏa thuận chính thức, hệ thống sẽ sử dụng sprite xe đồ họa vector trừu tượng tự dựng (`sim/car_template.png`, không chứa logo hoặc đường nét nhận diện nhãn hiệu độc quyền) để loại bỏ 100% rủi ro pháp lý.

