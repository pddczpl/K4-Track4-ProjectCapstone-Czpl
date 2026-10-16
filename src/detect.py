"""
Trụ cột: HỌC (Learning) & BIỂU DIỄN (Representation)
===================================================
Mục đích:
- Nhận diện phương tiện giao thông (car, truck, bus, motorcycle) trong luồng video dashcam.
- Sử dụng mô hình pretrained YOLOv8n (ultralytics) nhẹ, chạy mượt trên CPU máy tính xách tay.
- Nguồn gốc tập dữ liệu:
  + YOLOv8n được huấn luyện trên tập dữ liệu MS COCO (Common Objects in Context, 80 lớp, ~118.000 ảnh).
  + Lớp quan sát: 2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'.
- Hạn chế của model học:
  1. COCO chủ yếu là ảnh chụp thông thường (khung ngang, góc nhìn người đi bộ), không chuyên biệt cho góc nhìn dashcam gắn kính lái ô tô.
  2. Tại giao thông Việt Nam, xe máy điền vào khoảng trống sát đầu xe (gap filling), dễ gây ra hiện tượng che khuất một phần (partial occlusion) hoặc gộp box.
  3. Model COCO không phân biệt được các mẫu xe điện VinFast cụ thể (VF3, VF5, VF e34, VF8, VF9) mà chỉ phân loại chung thành 'car',
     do đó chiều rộng xe giả định cần có cơ chế tùy biến hoặc dùng giá trị kỳ vọng (1.80m).
"""

from typing import List, Dict, Any, Optional
import numpy as np
from ultralytics import YOLO


# Bảng mã lớp COCO tương ứng với phương tiện đường bộ
TARGET_COCO_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


class VehicleDetector:
    """Module phát hiện phương tiện sử dụng mô hình học YOLO pretrained."""
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.35,
        device: str = "cpu"
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model = YOLO(model_path)
        self.target_classes = list(TARGET_COCO_CLASSES.keys())

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Thực hiện inference phát hiện phương tiện trên một khung hình.
        Trả về danh sách các phát hiện: [{box: (x1, y1, x2, y2), conf, class_id, class_name}]
        """
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            classes=self.target_classes,
            device=self.device,
            verbose=False
        )

        detections = []
        if not results or len(results) == 0:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        cls_ids = boxes.cls.cpu().numpy().astype(int)

        for i in range(len(xyxy)):
            c_id = int(cls_ids[i])
            c_name = TARGET_COCO_CLASSES.get(c_id, "vehicle")
            detections.append({
                "box": tuple(xyxy[i]),
                "confidence": float(confs[i]),
                "class_id": c_id,
                "class_name": c_name,
            })

        return detections
