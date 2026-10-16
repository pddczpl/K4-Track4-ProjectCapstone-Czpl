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
- **15 giây mở đầu bắt buộc (Tuyên bố minh bạch dữ liệu đầu vào):**
  > *"Kính thưa Hội đồng Giám khảo, trước khi bắt đầu, tôi xin nêu rõ: **toàn bộ đầu vào của buổi demo hôm nay là tệp video dashcam thực tế và video mô phỏng tổng hợp (sim replay) có phát lại, không kết nối trực tiếp với cảm biến vật lý trên xe thật**. Tôi xin giới thiệu đề tài: Trợ lý Giám sát Cự ly Bám đuôi & Thời gian Va chạm cho kịch bản đội xe taxi điện GSM (Xanh SM)."*
- **Người dùng mục tiêu cụ thể:**
  - **Người dùng chính:** Nhân viên phòng Vận hành & Giám sát An toàn Đội xe GSM (Fleet Safety Auditor) — cuối ca quét video hành trình để tự động phát hiện, chấm điểm các tài xế có tần suất bám đuôi nguy hiểm cao cần đào tạo lại.
  - **Người dùng phụ:** Tài xế xe dịch vụ taxi điện trên các chặng đường dài/đô thị.
- **Nỗi đau thực tế:**
  - Va chạm đuôi xe chiếm tỷ trọng lớn trong va chạm taxi đô thị. Đội xe chỉ biết sau khi sự cố đã xảy ra.
  - Các dòng xe phổ thông (như VF5 Plus, VF e34) không có sẵn hệ thống ADAS radar đắt tiền; giải pháp phần mềm trên camera hành trình là hướng tiếp cận chi phí thấp.
- **Đầu ra hệ thống:**
  - Bounding box + Ước lượng cự ly $Z$ (m) kèm dải bất định $\pm 1.96\sigma$ + Vận tốc tương đối $v_Z$ + Thời gian va chạm TTC (s) + Phân loại cảnh báo: **AN TOÀN / CHÚ Ý / NGUY HIỂM / KHÔNG CHẮC CHẮN**.

---

### 2. Phút 1:00 – 5:00: Demo Trực tiếp trên Hệ thống Chạy thật (4 phút)
1. **Khởi động ứng dụng Streamlit trực tiếp:**
   - Chạy lệnh: `streamlit run app/main.py`.
2. **Demo 1: Chạy trên Video Mô phỏng Kiểm chuẩn (Ground Truth Sim):**
   - Bấm ▶️ Chạy Video.
   - Cho Giám khảo thấy xe giảm cự ly từ 30m về 6.5m, hệ thống chuyển sang mức Đỏ (NGUY HIỂM) khi $TTC < 2.0s$.
3. **Demo 2: So sánh Bật/Tắt Kalman trung thực:**
   - Chỉ cho Giám khảo thấy: Bật Kalman giúp **giảm 30.2% phương sai nhiễu** của khoảng cách và **cung cấp vận tốc tương đối $v_Z$ để tính TTC**. Khi tắt Kalman, nếu chỉ lấy đạo hàm sai phân từ khoảng cách thô thì TTC bị nhiễu loạn nghiêm trọng (sai số trung bình vọt lên >11 giây).
4. **Demo 3: Xử lý video do Giám khảo đưa ra tại chỗ (Tải lên file bất kỳ):**
   - Chuyển sang nguồn *"📤 Tải lên Video bất kỳ (Giám khảo)"* $\to$ Tải tệp MP4 của Giám khảo và chạy trực tiếp.
   *(Dự phòng: Nếu máy chiếu hoặc tệp lỗi, chuyển sang nguồn 📼 Video Dự phòng Render sẵn `results/demo_backup.mp4` và giải thích minh bạch).*

---

### 3. Phút 5:00 – 7:00: Một Số đo, Một Ca lỗi, Trụ cột & Tác động (2 phút)

