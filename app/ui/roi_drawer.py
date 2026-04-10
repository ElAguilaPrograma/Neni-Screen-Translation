from html import escape

from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsTextItem,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPen, QColor, QBrush
from app import settings as app_settings

class ROISchema:
    def __init__(self, roi_id, x, y, w, h):
        self.roi_id = roi_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        
class ROIDrawer(QGraphicsScene):
    rois_changed = Signal(bool)
    _ROI_KIND_KEY = 0
    _ROI_ID_KEY = 1
    _ROI_KIND_RECT = "roi_rect"
    _DEFAULT_TEXT_STYLE = app_settings.get_default_overlay_text_style()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit_mode = True
        self.rois: list[ROISchema] = []
        self.current_item = None
        self.start_point = None
        self.text_items: dict[int, QGraphicsTextItem] = {}
        self.roi_text_cache: dict[int, str] = {}
        self.text_style = app_settings.get_default_overlay_text_style()

    def _is_roi_rect_item(self, item):
        return isinstance(item, QGraphicsRectItem) and item.data(self._ROI_KIND_KEY) == self._ROI_KIND_RECT

    def _iter_roi_rect_items(self):
        return [item for item in self.items() if self._is_roi_rect_item(item)]

    def _find_roi_schema(self, roi_id):
        for roi in self.rois:
            if roi.roi_id == roi_id:
                return roi
        return None

    def _color_to_css(self, color):
        if len(color) == 3:
            r, g, b = color
            return f"rgb({int(r)}, {int(g)}, {int(b)})"

        if len(color) == 4:
            r, g, b, a = color
            alpha = max(0.0, min(255.0, float(a))) / 255.0
            return f"rgba({int(r)}, {int(g)}, {int(b)}, {alpha:.2f})"

        return "rgba(0, 0, 0, 0.8)"

    def _build_text_html(self, clean_text):
        html_text = escape(clean_text).replace("\n", "<br/>")
        style = self.text_style
        background_css = self._color_to_css(style["background_rgba"])
        text_css = self._color_to_css(style["text_rgb"])
        border_css = self._color_to_css(style["border_rgba"])
        accent_css = self._color_to_css(style["accent_rgb"])

        return (
            "<div style='"
            f"background-color: {background_css};"
            f"border: 1px solid {border_css};"
            f"border-left: 4px solid {accent_css};"
            f"color: {text_css};"
            f"padding: {int(style['padding_y_px'])}px {int(style['padding_x_px'])}px;"
            f"border-radius: {int(style['border_radius_px'])}px;"
            f"font-size: {int(style['font_size_px'])}px;"
            "font-family: Segoe UI, Arial, sans-serif;"
            "font-weight: 600;"
            "line-height: 1.3;"
            "'>"
            f"{html_text}</div>"
        )

    def _refresh_text_items(self):
        for roi_id, text in list(self.roi_text_cache.items()):
            self.update_roi_text(roi_id, text)

    def configure_text_style(
        self,
        *,
        font_size_px=None,
        background_rgba=None,
        text_rgb=None,
        border_rgba=None,
        accent_rgb=None,
        padding_x_px=None,
        padding_y_px=None,
        border_radius_px=None,
    ):
        updates = {}
        if font_size_px is not None:
            updates["font_size_px"] = max(10, int(font_size_px))
        if background_rgba is not None:
            updates["background_rgba"] = background_rgba
        if text_rgb is not None:
            updates["text_rgb"] = text_rgb
        if border_rgba is not None:
            updates["border_rgba"] = border_rgba
        if accent_rgb is not None:
            updates["accent_rgb"] = accent_rgb
        if padding_x_px is not None:
            updates["padding_x_px"] = max(0, int(padding_x_px))
        if padding_y_px is not None:
            updates["padding_y_px"] = max(0, int(padding_y_px))
        if border_radius_px is not None:
            updates["border_radius_px"] = max(0, int(border_radius_px))

        if updates:
            self.text_style = app_settings.merge_overlay_text_style(self.text_style, updates)
            self._refresh_text_items()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item_under_cursor = self.itemAt(event.scenePos(), self.views()[0].transform())
            if item_under_cursor:
                print("Seleccionando item existente")
                super().mousePressEvent(event)
                return
            self.start_point = event.scenePos()
            self.current_item = QGraphicsRectItem(QRectF(self.start_point, self.start_point))
            self.current_item.setData(self._ROI_KIND_KEY, self._ROI_KIND_RECT)
            self.current_item.setPen(QPen(QColor(0, 255, 0), 2))
            self.current_item.setBrush(QBrush(QColor(0, 255, 0, 50)))
            self.current_item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
            # Seleccion y movimiento en modo edición
            self.addItem(self.current_item)
        
        elif event.button() == Qt.RightButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if self._is_roi_rect_item(item):
                self.removeItem(item)
                self.save_rois()
                return
                
        super().mousePressEvent(event)
        
    def mouseClickRightButton(self, event):
        print("Borrando de roi_drawer")
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if self._is_roi_rect_item(item):
            self.removeItem(item)
    
    def mouseMoveEvent(self, event):
        if self.current_item and self.start_point:
            end_point = event.scenePos()
            rect = QRectF(self.start_point, end_point).normalized()
            self.current_item.setRect(rect)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.current_item:
            rect = self.current_item.rect()
            if rect.width() < 25 or rect.height() < 25:
                self.removeItem(self.current_item)
                self.current_item = None
                return
        self.start_point = None
        self.current_item = None
        self.save_rois()
        super().mouseReleaseEvent(event)
        
    def save_rois(self):
        roi_items = []
        for item in self._iter_roi_rect_items():
            r = item.sceneBoundingRect()
            roi_items.append((item, r))

        # Orden estable para mantener ids predecibles en pipeline y overlay.
        roi_items.sort(key=lambda pair: (pair[1].y(), pair[1].x()))

        self.rois = []
        valid_ids = set()
        for i, (item, rect) in enumerate(roi_items):
            item.setData(self._ROI_ID_KEY, i)
            self.rois.append(ROISchema(i, rect.x(), rect.y(), rect.width(), rect.height()))
            valid_ids.add(i)
            print(f"ROI guardada: ID={i}, x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")

        for roi_id in list(self.text_items.keys()):
            if roi_id not in valid_ids:
                text_item = self.text_items.pop(roi_id)
                self.removeItem(text_item)
                self.roi_text_cache.pop(roi_id, None)

        self.rois_changed.emit(len(self.rois) > 0)

    def update_roi_text(self, roi_id, text):
        roi_id = int(roi_id)
        roi = self._find_roi_schema(roi_id)
        if roi is None:
            stale_item = self.text_items.pop(roi_id, None)
            if stale_item:
                self.removeItem(stale_item)
            self.roi_text_cache.pop(roi_id, None)
            return

        clean_text = (text or "").strip()
        if not clean_text:
            text_item = self.text_items.pop(roi_id, None)
            if text_item:
                self.removeItem(text_item)
            self.roi_text_cache.pop(roi_id, None)
            return

        self.roi_text_cache[roi_id] = clean_text

        text_item = self.text_items.get(roi_id)
        if text_item is None:
            text_item = QGraphicsTextItem()
            text_item.setDefaultTextColor(QColor(255, 255, 255))
            text_item.setZValue(2000)
            text_item.setAcceptedMouseButtons(Qt.NoButton)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(16)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 180))
            text_item.setGraphicsEffect(shadow)

            self.addItem(text_item)
            self.text_items[roi_id] = text_item

        text_item.setHtml(self._build_text_html(clean_text))
        horizontal_margin = max(6.0, float(self.text_style["padding_x_px"]))
        vertical_margin = max(4.0, float(self.text_style["padding_y_px"]))
        text_item.setTextWidth(max(80.0, float(roi.w) - (horizontal_margin * 2.0)))
        text_item.setPos(float(roi.x) + horizontal_margin, float(roi.y) + vertical_margin)

    def clear_roi_texts(self):
        for text_item in self.text_items.values():
            self.removeItem(text_item)
        self.text_items.clear()
        self.roi_text_cache.clear()

        