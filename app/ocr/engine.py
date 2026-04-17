import logging
import numpy as np
from rapidocr import LangCls, LangRec, RapidOCR, EngineType, LangDet, ModelType, OCRVersion


logger = logging.getLogger(__name__)

class OCREngine:
    _instance = None
    
    """
    Motores de inferencia OCR disponibles
    
    onnxruntime: Ligereo y rápido, compatible con CPU y GPU, pero puede tener menor precisión en algunos casos.
    openvino: Optimizado para Intel hardware, ofrece buen rendimiento en entornos específicos en CPU intel y graficos integrados.
    paddle: Proporciona alta precisión en reconocimiento de texto. Cuidado con su rendimiento en CPU, puede ser lento sin GPU.
    Revisar bien la instalación y compatibilidad de versiones.
    torch: No usar.
    """
    
    """
    Etapas del OCR:
    1. Detección de texto: Identifica regiones en la imagen que contienen texto.
    
    2. Clasificación de orientación: Determina la orientación del texto (horizontal, vertical, etc.) para corregirla antes del reconocimiento.
    
    3. Reconocimiento de texto: Convierte las regiones detectadas en texto legible.
    """
    
    """
    Consideraciones:
    La detección se puede configurar en ch, en o multi. Esto debo ponerlo en el menu de ajustes.
    La clasificación de orientación solo puede ser ch, pero funciona bien para texto en otros idiomas, asi que se puede usar siempre.
    Si el texto siempre sera horizontal, se puede desactivar la clasificación de orientación para mejorar el rendimiento. 
    Esto también se debera configurar en ajustes.
    
    El reconocimiento de texto se puede configurar en varios idiomas (ch, ch_doc, en, arabic, chinese_cht, cyrillic, devanagari, japan, korean, ka, latin, ta, te, eslav, th y el).
    esto si o si debe configurarse en ajustes, ya que afecta directamente el rendimiento y la precisión. 
    Si se sabe que el texto a reconocer es principalmente en un idioma específico, es recomendable configurar el motor para ese idioma para obtener mejores resultados.
    """
    
    """
    Uso de RAM Y CPU por motor:
    onnxruntime: Entre 120 - 150 MB de RAM, uso moderado de CPU, alcanza pico de CPU de hasta el 70% durante la inferencia. Rapidez: Rapida - moderada
    openvino: Entre 500 - 600 MB de RAM, uso muy eficiente de CPU Intel, con picos de CPU de solo 7% durante la inferencia. - Rapido en procesaro Intel
    paddle: Por definir.
    """
    
    """
    Uso de VRAM y GPU por motor:
    Por definir.
    """
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCREngine, cls).__new__(cls)
            # TODO: Hacer esto configurable desde UI para soportar múltiples idiomas.
            logger.info("Inicializando RapidOCR...")
            cls._instance.engine = RapidOCR(
                params={
                    "Det.engine_type": EngineType.OPENVINO,
                    "Det.lang:type": LangDet.EN, 
                    "Det.ocr_version": OCRVersion.PPOCRV5,
                    "Rec.engine_type": EngineType.OPENVINO,
                    "Rec.lang:type": LangRec.EN,
                    "Rec.ocr_version": OCRVersion.PPOCRV5,
                    # Ajustes de clasificación, desactivado por defecto
                    "Global.use_cls": False,
                    "Cls.engine_type": EngineType.OPENVINO,
                    "Cls.lang:type": LangCls.CH
                }
            )
            logger.info("Rapid OCR engine inicializado.")
        return cls._instance
    
    def read(self, image: np.ndarray) -> str:
        if image is None or image.size == 0:
            logger.warning("OCR read() llamado con imagen vacía/None.")
            return ""

        try:
            # logger.debug(f"OCR input shape: {image.shape}, dtype: {image.dtype}")
            output = self.engine(image, use_cls=False)
            # logger.debug(f"OCR raw output type: {type(output)}, output: {output}")
            
            # Manejo para diferentes formatos de salida (tuple)
            if isinstance(output, tuple):
                logger.debug("Output es tuple (formato antiguo). Parseando...")
                result = output[0] if len(output) > 0 else None
                if result and isinstance(result, list) and len(result) > 0:
                    texts = [line[1] if len(line) > 1 else "" for line in result]
                    text_raw = "\n".join([t for t in texts if t])
                    logger.info(f"OCR tuple output parsed: {text_raw}")
                    return text_raw
                logger.warning("Tuple output vacío o formato inesperado.")
                return ""
            
            # Manejo para salida de RapidOCROutput (formato nuevo)
            txts = getattr(output, "txts", None)
            if txts:
                logger.debug(f"OCR txts found: {len(txts)} items")
                text_raw = "\n".join([text for text in txts if text])
                logger.info(f"OCR recognized text: {text_raw}")
                return text_raw
            
            logger.warning(f"No text found in output. Output attrs")
            return ""
        except Exception as exc:
            logger.exception(f"Error crítico en OCR read(): {exc}")
            return ""
    
ocr_processor = OCREngine()