#### A. 1 Số đo kiểm chứng được (`results/metrics.json` — 300 khung hình mô phỏng)
Báo cáo đầy đủ mọi dải đo, **không giấu số xấu**:

| Dải cự ly kiểm thử | Số mẫu | Tỷ lệ nhận diện | MAE Đo thô (Raw) | MAE Kalman Filter | RMSE Kalman | So sánh MAE (Kalman vs Raw) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Toàn bộ hành trình** | **300** | **100.0%** | **0.618 m** | **0.683 m** | **0.875 m** | **Kalman TỆ HƠN 10.5%** |
| **5 – 10m (Nguy hiểm)** | 104 | 100.0% | **0.071 m** | **0.347 m** | 0.406 m | **Kalman TỆ HƠN 392.2%** |
| **10 – 20m (Chú ý)** | 105 | 100.0% | 0.486 m | **0.434 m** | 0.508 m | **Kalman CẢI THIỆN 10.6%** |
| **20 – 40m (Xa/An toàn)** | 91 | 100.0% | 1.397 m | **1.355 m** | 1.427 m | **Kalman CẢI THIỆN 3.0%** |

- **Giải thích trung thực vì sao Kalman tệ hơn ở dải 5–10m:**
  + Trong mô phỏng, xe phanh gấp từ $-5.0$ m/s rồi dừng/giữ cự ly ở 6.5m. Bộ lọc Kalman dùng mô hình chuyển động vận tốc tuyến tính ($F = \begin{bmatrix} 1 & \Delta t \\ 0 & 1 \end{bmatrix}$) nên gặp hiện tượng **độ trễ pha (phase lag)** khi vật thể đổi gia tốc đột ngột.
  + Trong khi đó, phép đo thô Pinhole đo từng khung hình độc lập không có quán tính lịch sử; trên ảnh sim sạch không có che khuất, box Pinhole đo tức thời lại ra số tĩnh rất khít ($0.071$m).
- **Vậy giá trị thực sự của Kalman là gì?**
  1. **Giảm phương sai nhiễu: 30.2%** (triệt tiêu hiện tượng giật box giữa các khung hình liên tiếp).
  2. **Cung cấp vận tốc tương đối $v_Z$ và TTC ổn định:**
     - Nếu tính TTC bằng sai phân đo thô ($v_Z = \Delta Z / \Delta t$): Sai số TTC MAE là **11.77 giây** (nhiễu pixel làm đạo hàm bùng nổ).
     - Nếu dùng Trung bình trượt (Moving Average 5 khung): Sai số TTC MAE là **7.47 giây**.
     - Dùng **Kalman Filter**: Sai số TTC MAE giảm xuống **3.80 giây** (giảm >67% sai số so với sai phân thô).
- **Hiệu năng hệ thống (Đo trên CPU laptop):**
  - Tốc độ: **46.5 FPS**. Độ trễ trung vị: **p50 = 20.95 ms**, **p95 = 25.5 ms** (nhận diện/theo dõi: ~19.8ms, hình học & Kalman: ~0.06ms, render: ~1.6ms).

#### B. 1 Ca lỗi có chủ đích (`results/failure_case.png`)
- **Hiện tượng:** Che khuất một phần (Partial Occlusion) do rào chắn hoặc xe máy tạt đầu che mất 40% bề ngang xe phía trước.
- **Cơ chế lỗi:** Bề rộng box giảm từ 206px xuống 123px $\implies Z = f \cdot W / w_{\text{px}}$ nhảy từ 12.0m lên **20.08m (sai số $+8.08$m, tức $+67.4\%$)**.
- **Hậu quả an toàn:** Xe thực tế đang ở cự ly cảnh báo chú ý (12m), nhưng hệ thống tưởng ở xa (20m, an toàn), dẫn tới nguy cơ bỏ sót cảnh báo.
- **Cơ chế giảm thiểu:** Quy tắc Nghi ngờ (Rule of Suspicion) dựa trên khoảng cách Mahalanobis trong Kalman: khi kích thước box sụt giảm đột biến không khớp với động lực học, hệ thống hạ mức cảnh báo về **"KHÔNG CHẮC CHẮN"**.

