# KỊCH BẢN THUYẾT TRÌNH 10 PHÚT & BẢO VỆ CAPSTONE (PITCH & Q&A)
## VinFast Following-Distance & Collision-Time Assistant — GSM Fleet Safety
**Track 4: Computer Vision & Robotics | Vin Perception Hackathon**

---

## I. Kịch bản Trình bày 10 Phút (Phân bổ Đúng Khung Giờ Đề bài)

```mermaid
gantt
    title Phân bổ 10 Phút Trình bày & Hỏi đáp
    dateFormat  mm:ss
    axisFormat  %M:%S
    1 phút: Bài toán Vin & Người dùng         :00:00, 01:00
    4 phút: Demo Trực tiếp & Nhận Video Đưa Ra:01:00, 05:00
    2 phút: 1 Số đo + 1 Ca lỗi + Trụ cột + Tác động :05:00, 07:00
    3 phút: Hội đồng Hỏi đáp (Q&A)            :07:00, 10:00
```

### 1. Phút 0:00 – 1:00: Bài toán Vin & Người dùng là ai (1 phút)
- **Lời mở đầu:**
  > *"Kính thưa Hội đồng Giám khảo, tôi xin giới thiệu **VinFast Following-Distance & Collision-Time Assistant** — hệ thống nhận thức thị giác máy tính hỗ trợ giám sát cự ly an toàn và thời gian va chạm dành riêng cho **đội xe taxi điện GSM (Xanh SM)** với hơn 35.000 xe VinFast."*
- **Nỗi đau cụ thể:**
  - Va chạm đuôi xe (rear-end crash) chiếm tới **30% tổng số vụ tai nạn taxi đô thị**. Hiện nay, đội ngũ kiểm tra an toàn GSM chỉ phát hiện ra hành vi bám đuôi sau khi đã xảy ra tai nạn đáng tiếc.
  - Các dòng xe phổ thông như VF5 Plus, VF e34 rất cần một giải pháp phần mềm thông minh, chạy trực tiếp trên vi xử lý camera hành trình sẵn có mà không phát sinh thêm chi phí phần cứng.
- **Đầu ra dùng được ngay:**
  - Nhận thức theo thời gian thực: Bounding Box + Cự ly khoảng cách $Z$ (m) kèm dải tin cậy $\pm 1.96\sigma$ + Vận tốc tương đối $v_Z$ + Thời gian va chạm TTC (s) + Phân loại cảnh báo tức thời: **AN TOÀN / CHÚ Ý / NGUY HIỂM / KHÔNG CHẮC CHẮN**.

---

### 2. Phút 1:00 – 5:00: Demo Trực tiếp trên Hệ thống Chạy thật (4 phút)
1. **Khởi động ứng dụng Streamlit trực tiếp:**
   - Chạy lệnh: `streamlit run app/main.py`.
   - Giới thiệu giao diện tiếng Việt được thiết kế chuyên biệt cho giám sát an toàn.
2. **Demo 1: Chạy trên Video Mô phỏng Kiểm chuẩn (Ground Truth Sim):**
   - Bấm ▶️ Chạy Video.
   - Chỉ cho Giám khảo thấy: Xe phía trước phanh gấp từ 30m giảm xuống 6.5m (vào vùng đỏ NGUY HIỂM vì TTC < 2.0s và cự ly sát).
   - Biểu đồ thời gian thực cập nhật mượt mà quỹ đạo $Z(t)$ so với Raw.
3. **Demo 2: Thao tác Bật/Tắt Kalman để so sánh trực quan:**
   - Khi tắt Kalman: Số đo khoảng cách bị rung giật (box jitter), vận tốc tương đối không ổn định.
   - Khi bật Kalman: Tín hiệu phẳng mịn, dải tin cậy $\pm 1.96\sigma$ ôm khít sai số thực tế, vận tốc $v_Z$ và TTC được tính toán mượt mà.
4. **Demo 3: Xử lý video do Giám khảo đưa ra tại chỗ (Tải lên file bất kỳ):**
   - Chuyển sang nguồn *"📤 Tải lên Video bất kỳ (Giám khảo)"*.
   - Nhận video từ USB hoặc tệp do Giám khảo cung cấp; hệ thống xử lý frame-by-frame ngay lập tức mà không gặp bất kỳ lỗi crash nào.
   *(Nếu xảy ra sự cố máy chiếu/kết nối, chuyển ngay sang nguồn 📼 Video Dự phòng Render sẵn `results/demo_backup.mp4` và giải thích minh bạch).*

