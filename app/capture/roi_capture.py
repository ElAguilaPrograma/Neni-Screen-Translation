from app.utils.win32_utils import capture_window_roi_for_ocr

class ROICapture:
    @staticmethod
    def capture(hwnd, x, y, w, h):
        frame_bgr = capture_window_roi_for_ocr(hwnd, x, y, w, h)
        
        if frame_bgr is None:
            raise RuntimeError("No se pudo capturar la ROI de la ventana.")
        
        return frame_bgr