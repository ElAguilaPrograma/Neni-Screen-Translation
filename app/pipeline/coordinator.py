import numpy as np
import xxhash
from PySide6.QtCore import QObject, Signal, QTimer
from app.capture.roi_capture import ROICapture
from app.pipeline.ocr_worker import OCRWorker
from app.translation.translator import translator
from app import settings as app_settings
import re

class PipelineCoordinator(QObject):
    text_detected = Signal(int, str)
    text_normalized = Signal(int, str)
    text_ready = Signal(int, str)
    _non_ascii_re = re.compile(r"[^\x00-\x7F]+")
    
    def __init__(self, hwnd, active=False, parent=None):
        super().__init__(parent)
        self.hwnd = hwnd
        self.active_rois = {}
        self.last_frames = {}
        self.last_texts = {}
        self.active = active
        self.debug_logging = False
        runtime_settings = app_settings.get_pipeline_settings()
        self._poll_interval_ms = int(runtime_settings["poll_interval_ms"])

        # Umbrales de deduplicacion para evitar OCR por jitter visual del capturador.
        self._min_changed_ratio = float(runtime_settings["min_changed_ratio"])  # % de pixeles cuantizados deben cambiar.
        self._quant_step = int(runtime_settings["quant_step"])  # 8 niveles por canal en escala de grises (0-255 >> 3)
        self._max_signature_side = int(runtime_settings["max_signature_side"])
        self._forced_roi_ids = set()

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_cycle)

        self.ocr_worker = OCRWorker(
            max_pending_rois=runtime_settings["max_pending_rois"],
            parent=self,
        )
        self.ocr_worker.text_ready.connect(self._on_worker_text_ready)
        self.ocr_worker.worker_error.connect(self._on_worker_error)
        self.ocr_worker.start()

        if self.active:
            self.timer.start(self._poll_interval_ms)

    def start_cycle(self, poll_interval_ms=None):
        if poll_interval_ms is None:
            poll_interval_ms = app_settings.get_pipeline_settings()["poll_interval_ms"]
        self._poll_interval_ms = int(poll_interval_ms)
        self.active = True
        if self.timer.isActive():
            self.timer.setInterval(self._poll_interval_ms)
            return
        self.timer.start(self._poll_interval_ms)

    def apply_runtime_settings(self, runtime_settings=None):
        if runtime_settings is None:
            runtime_settings = app_settings.get_pipeline_settings()

        self._poll_interval_ms = int(runtime_settings["poll_interval_ms"])
        self._min_changed_ratio = float(runtime_settings["min_changed_ratio"])
        self._quant_step = int(runtime_settings["quant_step"])
        self._max_signature_side = int(runtime_settings["max_signature_side"])

        if self.ocr_worker:
            self.ocr_worker.max_pending_rois = max(1, int(runtime_settings["max_pending_rois"]))

        if self.timer and self.timer.isActive():
            self.timer.setInterval(self._poll_interval_ms)
        
    def stop_cycle(self):
        if not self.timer:
            return
        self.timer.stop()
        self.ocr_worker.clear_pending()
        self._forced_roi_ids.clear()
        self.active = False

    def shutdown(self):
        self.stop_cycle()
        if self.ocr_worker and self.ocr_worker.isRunning():
            self.ocr_worker.stop()
            self.ocr_worker.wait(1000)

    def _log(self, message):
        if self.debug_logging:
            print(message)
        
    def update_rois(self, rois_list):
        self.active_rois = {roi.roi_id: roi for roi in rois_list}
        
        current_ids = set(self.active_rois.keys())
        old_ids = set(self.last_frames.keys())
        for r_id in old_ids - current_ids:
            del self.last_frames[r_id]
            self.last_texts.pop(r_id, None)

        self.ocr_worker.prune_pending(current_ids)
        self._forced_roi_ids.intersection_update(current_ids)

    def _build_signature(self, frame: np.ndarray) -> np.ndarray:
        # BGR a grayscale con aritmetica entera para reducir alocaciones/costo CPU.
        b = frame[:, :, 0].astype(np.uint16)
        g = frame[:, :, 1].astype(np.uint16)
        r = frame[:, :, 2].astype(np.uint16)
        gray = ((29 * b + 150 * g + 77 * r) >> 8).astype(np.uint8)

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
            
    def _capture_and_dispatch(self, force=False):
        if not self.hwnd:
            self._log("No se ha establecido un HWND valido para la captura.")
            return 0

        if not self.active_rois:
            self._log("No hay ROIs activas para procesar.")
            return 0

        window_frame = ROICapture.capture_window_frame(self.hwnd)
        if window_frame is None:
            self._log("No se pudo capturar el frame base de la ventana.")
            return 0

        dispatched = 0
        for roi_id, roi in self.active_rois.items():
            try:
                frame = ROICapture.crop_frame(
                    self.hwnd,
                    window_frame,
                    roi.x,
                    roi.y,
                    roi.w,
                    roi.h,
                )

                if frame is None:
                    self._log(f"Error al capturar ROI {roi_id}.")
                    continue

                if not force and not self._should_run_ocr(roi_id, frame):
                    self._log(f"ROI {roi_id} sin cambios significativos, omitiendo OCR.")
                    continue

                if force:
                    self._forced_roi_ids.add(roi_id)
                self.ocr_worker.submit(roi_id, np.ascontiguousarray(frame))
                dispatched += 1
            except Exception as e:
                print(f"Error en el ciclo de procesamiento para ROI {roi_id}: {e}")

        return dispatched

    def process_cycle(self):
        if not self.active:
            self.stop_cycle()
            return

        self.timer.stop()
        try:
            self._capture_and_dispatch(force=False)
        finally:
            if self.active:
                self.timer.start(self._poll_interval_ms)

    def force_detection(self):
        """Dispara una deteccion+traduccion inmediata para todas las ROI activas."""
        return self._capture_and_dispatch(force=True)

    def _on_worker_text_ready(self, roi_id, raw_text):
        forced = roi_id in self._forced_roi_ids
        if forced:
            self._forced_roi_ids.discard(roi_id)

        if not self.active and not forced:
            return

        if not raw_text.strip():
            return

        normalized_text = self.normalize_text(raw_text)
        if not normalized_text:
            return

        if not forced and self.last_texts.get(roi_id) == normalized_text:
            return
        self.last_texts[roi_id] = normalized_text

        try:
            translated_text = translator.translate(normalized_text)
        except Exception as e:
            print(f"Error al traducir ROI {roi_id}: {e}")
            translated_text = normalized_text

        self.text_detected.emit(roi_id, raw_text)
        self.text_normalized.emit(roi_id, normalized_text)
        self.text_ready.emit(roi_id, translated_text)

    def _on_worker_error(self, message):
        print(message)
            
    def normalize_text(self, text):
        text = text.replace("\n", " ")
        text = self._non_ascii_re.sub(" ", text)  # Remover no-ASCII si es ingles puro
        text = " ".join(text.split())
        return text.strip()
    