#### C. Ước lượng tác động đội xe GSM (`IMPACT.md`, kịch bản cơ sở từ `eval/impact_calc.py`)
- Kịch bản giả định đội xe 30.000 xe taxi:
  - Giảm thiểu ước tính: **~394 vụ va chạm đuôi xe / năm**.
  - Tiết kiệm chi phí sửa chữa trực tiếp: **~7.87 tỷ VNĐ / năm**.
  - Giảm 1.181 ngày xe nằm xưởng, giữ lại **~1.42 tỷ VNĐ** doanh thu khai thác.
  - Tổng giá trị thặng dư ước tính: **~9.29 tỷ VNĐ / năm** (nhấn mạnh đây là mô hình ước lượng giả định, không phải số đo thực tế).

---

### 4. Phút 7:00 – 10:00: Hội đồng Hỏi đáp (Q&A - 3 phút)
*(Xem 14 câu hỏi & đáp án chi tiết ở Mục III).*

---

## II. GIỚI HẠN CỦA NHỮNG GÌ ĐÃ CHỨNG MINH (BẮT BUỘC NÊU RÕ)

> [!WARNING]
> Những điều hệ thống **CHƯA** chứng minh được và giới hạn kỹ thuật:
> 1. **Tính chất tự kiểm tra của mô phỏng (Consistency Check):** Video mô phỏng được sinh ra từ chính công thức Pinhole phối cảnh mà bộ ước lượng đảo ngược lại. Do đó, kết quả MAE trong mô phỏng chỉ chứng minh được tính nhất quán của code và hiệu năng của bộ lọc Kalman, **KHÔNG đồng nghĩa với sai số ngoài đời thực**.
> 2. **Chưa có Ground Truth ngoài đời thực:** Nhóm không có cảm biến Lidar hay Radar tham chiếu ngoài đời thực trong khuôn khổ 2 giờ thi; các clip dashcam thật chỉ dùng để kiểm tra trực quan về khả năng detect và track.
> 3. **Phụ thuộc góc nhìn và độ phẳng mặt đường:** Mô hình Pinhole giả định xe đi thẳng phía trước (yaw $\approx 0^\circ$) và mặt đường phẳng. Khi xe quay góc xiên $>30^\circ$, lên xuống dốc gắt hoặc nhún phanh mạnh, sai số khoảng cách sẽ tăng cao.
> 4. **Giới hạn khoảng cách nhận diện:** Ngoài 35m ở độ phân giải 720p, xe nhỏ hơn 45 pixel khiến detector YOLOv8n dễ bị rớt khung hình (missed detections).
> 5. **Đầu vào demo:** Toàn bộ demo chạy trên video tải lên / video mẫu và sim, không phải luồng camera gắn trên xe đang chạy.

---

## III. 14 Câu hỏi Giám khảo & Đáp án Ngắn gọn, Trung thực

#### 1. "Mô phỏng của bạn dùng cùng công thức Pinhole với bộ ước lượng, vậy có phải bạn đang đánh giá vòng tròn (circular evaluation) không?"
> **Đáp án:**
> *"Đúng một phần, thưa Giám khảo. Vì dùng chung công thức Pinhole nên bài test sim này thực chất là một **Consistency Check (kiểm tra tính nhất quán)** và kiểm thử động lực học của bộ lọc Kalman khi có nhiễu Gaussian và chuyển động đổi tốc độ. Nó chưa phản ánh được toàn bộ sai số quang học phức tạp ngoài đời (méo thấu kính, dốc cầu, nhún xe). Đó là lý do chúng tôi ghi rõ đây là giới hạn của sim trong tài liệu."*

