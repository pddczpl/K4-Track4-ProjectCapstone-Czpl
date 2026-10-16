# Prompt cho Codex / Antigravity — Vin Perception Hackathon (VinFast, làm 1 mình, không webcam)

Copy toàn bộ phần dưới dòng `---` và dán vào Codex/Antigravity, chạy trong thư mục repo này.

---

## VAI TRÒ
Bạn là kỹ sư computer vision senior, làm pair với tôi. Tôi làm MỘT MÌNH, có 2 giờ build + 10 phút demo, laptop KHÔNG có webcam. Hãy đọc kỹ `README.md` và `index.html` trong repo (đề bài Vin Perception Hackathon, Track 4) trước khi làm, đặc biệt các mục: Yêu cầu (4 điều), Bảy trụ cột, Chấm điểm (6 tiêu chí), Checklist trước demo. Mọi quyết định thiết kế phải bám thang điểm đó.

## ĐỀ TÀI (đã chốt)
**VinFast Following-Distance & Collision-Time Assistant** — cảnh báo khoảng cách an toàn và thời gian va chạm (TTC) từ video dashcam của xe VinFast.
- Người dùng cụ thể: tài xế/đội vận hành xe taxi điện (vd. GSM/Xanh SM dùng VinFast) và đội kiểm tra an toàn đội xe, muốn chấm điểm hành vi bám đuôi từ video hành trình.
- Nỗi đau: bám đuôi sát là nguyên nhân phổ biến gây va chạm đuôi xe; hiện chỉ biết sau khi xảy ra sự cố.
- Đầu ra dùng ngay: khung hình có box + khoảng cách ước lượng (m) + TTC (s) + mức cảnh báo (An toàn / Chú ý / Nguy hiểm), và báo cáo CSV/biểu đồ cuối video (số lần bám đuôi nguy hiểm).

## RÀNG BUỘC
- KHÔNG có webcam. Đầu vào thật = (a) file video dashcam (tải clip dashcam công khai có giấy phép dùng được, hoặc video quay bằng điện thoại nếu tôi có), (b) tải lên tại chỗ qua giao diện để "xử lý đầu vào do giám khảo đưa ra", (c) sim tổng hợp có ground truth. Nếu cần tôi sẽ dùng camera điện thoại quay clip rồi chép vào máy; hỗ trợ cả đường dẫn file lẫn upload.
- Chạy được trên laptop thường (CPU hoặc GPU nhỏ), Windows 11, Python 3.11. Dùng model pretrained, KHÔNG train từ đầu.
- Dữ liệu an toàn: không dùng dữ liệu thật của bệnh nhân/sinh viên. Clip công khai phải ghi rõ nguồn + giấy phép trong `DATA.md`.
- Ưu tiên một vòng end-to-end chạy sớm (trong ~30 phút), rồi mới cải thiện. Commit nhỏ theo từng mốc.

## KIẾN TRÚC & TRỤ CỘT (phải dùng ≥ 2, làm rõ "nằm ở đâu" và "vì sao chọn")
1. **Học** — YOLO pretrained (ultralytics, `yolo11n` hoặc `yolov8n`, lớp car/truck/bus/motorcycle) + tracker (ByteTrack tích hợp). Ghi rõ model học từ dữ liệu nào (COCO) và hạn chế.
2. **Hình học** — ước lượng khoảng cách bằng mô hình pinhole: `Z = f * W_real / w_px` (dùng chiều rộng xe giả định theo lớp, vd. ~1.8 m cho ô tô) và phương án thứ hai dựa vào điểm tiếp đất trên mặt phẳng đường (`Z = f * h_cam / (y_bottom - y_horizon)`). So sánh hai phương án, giải thích vì sao chọn cái cuối cùng. Hiệu chuẩn tiêu cự `f` (từ FOV khai báo hoặc ArUco/bàn cờ nếu có; nếu không, ghi rõ giả định và phân tích độ nhạy theo `f`).
3. **Bất định** — Kalman filter (NumPy, trạng thái [Z, vZ], tự viết) lọc khoảng cách, lấy vận tốc tương đối để tính `TTC = Z / (-vZ)`. Xuất độ bất định (σ) cùng khoảng cách, hiển thị dải tin cậy, và quy tắc "nghi ngờ": khi σ lớn hoặc box nhảy thì hạ cảnh báo/ghi "không chắc". Giải thích vì sao lọc tốt hơn dùng khung đơn lẻ (đo bằng số).
4. **Thời gian** — đo độ trễ từng tầng (đọc khung → detect → track → lọc → render) và FPS; báo cáo p50/p95; xử lý khung rớt/timestamp không đều khi tính vận tốc (dùng dt thật, không giả định hằng số).
5. **Bằng chứng** (bắt buộc cho điểm) — xem phần ĐO LƯỜNG.

