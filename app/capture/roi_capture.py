from app.utils.win32_utils import (
    capture_window_for_ocr,
    capture_window_roi_for_ocr,
    crop_bgr_frame_for_ocr,
)

class ROICapture:
    @staticmethod
    def capture_window_frame(hwnd):
        return capture_window_for_ocr(hwnd)

    @staticmethod
    def crop_frame(hwnd, frame_bgr, x, y, w, h):
        return crop_bgr_frame_for_ocr(hwnd, frame_bgr, x, y, w, h)

    @staticmethod
    def capture(hwnd, x, y, w, h):
        frame_bgr = capture_window_roi_for_ocr(hwnd, x, y, w, h)
        
        if frame_bgr is None:
            raise RuntimeError("No se pudo capturar la ROI de la ventana.")
        
        return frame_bgr