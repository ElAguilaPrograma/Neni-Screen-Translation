import logging
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


logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    
    window_selected = None
    overlay: WindowOverlay = None
    pipeline_coordinator: PipelineCoordinator = None

    def __init__(self):
        super().__init__()

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
        
        self.btn_select.setObjectName("btn_select")
        self.btn_start.setObjectName("btn_start")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_translate.setObjectName("btn_translate")
        self.btn_translate.setEnabled(False)
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
        """)
        
        self.btn_select.clicked.connect(self.on_select)
        self.btn_start.clicked.connect(self.on_start_overlay)
        self.btn_stop.clicked.connect(self.on_stop_overlay)
        self.btn_translate.clicked.connect(self.on_translate)
        
    def on_select(self):
        dialog = WindowSelectorDialog(self)
        if dialog.exec() == QDialog.Accepted:
            hwnd = dialog.get_selected_window()
            if hwnd:
                logger.info("Ventana seleccionada: %s", hwnd)
                self.btn_select.setText(f"Ventana: {hwnd}")
                self.update_preview(hwnd)
                self.window_selected = hwnd
                return self.window_selected
            else:
                logger.warning("No se seleccionó ninguna ventana.")
                self.preview_label.setText("No se seleccionó ninguna ventana")
        
    def on_start_overlay(self):
        if not self.window_selected:
            logger.warning("No hay ventana seleccionada para superponer.")
            return
        
        if not self.overlay:
            self.overlay = WindowOverlay(0, 0, 100, 100)
            self.overlay.closed.connect(self.on_stop_overlay)
            self.overlay.rois_has_items.connect(self.on_overlay_rois_changed)

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
            logger.info("Pausando ciclo de procesamiento para definir ROI...")
            self.pipeline_coordinator.stop_cycle()

        self.btn_start.setText("Definiendo ROI... (Presiona Enter para confirmar)")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_translate.setEnabled(self.has_overlay_rois())
        
    def on_stop_overlay(self):
        stop_native_overlay_tracking()

        if self.overlay:
            self.overlay.hide()

        self.btn_start.setEnabled(True)
        self.btn_start.setText("Seleccionar regiones de interés (ROI)")
        self.btn_stop.setEnabled(False)
        self.btn_translate.setEnabled(False)
        logger.info("Selección de ROI detenida.")
        
        PipelineCoordinator.stop_cycle(self.pipeline_coordinator)
        logger.info("Pipeline de procesamiento detenido.")
        
    def on_translate(self):
        logger.info("Iniciando traducción... (funcionalidad no implementada)")
        if not self.overlay or not hasattr(self.overlay, "scene") or not self.overlay.scene.rois:
            logger.warning("No hay ROIs definidas para procesar OCR.")
            return

        self.btn_start.setText("Seleccionar regiones de interés (ROI)")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_translate.setEnabled(False)
        self.overlay.set_mode("active") 
        if self.window_selected:
            logger.info("Creando PipelineCoordinator para ventana %s...", self.window_selected)
            try:
                self.pipeline_coordinator = PipelineCoordinator(self.window_selected, True)
                self.pipeline_coordinator.text_ready.connect(self.on_text_ready)
                self.pipeline_coordinator.update_rois(self.overlay.scene.rois)
            except Exception as e:
                logger.exception("Error al crear PipelineCoordinator.")
        
    def on_text_ready(self, roi_id, text):
        logger.debug("Texto OCR listo para ROI %s: %s", roi_id, text)
        

    def has_overlay_rois(self):
        if not self.overlay or not hasattr(self.overlay, "scene"):
            return False
        return len(self.overlay.scene.rois) > 0

    def on_overlay_rois_changed(self, has_rois: bool):
        if not self.overlay:
            self.btn_translate.setEnabled(False)
            return
        self.btn_translate.setEnabled(self.overlay.mode == "edit" and has_rois)

    def closeEvent(self, event):
        stop_native_overlay_tracking()
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
            logger.warning("No hay ventana seleccionada para iniciar la selección de ROI.")
            return 
        
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.overlay and self.overlay.mode == "edit":
                logger.debug("Ya estas en modo edición, presionando Enter para confirmar la selección...")
            if event.modifiers() & Qt.AltModifier:
                logger.info("Alt + Enter presionado: Iniciando selección de ROI...")
                if self.overlay:
                    self.overlay.set_mode("edit")
                else:
                    logger.warning("Se esta creando de nuevo?")
                    self.on_start_overlay()
        return super().keyPressEvent(event)