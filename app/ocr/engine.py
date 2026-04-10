import os
import threading
import ctypes
from pathlib import Path
import numpy as np
import onnxruntime as ort
from rapidocr import RapidOCR

class OCREngine:
    _instance = None
    _cuda_required_dlls = (
        "cublasLt64_12.dll",
        "cublas64_12.dll",
        "cudart64_12.dll",
        "cudnn64_9.dll",
    )

    _provider_priority = (
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    )
    _supported_provider_params = {
        "CUDAExecutionProvider": {
            "EngineConfig.onnxruntime.use_cuda": True,
            "EngineConfig.onnxruntime.use_dml": False,
        },
        "DmlExecutionProvider": {
            "EngineConfig.onnxruntime.use_cuda": False,
            "EngineConfig.onnxruntime.use_dml": True,
        },
        "CPUExecutionProvider": {
            "EngineConfig.onnxruntime.use_cuda": False,
            "EngineConfig.onnxruntime.use_dml": False,
        },
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCREngine, cls).__new__(cls)
            # Afinar runtime CPU antes de inicializar ONNX/RapidOCR.
            os.environ.setdefault("OMP_NUM_THREADS", "2")
            os.environ.setdefault("ORT_NUM_THREADS", "2")
            os.environ.setdefault("ORT_INTER_OP_NUM_THREADS", "1")
            os.environ.setdefault("ORT_INTRA_OP_NUM_THREADS", "2")
            cls._instance._engine_lock = threading.RLock()
            cls._instance._dll_directory_handles = []
            cls._instance._configure_windows_cuda_dll_search_paths()
            cls._instance.available_providers = tuple(ort.get_available_providers())
            cls._instance.current_device = cls._instance._select_default_provider()
            cls._instance.engine = cls._instance._build_engine_for_provider(cls._instance.current_device)
            print(f"Rapido OCR engine inicializado con provider: {cls._instance.current_device}")
        return cls._instance
    
    def _configure_windows_cuda_dll_search_paths(self):
        if os.name != "nt" or not hasattr(os, "add_dll_directory"):
            return

        candidate_dirs = []

        for env_key, env_value in os.environ.items():
            if not env_key.upper().startswith("CUDA_PATH"):
                continue
            if not env_value:
                continue
            base = Path(env_value)
            candidate_dirs.append(base / "bin")
            candidate_dirs.append(base / "bin" / "x64")

        cuda_root = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
        if cuda_root.exists():
            for version_dir in sorted(cuda_root.glob("v12*"), reverse=True):
                candidate_dirs.append(version_dir / "bin")
                candidate_dirs.append(version_dir / "bin" / "x64")

        cudnn_root = Path(r"C:\Program Files\NVIDIA\CUDNN")
        if cudnn_root.exists():
            for cudnn_bin in sorted(cudnn_root.glob("v*/bin/12*/x64"), reverse=True):
                candidate_dirs.append(cudnn_bin)

        normalized = []
        seen = set()
        for path_obj in candidate_dirs:
            path_str = str(path_obj)
            if path_str in seen:
                continue
            seen.add(path_str)
            if path_obj.exists() and path_obj.is_dir():
                normalized.append(path_str)

        if not normalized:
            return

        current_path = os.environ.get("PATH", "")
        current_parts = [p for p in current_path.split(";") if p]

        for dll_dir in normalized:
            try:
                handle = os.add_dll_directory(dll_dir)
                self._dll_directory_handles.append(handle)
            except OSError:
                continue
            if dll_dir not in current_parts:
                current_parts.insert(0, dll_dir)

        os.environ["PATH"] = ";".join(current_parts)

    def _missing_cuda_dlls(self):
        if os.name != "nt":
            return []

        missing = []
        for dll_name in self._cuda_required_dlls:
            try:
                ctypes.WinDLL(dll_name)
            except OSError:
                missing.append(dll_name)
        return missing

    def _is_provider_runtime_ready(self, provider: str, silent: bool = False) -> bool:
        if provider != "CUDAExecutionProvider":
            return True

        missing_dlls = self._missing_cuda_dlls()
        if not missing_dlls:
            return True

        if not silent:
            print(
                "CUDAExecutionProvider detectado, pero faltan DLLs de runtime: "
                + ", ".join(missing_dlls)
                + ". Se usara CPUExecutionProvider."
            )
        return False

    def get_selectable_providers(self):
        selectable = []
        for provider in self._provider_priority:
            if provider in self.available_providers and self._is_provider_runtime_ready(provider, silent=True):
                selectable.append(provider)

        if not selectable:
            selectable.append("CPUExecutionProvider")
        return tuple(selectable)

    def _select_default_provider(self) -> str:
        for provider in self._provider_priority:
            if provider in self.available_providers and self._is_provider_runtime_ready(provider):
                return provider
        return "CPUExecutionProvider"

    def _build_engine_for_provider(self, provider: str) -> RapidOCR:
        if provider not in self._supported_provider_params:
            raise ValueError(f"Provider OCR no soportado por esta integracion: {provider}")

        if not self._is_provider_runtime_ready(provider):
            raise ValueError(f"Runtime incompleto para provider: {provider}")

        params = self._supported_provider_params[provider]
        return RapidOCR(params=params)

    def reinitialize(self, provider: str) -> None:
        if provider not in self.available_providers:
            raise ValueError(f"Provider no disponible en este entorno: {provider}")

        if provider not in self._supported_provider_params:
            raise ValueError(f"Provider no soportado por esta integracion: {provider}")

        next_engine = self._build_engine_for_provider(provider)
        with self._engine_lock:
            self.engine = next_engine
            self.current_device = provider
    
    def read(self, image: np.ndarray) -> str:
        if image is None or image.size == 0:
            return ""

        with self._engine_lock:
            output = self.engine(image)

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