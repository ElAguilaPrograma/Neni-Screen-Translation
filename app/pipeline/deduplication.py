import numpy as np
import xxhash
import cv2

class Deduplication:
    def __init__(self):
        # Umbral para cambios estructurales (bordes). Ajustable para balancear sensibilidad vs. rendimiento.
        self._min_edge_changed_ratio = 0.015 
        # Resolución máxima de la firma para capturar bien los bordes sin consumir mucha CPU
        self._max_signature_side = 120 
        # Cuantos bits descartar al cuantizar la imagen para el hash. Ajustable para balancear sensibilidad vs. colisiones.
        self._quant_step = 3

    def _get_gray_downsampled(self, frame_bgr: np.ndarray) -> np.ndarray:
        h, w = frame_bgr.shape[:2]
        
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        scale = min(1.0, self._max_signature_side / max(h, w))
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            small = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            small = gray
            
        return small
        
    def _build_edge_signature(self, gray_small: np.ndarray) -> np.ndarray:
        edges = cv2.Canny(gray_small, threshold1=100, threshold2=200)
        return (edges > 0).astype(np.uint8)

    def _should_run_ocr(self, roi_id: int, frame: np.ndarray, last_frames: dict) -> bool:
        gray_small = self._get_gray_downsampled(frame)
        
        quantized = (gray_small >> self._quant_step).astype(np.uint8)
        current_hash = xxhash.xxh64_hexdigest(quantized.tobytes())
        
        previous = last_frames.get(roi_id)
        if previous is None:
            edge_signature = self._build_edge_signature(gray_small)
            last_frames[roi_id] = {
                "hash": current_hash,
                "edge_signature": edge_signature,
            }
            return True

        if previous["hash"] == current_hash:
            return False

        edge_signature = self._build_edge_signature(gray_small)
        prev_edge = previous.get("edge_signature")
        
        if prev_edge is None or edge_signature.shape != prev_edge.shape:
            last_frames[roi_id] = {
                "hash": current_hash,
                "edge_signature": edge_signature,
            }
            return True
            
        diff = np.abs(edge_signature.astype(np.int8) - prev_edge.astype(np.int8))
        changed_ratio = np.count_nonzero(diff) / float(diff.size)
        
        last_frames[roi_id] = {
            "hash": current_hash,
            "edge_signature": edge_signature,
        }
        
        return changed_ratio >= self._min_edge_changed_ratio