#### 2. "Tại sao số đo của Kalman ở dải 5–10m lại tệ hơn đo thô tới gần 4 lần?"
> **Đáp án:**
> *"Vì hiện tượng **độ trễ pha (phase lag)** khi xe phanh gấp. Trong kịch bản sim, xe phía trước đổi tốc độ đột ngột từ $-5.2$ m/s rồi khựng lại ở 6.5m. Bộ lọc Kalman vận tốc tuyến tính cần 4–5 khung hình để thích ứng với gia tốc mới, nên ước lượng bị trễ khoảng 0.27m. Trong khi đó đo thô Pinhole không có bộ nhớ lịch sử nên trên ảnh sim sạch không bị trễ. Đổi lại, Kalman giúp giảm 30.2% phương sai nhiễu và là cách duy nhất ước lượng được TTC ổn định."*

#### 3. "Nếu ra đường thật thì sai số khoảng cách là bao nhiêu?"
> **Đáp án:**
> *"Chúng tôi **chưa có số đo ground truth ngoài đời thực** vì không có thiết bị đo chuẩn (như LiDAR hay Radar RTK) trong 2 giờ thi. Dựa trên phân tích độ nhạy hình học: với sai lệch chiều rộng xe $\pm 7\%$ và rung lắc kính lái $\pm 3$ pixel, sai số ngoài đời ở cự ly 15m ước tính sẽ rơi vào khoảng **$\pm 1.5 - 2.5$ mét**, cao hơn trong môi trường mô phỏng."*

#### 4. "Xe ở làn bên cạnh hoặc xe máy tạt đầu thì hệ thống xử lý thế nào, có bị báo động giả không?"
> **Đáp án:**
> *"Có nguy cơ báo động giả nếu lấy xe gần nhất bất kỳ. Do đó trong pipeline, chúng tôi định nghĩa một **hành lang di chuyển hình thang (ego-lane corridor)** ở trung tâm khung hình. Chỉ những phương tiện có điểm tiếp đất nằm trong hành lang này mới được coi là xe dẫn đường và kích hoạt cảnh báo; các xe làn bên chỉ được vẽ hộp xám theo dõi."*

#### 5. "Vì sao chọn mô hình Hình học Pinhole cổ điển thay vì mô hình Monocular Depth Estimation deep learning (như MiDaS, Depth Anything)?"
> **Đáp án:**
> *"Mô hình Monocular Depth deep learning chỉ cho ra bản đồ độ sâu tương đối (relative depth), không có đơn vị mét vật lý nếu không có hệ số scale. Ngoài ra các model này rất nặng (thường $> 80$ms trên CPU thông thường), khó đáp ứng tần số thời gian thực 30 Hz trên phần cứng xe phổ thông. Pinhole tính khoảng cách mét tuyệt đối chỉ mất **0.06 ms**."*

#### 6. "Vì sao cần tự viết bộ lọc Kalman mà không dùng trung bình trượt (Moving Average)?"
> **Đáp án:**
> *"Trung bình trượt gây trễ pha lớn và không ước lượng được vận tốc tương đối $v_Z$. Để tính TTC bằng trung bình trượt, ta vẫn phải làm sai phân số, dẫn đến sai số TTC MAE lên tới **7.47 giây**. Bộ lọc Kalman trạng thái $[Z, v_Z]^T$ ước lượng trực tiếp vận tốc, giúp sai số TTC giảm xuống **3.80 giây**."*

#### 7. "Tiêu cự $f$ lấy ở đâu nếu Giám khảo đưa một video bất kỳ không biết thông số camera?"
> **Đáp án:**
> *"Hệ thống tự động quy đổi $f$ theo độ phân giải ngang của video dựa trên giả định góc mở HFOV (mặc định $90^\circ$ cho dashcam thông thường, hoặc $50^\circ$ cho camera hẹp). Trên giao diện có thanh trượt để tinh chỉnh $f$ trực tiếp. Trên xe VinFast sản xuất thực tế, camera kính lái được cố định và hiệu chuẩn tiêu cự từ nhà máy."*