(Hai trụ cột chính để nhấn mạnh khi demo: **Hình học + Bất định**; phụ: Thời gian, Bằng chứng.)

## ĐO LƯỜNG: "1 số đo + 1 ca lỗi" (10 điểm bằng chứng — làm nghiêm túc)
Vì không có ground truth ngoài đời, tạo ground truth bằng **sim tổng hợp**:
- Viết `sim/` dựng cảnh đường đơn giản (PyBullet hoặc renderer OpenCV thuần: hộp xe có kích thước thật, camera pinhole biết `f`, chiều cao gắn cam, khoảng cách thật giảm dần/đổi tốc độ, có nhiễu Gaussian + blur + thay đổi sáng). Sinh video + `ground_truth.csv` (t, Z thật).
- Chạy đúng pipeline production trên video sim, tính **MAE / RMSE khoảng cách theo dải 5–10m, 10–20m, 20–40m** và sai số TTC; so sánh **không lọc vs Kalman**. Đây là "số đo" chính; báo cáo rõ nó đo như thế nào (để cả team — tức tôi — giải thích được).
- Thêm kiểm tra trên clip dashcam thật: ít nhất vài mốc khoảng cách tham chiếu ước lượng được (vd. vạch kẻ đường có độ dài chuẩn, biển báo/biển số cỡ chuẩn) và nói rõ độ tin cậy thấp hơn sim.
- **Ca lỗi có chủ đích**: tìm và lưu một ca hệ thống sai (vd. xe bị che khuất một phần → box nhỏ → khoảng cách quá xa; dốc/đường cong phá giả định mặt phẳng; xe tải rộng hơn 1.8 m → ước lượng sai; ban đêm/mưa → rớt detect). Lưu ảnh/đoạn video, phân tích nguyên nhân gốc bằng số (vd. sai số theo độ sai lệch của `W_real`), và nêu giới hạn của những gì đã chứng minh (không phải tuyên bố chung chung).
- Xuất `results/metrics.json`, `results/failure_case.mp4|png`, biểu đồ `results/*.png`.

## GIAO DIỆN & DEMO
- Streamlit (hoặc Gradio) một trang: chọn video có sẵn / **upload video bất kỳ** / sim; chạy trực tiếp, hiển thị khung đã chú thích, đồng hồ khoảng cách + TTC + mức cảnh báo, FPS/độ trễ, biểu đồ Z(t) có dải σ, nút bật/tắt Kalman, ô chỉnh `f`, `W_real`.
- Chế độ "stream" xử lý và hiển thị từng khung theo thời gian thực (đọc file như một nguồn camera), không chỉ render xong rồi mới phát — để demo "trực tiếp" thuyết phục.
- Xử lý lỗi vững: video hỏng/định dạng lạ không làm app sập; có nút reset. Chuẩn bị video đầu ra đã xử lý sẵn (`demo_backup.mp4`) làm dự phòng.
- Giao diện tiếng Việt.

