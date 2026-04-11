import numpy as np
import xxhash

class Deduplication:
    def __init__(self):
        # Umbrales de deduplicacion para evitar OCR por jitter visual del capturador.
        self._min_changed_ratio = 0.01  # % de pixeles cuantizados deben cambiar.
        self._quant_step = 3  # 8 niveles por canal en escala de grises (0-255 >> 3)
        self._max_signature_side = 96

    def _build_signature(self, frame: np.ndarray) -> np.ndarray:
        # Convertir BGR a escala de grises con float 16.
        b = frame[:, :, 0].astype(np.uint16, copy=False)
        g = frame[:, :, 1].astype(np.uint16, copy=False)
        r = frame[:, :, 2].astype(np.uint16, copy=False)
        gray = ((29 * b + 150 * g + 77 * r) >> 8).astype(np.uint8)

        h, w = gray.shape
        step_y = max(1, h // self._max_signature_side)
        step_x = max(1, w // self._max_signature_side)
        small = gray[::step_y, ::step_x]

        return (small >> self._quant_step).astype(np.uint8)

    def _should_run_ocr(self, roi_id: int, frame: np.ndarray, last_frames: dict) -> bool:
        signature = self._build_signature(frame)
        current_hash = xxhash.xxh64_hexdigest(signature.tobytes())

        previous = last_frames.get(roi_id)
        if previous is None:
            last_frames[roi_id] = {
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
            last_frames[roi_id] = {
                "hash": current_hash,
                "signature": signature,
            }
            return True

        diff = np.abs(
            signature[:min_h, :min_w].astype(np.int16)
            - prev_signature[:min_h, :min_w].astype(np.int16)
        )
        changed_ratio = float(np.count_nonzero(diff >= 2)) / float(diff.size)

        last_frames[roi_id] = {
            "hash": current_hash,
            "signature": signature,
        }
        return changed_ratio >= self._min_changed_ratio