#### 8. "Giả định bề rộng xe $W_{\text{real}} = 1.80$m có hợp lý không khi ngoài đường có nhiều loại xe khác nhau?"
> **Đáp án:**
> *"Hệ thống phân loại theo lớp: xe con $1.80$m, xe tải $2.50$m, xe buýt $2.55$m, xe máy $0.80$m. Với dòng xe con VinFast, chiều rộng dao động từ $1.72$m (VF5) đến $1.93$m (VF8), sai lệch $\le 7\%$. Sai lệch này dẫn tới sai số khoảng cách tỉ lệ thuận $\Delta Z / Z \approx \Delta W / W$."*

#### 9. "Khi nào hệ thống sẽ nghi ngờ kết quả đo của chính nó?"
> **Đáp án:**
> *"Hệ thống áp dụng **Quy tắc Nghi ngờ (Rule of Suspicion)**:
> 1. Khi độ bất định tương đối của Kalman $\sigma_Z / Z > 25\%$.
> 2. Khi phần dư đo đạc vượt ngưỡng khoảng cách Mahalanobis $\chi^2 > 9.0$ (tương đương lệch $>3\sigma$).
> Lúc này hệ thống lập tức hạ mức cảnh báo xuống 'KHÔNG CHẮC CHẮN' để tránh báo động giả."*

#### 10. "Hệ thống có chạy được thời gian thực (real-time) trên phần cứng xe không?"
> **Đáp án:**
> *"Trên CPU máy tính thử nghiệm, hệ thống đạt **46.5 FPS** (độ trễ p50 là **20.95 ms**). Khối lượng tính toán nặng nhất là YOLOv8n (~19.8ms), còn phần hình học và Kalman chỉ tốn ~0.06ms. Trên phần cứng nhúng ô tô, hoàn toàn có thể chạy mượt ở tần số 30 Hz."*

#### 11. "Nếu đường dốc hoặc xe bị nhún lắc khi phanh gấp thì phương án tiếp đất mặt đường ($Z_{\text{ground}}$) bị ảnh hưởng thế nào?"
> **Đáp án:**
> *"Phương án tiếp đất phụ thuộc vào khoảng cách pixel tới đường chân trời $(y_{\text{bottom}} - y_{\text{horizon}})$. Khi xe nhún phanh hoặc lên dốc, vị trí chân trời biểu kiến thay đổi làm $Z_{\text{ground}}$ có thể sai lệch 5–15 mét. Đó là lý do chúng tôi chọn Phương án bề rộng $Z_{\text{width}}$ làm bộ ước lượng chính vì không bị phụ thuộc vào góc nhún pitch."*

#### 12. "Con số tiết kiệm ~9.29 tỷ VNĐ trong IMPACT.md dựa trên cơ sở nào, có kiểm chứng được không?"
> **Đáp án:**
> *"Đây là **mô hình ước lượng giả định** (kịch bản cơ sở do script `eval/impact_calc.py` tính toán), **không phải số liệu tài chính đã kiểm chứng**. Mô hình giả định đội 30.000 xe, mỗi xe gặp 350 sự kiện bám đuôi sát/năm, xác suất xảy ra va chạm là 0.015% và cảnh báo giúp ngăn chặn được 25% số vụ. Chúng tôi đã đưa cả 3 kịch bản (thận trọng 0.51 tỷ, cơ sở 9.29 tỷ, lạc quan 51.7 tỷ) trong tài liệu để thể hiện tính bất định."*

