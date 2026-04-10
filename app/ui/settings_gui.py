import onnxruntime as ort
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame, QSpacerItem, QSizePolicy,
                             QSpinBox, QSlider, QColorDialog)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

# Aqui manejare las opciones de configuracion globales, como el OCR engine, modelo de traducción,
# usar o no GPU, color de fondo del overlay, opacidad del overlay, etc.
# y otras cosas que puedan ser necesarias en varias partes de la app. 

class SettingsDialog(QDialog):
    # Señal para indicar el provider seleccionado 
    settings_changed = Signal(str)
    overlay_text_style_changed = Signal(dict)
    _DEFAULT_OVERLAY_STYLE = {
        "font_size_px": 16,
        "background_rgba": (12, 18, 32, 212),
    }
    
    def __init__(self, current_device, parent=None, providers_override=None, initial_overlay_style=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setFixedSize(520, 430)
        self.current_device = current_device
        self.providers_override = list(providers_override) if providers_override else None
        self.overlay_style = dict(self._DEFAULT_OVERLAY_STYLE)
        if isinstance(initial_overlay_style, dict):
            self.overlay_style.update(initial_overlay_style)

        bg_rgba = self.overlay_style.get("background_rgba", (12, 18, 32, 212))
        if len(bg_rgba) == 4:
            self._bg_color = QColor(int(bg_rgba[0]), int(bg_rgba[1]), int(bg_rgba[2]))
            self._bg_opacity = int(bg_rgba[3])
        else:
            self._bg_color = QColor(12, 18, 32)
            self._bg_opacity = 212

        self._is_ready = False
        
        self.init_ui()
        self.load_providers()
        self._sync_overlay_controls_from_style()
        self._is_ready = True
        self._emit_overlay_preview()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Sección de aceleración
        header = QLabel("Aceleración de Hardware")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(header)
        
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)

        # Selector de Dispositivo
        device_layout = QHBoxLayout()
        self.label_info = QLabel("Motor de ejecución:")
        self.combo_devices = QComboBox()
        self.combo_devices.setMinimumWidth(200)
        
        device_layout.addWidget(self.label_info)
        device_layout.addWidget(self.combo_devices)
        card_layout.addLayout(device_layout)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        card_layout.addWidget(self.label_status)
        
        layout.addWidget(card)

        # Sección visual de traducción sobre ROI
        overlay_header = QLabel("Texto de Traducción en Overlay")
        overlay_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(overlay_header)

        overlay_card = QFrame()
        overlay_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)
        overlay_layout = QVBoxLayout(overlay_card)
        overlay_layout.setSpacing(10)

        font_layout = QHBoxLayout()
        font_label = QLabel("Tamaño del texto:")
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(10, 42)
        self.spin_font_size.setSingleStep(1)
        self.spin_font_size.setSuffix(" px")
        self.spin_font_size.setMinimumWidth(120)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.spin_font_size)
        font_layout.addStretch()
        overlay_layout.addLayout(font_layout)

        color_layout = QHBoxLayout()
        color_label = QLabel("Color de fondo:")
        self.btn_bg_color = QPushButton("Elegir color")
        self.btn_bg_color.setObjectName("btn_color")
        self.btn_bg_color.setMinimumWidth(140)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.btn_bg_color)
        color_layout.addStretch()
        overlay_layout.addLayout(color_layout)

        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Opacidad del fondo:")
        self.slider_bg_opacity = QSlider(Qt.Horizontal)
        self.slider_bg_opacity.setRange(35, 255)
        self.slider_bg_opacity.setSingleStep(5)
        self.slider_bg_opacity.setPageStep(10)
        self.label_opacity_value = QLabel("0%")
        self.label_opacity_value.setMinimumWidth(42)
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.slider_bg_opacity)
        opacity_layout.addWidget(self.label_opacity_value)
        overlay_layout.addLayout(opacity_layout)

        self.overlay_hint = QLabel("Los cambios se aplican en tiempo real al overlay.")
        self.overlay_hint.setWordWrap(True)
        self.overlay_hint.setStyleSheet("color: #5f6b76; font-size: 12px;")
        overlay_layout.addWidget(self.overlay_hint)

        layout.addWidget(overlay_card)
        
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        buttons_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_apply = QPushButton("Aplicar Cambios")
        self.btn_apply.setObjectName("btn_save")

        # Estilos del dialogo + botones (evita texto invisible en temas oscuros).
        self.setStyleSheet("""
            QDialog {
                background: #f5f5f5;
            }
            QLabel {
                color: #222;
            }
            QComboBox {
                background: #ffffff;
                color: #222;
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #222;
                selection-background-color: #dbeeff;
                selection-color: #111;
                border: 1px solid #c8c8c8;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                border: 1px solid #ccc;
                background: #f9f9f9;
                color: #222;
            }
            QPushButton#btn_save {
                background: #0078d4;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_color {
                color: #111;
                font-weight: 600;
            }
            QPushButton#btn_save:hover { background: #005a9e; }
            QSpinBox {
                background: #ffffff;
                color: #222;
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #c8c8c8;
                height: 6px;
                border-radius: 3px;
                background: #e8e8e8;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: #0078d4;
            }
        """)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_apply)
        layout.addLayout(buttons_layout)

        self.spin_font_size.valueChanged.connect(self._on_overlay_control_changed)
        self.slider_bg_opacity.valueChanged.connect(self._on_overlay_control_changed)
        self.btn_bg_color.clicked.connect(self._on_pick_background_color)
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self.accept_settings)

    def _sync_overlay_controls_from_style(self):
        font_size = int(self.overlay_style.get("font_size_px", 16))
        self.spin_font_size.setValue(max(10, min(42, font_size)))
        self.slider_bg_opacity.setValue(max(35, min(255, int(self._bg_opacity))))
        self._update_color_button()
        self._update_opacity_label()

    def _update_color_button(self):
        preview_color = self._bg_color.name()
        self.btn_bg_color.setStyleSheet(
            "QPushButton#btn_color {"
            f"background: {preview_color};"
            "border: 1px solid #c8c8c8;"
            "color: #111;"
            "font-weight: 600;"
            "}"
        )

    def _update_opacity_label(self):
        alpha = int(self.slider_bg_opacity.value())
        self.label_opacity_value.setText(f"{round(alpha * 100 / 255)}%")

    def _compose_overlay_style(self):
        alpha = int(self.slider_bg_opacity.value())
        return {
            "font_size_px": int(self.spin_font_size.value()),
            "background_rgba": (
                int(self._bg_color.red()),
                int(self._bg_color.green()),
                int(self._bg_color.blue()),
                alpha,
            ),
        }

    def _emit_overlay_preview(self):
        if not self._is_ready:
            return
        self.overlay_style = self._compose_overlay_style()
        self.overlay_text_style_changed.emit(dict(self.overlay_style))

    def _on_overlay_control_changed(self):
        self._update_opacity_label()
        self._emit_overlay_preview()

    def _on_pick_background_color(self):
        selected = QColorDialog.getColor(self._bg_color, self, "Selecciona color de fondo")
        if not selected.isValid():
            return
        self._bg_color = selected
        self._update_color_button()
        self._emit_overlay_preview()

    def get_overlay_text_style(self):
        return dict(self._compose_overlay_style())

    def load_providers(self):
        providers = self.providers_override if self.providers_override is not None else ort.get_available_providers()
        
        self.provider_map = {
            "CUDAExecutionProvider": "NVIDIA GPU (CUDA)",
            "DmlExecutionProvider": "Graficos Integrados (DirectML)",
            "CPUExecutionProvider": "Procesador (CPU)",
        }

        for provider in providers:
            if provider in self.provider_map:
                self.combo_devices.addItem(self.provider_map[provider], provider)

        if self.combo_devices.count() == 0:
            self.combo_devices.addItem(self.provider_map["CPUExecutionProvider"], "CPUExecutionProvider")

        index = self.combo_devices.findData(self.current_device)
        if index >= 0:
            self.combo_devices.setCurrentIndex(index)
        else:
            cpu_index = self.combo_devices.findData("CPUExecutionProvider")
            if cpu_index >= 0:
                self.combo_devices.setCurrentIndex(cpu_index)

        self._set_provider_status(providers)

    def _set_provider_status(self, providers):
        has_cuda = "CUDAExecutionProvider" in providers
        has_dml = "DmlExecutionProvider" in providers

        if has_cuda or has_dml:
            options = []
            if has_cuda:
                options.append("CUDA")
            if has_dml:
                options.append("DirectML")
            self.label_status.setText(
                "Aceleración disponible: " + ", ".join(options)
            )
            self.label_status.setStyleSheet("color: #1a6b1a;")
            return

        self.label_status.setText(
            "Solo CPU disponible. Instala un runtime con GPU para habilitar más opciones."
        )
        self.label_status.setStyleSheet("color: #8a6d00;")

    def accept_settings(self):
        selected_provider = self.combo_devices.currentData()
        self.settings_changed.emit(selected_provider)
        self.overlay_style = self._compose_overlay_style()
        self.accept()