import threading

import argostranslate.package
import argostranslate.translate
from app import settings as app_settings

class TranslatorEngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslatorEngine, cls).__new__(cls)
            cls._instance._lock = threading.RLock()
            cls._instance._translation = None
            cls._instance._cache = {}
            cfg = app_settings.get_translation_settings()
            cls._instance._cache_limit = int(cfg["cache_limit"])
            cls._instance._auto_install_package = bool(cfg["auto_install_package"])
            cls._instance.from_code = cfg["from_code"]
            cls._instance.to_code = cfg["to_code"]
            cls._instance.setup_translator()
        return cls._instance
    
    def setup_translator(self):
        cfg = app_settings.get_translation_settings()
        self.from_code = cfg["from_code"]
        self.to_code = cfg["to_code"]
        self._cache_limit = int(cfg["cache_limit"])
        self._auto_install_package = bool(cfg["auto_install_package"])
        with self._lock:
            self._cache.clear()

        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next((lang for lang in installed_languages if lang.code == self.from_code), None)
        to_lang = next((lang for lang in installed_languages if lang.code == self.to_code), None)

        if self._auto_install_package and (from_lang is None or to_lang is None):
            self._install_language_package_if_missing()
            installed_languages = argostranslate.translate.get_installed_languages()
            from_lang = next((lang for lang in installed_languages if lang.code == self.from_code), None)
            to_lang = next((lang for lang in installed_languages if lang.code == self.to_code), None)

        if from_lang is None or to_lang is None:
            self._translation = None
            print(
                f"No se encontro paquete de traduccion instalado para {self.from_code}->{self.to_code}."
            )
            return

        self._translation = from_lang.get_translation(to_lang)
        print(f"Traductor cargado: {self.from_code} -> {self.to_code}")

    def _install_language_package_if_missing(self):
        try:
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
        except Exception as e:
            print(f"No se pudo actualizar el indice de paquetes de Argos: {e}")
            return

        package_to_install = next(
            (
                package
                for package in available_packages
                if package.from_code == self.from_code and package.to_code == self.to_code
            ),
            None,
        )

        if package_to_install is None:
            print(f"No hay paquete disponible en Argos para {self.from_code}->{self.to_code}.")
            return

        try:
            print(f"Instalando paquete Argos {self.from_code}->{self.to_code}...")
            downloaded_path = package_to_install.download()
            argostranslate.package.install_from_path(downloaded_path)
            print(f"Paquete de traduccion instalado: {self.from_code}->{self.to_code}")
        except Exception as e:
            print(f"No se pudo instalar paquete Argos {self.from_code}->{self.to_code}: {e}")

    def translate(self, text):
        source_text = (text or "").strip()
        if not source_text:
            return ""

        with self._lock:
            cached = self._cache.get(source_text)
            if cached is not None:
                return cached

        if self._translation is None:
            return source_text

        try:
            translated = self._translation.translate(source_text)
        except Exception as e:
            print(f"Error al traducir texto con ArgosTranslate: {e}")
            translated = source_text

        translated = (translated or "").strip() or source_text

        with self._lock:
            if len(self._cache) >= self._cache_limit:
                self._cache.pop(next(iter(self._cache)))
            self._cache[source_text] = translated

        return translated

translator = TranslatorEngine()