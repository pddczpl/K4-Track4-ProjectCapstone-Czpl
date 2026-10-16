"""
Trụ cột: BIỂU DIỄN & THEO DÕI (Tracking)
=======================================
Mục đích:
- Liên kết các bounding box qua từng khung hình để duy trì danh tính phương tiện (Track ID).
- Tích hợp ByteTrack từ ultralytics, kết hợp cơ chế gán ID dự phòng (IoU-based association fallback)
  đảm bảo pipeline hoạt động liên tục ngay cả khi ByteTrack chưa khởi tạo xong hoặc bị ngắt quãng.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from ultralytics import YOLO
from src.detect import TARGET_COCO_CLASSES


def compute_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return max(0.0, float(iou))


class VehicleTracker:
    """Module theo dõi đối tượng phương tiện qua chuỗi khung hình."""
    def __init__(
        self,
        model: Optional[YOLO] = None,
        confidence_threshold: float = 0.35,
        device: str = "cpu"
    ):
        if model is None:
            pkg_model = os.path.join(os.path.dirname(__file__), "..", "models", "yolov8n.pt")
            cwd_model = os.path.join("models", "yolov8n.pt")
            if os.path.exists(pkg_model):
                model_path = os.path.abspath(pkg_model)
            elif os.path.exists(cwd_model):
                model_path = os.path.abspath(cwd_model)
            else:
                model_path = "yolov8n.pt"
            self.model = YOLO(model_path)
        else:
            self.model = model
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.target_classes = list(TARGET_COCO_CLASSES.keys())
        self._next_fallback_id = 1
        self._active_fallback_tracks: Dict[int, Dict[str, Any]] = {}

    def track(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Theo dõi các phương tiện trong frame bằng ByteTrack.
        Trả về danh sách: [{track_id, box, confidence, class_id, class_name}]
        """
        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.confidence_threshold,
            classes=self.target_classes,
            device=self.device,
            verbose=False
        )

        tracked_objects = []
        if not results or len(results) == 0:
            return tracked_objects

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return tracked_objects

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        cls_ids = boxes.cls.cpu().numpy().astype(int)
        ids = boxes.id.int().cpu().tolist() if boxes.id is not None else None

        for i in range(len(xyxy)):
            box = tuple(xyxy[i])
            c_id = int(cls_ids[i])
            c_name = TARGET_COCO_CLASSES.get(c_id, "vehicle")

            if ids is not None and i < len(ids):
                tid = int(ids[i])
            else:
                # Fallback gán ID dựa trên IoU
                tid = self._assign_fallback_id(box, c_name)

            tracked_objects.append({
                "track_id": tid,
                "box": box,
                "confidence": float(confs[i]),
                "class_id": c_id,
                "class_name": c_name,
            })

        return tracked_objects

    def _assign_fallback_id(self, box: Tuple[float, float, float, float], class_name: str) -> int:
        best_id = None
        best_iou = 0.30
        for tid, data in self._active_fallback_tracks.items():
            if data["class_name"] == class_name:
                iou = compute_iou(box, data["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid

        if best_id is not None:
            self._active_fallback_tracks[best_id]["box"] = box
            return best_id
        else:
            new_id = self._next_fallback_id
            self._next_fallback_id += 1
            self._active_fallback_tracks[new_id] = {"box": box, "class_name": class_name}
            return new_id

    def reset(self) -> None:
        self._next_fallback_id = 1
        self._active_fallback_tracks.clear()
