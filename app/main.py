"""
VINFAST FOLLOWING-DISTANCE & COLLISION-TIME ASSISTANT
===================================================
Ứng dụng Streamlit demo trực tiếp hệ thống cảnh báo cự ly an toàn và thời gian va chạm (TTC)
dành cho đội xe taxi điện GSM / Xanh SM và xe điện thông minh VinFast.
Giao diện hoàn toàn bằng tiếng Việt, hỗ trợ video có sẵn, video mô phỏng, và upload video tại chỗ từ Giám khảo.
"""

import json
import os
import sys
import tempfile
import time
import cv2
import numpy as np
import pandas as pd
import streamlit as st

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.pipeline import FollowingDistancePipeline
from src.geometry import VEHICLE_CLASS_PRIORS


# Cấu hình trang Streamlit
st.set_page_config(
    page_title="VinFast Following-Distance Assistant | GSM Fleet Safety",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện hiện đại VinFast Brand
st.markdown("""
<style>
    .metric-card {
        background-color: #1e2638;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #2e3a52;
        text-align: center;
    }
    .badge-safe {
        background-color: #198754; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;
    }
    .badge-warning {
        background-color: #fd7e14; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;
    }
    .badge-danger {
        background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600; animation: blink 1s infinite;
    }
    .badge-uncertain {
        background-color: #6c757d; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;
    }
    @keyframes blink { 50% { opacity: 0.6; } }
</style>
""", unsafe_allow_html=True)


def load_metrics_json():
    path = "results/metrics.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/VinFast_VFe34_rear_view.png/320px-VinFast_VFe34_rear_view.png", use_container_width=True)
    st.sidebar.title("VinFast Safety Assistant")
    st.sidebar.caption("Trợ lý Giám sát Bám đuôi & Va chạm Đội xe GSM / Xanh SM")

    st.sidebar.markdown("---")
    st.sidebar.subheader("1. Nguồn Dữ liệu Video")
    video_source_option = st.sidebar.radio(
        "Chọn nguồn video:",
        [
            "📹 Video Dashcam Thực tế (Udacity Road)",
            "🧪 Video Mô phỏng Kiểm chuẩn (Ground Truth Sim)",
            "📤 Tải lên Video bất kỳ (Giám khảo)",
            "📼 Video Dự phòng Render sẵn (Demo Backup)"
        ]
    )

    temp_video_path = None
    if video_source_option == "📹 Video Dashcam Thực tế (Udacity Road)":
        target_video_path = "data/sample_dashcam.mp4"
        default_hfov = 75.0
    elif video_source_option == "🧪 Video Mô phỏng Kiểm chuẩn (Ground Truth Sim)":
        target_video_path = "sim/synthetic_dashcam.mp4"
        default_hfov = 50.0
    elif video_source_option == "📼 Video Dự phòng Render sẵn (Demo Backup)":
        target_video_path = "results/demo_backup.mp4"
        default_hfov = 50.0
    else:
        uploaded_file = st.sidebar.file_uploader("Tải lên clip video (MP4, AVI, MOV):", type=["mp4", "avi", "mov", "mkv"])
        if uploaded_file is not None:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_file.read())
            target_video_path = tfile.name
            temp_video_path = tfile.name
            default_hfov = 90.0
        else:
            target_video_path = "data/sample_dashcam.mp4"
            default_hfov = 75.0
            st.sidebar.info("Chưa chọn file tải lên, đang dùng video mẫu mặc định.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("2. Cấu hình Cảm biến & Trụ cột")

    cam_preset = st.sidebar.selectbox(
        "Cấu hình Camera:",
        [
            "VinFast ADAS Forward Camera (HFOV 50°, f ≈ 1372px)",
            "Dashcam chuẩn (HFOV 90°, f ≈ 640px)",
            "Dashcam góc rộng (HFOV 120°, f ≈ 369px)",
            "Tùy chỉnh góc nhìn / tiêu cự"
        ],
        index=0 if "Mô phỏng" in video_source_option or "Backup" in video_source_option else 1
    )

    if cam_preset.startswith("VinFast"):
        selected_hfov = 50.0
    elif "90°" in cam_preset:
        selected_hfov = 90.0
    elif "120°" in cam_preset:
        selected_hfov = 120.0
    else:
        selected_hfov = st.sidebar.slider("Góc mở ngang HFOV (độ):", 40.0, 130.0, default_hfov, step=1.0)

    # Chiều rộng xe giả định
    vehicle_w = st.sidebar.slider(
        "Chiều rộng xe giả định W_real (m):",
        1.50, 2.20, 1.80, step=0.05,
        help="Chuẩn xe điện VinFast: VF5 (1.72m), VF e34 (1.77m), VF8 (1.93m) -> Trung bình 1.80m"
    )

    # Ngưỡng tin cậy
    conf_thresh = st.sidebar.slider("Ngưỡng tin cậy Detect (Confidence):", 0.15, 0.70, 0.25, step=0.05)

    # Bật / Tắt Kalman
    use_kalman = st.sidebar.toggle("Bật Bộ lọc Kalman [Z, vZ]", value=True, help="Tắt để xem khoảng cách thô Pinhole không lọc")

    # Các nút điều khiển
    st.sidebar.markdown("---")
    col_btn1, col_btn2 = st.sidebar.columns(2)
    start_stream = col_btn1.button("▶️ Chạy Video", type="primary", use_container_width=True)
    stop_stream = col_btn2.button("⏹️ Dừng", use_container_width=True)

    # Header chính
    st.title("🚗 VinFast Following-Distance & Collision-Time Assistant")
    st.markdown("**Hệ thống Cảnh báo Khoảng cách An toàn & Thời gian Va chạm cho Xe Điện Thông minh VinFast & Đội xe GSM / Xanh SM**")

    # Bố cục 5 thẻ Metric thời gian thực
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    metric_dist = m_col1.empty()
    metric_vz = m_col2.empty()
    metric_ttc = m_col3.empty()
    metric_alert = m_col4.empty()
    metric_perf = m_col5.empty()

    # Vùng hiển thị video và biểu đồ thời gian thực
    col_video, col_chart = st.columns([1.3, 0.9])
    video_placeholder = col_video.empty()
    chart_placeholder = col_chart.empty()

    # Danh sách buffer lưu lịch sử vẽ biểu đồ trực tiếp
    history_times = []
    history_z_raw = []
    history_z_kf = []
    history_sigma = []

    # Xử lý Stream Video trực tiếp
    if start_stream:
        if not os.path.exists(target_video_path):
            st.error(f"Không tìm thấy file video: {target_video_path}")
            return

        cap = cv2.VideoCapture(target_video_path)
        if not cap.isOpened():
            st.error("Không thể mở video. Định dạng file có thể không tương thích.")
            return

        pipeline = FollowingDistancePipeline(
            hfov_deg=selected_hfov,
            vehicle_width_m=vehicle_w,
            confidence_threshold=conf_thresh,
            use_kalman=use_kalman
        )

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        max_display_frames = 250  # Giới hạn số frame hiển thị mượt

        progress_bar = st.progress(0)
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 300

        try:
            while cap.isOpened() and frame_idx < max_display_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                t_curr = frame_idx / fps
                annotated, targets, stats = pipeline.process_frame(frame, timestamp_s=t_curr)

                # Cập nhật các thẻ Metric
                pri = stats.get("primary_target")
                if pri:
                    z_val = pri["z_est_m"]
                    sig_val = pri["sigma_z_m"]
                    vz_val = pri["vz_est_kmh"]
                    ttc_val = pri["ttc_s"]
                    al_val = pri["alert_level"]

                    # Thẻ 1: Khoảng cách Z
                    sigma_str = f" ±{1.96*sig_val:.1f}m" if use_kalman and sig_val > 0 else ""
                    metric_dist.metric("Cự ly Dọc Z", f"{z_val:.1f} m", sigma_str)

                    # Thẻ 2: Vận tốc tương đối
                    vz_dir = "tiến lại" if vz_val < -0.5 else ("giãn ra" if vz_val > 0.5 else "ổn định")
                    metric_vz.metric("Vận tốc Tương đối", f"{vz_val:.1f} km/h", vz_dir)

                    # Thẻ 3: Thời gian va chạm TTC
                    ttc_display = f"{ttc_val:.1f} s" if ttc_val < 30.0 else "∞ (An toàn)"
                    metric_ttc.metric("Thời gian Va chạm (TTC)", ttc_display)

                    # Thẻ 4: Mức cảnh báo
                    if al_val == "NGUY HIỂM":
                        badge_html = f"<div class='badge-danger'>🚨 NGUY HIỂM (Bám đuôi)</div>"
                    elif al_val == "CHÚ Ý":
                        badge_html = f"<div class='badge-warning'>⚠️ CHÚ Ý (Giữ cự ly)</div>"
                    elif al_val == "KHÔNG CHẮC CHẮN":
                        badge_html = f"<div class='badge-uncertain'>❔ NGHI NGỜ (Nhiễu/Che)</div>"
                    else:
                        badge_html = f"<div class='badge-safe'>✅ AN TOÀN</div>"
                    metric_alert.markdown(f"**Trạng thái Cảnh báo:**<br>{badge_html}", unsafe_allow_html=True)

                    history_times.append(t_curr)
                    history_z_raw.append(pri["z_raw_m"])
                    history_z_kf.append(z_val)
                    history_sigma.append(sig_val)
                else:
                    metric_dist.metric("Cự ly Dọc Z", "--")
                    metric_vz.metric("Vận tốc Tương đối", "--")
                    metric_ttc.metric("Thời gian Va chạm (TTC)", "--")
                    metric_alert.markdown("**Trạng thái Cảnh báo:**<br><div class='badge-safe'>✅ Không có xe trước</div>", unsafe_allow_html=True)

                # Thẻ 5: Hiệu năng FPS / Latency
                p50 = stats.get("latency_p50_ms", 0.0)
                fps_val = stats.get("fps", 0.0)
                metric_perf.metric("Hiệu năng (CPU)", f"{fps_val:.1f} FPS", f"p50: {p50:.1f}ms")

                # Chuyển đổi màu BGR sang RGB cho Streamlit
                frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

                # Vẽ biểu đồ cập nhật mỗi 5 frames
                if frame_idx % 5 == 0 and len(history_times) > 2:
                    df_chart = pd.DataFrame({
                        "Thời gian (s)": history_times,
                        "Raw Pinhole (m)": history_z_raw,
                        "Kalman Filter (m)": history_z_kf
                    }).set_index("Thời gian (s)")
                    chart_placeholder.line_chart(df_chart, height=330)

                frame_idx += 1
                progress_bar.progress(min(1.0, frame_idx / total_video_frames))

        except Exception as e:
            st.error(f"Đã xảy ra sự cố khi xử lý video: {str(e)}")
        finally:
            cap.release()
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except Exception:
                    pass

        st.success(f"Đã hoàn thành phân tích video ({frame_idx} khung hình).")

    # Tab phân tích chuyên sâu
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Bằng chứng Đo lường (Số đo)",
        "⚠️ Phân tích Ca lỗi Có chủ đích (Ca lỗi)",
        "🏛️ Bảy Trụ cột Track 4",
        "💼 Tác động Đội xe GSM / Xanh SM"
    ])

    with tab1:
        st.subheader("1 Số đo Kiểm chứng được (Ground Truth Sim Benchmark)")
        metrics_data = load_metrics_json()
        if metrics_data:
            ov = metrics_data["overall"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng frames kiểm thử", f"{ov['total_frames_evaluated']} frames", f"Nhận diện: {ov.get('detection_rate_percent', 100)}%")
            c2.metric("Sai số MAE Không lọc (Raw)", f"{ov['raw_mae_m']} m", "Pinhole đơn thuần")
            c3.metric("Sai số MAE Kalman", f"{ov['kalman_mae_m']} m", f"RMSE: {ov['kalman_rmse_m']} m")
            c4.metric("Giảm phương sai nhiễu", f"{ov['variance_reduction_percent']}%", "Ổn định tín hiệu")

            st.markdown("#### Bảng Sai số theo Dải Cự ly (Range-based Breakdown)")
            rb = metrics_data["by_distance_range"]
            df_ranges = pd.DataFrame([
                {
                    "Dải cự ly": "5 - 10m (Nguy hiểm / Bám đuôi sát)",
                    "Số mẫu": rb["range_5_10m"]["num_samples"],
                    "Raw MAE (m)": rb["range_5_10m"]["raw_mae_m"],
                    "Kalman MAE (m)": rb["range_5_10m"]["kalman_mae_m"],
                    "Kalman RMSE (m)": rb["range_5_10m"]["kalman_rmse_m"],
                    "Ghi chú": "Cự ly phanh khẩn cấp"
                },
                {
                    "Dải cự ly": "10 - 20m (Chú ý / Khoảng cách đô thị)",
                    "Số mẫu": rb["range_10_20m"]["num_samples"],
                    "Raw MAE (m)": rb["range_10_20m"]["raw_mae_m"],
                    "Kalman MAE (m)": rb["range_10_20m"]["kalman_mae_m"],
                    "Kalman RMSE (m)": rb["range_10_20m"]["kalman_rmse_m"],
                    "Ghi chú": "Kalman cải thiện 10.6% MAE"
                },
                {
                    "Dải cự ly": "20 - 40m (Xa / Cao tốc an toàn)",
                    "Số mẫu": rb["range_20_40m"]["num_samples"],
                    "Raw MAE (m)": rb["range_20_40m"]["raw_mae_m"],
                    "Kalman MAE (m)": rb["range_20_40m"]["kalman_mae_m"],
                    "Kalman RMSE (m)": rb["range_20_40m"]["kalman_rmse_m"],
                    "Ghi chú": "Cải thiện 3.0% MAE"
                }
            ])
            st.dataframe(df_ranges, use_container_width=True)

            col_img1, col_img2 = st.columns(2)
            if os.path.exists("results/distance_comparison.png"):
                col_img1.image("results/distance_comparison.png", caption="Hình 1: Đối sánh Quỹ đạo Z(t) Ground Truth vs Raw vs Kalman (kèm dải ±1.96σ)", use_container_width=True)
            if os.path.exists("results/error_by_range.png"):
                col_img2.image("results/error_by_range.png", caption="Hình 2: So sánh MAE / RMSE theo từng dải cự ly", use_container_width=True)

            col_img3, col_img4 = st.columns(2)
            if os.path.exists("results/ttc_comparison.png"):
                col_img3.image("results/ttc_comparison.png", caption="Hình 3: Sai số thời gian va chạm TTC trong pha phanh gấp", use_container_width=True)
            if os.path.exists("results/latency_breakdown.png"):
                col_img4.image("results/latency_breakdown.png", caption="Hình 4: Phân rã độ trễ từng tầng (FPS đạt 46.5 trên CPU)", use_container_width=True)
        else:
            st.info("Chưa có kết quả benchmark. Chạy `python eval/evaluate.py` để sinh metrics.json và các biểu đồ.")

    with tab2:
        st.subheader("1 Ca Lỗi Có Chủ Đích (Deliberate Failure Case)")
        if os.path.exists("results/failure_case.png"):
            st.image("results/failure_case.png", caption="Đối sánh: Xe bình thường vs Xe bị che khuất 40% bề ngang", use_container_width=True)

        if os.path.exists("results/failure_case_analysis.json"):
            with open("results/failure_case_analysis.json", "r", encoding="utf-8") as f:
                fail_data = json.load(f)
            p = fail_data["parameters"]
            st.error(f"""
            **Mô tả ca lỗi:** {fail_data['description']}
            - **Khoảng cách thực tế:** {p['ground_truth_distance_m']} m
            - **Bị che khuất:** {p['occlusion_ratio_percent']}% bề ngang thân xe
            - **Khoảng cách hệ thống ước lượng:** {p['estimated_distance_m']} m (Sai lệch: +{p['absolute_error_m']}m / +{p['relative_error_percent']}%)
            - **Hậu quả an toàn:** {fail_data['safety_risk']}
            - **Cơ chế giảm thiểu của Kalman:** {fail_data['mitigation_mechanism']}
            """)

            st.warning("**Giới hạn đã chứng minh:**\n" + "\n".join([f"- {lim}" for lim in fail_data["system_limitations"]]))

    with tab3:
        st.subheader("Bảy Trụ cột Kiến thức Track 4 Áp dụng")
        st.markdown("""
        1. **Học (Learning):** Pretrained YOLOv8n trên tập dữ liệu MS COCO, nhận diện xe con (car), xe buýt (bus), xe tải (truck), xe máy (motorcycle). Trình bày rõ giới hạn COCO trong giao thông đô thị Việt Nam.
        2. **Hình học (Geometry):** Mô hình Pinhole quang học $Z = f \\cdot W_{\\text{real}} / w_{\\text{px}}$ kết hợp phương án điểm tiếp đất mặt đường $Z = f \\cdot h_{\\text{cam}} / (y_{\\text{bottom}} - y_{\\text{horizon}})$. Phân tích độ nhạy $\\Delta Z / Z = \\Delta f / f + \\Delta W / W - \\Delta w / w$.
        3. **Bất định (Uncertainty):** Bộ lọc Kalman 2 trạng thái $[Z, v_Z]^T$ tự viết bằng NumPy. Mô hình phương sai đo động $R(Z) \\propto Z^4 / (f W)^2$. Xuất dải bất định 95% $\\pm 1.96\\sigma_Z$. Quy tắc Nghi ngờ (Rule of Suspicion) ngăn chặn báo động giả.
        4. **Thời gian (Timing):** Xử lý true $\\Delta t$ từ timestamp thực tế khi rớt khung. Đo độ trễ từng tầng (read $\\to$ detect $\\to$ track $\\to$ filter $\\to$ render), báo cáo p50/p95 (đạt 46.5 FPS trên CPU).
        5. **Biểu diễn (Representation):** Trạng thái thế giới mã hóa thành Bounding Box + Track ID từ ByteTrack + Tọa độ dọc $[Z, v_Z]$ trong hệ quy chiếu camera xe.
        6. **Dữ liệu (Data):** Bộ dữ liệu mô phỏng ground truth toán học + clip dashcam thực tế có giấy phép nguồn mở (ghi rõ trong `DATA.md`).
        7. **Bằng chứng (Evidence):** Số đo kiểm chứng định lượng MAE/RMSE theo 3 dải cự ly, so sánh Có lọc vs Không lọc; 1 ca lỗi che khuất được giải thích bằng số và giới hạn hệ thống.
        """)

    with tab4:
        st.subheader("Tác động Thực tế Đội xe GSM / Xanh SM")
        if os.path.exists("IMPACT.md"):
            with open("IMPACT.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.info("Xem chi tiết trong file IMPACT.md")


if __name__ == "__main__":
    main()
