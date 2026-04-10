from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QEvent

from app.ui.window_selector import WindowSelectorDialog
from app.utils.win32_utils import (
    capture_window,
    start_native_overlay_tracking,
    stop_native_overlay_tracking,
)
from app.ui.overlay import WindowOverlay
from app.ui.dialog import AppDialog
from app.ui.theme import (
    get_main_window_stylesheet,
    get_preview_label_stylesheet,
    resolve_dark_mode,
)
from app.pipeline.coordinator import PipelineCoordinator
from app.ui.settings_gui import SettingsDialog
from app import settings as app_settings

class MainWindow(QMainWindow):
    
    window_selected = None
    overlay: WindowOverlay = None
    pipeline_coordinator: PipelineCoordinator = None

    def __init__(self):
        super().__init__()

        self.overlay_text_style = app_settings.get_overlay_text_style()
        self._theme_mode = app_settings.get_theme_mode()
        self._is_dark_theme = resolve_dark_mode(self._theme_mode)
        self._applying_theme = False
        self._main_stylesheet_cache = None
        self._preview_stylesheet_cache = None

        self.setWindowTitle("Screen Translator")
        self.setFixedSize(*app_settings.UI_SIZES["main_window"])
        
        # Estructura de la interfaz
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Botones
        self.btn_select = QPushButton("Seleccionar Ventana")
        self.btn_start = QPushButton("Seleccionar regiones de interés (ROI)")
        self.preview_label = QLabel("La ventana seleccionada aparecerá aquí")
        self.btn_stop = QPushButton("Detener Selección")
        self.btn_translate = QPushButton("Iniciar Traducción")
        self.btn_stop_translation = QPushButton("Detener Traducción")
        self.btn_force_detection = QPushButton("Forza deteccion y traducción")
        self.btn_settings = QPushButton("Abrir Configuración")
        
        self.btn_select.setObjectName("btn_select")
        self.btn_start.setObjectName("btn_start")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_translate.setObjectName("btn_translate")
        self.btn_stop_translation.setObjectName("btn_stop_translation")
        self.btn_force_detection.setObjectName("btn_force_detection")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_translate.setEnabled(False)
        self.btn_force_detection.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_stop_translation.setEnabled(False)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        
        layout.addWidget(self.btn_select)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_translate)
        layout.addWidget(self.btn_stop_translation)
        layout.addWidget(self.btn_force_detection)
        layout.addWidget(self.btn_settings)
        self._apply_theme()
        
        self.btn_select.clicked.connect(self.on_select)
        self.btn_start.clicked.connect(self.on_start_overlay)
        self.btn_stop.clicked.connect(self.on_stop_overlay)
        self.btn_translate.clicked.connect(self.on_translate)
        self.btn_stop_translation.clicked.connect(self.on_stop_translation)
        self.btn_force_detection.clicked.connect(self.on_force_detection)
        self.btn_settings.clicked.connect(self.open_settings)
        
    def on_select(self):
        dialog = WindowSelectorDialog(self)
        if dialog.exec() == QDialog.Accepted:
            hwnd = dialog.get_selected_window()
            if hwnd:
                print(f"Ventana seleccionada: {hwnd}")
                self.btn_select.setText(f"Ventana: {hwnd}")
                self.update_preview(hwnd)
                self.window_selected = hwnd
                return self.window_selected
            else:
                print("No se seleccionó ninguna ventana.")
                self.preview_label.setText("No se seleccionó ninguna ventana")
                self._show_dialog("Aviso", "No se selecciono ninguna ventana objetivo.")
        
    def on_start_overlay(self):
        if not self.window_selected:
            print("No hay ventana seleccionada para superponer.")
            self._show_dialog("Aviso", "Selecciona una ventana antes de definir regiones de interes.")
            return
        
        if not self.overlay:
            self.overlay = WindowOverlay(0, 0, 100, 100)
            self.overlay.closed.connect(self.on_stop_overlay)
            self.overlay.rois_has_items.connect(self.on_overlay_rois_changed)

        self._apply_overlay_text_style(dict(self.overlay_text_style))

        self.overlay.set_mode("edit")
        self.overlay.show()
        start_native_overlay_tracking(
            self.window_selected,
            self.overlay,
            poll_interval_ms=app_settings.get_overlay_tracker_poll_interval_ms(),
            force_reanchor_ms=app_settings.get_overlay_tracker_force_reanchor_ms(),
        )
        
        # Validar aqui si active en pipeline es true, de ser asi llamar a stop_cycle para pausarlo mientras se define el ROI.
        if hasattr(self.pipeline_coordinator, "active") and self.pipeline_coordinator.active:
            print("Pausando ciclo de procesamiento para definir ROI...")
            self.pipeline_coordinator.stop_cycle()

        self.btn_start.setText("Definiendo ROI...")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_translate.setEnabled(self.has_overlay_rois())
        self._refresh_action_buttons()
        
    def on_stop_overlay(self):
        stop_native_overlay_tracking()

        if self.overlay:
            self.overlay.clear_roi_texts()
            self.overlay.hide()

        self.btn_start.setEnabled(True)
        self.btn_start.setText("Seleccionar regiones de interés (ROI)")
        self.btn_stop.setEnabled(False)
        self.btn_translate.setEnabled(False)
        self.btn_force_detection.setEnabled(False)
        print("Seleccion de ROI detenida.")

        if self.pipeline_coordinator:
            self.pipeline_coordinator.stop_cycle()
            print("Pipeline de procesamiento detenido.")
        
    def on_translate(self):
        print("Iniciando traducción...")
        if not self.overlay or not hasattr(self.overlay, "scene") or not self.overlay.scene.rois:
            print("No hay ROIs definidas para procesar OCR.")
            self._show_dialog("Aviso", "No hay regiones de interes definidas para iniciar la traduccion.")
            return

        self.btn_start.setText("Seleccionar regiones de interés (ROI)")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_translate.setEnabled(False)
        self.btn_stop_translation.setEnabled(True)
        if self.overlay.mode != "active":
            self.overlay.set_mode("active")
        if self.window_selected:
            print(f"Activando PipelineCoordinator para ventana {self.window_selected}...")
            try:
                worker_running = bool(
                    self.pipeline_coordinator
                    and getattr(self.pipeline_coordinator, "ocr_worker", None)
                    and self.pipeline_coordinator.ocr_worker.isRunning()
                )

                if not self.pipeline_coordinator or not worker_running:
                    if self.pipeline_coordinator:
                        self.pipeline_coordinator.shutdown()
                    self.pipeline_coordinator = PipelineCoordinator(self.window_selected, False, self)
                    self.pipeline_coordinator.text_detected.connect(self.on_text_detected)
                    self.pipeline_coordinator.text_normalized.connect(self.on_text_normalized)
                    self.pipeline_coordinator.text_ready.connect(self.on_text_ready)
                else:
                    self.pipeline_coordinator.hwnd = self.window_selected

                self.pipeline_coordinator.update_rois(self.overlay.scene.rois)
                self.pipeline_coordinator.start_cycle(app_settings.get_pipeline_poll_interval_ms())
                self._refresh_action_buttons()
            except Exception as e:
                print(f"Error al crear PipelineCoordinator: {e}")
                self._show_dialog("Error", f"No se pudo iniciar la traduccion.\n\nDetalle: {e}")

    def on_stop_translation(self):
        if self.pipeline_coordinator:
            print("Deteniendo traducción...")
            self.pipeline_coordinator.stop_cycle()
            self._refresh_action_buttons()
        self.btn_stop_translation.setEnabled(False)
        self.btn_force_detection.setEnabled(False)
        if self.overlay:
            self.overlay.set_mode(None)
        
    def on_force_detection(self):
        if not self.overlay or self.overlay.mode != "active" or not self.has_overlay_rois():
            print("Forzar detección no disponible: se requiere overlay activo con ROI definidas.")
            self._show_dialog(
                "Aviso",
                "Forzar deteccion requiere overlay activo y al menos una ROI definida.",
            )
            self._refresh_action_buttons()
            return

        if not self.pipeline_coordinator:
            try:
                self.pipeline_coordinator = PipelineCoordinator(self.window_selected, False, self)
                self.pipeline_coordinator.text_ready.connect(self.on_text_ready)
            except Exception as e:
                print(f"No se pudo inicializar PipelineCoordinator para forzar detección: {e}")
                self._show_dialog("Error", f"No se pudo forzar deteccion.\n\nDetalle: {e}")
                return

        self.pipeline_coordinator.hwnd = self.window_selected
        self.pipeline_coordinator.update_rois(self.overlay.scene.rois)

        dispatched = self.pipeline_coordinator.force_detection()
        if dispatched:
            print(f"Detección y traducción forzadas para {dispatched} ROI(s).")
        else:
            print("No se pudo forzar detección: no hubo ROIs válidas o falló la captura.")
            self._show_dialog(
                "Aviso",
                "No se pudo forzar deteccion porque no hubo ROIs validas o fallo la captura.",
            )
            
    def on_text_detected(self, roi_id, text):
        print("------------------------------------------")
        print(f"Texto detectado listo para ROI {roi_id}: {text}")
        if self.overlay and self.overlay.mode == "active":
            self.overlay.update_roi_text(roi_id, text)
            
    def on_text_normalized(self, roi_id, text):
        print(f"Texto normalizado listo para ROI {roi_id}: {text}")
        if self.overlay and self.overlay.mode == "active":
            self.overlay.update_roi_text(roi_id, text)
        
    def on_text_ready(self, roi_id, text):
        print(f"Texto traducido listo para ROI {roi_id}: {text}")
        if self.overlay and self.overlay.mode == "active":
            self.overlay.update_roi_text(roi_id, text)
        print("------------------------------------------")

    def has_overlay_rois(self):
        if not self.overlay or not hasattr(self.overlay, "scene"):
            return False
        return len(self.overlay.scene.rois) > 0

    def on_overlay_rois_changed(self, has_rois: bool):
        if not self.overlay:
            self.btn_translate.setEnabled(False)
            self.btn_force_detection.setEnabled(False)
            return
        self.btn_translate.setEnabled(self.overlay.mode == "edit" and has_rois)
        self._refresh_action_buttons()

    def _refresh_action_buttons(self):
        has_rois = self.has_overlay_rois()
        is_active_mode = bool(self.overlay and self.overlay.mode == "active")
        self.btn_force_detection.setEnabled(has_rois and is_active_mode)

    def closeEvent(self, event):
        stop_native_overlay_tracking()
        if self.pipeline_coordinator:
            self.pipeline_coordinator.shutdown()
        return super().closeEvent(event)

    def update_preview(self, hwnd):
        pixmap = capture_window(hwnd)
        if pixmap is None or pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("No se pudo capturar la ventana")
            self._show_dialog("Aviso", "No se pudo capturar la ventana seleccionada.")
            return

        self.preview_label.setText("")
        scaled_pixmap = pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled_pixmap)
    
    def open_settings(self):
        from app.ocr.engine import ocr_processor
        current = getattr(ocr_processor, "current_device", "CPUExecutionProvider")
        providers = getattr(ocr_processor, "get_selectable_providers", lambda: ("CPUExecutionProvider",))()
        if current not in providers and providers:
            current = providers[0]

        original_overlay_style = dict(self.overlay_text_style)
        
        dialog = SettingsDialog(
            current,
            self,
            providers_override=providers,
            initial_overlay_style=dict(self.overlay_text_style),
            initial_pipeline_settings=app_settings.get_pipeline_settings(),
            initial_translation_settings=app_settings.get_translation_settings(),
            initial_theme_mode=app_settings.get_theme_mode(),
        )
        dialog.settings_changed.connect(self.reinit_ocr_engine)
        dialog.overlay_text_style_changed.connect(self._apply_overlay_text_style)
        dialog.pipeline_settings_changed.connect(self._apply_pipeline_settings)
        dialog.translation_settings_changed.connect(self._apply_translation_settings)
        dialog.theme_mode_changed.connect(self._apply_theme_settings)

        if dialog.exec() == QDialog.Accepted:
            self.overlay_text_style = dialog.get_overlay_text_style()
            self._apply_overlay_text_style(dict(self.overlay_text_style))
            app_settings.set_overlay_text_style(self.overlay_text_style)
            app_settings.save_settings_to_disk()
            return

        self.overlay_text_style = original_overlay_style
        self._apply_overlay_text_style(dict(self.overlay_text_style))

    def _apply_overlay_text_style(self, style_updates):
        if not isinstance(style_updates, dict) or not style_updates:
            return

        previous_style = dict(self.overlay_text_style)
        self.overlay_text_style = app_settings.merge_overlay_text_style(
            self.overlay_text_style,
            style_updates,
        )

        if self.overlay:
            changed_keys = {
                key: value
                for key, value in self.overlay_text_style.items()
                if previous_style.get(key) != value
            }
            if changed_keys:
                self.overlay.configure_roi_text_style(**changed_keys)

    def _apply_pipeline_settings(self, pipeline_updates):
        if not isinstance(pipeline_updates, dict) or not pipeline_updates:
            return

        normalized = app_settings.set_pipeline_settings(pipeline_updates)
        if self.pipeline_coordinator:
            self.pipeline_coordinator.apply_runtime_settings(normalized)

    def _apply_translation_settings(self, translation_updates):
        if not isinstance(translation_updates, dict) or not translation_updates:
            return

        normalized = app_settings.set_translation_settings(translation_updates)
        try:
            from app.translation.translator import translator as translator_engine

            translator_engine.setup_translator()
            print(
                "Configuracion de traduccion aplicada: "
                f"{normalized['from_code']}->{normalized['to_code']}"
            )
        except Exception as e:
            print(f"No se pudo recargar el traductor con nueva configuracion: {e}")

    def _apply_theme_settings(self, theme_mode):
        self._theme_mode = app_settings.set_theme_mode(theme_mode)
        self._apply_theme()

    def _apply_theme(self):
        if self._applying_theme:
            return

        is_dark = resolve_dark_mode(self._theme_mode)
        main_stylesheet = get_main_window_stylesheet(is_dark)
        preview_stylesheet = get_preview_label_stylesheet(is_dark)

        if (
            self._is_dark_theme == is_dark
            and self._main_stylesheet_cache == main_stylesheet
            and self._preview_stylesheet_cache == preview_stylesheet
        ):
            return

        self._applying_theme = True
        try:
            self._is_dark_theme = is_dark

            if self._main_stylesheet_cache != main_stylesheet:
                self.setStyleSheet(main_stylesheet)
                self._main_stylesheet_cache = main_stylesheet

            if hasattr(self, "preview_label") and self._preview_stylesheet_cache != preview_stylesheet:
                self.preview_label.setStyleSheet(preview_stylesheet)
                self._preview_stylesheet_cache = preview_stylesheet
        finally:
            self._applying_theme = False
        
    def reinit_ocr_engine(self, new_provider):
        from app.ocr.engine import ocr_processor
        print(f"Reinicializando OCR Engine con nuevo provider: {new_provider}")

        was_active = False
        if self.pipeline_coordinator and self.pipeline_coordinator.active:
            was_active = True
            self.pipeline_coordinator.stop_cycle()

        try:
            ocr_processor.reinitialize(new_provider)
            app_settings.set_preferred_ocr_provider(ocr_processor.current_device)
            print(f"Provider activo: {ocr_processor.current_device}")
        except Exception as e:
            print(f"No se pudo aplicar provider {new_provider}: {e}")
        finally:
            if was_active:
                self.pipeline_coordinator.start_cycle(app_settings.get_pipeline_poll_interval_ms())

    def _show_dialog(self, title, message):
        notice = AppDialog(title, message, self)
        notice.exec()

    def changeEvent(self, event):
        if (
            not self._applying_theme
            and event.type() in (QEvent.ApplicationPaletteChange, QEvent.PaletteChange)
        ):
            if app_settings.get_theme_mode() == "auto":
                self._theme_mode = "auto"
                self._apply_theme()
        super().changeEvent(event)