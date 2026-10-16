"""
Trụ cột: THỜI GIAN (Timing)
===========================
Mục đích:
- Đo lường độ trễ chi tiết qua từng tầng trong pipeline xử lý:
  T_read -> T_detect -> T_track -> T_geometry_kalman -> T_render -> T_total.
- Báo cáo số liệu thời gian thực: FPS hiện tại, độ trễ trung bình, p50 (median), p95.
- Xử lý timestamp thực tế (true dt) giữa các khung hình, không giả định hằng số (30 FPS)
  nhằm đảm bảo Kalman Filter ước lượng vận tốc tương đối vZ chính xác khi bị rớt khung (frame drop)
  hoặc video có tốc độ khung hình biến thiên (VFR).
"""

import time
from collections import deque
from typing import Dict, Optional
import numpy as np


class StageTimer:
    """Đo thời gian thực thi từng block code với context manager."""
    def __init__(self):
        self.durations: Dict[str, float] = {}
        self._starts: Dict[str, float] = {}

    def start(self, stage_name: str) -> None:
        self._starts[stage_name] = time.perf_counter()

    def stop(self, stage_name: str) -> float:
        if stage_name in self._starts:
            duration_ms = (time.perf_counter() - self._starts[stage_name]) * 1000.0
            self.durations[stage_name] = duration_ms
            return duration_ms
        return 0.0

    def get_stage_ms(self, stage_name: str) -> float:
        return self.durations.get(stage_name, 0.0)


class PipelineTiming:
    """Quản lý đo lường độ trễ toàn bộ pipeline, tính p50, p95 và true dt."""
    def __init__(self, history_size: int = 150):
        self.history_size = history_size
        self.timer = StageTimer()
        self.history_total_ms: deque = deque(maxlen=history_size)
        self.history_stages: Dict[str, deque] = {
            "read": deque(maxlen=history_size),
            "detect": deque(maxlen=history_size),
            "track": deque(maxlen=history_size),
            "geometry_kalman": deque(maxlen=history_size),
            "render": deque(maxlen=history_size),
        }
        self.last_frame_timestamp: Optional[float] = None
        self.frame_count: int = 0
        self.last_dt: float = 0.0333  # Mặc định ~30 FPS

    def update_timestamp(self, current_timestamp: Optional[float] = None) -> float:
        """
        Tính toán delta t thực tế.
        Nếu không có timestamp từ video, dùng high-resolution wall clock.
        """
        now = current_timestamp if current_timestamp is not None else time.perf_counter()
        if self.last_frame_timestamp is None:
            dt = 0.0333
        else:
            dt = now - self.last_frame_timestamp
            # Giới hạn dt hợp lý nếu có gián đoạn lớn
            if dt <= 0.0001:
                dt = 0.001
            elif dt > 0.5:
                dt = 0.5
        self.last_frame_timestamp = now
        self.last_dt = dt
        self.frame_count += 1
        return dt

    def record_stage(self, stage_name: str, duration_ms: float) -> None:
        if stage_name in self.history_stages:
            self.history_stages[stage_name].append(duration_ms)

    def record_total(self, total_ms: float) -> None:
        self.history_total_ms.append(total_ms)

    def get_stats(self) -> Dict[str, float]:
        """Trả về FPS, mean, p50, p95 latency."""
        if not self.history_total_ms:
            return {
                "fps": 0.0,
                "latency_mean_ms": 0.0,
                "latency_p50_ms": 0.0,
                "latency_p95_ms": 0.0,
                "last_dt_s": self.last_dt,
                "frame_count": self.frame_count,
            }

        arr = np.array(self.history_total_ms)
        mean_lat = float(np.mean(arr))
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))
        fps = 1000.0 / mean_lat if mean_lat > 0 else 0.0

        stage_breakdown = {}
        for k, dq in self.history_stages.items():
            stage_breakdown[f"stage_{k}_mean_ms"] = float(np.mean(dq)) if dq else 0.0

        stats = {
            "fps": fps,
            "latency_mean_ms": mean_lat,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "last_dt_s": self.last_dt,
            "frame_count": self.frame_count,
        }
        stats.update(stage_breakdown)
        return stats
