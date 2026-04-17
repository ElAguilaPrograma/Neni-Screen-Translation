from collections import deque
import threading
from PySide6.QtCore import QThread, Signal
from app.ocr.engine import ocr_processor

class OCRWorker(QThread):
    text_ready = Signal(int, str)
    worker_error = Signal(str)
    
    def __init__(self, max_pending_rois= None, parent=None):
        super().__init__(parent)
        if max_pending_rois is None:
            # Harcodeado ahora pero mas adelante se centralizara en ajustes
            max_pending_rois = 8
        self.max_pending_rois = max(1, int(max_pending_rois))
        self.pending_by_rois = {}
        self.pending_order = deque()
        self.lock = threading.Lock()
        self._has_work = threading.Event()
        self.stop_event = threading.Event()
        
    def submit(self, roi_id, frame):
        roi_id = int(roi_id)
        with self.lock:
            if roi_id in self.pending_by_rois:
                self.pending_by_rois[roi_id] = frame
                return True
            
            if len(self.pending_by_rois) >= self.max_pending_rois:
                oldest_roi_id = None
                while self.pending_order:
                    candidate = self.pending_order.popleft()
                    if candidate in self.pending_by_rois:
                        oldest_roi_id = candidate
                        break
                if oldest_roi_id is not None:
                    self.pending_by_rois.pop(oldest_roi_id, None)
                    
            self.pending_by_rois[roi_id] = frame
            self.pending_order.append(roi_id)
            self._has_work.set()
            return True

    def start_worker(self):
        # Reiniciar el worker tras un stop/shutdown sin recrear la instancia.
        if self.isRunning():
            return
        self.stop_event.clear()
        self.start()
        
    def clean_pending(self):
        with self.lock:
            self.pending_by_rois.clear()
            self.pending_order.clear()
        self._has_work.clear()
        
    def prune_pending(self, valid_roi_ids):
        valid_roi_ids = {int(roi_id) for roi_id in valid_roi_ids}
        with self.lock:
            for roi_id in list(self.pending_by_rois.keys()):
                if roi_id not in valid_roi_ids:
                    self.pending_by_rois.pop(roi_id, None)
            self.pending_order = deque(
                roi_id for roi_id in self.pending_order if roi_id in self.pending_by_rois
            )
            if not self.pending_by_rois:
                self._has_work.clear()
                
    def stop(self):
        self.stop_event.set()
        self._has_work.set()
        
    def run(self):
        while not self.stop_event.is_set():
            self._has_work.wait(timeout=0.5)
            if self.stop_event.is_set():
                break
            
            roi_id = None
            frame = None
            with self.lock:
                while self.pending_order:
                    candidate  = self.pending_order.popleft()
                    if candidate in self.pending_by_rois:
                        roi_id = candidate
                        frame = self.pending_by_rois.pop(roi_id, None)
                        break
                    
                if not self.pending_by_rois:
                    self._has_work.clear()
                    
            if frame is None:
                continue
            
            try:
                raw_text = ocr_processor.read(frame)
                self.text_ready.emit(roi_id, raw_text)
            except Exception as exc:
                self.worker_error.emit(f"Error en OCRWorker para ROI {roi_id}: {exc}")