---

### 3. Phút 5:00 – 7:00: Một Số đo, Một Ca lỗi, Trụ cột & Tác động (2 phút)
- **1 Số đo kiểm chứng được (`results/metrics.json`):**
  - Thực hiện trên 300 frames mô phỏng có ground truth toán học.
  - Tỷ lệ nhận diện đạt **100%**.
  - Sai số MAE khoảng cách:
    + Dải 5 – 10m (Nguy hiểm): **0.347m** (cự ly phanh chuẩn xác dưới 35cm).
    + Dải 10 – 20m (Chú ý): **0.434m** (Kalman cải thiện **10.6% MAE** so với Pinhole thô).
    + Dải 20 – 40m (Xa/An toàn): **1.355m**.
  - **Giảm phương sai nhiễu: 30.2%** nhờ bộ lọc Kalman.
  - Hiệu năng: Đạt **46.5 FPS** trên CPU laptop thường, độ trễ trung vị **p50 = 20.95ms**, **p95 = 25.5ms**.
- **1 Ca lỗi có chủ đích (`results/failure_case.png`):**
  - *Hiện tượng che khuất một phần (Partial Occlusion):* Khi xe máy hoặc dải phân cách che mất 40% bề rộng đuôi xe.
  - *Nguyên nhân:* Bounding box thu nhỏ từ 206px xuống 123px $\implies$ Công thức Pinhole ước lượng nhầm khoảng cách từ 12m thành **20.1m** (sai số $+67.4\%$).
  - *Hậu quả & Giảm thiểu:* Nguy cơ bỏ sót cảnh báo. Bộ lọc Kalman phát hiện kích thước nhảy bất thường qua kiểm định Mahalanobis, tự động bật cờ `is_uncertain`, chuyển cảnh báo sang **"KHÔNG CHẮC CHẮN / NGHI NGỜ"** chứ không báo an toàn giả tạo.
- **Tác động ước lượng cho GSM (`IMPACT.md`):**
  - Giảm thiểu ước tính **598 vụ va chạm đuôi xe / năm** trên toàn đội 35.000 xe GSM.
  - Tiết kiệm trực tiếp chi phí sửa chữa & bảo hiểm: **~13.1 tỷ VNĐ/năm** (~$526.000 USD).
  - Giảm 1.794 ngày xe nằm xưởng, giữ lại thêm **2.1 tỷ VNĐ** doanh thu khai thác.

---

### 4. Phút 7:00 – 10:00: Hội đồng Hỏi đáp (Q&A - 3 phút)
*(Xem 10 câu hỏi & đáp án chi tiết ở Mục II).*

---

## II. 10 Câu hỏi Giám khảo Thường hỏi & Đáp án Ngắn gọn, Trung thực

#### 1. Vì sao chọn mô hình Hình học Pinhole cổ điển thay vì mô hình Monocular Depth Estimation deep learning (như MiDaS, Depth Anything)?
> **Đáp án:**
> *"Mô hình Monocular Depth thuần deep learning xuất ra bản đồ độ sâu tương đối (relative depth), không có đơn vị vật lý mét chuẩn xác nếu không có scale factor. Ngoài ra, các model đó rất nặng (đòi hỏi GPU rời, độ trễ >80ms/khung), không thể chạy thời gian thực trên chip xe phổ thông. Ngược lại, mô hình Pinhole kết hợp kích thước vật lý chuẩn của xe VinFast cho ra khoảng cách mét tuyệt đối, tốc độ tính toán chỉ mất **0.06 ms**, hoàn toàn chạy mượt trên CPU."*

#### 2. Vì sao cần tự viết bộ lọc Kalman mà không dùng trung bình trượt (Moving Average)?
> **Đáp án:**
> *"Trung bình trượt gây ra độ trễ pha rất lớn (phase lag), đặc biệt nguy hiểm khi xe trước phanh gấp. Bộ lọc Kalman trạng thái $[Z, v_Z]^T$ dự đoán động lực học liên tục, vừa triệt tiêu nhiễu giật của bounding box (giảm 30.2% phương sai), vừa ước lượng được trực tiếp vận tốc tương đối $v_Z$ để tính TTC mà không làm đạo hàm số bị bùng nổ nhiễu."*

