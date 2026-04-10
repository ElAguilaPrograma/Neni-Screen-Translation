from collections import deque
import threading

from PySide6.QtCore import QThread, Signal

from app.ocr.engine import ocr_processor

class OCRWorker(QThread):
    text_ready = Signal(int, str)
    worker_error = Signal(str)

    def __init__(self, max_pending_rois=8, parent=None):
        super().__init__(parent)
        self.max_pending_rois = max(1, int(max_pending_rois))
        self._pending_by_roi = {}
        self._pending_order = deque()
        self._lock = threading.Lock()
        self._has_work = threading.Event()
        self._stop_event = threading.Event()

    def submit(self, roi_id, frame):
        roi_id = int(roi_id)
        with self._lock:
            if roi_id in self._pending_by_roi:
                self._pending_by_roi[roi_id] = frame
                return True

            if len(self._pending_by_roi) >= self.max_pending_rois:
                oldest_roi_id = None
                while self._pending_order:
                    candidate = self._pending_order.popleft()
                    if candidate in self._pending_by_roi:
                        oldest_roi_id = candidate
                        break
                if oldest_roi_id is not None:
                    self._pending_by_roi.pop(oldest_roi_id, None)

            self._pending_by_roi[roi_id] = frame
            self._pending_order.append(roi_id)
            self._has_work.set()
            return True

    def clear_pending(self):
        with self._lock:
            self._pending_by_roi.clear()
            self._pending_order.clear()
        self._has_work.clear()

    def prune_pending(self, valid_roi_ids):
        valid_roi_ids = {int(roi_id) for roi_id in valid_roi_ids}
        with self._lock:
            for roi_id in list(self._pending_by_roi.keys()):
                if roi_id not in valid_roi_ids:
                    self._pending_by_roi.pop(roi_id, None)
            self._pending_order = deque(
                roi_id for roi_id in self._pending_order if roi_id in self._pending_by_roi
            )
            if not self._pending_by_roi:
                self._has_work.clear()

    def stop(self):
        self._stop_event.set()
        self._has_work.set()

    def run(self):
        while not self._stop_event.is_set():
            self._has_work.wait(timeout=0.05)
            if self._stop_event.is_set():
                break

            roi_id = None
            frame = None
            with self._lock:
                while self._pending_order:
                    candidate = self._pending_order.popleft()
                    if candidate in self._pending_by_roi:
                        roi_id = candidate
                        frame = self._pending_by_roi.pop(candidate)
                        break

                if not self._pending_by_roi:
                    self._has_work.clear()

            if frame is None:
                continue

            try:
                raw_text = ocr_processor.read(frame)
                self.text_ready.emit(roi_id, raw_text)
            except Exception as exc:
                self.worker_error.emit(f"OCRWorker error ROI {roi_id}: {exc}")
