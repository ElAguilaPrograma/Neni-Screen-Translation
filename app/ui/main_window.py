from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

from app.ui.window_selector import WindowSelectorDialog
from app.utils.win32_utils import (
    capture_window,
    start_native_overlay_tracking,
    stop_native_overlay_tracking,
)
from app.ui.overlay import WindowOverlay
from app.pipeline.coordinator import PipelineCoordinator
from app.ui.settings_gui import SettingsDialog

class MainWindow(QMainWindow):
    
    window_selected = None
    overlay: WindowOverlay = None
    pipeline_coordinator: PipelineCoordinator = None

    def __init__(self):
        super().__init__()

        self.overlay_text_style = {
            "font_size_px": 16,
            "background_rgba": (12, 18, 32, 212),
        }

        self.setWindowTitle("Screen Translator")
        self.setFixedSize(700, 600)
        
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
        self.btn_force_detection = QPushButton("Forza deteccion y traducción")
        self.btn_settings = QPushButton("Abrir Ajustes de OCR")
        
        self.btn_select.setObjectName("btn_select")
        self.btn_start.setObjectName("btn_start")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_translate.setObjectName("btn_translate")
        self.btn_force_detection.setObjectName("btn_force_detection")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_translate.setEnabled(False)
        self.btn_force_detection.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet(
            """
            QLabel {
                background-color: #ffffff;
                border: 1px dashed #cfcfcf;
                border-radius: 8px;
                color: #777;
            }
            """
        )
        
        layout.addWidget(self.btn_select)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_translate)
        layout.addWidget(self.btn_force_detection)
        layout.addWidget(self.btn_settings)
        # Estilos
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5; /* Fondo gris muy claro */
            }
            QPushButton {
                background-color: #ffffff;   /* Botones blancos */
                border: 1px solid #dcdcdc;  /* Borde gris fino */
                border-radius: 8px;          /* Esquinas redondeadas */
                padding: 10px;               /* Espacio interno para que el botón sea alto */
                font-size: 14px;
                color: #333;                 /* Texto gris oscuro */
            }
            QPushButton:hover {
                background-color: #eeeeee;   /* Color al pasar el ratón por encima */
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                border: 1px solid #d9d9d9;
                color: #9a9a9a;
            }
            /* Estilo específico para el botón que llamamos 'btn_start' */
            QPushButton#btn_start {
                background-color: #0078d4;   /* Azul estilo Windows/Mac */
                color: white;                /* Texto blanco */
                font-weight: bold;
                border: none;                /* Sin borde para que se vea más limpio */
            }
            QPushButton#btn_start:hover {
                background-color: #005a9e;   /* Azul más oscuro al pasar el ratón */
            }
            QPushButton#btn_start:disabled {
                background-color: #86b7e3;
                color: #eef5fb;
                border: none;
            }
            QPushButton#btn_select:hover {
                background-color: #e8f1fb;   /* Hover suave para selección de ventana */
                border-color: #9dc3e6;
            }
            QPushButton#btn_select:disabled {
                background-color: #f0f0f0;
                border-color: #d9d9d9;
                color: #9a9a9a;
            }
            QPushButton#btn_stop {
                background-color: #d13438;   /* Rojo para detener selección */
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_stop:hover {
                background-color: #a4262c;   /* Rojo más oscuro en hover */
            }
            QPushButton#btn_stop:disabled {
                background-color: #de8f91;
                color: #fdf3f3;
                border: none;
            }
            QPushButton#btn_translate {
                background-color: #107c10;   /* Verde para iniciar traducción */
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_translate:hover {
                background-color: #0b5a0b;   /* Verde más oscuro en hover */
            }
            QPushButton#btn_translate:disabled {
                background-color: #7eb57e;
                color: #f1faef;
                border: none;
            }
            QPushButton#btn_force_detection {
                background-color: #ff8c00;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_force_detection:hover {
                background-color: #cf7000;
            }
            QPushButton#btn_force_detection:disabled {
                background-color: #f2be83;
                color: #fff8ef;
                border: none;
            }
            QPushButton#btn_settings:hover {
                background-color: #f1f6fc;
                border-color: #a8c5e5;
            }
        """)
        
        self.btn_select.clicked.connect(self.on_select)
        self.btn_start.clicked.connect(self.on_start_overlay)
        self.btn_stop.clicked.connect(self.on_stop_overlay)
        self.btn_translate.clicked.connect(self.on_translate)
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
        
    def on_start_overlay(self):
        if not self.window_selected:
            print("No hay ventana seleccionada para superponer.")
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
            poll_interval_ms=16,
            force_reanchor_ms=800,
        )
        
        # Validar aqui si active en pipeline es true, de ser asi llamar a stop_cycle para pausarlo mientras se define el ROI.
        if hasattr(self.pipeline_coordinator, "active") and self.pipeline_coordinator.active:
            print("Pausando ciclo de procesamiento para definir ROI...")
            self.pipeline_coordinator.stop_cycle()

        self.btn_start.setText("Definiendo ROI... (Presiona Enter para confirmar)")
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
        print("Iniciando traducción... (funcionalidad no implementada)")
        if not self.overlay or not hasattr(self.overlay, "scene") or not self.overlay.scene.rois:
            print("No hay ROIs definidas para procesar OCR.")
            return

        self.btn_start.setText("Seleccionar regiones de interés (ROI)")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_translate.setEnabled(False)
        self.overlay.set_mode("active") 
        if self.window_selected:
            print(f"Activando PipelineCoordinator para ventana {self.window_selected}...")
            try:
                if not self.pipeline_coordinator:
                    self.pipeline_coordinator = PipelineCoordinator(self.window_selected, False, self)
                    self.pipeline_coordinator.text_detected.connect(self.on_text_detected)
                    self.pipeline_coordinator.text_normalized.connect(self.on_text_normalized)
                    self.pipeline_coordinator.text_ready.connect(self.on_text_ready)
                else:
                    self.pipeline_coordinator.hwnd = self.window_selected

                self.pipeline_coordinator.update_rois(self.overlay.scene.rois)
                self.pipeline_coordinator.start_cycle(400)
                self._refresh_action_buttons()
            except Exception as e:
                print(f"Error al crear PipelineCoordinator: {e}")

    def on_force_detection(self):
        if not self.overlay or self.overlay.mode != "active" or not self.has_overlay_rois():
            print("Forzar detección no disponible: se requiere overlay activo con ROI definidas.")
            self._refresh_action_buttons()
            return

        if not self.pipeline_coordinator:
            try:
                self.pipeline_coordinator = PipelineCoordinator(self.window_selected, False, self)
                self.pipeline_coordinator.text_ready.connect(self.on_text_ready)
            except Exception as e:
                print(f"No se pudo inicializar PipelineCoordinator para forzar detección: {e}")
                return

        self.pipeline_coordinator.hwnd = self.window_selected
        self.pipeline_coordinator.update_rois(self.overlay.scene.rois)

        dispatched = self.pipeline_coordinator.force_detection()
        if dispatched:
            print(f"Detección y traducción forzadas para {dispatched} ROI(s).")
        else:
            print("No se pudo forzar detección: no hubo ROIs válidas o falló la captura.")
            
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
            return

        self.preview_label.setText("")
        scaled_pixmap = pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled_pixmap)
        
    def keyPressEvent(self, event):
        if not self.window_selected:
            print("No hay ventana seleccionada para iniciar la selección de ROI.")
            return 
        
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.overlay and self.overlay.mode == "edit":
                print("Ya estas en modo edición, presionando Enter para confirmar la selección...")
            if event.modifiers() & Qt.AltModifier:
                print("Alt + Enter presionado: Iniciando selección de ROI...")
                if self.overlay:
                    self.overlay.set_mode("edit")
                else:
                    print("Se esta creando de nuevo?")
                    self.on_start_overlay()
        return super().keyPressEvent(event)
    
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
        )
        dialog.settings_changed.connect(self.reinit_ocr_engine)
        dialog.overlay_text_style_changed.connect(self._apply_overlay_text_style)

        if dialog.exec() == QDialog.Accepted:
            self.overlay_text_style = dialog.get_overlay_text_style()
            self._apply_overlay_text_style(dict(self.overlay_text_style))
            return

        self.overlay_text_style = original_overlay_style
        self._apply_overlay_text_style(dict(self.overlay_text_style))

    def _apply_overlay_text_style(self, style_updates):
        if not isinstance(style_updates, dict) or not style_updates:
            return

        self.overlay_text_style.update(style_updates)
        if self.overlay:
            self.overlay.configure_roi_text_style(**style_updates)
        
    def reinit_ocr_engine(self, new_provider):
        from app.ocr.engine import ocr_processor
        print(f"Reinicializando OCR Engine con nuevo provider: {new_provider}")

        was_active = False
        if self.pipeline_coordinator and self.pipeline_coordinator.active:
            was_active = True
            self.pipeline_coordinator.stop_cycle()

        try:
            ocr_processor.reinitialize(new_provider)
            print(f"Provider activo: {ocr_processor.current_device}")
        except Exception as e:
            print(f"No se pudo aplicar provider {new_provider}: {e}")
        finally:
            if was_active:
                self.pipeline_coordinator.start_cycle(400)