#### 3. Tiêu cự $f$ lấy ở đâu nếu Giám khảo đưa một video bất kỳ không biết thông số camera?
> **Đáp án:**
> *"Nếu có thông số FOV từ nhà sản xuất dashcam, ta tính $f = \frac{W}{2\tan(\text{HFOV}/2)}$. Nếu không biết trước, hệ thống cung cấp thanh trượt hiệu chuẩn nhanh trên giao diện (mặc định $f \approx 640$px cho 90° hoặc $1372$px cho camera ADAS VinFast 50°). Trong thực tế sản xuất của VinFast, camera trên kính lái là linh kiện cố định, tiêu cự được hiệu chuẩn một lần duy nhất tại nhà máy bằng bảng cờ (checkerboard target)."*

#### 4. Giả định bề rộng xe $W_{\text{real}} = 1.80$m có hợp lý không khi ngoài đường có nhiều loại xe khác nhau?
> **Đáp án:**
> *"Trong pipeline, chúng tôi không dùng một số cố định cho mọi xe mà phân loại theo mô hình học: xe con $1.80$m, xe tải $2.50$m, xe buýt $2.55$m, xe máy $0.80$m. Với xe con VinFast, kích thước dao động rất hẹp: VF5 là $1.72$m, VF e34 là $1.77$m, VF8 là $1.93$m (sai lệch $\le 7\%$). Phân tích độ nhạy của chúng tôi cho thấy sai lệch $7\%$ chiều rộng chỉ làm sai số khoảng cách $\pm 0.7$m ở cự ly 10m — hoàn toàn nằm trong dải dung sai an toàn."*

#### 5. Sai số thực tế của hệ thống là bao nhiêu và được đo đạc như thế nào?
> **Đáp án:**
> *"Vì không có ground truth cảm biến ngoài đời thực trong 2 giờ thi, chúng tôi đã xây dựng môi trường mô phỏng vật lý có Ground Truth toán học tuyệt đối. Kết quả đo được: ở cự ly nguy hiểm 5–10m, MAE đạt **0.347m**; ở cự ly 10–20m, MAE đạt **0.434m**; và dải 20–40m, MAE là **1.355m**. Sai số tăng dần theo bình phương khoảng cách đúng theo quy luật quang học Pinhole."*

#### 6. Giới hạn vật lý lớn nhất của hệ thống này là gì?
> **Đáp án:**
> *"Hệ thống giả định nhìn thấy trọn vẹn bề ngang xe. Khi xe bị che khuất một phần (như ca lỗi chúng tôi đã chỉ ra) hoặc khi xe rẽ góc xiên lớn (yaw angle $> 45^\circ$), ước lượng bề ngang sẽ bị sai lệch. Giới hạn thứ hai là tầm xa: ngoài 35m ở độ phân giải 720p, xe nhỏ hơn 45px khiến detector rớt nhịp."*

#### 7. Khi nào hệ thống sẽ nghi ngờ kết quả đo của chính nó?
> **Đáp án:**
> *"Hệ thống áp dụng **Quy tắc Nghi ngờ (Rule of Suspicion)**:
> 1. Khi độ bất định tương đối của Kalman $\sigma_Z / Z > 25\%$.
> 2. Khi khoảng cách Mahalanobis của phần dư đo đạc vượt ngưỡng 9.0 (tương đương 3 sigma).
> Khi đó hệ thống lập tức hạ mức cảnh báo xuống 'KHÔNG CHẮC CHẮN' để ngăn phanh gấp oan uổng."*

#### 8. Hệ thống có chạy được thời gian thực (real-time) trên phần cứng xe VinFast không?
> **Đáp án:**
> *"Có. Toàn bộ pipeline đạt **46.5 FPS** trên CPU Intel máy tính xách tay thông thường, tổng độ trễ p50 chỉ **20.95 ms** (trong đó YOLOv8n chiếm 19.8ms, hình học & Kalman chỉ chiếm 0.06ms). Trên chip buồng lái Snapdragon 8155 hoặc vi điều khiển ADAS của xe VinFast, hệ thống hoàn toàn chạy ở tần số chuẩn 30 Hz."*

