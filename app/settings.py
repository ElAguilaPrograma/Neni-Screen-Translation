from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import threading


OCR_PROVIDER_LABELS = {
    "CUDAExecutionProvider": "NVIDIA GPU (CUDA)",
    "DmlExecutionProvider": "Graficos Integrados (DirectML)",
    "CPUExecutionProvider": "Procesador (CPU)",
}

OCR_PROVIDER_PRIORITY = (
    "CUDAExecutionProvider",
    "DmlExecutionProvider",
    "CPUExecutionProvider",
)

UI_SIZES = {
    "main_window": (800, 700),
    "settings_dialog": (620, 780),
}

OVERLAY_FONT_SIZE_RANGE = (10, 42)
OVERLAY_BG_OPACITY_RANGE = (35, 255)

RUNTIME_SETTINGS = {
    "pipeline_poll_interval_ms": 400,
    "overlay_tracker_poll_interval_ms": 16,
    "overlay_tracker_force_reanchor_ms": 800,
}

PIPELINE_SETTINGS = {
    "poll_interval_ms": 400,
    "min_changed_ratio": 0.01,
    "quant_step": 3,
    "max_signature_side": 96,
    "max_pending_rois": 8,
}

TRANSLATION_SETTINGS = {
    "from_code": "en",
    "to_code": "es",
    "cache_limit": 1024,
    "auto_install_package": True,
}

OCR_SETTINGS = {
    "provider_priority": OCR_PROVIDER_PRIORITY,
    "provider_params": {
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
    },
    "runtime_env_vars": {
        "OMP_NUM_THREADS": "2",
        "ORT_NUM_THREADS": "2",
        "ORT_INTER_OP_NUM_THREADS": "1",
        "ORT_INTRA_OP_NUM_THREADS": "2",
    },
    "cuda_required_dlls": (
        "cublasLt64_12.dll",
        "cublas64_12.dll",
        "cudart64_12.dll",
        "cudnn64_9.dll",
    ),
}


DEFAULT_OVERLAY_TEXT_STYLE = {
    "font_size_px": 16,
    "padding_x_px": 10,
    "padding_y_px": 7,
    "border_radius_px": 8,
    "background_rgba": (12, 18, 32, 212),
    "text_rgb": (245, 248, 255),
    "border_rgba": (255, 255, 255, 70),
    "accent_rgb": (72, 167, 255),
}


_settings_lock = threading.RLock()
_active_overlay_text_style = deepcopy(DEFAULT_OVERLAY_TEXT_STYLE)
_preferred_ocr_provider = "CPUExecutionProvider"

_SETTINGS_SCHEMA_VERSION = 1
_SETTINGS_DIR = Path.home() / ".screen_translator"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"


def _clamp_int(value, minimum, maximum, fallback):
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return int(fallback)
    return max(int(minimum), min(int(maximum), numeric))


def _clamp_float(value, minimum, maximum, fallback):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return max(float(minimum), min(float(maximum), numeric))


def _normalize_color(color, channels, fallback, alpha_min=0):
    if not isinstance(color, (list, tuple)) or len(color) != channels:
        return tuple(fallback)

    normalized = []
    for index in range(channels):
        minimum = alpha_min if index == channels - 1 and channels == 4 else 0
        normalized.append(_clamp_int(color[index], minimum, 255, fallback[index]))
    return tuple(normalized)


def get_default_overlay_text_style():
    return deepcopy(DEFAULT_OVERLAY_TEXT_STYLE)


