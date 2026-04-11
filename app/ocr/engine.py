import logging
import numpy as np
from rapidocr import RapidOCR


logger = logging.getLogger(__name__)

class OCREngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCREngine, cls).__new__(cls)
            # Aqui debo poner en un futuro que use cuda si esta disponible
            cls._instance.engine = RapidOCR()
            logger.info("Rapid OCR engine inicializado.")
        return cls._instance
    
    def read(self, image: np.ndarray) -> str:
        if image is None or image.size == 0:
            return ""

        output = self.engine(image)

        # Compatibilidad con versiones antiguas (tuple) y nuevas (RapidOCROutput).
        if isinstance(output, tuple):
            result = output[0]
            if result:
                texts = [line[1] for line in result if len(line) > 1 and line[1]]
                return "\n".join(texts)
            return ""

        txts = getattr(output, "txts", None)
        if txts:
            return "\n".join([text for text in txts if text])
        
        return ""
    
ocr_processor = OCREngine()