#### 9. Nếu đường dốc hoặc xe bị nhún lắc khi phanh gấp thì phương án tiếp đất mặt đường ($Z_{\text{ground}}$) bị ảnh hưởng thế nào?
> **Đáp án:**
> *"Đó chính là lý do vì sao chúng tôi chọn Phương án A (Width Prior) làm bộ ước lượng chính thay vì Phương án B (Ground plane). Phương án tiếp đất phụ thuộc vào khoảng cách pixel tới đường chân trời $(y_{\text{bottom}} - y_{\text{horizon}})$. Khi xe nhún phanh (pitch), đường chân trời dao động khiến $Z_{\text{ground}}$ nhảy 5–15 mét. Phương án bề ngang $Z_{\text{width}}$ bất biến trước dao động pitch."*

#### 10. Làm thế nào để mở rộng hệ thống này lên xe tự hành cấp độ cao hơn trong tương lai?
> **Đáp án:**
> *"Trong giai đoạn tiếp theo, ta có thể kết hợp (sensor fusion) đầu ra thị giác này với cụm cảm biến Radar sóng milimet 77GHz có sẵn trên xe VinFast VF8 bằng thuật toán Extended Kalman Filter (EKF). Radar cung cấp cự ly dọc và vận tốc Doppler trực tiếp trong sương mù/mưa lớn, còn camera cung cấp nhận diện phân loại vật thể chính xác."*

---

## III. Bảng Kiểm Tra Checklist 9 Mục Đề Bài (Pre-Demo Verification)

| STT | Tiêu chí Checklist Đề bài | Trạng thái | Minh chứng nằm ở tệp tin nào |
| :---: | :--- | :---: | :--- |
| **1** | Demo chạy trên đúng máy sẽ dùng, xử lý được video tải lên | **ĐÃ HOÀN THÀNH** | `app/main.py` (chạy mượt trên Windows 11, hỗ trợ file upload trực tiếp). |
| **2** | Có video quay sẵn để dự phòng nếu demo trực tiếp hỏng | **ĐÃ HOÀN THÀNH** | `results/demo_backup.mp4` (video đã render sẵn đầy đủ HUD & telemetry). |
| **3** | Có một con số đo, và cả team nói được nó đo như thế nào | **ĐÃ HOÀN THÀNH** | `results/metrics.json` (MAE 0.35m dải 5-10m, giảm phương sai 30.2%, đo qua sim `eval/evaluate.py`). |
| **4** | Có ít nhất một ca lỗi, kèm lý do vì sao hệ thống sai | **ĐÃ HOÀN THÀNH** | `results/failure_case.png` & `results/failure_case_analysis.json` (che khuất 40% làm sai lệch +67.4%). |
| **5** | Chỉ ra được ít nhất 2 trụ cột và vị trí của chúng | **ĐÃ HOÀN THÀNH** | Chỉ rõ 5 trụ cột: `src/geometry.py`, `src/kalman.py`, `src/timing.py`, `src/detect.py`, `eval/evaluate.py`. |
| **6** | Không dùng dữ liệu thật của bệnh nhân hoặc sinh viên | **ĐÃ HOÀN THÀNH** | `DATA.md` (chỉ dùng clip Udacity MIT License và sim tổng hợp). |
| **7** | Mỗi thành viên trả lời được vì sao chọn cách làm này | **ĐÃ HOÀN THÀNH** | Phần Q&A 10 câu hỏi ở trên (lý giải Pinhole vs Monocular Depth, Kalman vs Moving Average). |
| **8** | Nói được người dùng là ai và họ được gì khi dùng sản phẩm | **ĐÃ HOÀN THÀNH** | `IMPACT.md` (Đội kiểm tra an toàn GSM & tài xế Xanh SM). |
| **9** | Có ước lượng tác động nếu triển khai ở Vin bằng con số | **ĐÃ HOÀN THÀNH** | `IMPACT.md` (Giảm 598 vụ tai nạn đuôi xe/năm, tiết kiệm 15.3 tỷ VNĐ/năm). |
