import onnxruntime as ort
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame, QSpacerItem, QSizePolicy,
                             QSpinBox, QSlider, QColorDialog, QDoubleSpinBox,
                             QLineEdit, QCheckBox, QScrollArea, QWidget)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from app import settings as app_settings

# Aqui manejare las opciones de configuracion globales, como el OCR engine, modelo de traducción,
# usar o no GPU, color de fondo del overlay, opacidad del overlay, etc.
# y otras cosas que puedan ser necesarias en varias partes de la app. 

class SettingsDialog(QDialog):
    # Señal para indicar el provider seleccionado 
    settings_changed = Signal(str)
    overlay_text_style_changed = Signal(dict)
    pipeline_settings_changed = Signal(dict)
    translation_settings_changed = Signal(dict)
    
    def __init__(
        self,
        current_device,
        parent=None,
        providers_override=None,
        initial_overlay_style=None,
        initial_pipeline_settings=None,
        initial_translation_settings=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setFixedSize(*app_settings.UI_SIZES["settings_dialog"])
        self.current_device = current_device
        self.providers_override = list(providers_override) if providers_override else None
        self.overlay_style = app_settings.get_default_overlay_text_style()
        if isinstance(initial_overlay_style, dict):
            self.overlay_style = app_settings.merge_overlay_text_style(
                self.overlay_style,
                initial_overlay_style,
            )
        self.pipeline_settings = app_settings.normalize_pipeline_settings(initial_pipeline_settings)
        self.translation_settings = app_settings.normalize_translation_settings(initial_translation_settings)

        bg_rgba = self.overlay_style.get("background_rgba", app_settings.DEFAULT_OVERLAY_TEXT_STYLE["background_rgba"])
        if len(bg_rgba) == 4:
            self._bg_color = QColor(int(bg_rgba[0]), int(bg_rgba[1]), int(bg_rgba[2]))
            self._bg_opacity = int(bg_rgba[3])
        else:
            default_rgba = app_settings.DEFAULT_OVERLAY_TEXT_STYLE["background_rgba"]
            self._bg_color = QColor(int(default_rgba[0]), int(default_rgba[1]), int(default_rgba[2]))
            self._bg_opacity = int(default_rgba[3])

        self._is_ready = False
        
        self.init_ui()
        self.load_providers()
        self._sync_overlay_controls_from_style()
        self._sync_pipeline_controls_from_settings()
        self._sync_translation_controls_from_settings()
        self._is_ready = True
        self._emit_overlay_preview()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setContentsMargins(0, 0, 0, 0)
        scroll_area.viewport().setContentsMargins(0, 0, 0, 0)

        content_widget = QWidget()
        content_widget.setObjectName("settings_scroll_content")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
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
        self.spin_font_size.setRange(*app_settings.OVERLAY_FONT_SIZE_RANGE)
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
        self.slider_bg_opacity.setRange(*app_settings.OVERLAY_BG_OPACITY_RANGE)
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

        pipeline_header = QLabel("Pipeline OCR")
        pipeline_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(pipeline_header)

        pipeline_card = QFrame()
        pipeline_card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            """
        )
        pipeline_layout = QVBoxLayout(pipeline_card)
        pipeline_layout.setSpacing(10)

        poll_layout = QHBoxLayout()
        poll_label = QLabel("Intervalo de captura:")
        self.spin_poll_interval = QSpinBox()
        self.spin_poll_interval.setRange(100, 5000)
        self.spin_poll_interval.setSingleStep(25)
        self.spin_poll_interval.setSuffix(" ms")
        self.spin_poll_interval.setMinimumWidth(140)
        poll_layout.addWidget(poll_label)
        poll_layout.addWidget(self.spin_poll_interval)
        poll_layout.addStretch()
        pipeline_layout.addLayout(poll_layout)

        pending_layout = QHBoxLayout()
        pending_label = QLabel("ROIs pendientes max:")
        self.spin_max_pending_rois = QSpinBox()
        self.spin_max_pending_rois.setRange(1, 128)
        self.spin_max_pending_rois.setSingleStep(1)
        self.spin_max_pending_rois.setMinimumWidth(140)
        pending_layout.addWidget(pending_label)
        pending_layout.addWidget(self.spin_max_pending_rois)
        pending_layout.addStretch()
        pipeline_layout.addLayout(pending_layout)

        ratio_layout = QHBoxLayout()
        ratio_label = QLabel("Umbral cambio frame:")
        self.spin_min_changed_ratio = QDoubleSpinBox()
        self.spin_min_changed_ratio.setRange(0.0, 1.0)
        self.spin_min_changed_ratio.setDecimals(3)
        self.spin_min_changed_ratio.setSingleStep(0.005)
        self.spin_min_changed_ratio.setMinimumWidth(140)
        ratio_layout.addWidget(ratio_label)
        ratio_layout.addWidget(self.spin_min_changed_ratio)
        ratio_layout.addStretch()
        pipeline_layout.addLayout(ratio_layout)

        quant_layout = QHBoxLayout()
        quant_label = QLabel("Nivel de cuantización:")
        self.spin_quant_step = QSpinBox()
        self.spin_quant_step.setRange(0, 7)
        self.spin_quant_step.setSingleStep(1)
        self.spin_quant_step.setMinimumWidth(140)
        quant_layout.addWidget(quant_label)
        quant_layout.addWidget(self.spin_quant_step)
        quant_layout.addStretch()
        pipeline_layout.addLayout(quant_layout)

        signature_layout = QHBoxLayout()
        signature_label = QLabel("Firma max lado:")
        self.spin_max_signature_side = QSpinBox()
        self.spin_max_signature_side.setRange(16, 512)
        self.spin_max_signature_side.setSingleStep(8)
        self.spin_max_signature_side.setSuffix(" px")
        self.spin_max_signature_side.setMinimumWidth(140)
        signature_layout.addWidget(signature_label)
        signature_layout.addWidget(self.spin_max_signature_side)
        signature_layout.addStretch()
        pipeline_layout.addLayout(signature_layout)

        pipeline_hint = QLabel("Ajustes de rendimiento OCR: aplicar con cuidado para evitar latencia o ruido.")
        pipeline_hint.setWordWrap(True)
        pipeline_hint.setStyleSheet("color: #5f6b76; font-size: 12px;")
        pipeline_layout.addWidget(pipeline_hint)

        layout.addWidget(pipeline_card)

        translation_header = QLabel("Traducción")
        translation_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(translation_header)

        translation_card = QFrame()
        translation_card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            """
        )
        translation_layout = QVBoxLayout(translation_card)
        translation_layout.setSpacing(10)

        source_lang_layout = QHBoxLayout()
        source_lang_label = QLabel("Idioma origen:")
        self.edit_translation_from = QLineEdit()
        self.edit_translation_from.setMaxLength(8)
        self.edit_translation_from.setMinimumWidth(140)
        source_lang_layout.addWidget(source_lang_label)
        source_lang_layout.addWidget(self.edit_translation_from)
        source_lang_layout.addStretch()
        translation_layout.addLayout(source_lang_layout)

        target_lang_layout = QHBoxLayout()
        target_lang_label = QLabel("Idioma destino:")
        self.edit_translation_to = QLineEdit()
        self.edit_translation_to.setMaxLength(8)
        self.edit_translation_to.setMinimumWidth(140)
        target_lang_layout.addWidget(target_lang_label)
        target_lang_layout.addWidget(self.edit_translation_to)
        target_lang_layout.addStretch()
        translation_layout.addLayout(target_lang_layout)

        cache_layout = QHBoxLayout()
        cache_label = QLabel("Límite de caché:")
        self.spin_translation_cache_limit = QSpinBox()
        self.spin_translation_cache_limit.setRange(32, 32768)
        self.spin_translation_cache_limit.setSingleStep(64)
        self.spin_translation_cache_limit.setMinimumWidth(140)
        cache_layout.addWidget(cache_label)
        cache_layout.addWidget(self.spin_translation_cache_limit)
        cache_layout.addStretch()
        translation_layout.addLayout(cache_layout)

        self.check_auto_install_package = QCheckBox("Instalar paquete de idioma automáticamente")
        translation_layout.addWidget(self.check_auto_install_package)

        translation_hint = QLabel("Si cambias idioma, se recargará el motor de traducción al aplicar ajustes.")
        translation_hint.setWordWrap(True)
        translation_hint.setStyleSheet("color: #5f6b76; font-size: 12px;")
        translation_layout.addWidget(translation_hint)

        layout.addWidget(translation_card)
        
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area)

        buttons_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_apply = QPushButton("Aplicar Cambios")
        self.btn_apply.setObjectName("btn_save")

        # Estilos del dialogo + botones (evita texto invisible en temas oscuros).
        self.setStyleSheet("""
            QDialog {
                background: #f5f5f5;
            }
            QScrollArea {
                border: none;
                background: #f5f5f5;
            }
            QWidget#settings_scroll_content {
                background: #f5f5f5;
            }
            QLabel {
                color: #222;
                background: transparent;
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
            QDoubleSpinBox {
                background: #ffffff;
                color: #222;
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QLineEdit {
                background: #ffffff;
                color: #222;
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QCheckBox {
                color: #222;
            }
            QScrollBar:vertical {
                background: #ececec;
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #b8b8b8;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #979797;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                height: 0;
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
        root_layout.addLayout(buttons_layout)

        self.spin_font_size.valueChanged.connect(self._on_overlay_control_changed)
        self.slider_bg_opacity.valueChanged.connect(self._on_overlay_control_changed)
        self.btn_bg_color.clicked.connect(self._on_pick_background_color)
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self.accept_settings)

    def _sync_overlay_controls_from_style(self):
        font_min, font_max = app_settings.OVERLAY_FONT_SIZE_RANGE
        opacity_min, opacity_max = app_settings.OVERLAY_BG_OPACITY_RANGE
        font_size = int(self.overlay_style.get("font_size_px", app_settings.DEFAULT_OVERLAY_TEXT_STYLE["font_size_px"]))
        self.spin_font_size.setValue(max(font_min, min(font_max, font_size)))
        self.slider_bg_opacity.setValue(max(opacity_min, min(opacity_max, int(self._bg_opacity))))
        self._update_color_button()
        self._update_opacity_label()

    def _sync_pipeline_controls_from_settings(self):
        self.spin_poll_interval.setValue(int(self.pipeline_settings.get("poll_interval_ms", 400)))
        self.spin_max_pending_rois.setValue(int(self.pipeline_settings.get("max_pending_rois", 8)))
        self.spin_min_changed_ratio.setValue(float(self.pipeline_settings.get("min_changed_ratio", 0.01)))
        self.spin_quant_step.setValue(int(self.pipeline_settings.get("quant_step", 3)))
        self.spin_max_signature_side.setValue(int(self.pipeline_settings.get("max_signature_side", 96)))

    def _sync_translation_controls_from_settings(self):
        self.edit_translation_from.setText(str(self.translation_settings.get("from_code", "en")))
        self.edit_translation_to.setText(str(self.translation_settings.get("to_code", "es")))
        self.spin_translation_cache_limit.setValue(int(self.translation_settings.get("cache_limit", 1024)))
        self.check_auto_install_package.setChecked(bool(self.translation_settings.get("auto_install_package", True)))

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
        composed_style = dict(self.overlay_style)
        composed_style.update(
            {
                "font_size_px": int(self.spin_font_size.value()),
                "background_rgba": (
                    int(self._bg_color.red()),
                    int(self._bg_color.green()),
                    int(self._bg_color.blue()),
                    alpha,
                ),
            }
        )
        return app_settings.normalize_overlay_text_style(composed_style)

    def _compose_pipeline_settings(self):
        composed = {
            "poll_interval_ms": int(self.spin_poll_interval.value()),
            "max_pending_rois": int(self.spin_max_pending_rois.value()),
            "min_changed_ratio": float(self.spin_min_changed_ratio.value()),
            "quant_step": int(self.spin_quant_step.value()),
            "max_signature_side": int(self.spin_max_signature_side.value()),
        }
        return app_settings.normalize_pipeline_settings(composed)

    def _compose_translation_settings(self):
        composed = {
            "from_code": self.edit_translation_from.text().strip().lower(),
            "to_code": self.edit_translation_to.text().strip().lower(),
            "cache_limit": int(self.spin_translation_cache_limit.value()),
            "auto_install_package": bool(self.check_auto_install_package.isChecked()),
        }
        return app_settings.normalize_translation_settings(composed)

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

        for provider in providers:
            if provider in app_settings.OCR_PROVIDER_LABELS:
                self.combo_devices.addItem(app_settings.OCR_PROVIDER_LABELS[provider], provider)

        if self.combo_devices.count() == 0:
            self.combo_devices.addItem(
                app_settings.OCR_PROVIDER_LABELS["CPUExecutionProvider"],
                "CPUExecutionProvider",
            )

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
        self.pipeline_settings = self._compose_pipeline_settings()
        self.translation_settings = self._compose_translation_settings()
        self.pipeline_settings_changed.emit(dict(self.pipeline_settings))
        self.translation_settings_changed.emit(dict(self.translation_settings))
        self.accept()