#### 13. "Làm thế nào để mở rộng hệ thống này trong tương lai?"
> **Đáp án:**
> *"Tích hợp hợp nhất cảm biến (Sensor Fusion) với Radar sóng milimet 77GHz có sẵn trên các dòng xe cao cấp như VF8 qua thuật toán Extended Kalman Filter (EKF), kết hợp dữ liệu can-bus (vận tốc xe chủ, góc lái) để loại bỏ giả định tĩnh."*

#### 14. "Tại sao không dùng mô hình deep learning phát hiện 3D bounding box (như 3D Object Detection)?"
> **Đáp án:**
> *"Mô hình 3D bounding box từ ảnh đơn (monocular 3D) rất nhạy cảm với góc quay camera, yêu cầu tập dữ liệu huấn luyện xe ô tô được gán nhãn 3D phức tạp (như KITTI, nuScenes) vốn không phản ánh đúng xe buýt hay xe máy tại Việt Nam, và chi phí tính toán cao hơn nhiều so với YOLOv8n 2D kết hợp Pinhole."*

---

## IV. Bảng Kiểm Tra Checklist 9 Mục Đề Bài (Pre-Demo Verification)

| STT | Tiêu chí Checklist Đề bài | Trạng thái | Minh chứng & Ghi chú kiểm tra |
| :---: | :--- | :---: | :--- |
| **1** | Demo chạy trên đúng máy sẽ dùng, xử lý được video tải lên | **CẦN NGƯỜI DÙNG XÁC NHẬN** | *Hướng dẫn:* Người dùng phải tự chạy `streamlit run app/main.py` trên laptop demo trước giờ thi, thử upload 1 clip bất kỳ. |
| **2** | Có video quay sẵn để dự phòng nếu demo trực tiếp hỏng | **CÓ** | Tệp `results/demo_backup.mp4` đã render sẵn đầy đủ HUD & telemetry cảnh báo. |
| **3** | Có một con số đo, và cả team nói được nó đo như thế nào | **CÓ** | Tệp `results/metrics.json` và bảng ở mục I.3 (lưu ý: Kalman tệ hơn đo thô ở tổng thể và dải 5–10m, nhưng giảm phương sai 30.2% và ổn định TTC). Đo qua sim `eval/evaluate.py`. |
| **4** | Có ít nhất một ca lỗi, kèm lý do vì sao hệ thống sai | **CÓ** | Tệp `results/failure_case.png` và `results/failure_case_analysis.json` (che khuất 40% làm box co lại, khoảng cách bị tính xa hơn 67.4%). |
| **5** | Chỉ ra được ít nhất 2 trụ cột và vị trí của chúng | **CÓ** | 5 trụ cột: Học (`src/detect.py`), Hình học (`src/geometry.py`), Bất định (`src/kalman.py`), Thời gian (`src/timing.py`), Bằng chứng (`results/metrics.json`, `eval/evaluate.py`). |
| **6** | Không dùng dữ liệu thật của bệnh nhân hoặc sinh viên | **CÓ** | Xem `DATA.md` (chỉ dùng clip Udacity MIT License và sim tổng hợp toán học). |
| **7** | Mỗi thành viên trả lời được vì sao team chọn cách làm này | **CẦN NGƯỜI DÙNG XÁC NHẬN** | *Hướng dẫn:* Người dùng (làm 1 mình) đọc kỹ 14 câu hỏi Q&A ở mục III để tự tin trả lời trước hội đồng. |
| **8** | Nói được người dùng là ai và họ được gì khi dùng sản phẩm | **CÓ** | Người dùng chính: Nhân viên kiểm tra an toàn đội xe GSM duyệt video cuối ca để phát hiện tài xế bám đuôi nguy hiểm (`IMPACT.md`). |
| **9** | Có ước lượng tác động nếu triển khai ở Vin bằng con số | **CÓ** | Báo cáo `IMPACT.md` và script `eval/impact_calc.py` (kịch bản cơ sở: giảm ~394 vụ va chạm đuôi xe, tiết kiệm ~9.29 tỷ VNĐ/năm). |