def normalize_overlay_text_style(style):
    normalized = get_default_overlay_text_style()
    if not isinstance(style, dict):
        return normalized

    font_min, font_max = OVERLAY_FONT_SIZE_RANGE
    normalized["font_size_px"] = _clamp_int(
        style.get("font_size_px", normalized["font_size_px"]),
        font_min,
        font_max,
        normalized["font_size_px"],
    )
    normalized["padding_x_px"] = _clamp_int(
        style.get("padding_x_px", normalized["padding_x_px"]),
        0,
        64,
        normalized["padding_x_px"],
    )
    normalized["padding_y_px"] = _clamp_int(
        style.get("padding_y_px", normalized["padding_y_px"]),
        0,
        64,
        normalized["padding_y_px"],
    )
    normalized["border_radius_px"] = _clamp_int(
        style.get("border_radius_px", normalized["border_radius_px"]),
        0,
        32,
        normalized["border_radius_px"],
    )

    opacity_min, _ = OVERLAY_BG_OPACITY_RANGE
    normalized["background_rgba"] = _normalize_color(
        style.get("background_rgba", normalized["background_rgba"]),
        4,
        normalized["background_rgba"],
        alpha_min=opacity_min,
    )
    normalized["text_rgb"] = _normalize_color(
        style.get("text_rgb", normalized["text_rgb"]),
        3,
        normalized["text_rgb"],
    )
    normalized["border_rgba"] = _normalize_color(
        style.get("border_rgba", normalized["border_rgba"]),
        4,
        normalized["border_rgba"],
    )
    normalized["accent_rgb"] = _normalize_color(
        style.get("accent_rgb", normalized["accent_rgb"]),
        3,
        normalized["accent_rgb"],
    )
    return normalized


def merge_overlay_text_style(current_style, updates):
    merged = normalize_overlay_text_style(current_style)
    if isinstance(updates, dict):
        merged.update(updates)
    return normalize_overlay_text_style(merged)


def get_pipeline_poll_interval_ms():
    return int(get_pipeline_settings()["poll_interval_ms"])


def get_overlay_tracker_poll_interval_ms():
    return _clamp_int(
        RUNTIME_SETTINGS.get("overlay_tracker_poll_interval_ms", 16),
        10,
        1000,
        16,
    )


def get_overlay_tracker_force_reanchor_ms():
    return _clamp_int(
        RUNTIME_SETTINGS.get("overlay_tracker_force_reanchor_ms", 800),
        100,
        10000,
        800,
    )


def get_pipeline_settings():
    with _settings_lock:
        candidate = dict(PIPELINE_SETTINGS)
    return normalize_pipeline_settings(candidate)


def normalize_pipeline_settings(settings):
    baseline = {
        "poll_interval_ms": 400,
        "min_changed_ratio": 0.01,
        "quant_step": 3,
        "max_signature_side": 96,
        "max_pending_rois": 8,
    }
    if isinstance(settings, dict):
        baseline.update(settings)

    return {
        "poll_interval_ms": _clamp_int(
            baseline.get("poll_interval_ms", 400),
            100,
            5000,
            400,
        ),
        "min_changed_ratio": _clamp_float(
            baseline.get("min_changed_ratio", 0.01),
            0.0,
            1.0,
            0.01,
        ),
        "quant_step": _clamp_int(
            baseline.get("quant_step", 3),
            0,
            7,
            3,
        ),
        "max_signature_side": _clamp_int(
            baseline.get("max_signature_side", 96),
            16,
            512,
            96,
        ),
        "max_pending_rois": _clamp_int(
            baseline.get("max_pending_rois", 8),
            1,
            128,
            8,
        ),
    }


def get_translation_settings():
    with _settings_lock:
        candidate = dict(TRANSLATION_SETTINGS)
    return normalize_translation_settings(candidate)


def normalize_translation_settings(settings):
    baseline = {
        "from_code": "en",
        "to_code": "es",
        "cache_limit": 1024,
        "auto_install_package": True,
    }
    if isinstance(settings, dict):
        baseline.update(settings)

    normalized = {
        "from_code": str(baseline.get("from_code", "en") or "en").strip().lower(),
        "to_code": str(baseline.get("to_code", "es") or "es").strip().lower(),
        "cache_limit": _clamp_int(baseline.get("cache_limit", 1024), 32, 32768, 1024),
        "auto_install_package": bool(baseline.get("auto_install_package", True)),
    }
    if not normalized["from_code"]:
        normalized["from_code"] = "en"
    if not normalized["to_code"]:
        normalized["to_code"] = "es"
    return normalized


def set_pipeline_settings(settings):
    normalized = normalize_pipeline_settings(settings)
    with _settings_lock:
        PIPELINE_SETTINGS.update(normalized)
    return dict(normalized)


def set_translation_settings(settings):
    normalized = normalize_translation_settings(settings)
    with _settings_lock:
        TRANSLATION_SETTINGS.update(normalized)
    return dict(normalized)


