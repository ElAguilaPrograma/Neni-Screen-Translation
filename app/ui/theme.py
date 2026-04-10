import sys


def _is_windows_dark_mode() -> bool:
    if sys.platform != "win32":
        return False

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except Exception:
        return False


def resolve_dark_mode(theme_mode: str) -> bool:
    mode = str(theme_mode or "auto").strip().lower()
    if mode == "dark":
        return True
    if mode == "light":
        return False
    return _is_windows_dark_mode()


def get_preview_label_stylesheet(is_dark: bool) -> str:
    if is_dark:
        return (
            "QLabel {"
            "background-color: #252525;"
            "border: 1px dashed #4b4b4b;"
            "border-radius: 8px;"
            "color: #b8b8b8;"
            "}"
        )

    return (
        "QLabel {"
        "background-color: #ffffff;"
        "border: 1px dashed #cfcfcf;"
        "border-radius: 8px;"
        "color: #777;"
        "}"
    )


def get_main_window_stylesheet(is_dark: bool) -> str:
    if is_dark:
        return """
            QMainWindow {
                background-color: #1f1f1f;
            }
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #ececec;
            }
            QPushButton:hover {
                background-color: #353535;
            }
            QPushButton:disabled {
                background-color: #252525;
                border: 1px solid #353535;
                color: #737373;
            }
            QPushButton#btn_start {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_start:hover {
                background-color: #005a9e;
            }
            QPushButton#btn_start:disabled {
                background-color: #315f86;
                color: #b9d5ea;
                border: none;
            }
            QPushButton#btn_select:hover {
                background-color: #2f3c49;
                border-color: #4b647e;
            }
            QPushButton#btn_select:disabled {
                background-color: #252525;
                border-color: #353535;
                color: #737373;
            }
            QPushButton#btn_stop {
                background-color: #d13438;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_stop:hover {
                background-color: #a4262c;
            }
            QPushButton#btn_stop:disabled {
                background-color: #6f3b3d;
                color: #d8bcbc;
                border: none;
            }
            QPushButton#btn_translate {
                background-color: #107c10;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_translate:hover {
                background-color: #0b5a0b;
            }
            QPushButton#btn_translate:disabled {
                background-color: #426a42;
                color: #c8d8c8;
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
                background-color: #7c5d36;
                color: #dccfbf;
                border: none;
            }
            QPushButton#btn_settings:hover {
                background-color: #29313a;
                border-color: #4b5d70;
            }
            QPushButton#btn_stop_translation {
                background-color: #8b5cf6;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_stop_translation:hover {
                background-color: #7c3aed;
            }
            QPushButton#btn_stop_translation:disabled {
                background-color: #5b4c82;
                color: #cfc6e5;
                border: none;
            }
        """

    return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #dcdcdc;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
            color: #333;
        }
        QPushButton:hover {
            background-color: #eeeeee;
        }
        QPushButton:disabled {
            background-color: #f0f0f0;
            border: 1px solid #d9d9d9;
            color: #9a9a9a;
        }
        QPushButton#btn_start {
            background-color: #0078d4;
            color: white;
            font-weight: bold;
            border: none;
        }
        QPushButton#btn_start:hover {
            background-color: #005a9e;
        }
        QPushButton#btn_start:disabled {
            background-color: #86b7e3;
            color: #eef5fb;
            border: none;
        }
        QPushButton#btn_select:hover {
            background-color: #e8f1fb;
            border-color: #9dc3e6;
        }
        QPushButton#btn_select:disabled {
            background-color: #f0f0f0;
            border-color: #d9d9d9;
            color: #9a9a9a;
        }
        QPushButton#btn_stop {
            background-color: #d13438;
            color: white;
            font-weight: bold;
            border: none;
        }
        QPushButton#btn_stop:hover {
            background-color: #a4262c;
        }
        QPushButton#btn_stop:disabled {
            background-color: #de8f91;
            color: #fdf3f3;
            border: none;
        }
        QPushButton#btn_translate {
            background-color: #107c10;
            color: white;
            font-weight: bold;
            border: none;
        }
        QPushButton#btn_translate:hover {
            background-color: #0b5a0b;
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
        QPushButton#btn_stop_translation {
            background-color: #8b5cf6;
            color: white;
            font-weight: bold;
            border: none;
        }
        QPushButton#btn_stop_translation:hover {
            background-color: #7c3aed;
        }
        QPushButton#btn_stop_translation:disabled {
            background-color: #c4b5fd;
            color: #f5f3ff;
            border: none;
        }
    """


def get_settings_dialog_stylesheet(is_dark: bool) -> str:
    if is_dark:
        return """
            QDialog {
                background: #1f1f1f;
            }
            QScrollArea {
                border: none;
                background: #1f1f1f;
            }
            QWidget#settings_scroll_content {
                background: #1f1f1f;
            }
            QLabel {
                color: #e6e6e6;
                background: transparent;
            }
            QLabel#section_header {
                font-size: 16px;
                font-weight: bold;
                color: #f4f4f4;
            }
            QLabel#section_hint {
                color: #a7b5c2;
                font-size: 12px;
            }
            QLabel#theme_status {
                color: #b9c6d2;
            }
            QFrame#section_card {
                background-color: #292929;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
            QComboBox {
                background: #2f2f2f;
                color: #ececec;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background: #2f2f2f;
                color: #ececec;
                selection-background-color: #3c5a78;
                selection-color: #f2f2f2;
                border: 1px solid #4a4a4a;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                border: 1px solid #4a4a4a;
                background: #323232;
                color: #ececec;
            }
            QPushButton#btn_save {
                background: #0078d4;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_color {
                color: #f0f0f0;
                font-weight: 600;
            }
            QPushButton#btn_save:hover { background: #005a9e; }
            QSpinBox {
                background: #2f2f2f;
                color: #ececec;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QDoubleSpinBox {
                background: #2f2f2f;
                color: #ececec;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QLineEdit {
                background: #2f2f2f;
                color: #ececec;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QCheckBox {
                color: #e6e6e6;
            }
            QScrollBar:vertical {
                background: #292929;
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #696969;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                height: 0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4a4a4a;
                height: 6px;
                border-radius: 3px;
                background: #3a3a3a;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: #3da4ff;
            }
        """

    return """
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
        QLabel#section_header {
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }
        QLabel#section_hint {
            color: #5f6b76;
            font-size: 12px;
        }
        QLabel#theme_status {
            color: #505a63;
        }
        QFrame#section_card {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
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
    """
