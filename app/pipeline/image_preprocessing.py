import cv2
import numpy as np

class ImagePreprocessor:
    def __init__(self):
        # TODO: Centralizar en los ajustes/configuración del usuario más adelante
        self.scale_factor = 2.0 
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.kernel = np.ones((2, 2), np.uint8)

    def process(self, frame_bgr: np.ndarray) -> np.ndarray:
        if frame_bgr is None or frame_bgr.size == 0:
            return frame_bgr
            
        # 1. Escalado (upscaling) de la imagen
        width = int(frame_bgr.shape[1] * self.scale_factor)
        height = int(frame_bgr.shape[0] * self.scale_factor)
        img_resized = cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_CUBIC)
        
        # 2.- Denoising (Eliminación de ruido)
        img_denoising = cv2.medianBlur(img_resized, 3) # Debe ser impar 3 o 5.
        
        # 3. Conversion a escala de grises
        img_gray = cv2.cvtColor(img_denoising, cv2.COLOR_BGR2GRAY)
        
        # 4. Exualización de contraste adaptativa (CLAHE)
        img_clahe = self.clahe.apply(img_gray)
        
        #5 Operaciones morfológicas para mejorar la detección de texto
        img_final = cv2.morphologyEx(img_clahe, cv2.MORPH_CLOSE, self.kernel)
        
        return img_final