def get_ocr_provider_priority():
    configured = OCR_SETTINGS.get("provider_priority", OCR_PROVIDER_PRIORITY)
    if not isinstance(configured, (list, tuple)):
        configured = OCR_PROVIDER_PRIORITY

    normalized = []
    for provider in configured:
        provider_name = str(provider).strip()
        if provider_name and provider_name not in normalized:
            normalized.append(provider_name)

    if "CPUExecutionProvider" not in normalized:
        normalized.append("CPUExecutionProvider")
    return tuple(normalized)


def get_ocr_provider_params():
    configured = OCR_SETTINGS.get("provider_params", {})
    if not isinstance(configured, dict):
        configured = {}

    merged = deepcopy(OCR_SETTINGS["provider_params"])
    for provider, params in configured.items():
        if provider not in merged or not isinstance(params, dict):
            continue
        merged[provider].update(params)
    return merged


def get_ocr_runtime_env_vars():
    configured = OCR_SETTINGS.get("runtime_env_vars", {})
    if not isinstance(configured, dict):
        configured = {}

    merged = dict(OCR_SETTINGS["runtime_env_vars"])
    for key, value in configured.items():
        key_text = str(key).strip()
        value_text = str(value).strip()
        if key_text and value_text:
            merged[key_text] = value_text
    return merged


def get_ocr_cuda_required_dlls():
    configured = OCR_SETTINGS.get("cuda_required_dlls", ())
    if not isinstance(configured, (list, tuple)):
        configured = ()
    normalized = [str(name).strip() for name in configured if str(name).strip()]
    return tuple(normalized)


def get_overlay_text_style():
    with _settings_lock:
        return normalize_overlay_text_style(_active_overlay_text_style)


def set_overlay_text_style(style):
    global _active_overlay_text_style
    with _settings_lock:
        _active_overlay_text_style = normalize_overlay_text_style(style)
        return dict(_active_overlay_text_style)


def get_preferred_ocr_provider():
    with _settings_lock:
        provider = str(_preferred_ocr_provider or "").strip()
    if not provider:
        provider = "CPUExecutionProvider"
    return provider


def set_preferred_ocr_provider(provider):
    global _preferred_ocr_provider
    provider_name = str(provider or "").strip()
    if not provider_name:
        provider_name = "CPUExecutionProvider"
    with _settings_lock:
        _preferred_ocr_provider = provider_name
    return provider_name


def get_settings_file_path():
    return str(_SETTINGS_FILE)


def _to_json_safe(value):
    if isinstance(value, tuple):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    return value


def load_settings_from_disk():
    global _active_overlay_text_style
    global _preferred_ocr_provider

    if not _SETTINGS_FILE.exists():
        return False

    try:
        payload = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False

    if not isinstance(payload, dict):
        return False

    overlay_style = payload.get("overlay_text_style")
    if isinstance(overlay_style, dict):
        set_overlay_text_style(overlay_style)

    preferred_provider = payload.get("preferred_ocr_provider")
    if isinstance(preferred_provider, str) and preferred_provider.strip():
        set_preferred_ocr_provider(preferred_provider.strip())

    pipeline_overrides = payload.get("pipeline", {})
    if isinstance(pipeline_overrides, dict):
        set_pipeline_settings(pipeline_overrides)

    translation_overrides = payload.get("translation", {})
    if isinstance(translation_overrides, dict):
        set_translation_settings(translation_overrides)

    ocr_overrides = payload.get("ocr", {})
    if isinstance(ocr_overrides, dict):
        with _settings_lock:
            OCR_SETTINGS.update(ocr_overrides)

    return True


def save_settings_to_disk():
    with _settings_lock:
        payload = {
            "schema_version": _SETTINGS_SCHEMA_VERSION,
            "overlay_text_style": get_overlay_text_style(),
            "preferred_ocr_provider": get_preferred_ocr_provider(),
            "pipeline": deepcopy(PIPELINE_SETTINGS),
            "translation": deepcopy(TRANSLATION_SETTINGS),
            "ocr": {
                "provider_priority": list(get_ocr_provider_priority()),
            },
        }

    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = _SETTINGS_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(_to_json_safe(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(_SETTINGS_FILE)
    return True