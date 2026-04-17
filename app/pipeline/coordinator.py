import logging
import gc
from PySide6.QtCore import QObject, Signal, QTimer
from app.capture.roi_capture import ROICapture
from app.pipeline.normalize_text import NormalizeText
from app.pipeline.deduplication import Deduplication
from app.pipeline.image_preprocessing import ImagePreprocessor
from app.pipeline.ocr_worker import OCRWorker


logger = logging.getLogger(__name__)

class PipelineCoordinator(QObject):
    text_ready = Signal(int, str)
    worker_error = Signal(str)
    
    def __init__(self, hwnd, active = False):
        super().__init__()
        self.hwnd = hwnd
        self.active_rois = {}
        self.last_frames = {}
        self.last_texts = {}
        self.forced_roi_ids = set()
        self.active = active
        self.deduplication = Deduplication()
        self.timer = QTimer()
        self.normalize_text = NormalizeText()
        self.image_preprocessor = ImagePreprocessor()
        self.timer.timeout.connect(self.process_cycle)
        
        # Harcodeado ahora pero mas adelante se centralizara en ajustes
        self.timer_cycle = 400
        self.poll_interval_ms = self.timer_cycle
            
        self.ocr_worker = OCRWorker(
            max_pending_rois=8,
            parent=self
        )
        self.ocr_worker.text_ready.connect(self._on_worker_text_ready)
        self.ocr_worker.worker_error.connect(self._on_worker_error)

        if self.active:
            self.start_cycle(self.timer_cycle)

    def _ensure_worker_running(self):
        # OCR vive en su propio QThread para no bloquear la UI.
        if self.ocr_worker and not self.ocr_worker.isRunning():
            self.ocr_worker.start_worker()
        
    def start_cycle(self, poll_interval_ms=None):
        if poll_interval_ms is None:
            poll_interval_ms = self.timer_cycle
        
        self.poll_interval_ms = int(poll_interval_ms)
        self.active = True
        self._ensure_worker_running()
        if self.timer.isActive():
            self.timer.setInterval(self.poll_interval_ms)
            return
        self.timer.start(self.poll_interval_ms)
        
    def capture_and_dispatch(self, force=False):
        if not self.hwnd:
            logger.warning("No se ha establecido un HWND válido para la captura.")
            return
        
        if not self.active_rois:
            logger.info("No hay ROIs activas para capturar.")
            return 
        
        window_frame = ROICapture.capture_window_frame(self.hwnd)
        if window_frame is None:
            logger.error("No se pudo capurar el frame base de la ventana.")
            return
        
        dispached = 0
        for roi_id, roi in self.active_rois.items():
            try:
                frame = ROICapture.crop_frame(
                    self.hwnd,
                    window_frame,
                    roi.x,
                    roi.y,
                    roi.w,
                    roi.h
                )
                
                if frame is None:
                    logger.error("Error al capturar ROI %s.", roi_id)
                    continue
                
                if not force and not self.deduplication._should_run_ocr(roi_id, frame, self.last_frames):
                    continue
                
                if force:
                    self.forced_roi_ids.add(roi_id)
                
                self.run_ocr_pipeline(roi_id, frame)
                dispached += 1
            except Exception as e:
                logger.exception("Error al capturar y despachar ROI %s.", roi_id)
                
        del window_frame
        gc.collect()
        return dispached
    
    def force_detection(self):
        self._ensure_worker_running()
        self.capture_and_dispatch(force=True)
            
    def process_cycle(self):
        if not self.hwnd:
            logger.warning("No se ha establecido un HWND válido para la captura.")
            return
        
        if not self.active:
            self.stop_cycle()
            return
        
        self.timer.stop()      
        try:
            self.capture_and_dispatch(force=False)
        finally:
            if self.active:
                self.timer.start(self.timer_cycle)
            
    def stop_cycle(self):
        if not self.timer:
            return
        self.timer.stop()
        self.active_rois.clear()
        self.last_frames.clear()
        self.last_texts.clear()
        self.forced_roi_ids.clear()
        self.active = False
        self.ocr_worker.clean_pending()
        
    def update_rois(self, rois_list):
        self.active_rois = {roi.roi_id: roi for roi in rois_list}
        
        current_ids = set(self.active_rois.keys())
        old_ids = set(self.last_frames.keys())
        for r_id in old_ids - current_ids:
            del self.last_frames[r_id]
            self.last_texts.pop(r_id, None)
            
        self.ocr_worker.prune_pending(current_ids)
        self.forced_roi_ids.intersection_update(current_ids)
            
    def shutdown(self):
        self.stop_cycle()
        if self.ocr_worker and self.ocr_worker.isRunning():
            self.ocr_worker.stop()
            self.ocr_worker.wait(1000)
              
    def run_ocr_pipeline(self, roi_id, frame):
        processed_frame = self.image_preprocessor.process(frame)
        self.ocr_worker.submit(roi_id, processed_frame)

    def _on_worker_text_ready(self, roi_id, raw_text):
        roi_id = int(roi_id)
        is_forced = roi_id in self.forced_roi_ids
        self.forced_roi_ids.discard(roi_id)

        raw_text = (raw_text or "").strip()
        if not raw_text:
            return

        normalized_text = self.normalize_text.normalize_text(raw_text)
        if not normalized_text:
            return

        # Si no es forzado, evitamos emitir texto idéntico para reducir ruido visual.
        if not is_forced and self.last_texts.get(roi_id) == normalized_text:
            return

        self.last_texts[roi_id] = normalized_text
        self.text_ready.emit(roi_id, normalized_text)

    def _on_worker_error(self, error_message):
        logger.error(error_message)
        self.worker_error.emit(error_message)
    