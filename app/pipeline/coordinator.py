import numpy as np
import xxhash
from PySide6.QtCore import QObject, Signal, QTimer
from app.ocr.engine import ocr_processor
from app.capture.roi_capture import ROICapture
import re
import functools

def _measure_time(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        import time
        start = time.perf_counter()
        result = func(self, *args, **kwargs)
        end = time.perf_counter()
        print(f"Time taken by {func.__name__}: {end - start:.4f} seconds")
        return result
    return wrapper

class PipelineCoordinator(QObject):
    text_ready = Signal(int, str)
    
    def __init__(self, hwnd, active = False):
        super().__init__()
        self.hwnd = hwnd
        self.active_rois = {}
        self.last_frames = {}
        self.last_texts = {}
        self.active = active

        # Umbrales de deduplicacion para evitar OCR por jitter visual del capturador.
        self._min_changed_ratio = 0.01  # % de pixeles cuantizados deben cambiar.
        self._quant_step = 3  # 8 niveles por canal en escala de grises (0-255 >> 3)
        self._max_signature_side = 96

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_cycle)
        self.timer.start(400)
        
    def stop_cycle(self):
        self.timer.stop()
        self.active = False
        
    def update_rois(self, rois_list):
        self.active_rois = {roi.roi_id: roi for roi in rois_list}
        
        current_ids = set(self.active_rois.keys())
        old_ids = set(self.last_frames.keys())
        for r_id in old_ids - current_ids:
            del self.last_frames[r_id]
            self.last_texts.pop(r_id, None)

    def _build_signature(self, frame: np.ndarray) -> np.ndarray:
        # BGR a grayscale con pesos fijos y reduccion para comparacion barata.
        gray = (
            0.114 * frame[:, :, 0].astype(np.float32)
            + 0.587 * frame[:, :, 1].astype(np.float32)
            + 0.299 * frame[:, :, 2].astype(np.float32)
        ).astype(np.uint8)

        h, w = gray.shape
        step_y = max(1, h // self._max_signature_side)
        step_x = max(1, w // self._max_signature_side)
        small = gray[::step_y, ::step_x]

        # Cuantizar reduce falsos cambios por antialias/compositor/subpixel.
        return (small >> self._quant_step).astype(np.uint8)

    def _should_run_ocr(self, roi_id: int, frame: np.ndarray) -> bool:
        signature = self._build_signature(frame)
        current_hash = xxhash.xxh64_hexdigest(signature.tobytes())

        previous = self.last_frames.get(roi_id)
        if previous is None:
            self.last_frames[roi_id] = {
                "hash": current_hash,
                "signature": signature,
            }
            return True

        if previous["hash"] == current_hash:
            return False

        prev_signature = previous["signature"]
        min_h = min(prev_signature.shape[0], signature.shape[0])
        min_w = min(prev_signature.shape[1], signature.shape[1])
        if min_h <= 0 or min_w <= 0:
            self.last_frames[roi_id] = {
                "hash": current_hash,
                "signature": signature,
            }
            return True

        diff = np.abs(
            signature[:min_h, :min_w].astype(np.int16)
            - prev_signature[:min_h, :min_w].astype(np.int16)
        )
        changed_ratio = float(np.count_nonzero(diff >= 2)) / float(diff.size)

        self.last_frames[roi_id] = {
            "hash": current_hash,
            "signature": signature,
        }
        return changed_ratio >= self._min_changed_ratio
            
    def process_cycle(self):
        if not self.hwnd:
            print("No se ha establecido un HWND válido para la captura.")
            return
        
        if not self.active:
            self.stop_cycle()
            return
        
        self.timer.stop()
        
        try:
            for roi_id, roi in self.active_rois.items():
                try:
                    frame = ROICapture.capture(self.hwnd, roi.x, roi.y, roi.w, roi.h)
                    
                    if frame is None:
                        print(f"Error al capturar ROI {roi_id}.")
                        continue

                    if not self._should_run_ocr(roi_id, frame):
                        print(f"ROI {roi_id} sin cambios significativos, omitiendo OCR.")
                        continue

                    self.run_ocr_pipeline(roi_id, frame)   
                except Exception as e:
                    print(f"Error en el ciclo de procesamiento para ROI {roi_id}: {e}")
        finally:
            self.timer.start(400)
    
    @_measure_time            
    def run_ocr_pipeline(self, roi_id, frame):
        raw_text = ocr_processor.read(frame)
        if raw_text.strip():
            normalized_text = self.normalize_text(raw_text)
            if self.last_texts.get(roi_id) == normalized_text:
                return
            self.last_texts[roi_id] = normalized_text
            self.text_ready.emit(roi_id, normalized_text)
            
    def normalize_text(self, text):
        text = text.replace("\n", " ")
        text = re.sub(r'[^\x00-\x7F]+', ' ', text) # Remover no-ASCII si es inglés puro
        text = " ".join(text.split())
        return text.strip()
    