## TÁC ĐỘNG & ĐỘ HỮU ÍCH (30 điểm — làm thành 1 trang `IMPACT.md`)
- Người dùng + nỗi đau cụ thể gắn VinFast/đội xe điện (không chung chung).
- Phép tính tác động bằng con số, nêu rõ giả định và nguồn: vd. số xe × số giờ chạy × tỷ lệ sự kiện bám đuôi nguy hiểm phát hiện được × chi phí/sự cố đuôi xe trung bình ⇒ ước lượng giảm sự cố/chi phí. Nhãn rõ đây là ước lượng.
- Đường mở rộng (OTA/camera ADAS sẵn có của xe, chạy edge), rủi ro khi đưa vào thực tế (báo động giả, khác biệt camera, quyền riêng tư, trách nhiệm pháp lý).

## CẤU TRÚC REPO MONG MUỐN
```
app/            # streamlit app
src/            # detect.py, track.py, geometry.py, kalman.py, pipeline.py, timing.py
sim/            # sinh video + ground_truth.csv
eval/           # chạy đánh giá, vẽ biểu đồ, xuất metrics.json
data/           # clip dashcam + DATA.md (nguồn, giấy phép)
results/        # metrics, failure case, biểu đồ, demo_backup.mp4
tests/          # test hình học & Kalman bằng số đã biết
README_DEMO.md  # cách chạy, 1 lệnh
IMPACT.md  PITCH.md  DATA.md
requirements.txt
```
Giữ nguyên `README.md` và `index.html` của đề bài (không sửa).

## QUY TRÌNH LÀM (theo lịch 2 giờ)
1. (0–15') Đọc đề, xác nhận kế hoạch ngắn; tạo skeleton + `requirements.txt`; cài thư viện.
2. (15–60') **Vòng end-to-end thô**: video → YOLO+track → khoảng cách pinhole → Kalman → TTC → khung annotated. Chạy được trên 1 clip.
3. (60–75') Mốc kiểm tra: app Streamlit chạy từ đầu vào đến đầu ra.
4. (75–105') Sim + ground truth, đánh giá MAE/RMSE, so sánh lọc/không lọc, đo độ trễ.
5. (105–120') Ca lỗi, IMPACT.md, PITCH.md, video dự phòng, test cuối trên đúng máy demo.
Hãy tự kiểm chứng bằng cách chạy thật (không chỉ viết code): chạy pipeline, chạy test, xem số thật rồi mới báo cáo. Nếu số đo xấu, báo đúng số xấu và phân tích, đừng làm đẹp.

## PITCH 10 PHÚT (`PITCH.md`)
Kịch bản bám gợi ý của đề: 1' bài toán + người dùng; 4' demo trực tiếp (có bước nhận video do giám khảo đưa); 2' một số đo + một ca lỗi + trụ cột đã dùng + tác động; 3' hỏi đáp. Kèm 10 câu hỏi giám khảo có thể hỏi (vì sao pinhole thay vì depth network? vì sao Kalman? f lấy ở đâu? sai số bao nhiêu? giới hạn?) và đáp án ngắn, trung thực. Kèm checklist 9 mục của đề, tick từng mục kèm bằng chứng nằm ở file nào.

## TIÊU CHÍ HOÀN THÀNH
- [ ] `streamlit run app/main.py` chạy sạch trên Windows, xử lý được video upload tại chỗ.
- [ ] `results/metrics.json` có MAE/RMSE theo dải và so sánh lọc/không lọc; độ trễ p50/p95.
- [ ] Có ca lỗi được phân tích nguyên nhân + nêu giới hạn.
- [ ] ≥ 2 trụ cột được chỉ rõ trong code (comment/docstring đầu file) và trong PITCH.
- [ ] `IMPACT.md` có phép tính bằng số; `DATA.md` có nguồn/giấy phép; có video dự phòng.
- [ ] Mọi test trong `tests/` pass.

Bắt đầu bằng việc đọc README.md + index.html, tóm tắt lại 6 tiêu chí chấm điểm trong 6 dòng, đề xuất kế hoạch ngắn, rồi bắt tay làm bước 1.
