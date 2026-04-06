import ctypes
import threading
import time
from ctypes import wintypes
from typing import TYPE_CHECKING
from PySide6.QtGui import QImage, QPixmap

if TYPE_CHECKING:
	from app.ui.overlay import WindowOverlay

# Este módulo contiene funciones y estructuras para interactuar con la API de Windows

# Obtener la el hwnd de la ventana seleccionada
# Función callback que EnumWindows espera
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
_TRACKER_LOCK = threading.Lock()
_ACTIVE_TRACKER = None

def get_windows():
    windows = []
    
    def enum_handler(hwnd, lParam):
        # Verificar si la ventana es visible y tiene un título
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                windows.append((hwnd, buff.value))
                
        return True
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
    return windows


# Definiciones de constantes y estructuras para captura de pantalla en Windows

User32 = ctypes.windll.user32
Gdi32 = ctypes.windll.gdi32
Dwmapi = ctypes.windll.dwmapi
HRESULT = getattr(wintypes, "HRESULT", ctypes.c_long)

PW_RENDERFULLCONTENT = 0x00000002
DWMWA_EXTENDED_FRAME_BOUNDS = 9
SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
	_fields_ = [
		("biSize", wintypes.DWORD),
		("biWidth", wintypes.LONG),
		("biHeight", wintypes.LONG),
		("biPlanes", wintypes.WORD),
		("biBitCount", wintypes.WORD),
		("biCompression", wintypes.DWORD),
		("biSizeImage", wintypes.DWORD),
		("biXPelsPerMeter", wintypes.LONG),
		("biYPelsPerMeter", wintypes.LONG),
		("biClrUsed", wintypes.DWORD),
		("biClrImportant", wintypes.DWORD),
	]


class BITMAPINFO(ctypes.Structure):
	_fields_ = [
		("bmiHeader", BITMAPINFOHEADER),
		("bmiColors", wintypes.DWORD * 3),
	]


User32.IsWindow.argtypes = [wintypes.HWND]
User32.IsWindow.restype = wintypes.BOOL
User32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
User32.GetWindowRect.restype = wintypes.BOOL
User32.GetWindowDC.argtypes = [wintypes.HWND]
User32.GetWindowDC.restype = wintypes.HDC
User32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
User32.ReleaseDC.restype = ctypes.c_int
User32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
User32.PrintWindow.restype = wintypes.BOOL
if hasattr(User32, "GetDpiForWindow"):
	User32.GetDpiForWindow.argtypes = [wintypes.HWND]
	User32.GetDpiForWindow.restype = wintypes.UINT
Dwmapi.DwmGetWindowAttribute.argtypes = [
	wintypes.HWND,
	wintypes.DWORD,
	ctypes.c_void_p,
	wintypes.DWORD,
]
Dwmapi.DwmGetWindowAttribute.restype = HRESULT

Gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
Gdi32.CreateCompatibleDC.restype = wintypes.HDC
Gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
Gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
Gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
Gdi32.SelectObject.restype = wintypes.HGDIOBJ
Gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
Gdi32.DeleteObject.restype = wintypes.BOOL
Gdi32.DeleteDC.argtypes = [wintypes.HDC]
Gdi32.DeleteDC.restype = wintypes.BOOL
Gdi32.GetDIBits.argtypes = [
	wintypes.HDC,
	wintypes.HBITMAP,
	wintypes.UINT,
	wintypes.UINT,
	ctypes.c_void_p,
	ctypes.POINTER(BITMAPINFO),
	wintypes.UINT,
]
Gdi32.GetDIBits.restype = ctypes.c_int


def capture_window(hwnd):
	if not hwnd or not User32.IsWindow(hwnd):
		return None

	rect = wintypes.RECT()
	if not User32.GetWindowRect(hwnd, ctypes.byref(rect)):
		return None

	width = rect.right - rect.left
	height = rect.bottom - rect.top
	if width <= 0 or height <= 0:
		return None

	window_dc = User32.GetWindowDC(hwnd)
	if not window_dc:
		return None

	memory_dc = Gdi32.CreateCompatibleDC(window_dc)
	if not memory_dc:
		User32.ReleaseDC(hwnd, window_dc)
		return None

	bitmap = Gdi32.CreateCompatibleBitmap(window_dc, width, height)
	if not bitmap:
		Gdi32.DeleteDC(memory_dc)
		User32.ReleaseDC(hwnd, window_dc)
		return None

	old_bitmap = Gdi32.SelectObject(memory_dc, bitmap)
	try:
		if not User32.PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT):
			if not User32.PrintWindow(hwnd, memory_dc, 0):
				return None

		bitmap_info = BITMAPINFO()
		bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
		bitmap_info.bmiHeader.biWidth = width
		bitmap_info.bmiHeader.biHeight = -height
		bitmap_info.bmiHeader.biPlanes = 1
		bitmap_info.bmiHeader.biBitCount = 32
		bitmap_info.bmiHeader.biCompression = BI_RGB
		bitmap_info.bmiHeader.biSizeImage = width * height * 4

		image_size = width * height * 4
		buffer = (ctypes.c_ubyte * image_size)()
		scan_lines = Gdi32.GetDIBits(
			memory_dc,
			bitmap,
			0,
			height,
			buffer,
			ctypes.byref(bitmap_info),
			DIB_RGB_COLORS,
		)
		if scan_lines == 0:
			return None

		image = QImage(bytes(buffer), width, height, width * 4, QImage.Format_ARGB32)
		if image.isNull():
			return None

		return QPixmap.fromImage(image.copy())
	finally:
		Gdi32.SelectObject(memory_dc, old_bitmap)
		Gdi32.DeleteObject(bitmap)
		Gdi32.DeleteDC(memory_dc)
		User32.ReleaseDC(hwnd, window_dc)


def capture_window_roi_for_ocr(hwnd, x, y, w, h):
	try:
		import importlib
		np = importlib.import_module("numpy")
	except ImportError as exc:
		raise RuntimeError("Se requiere numpy para capture_window_roi_for_ocr") from exc

	if not hwnd or not User32.IsWindow(hwnd):
		return None

	rect = wintypes.RECT()
	if not User32.GetWindowRect(hwnd, ctypes.byref(rect)):
		return None

	window_width = rect.right - rect.left
	window_height = rect.bottom - rect.top
	if window_width <= 0 or window_height <= 0:
		return None

	scale = _get_window_scale(hwnd)
	if scale <= 0:
		scale = 1.0

	roi_x = int(round(float(x) * scale))
	roi_y = int(round(float(y) * scale))
	roi_w = max(1, int(round(float(w) * scale)))
	roi_h = max(1, int(round(float(h) * scale)))

	left = max(0, roi_x)
	top = max(0, roi_y)
	right = min(window_width, roi_x + roi_w)
	bottom = min(window_height, roi_y + roi_h)

	if right <= left or bottom <= top:
		return None

	window_dc = User32.GetWindowDC(hwnd)
	if not window_dc:
		return None

	memory_dc = Gdi32.CreateCompatibleDC(window_dc)
	if not memory_dc:
		User32.ReleaseDC(hwnd, window_dc)
		return None

	bitmap = Gdi32.CreateCompatibleBitmap(window_dc, window_width, window_height)
	if not bitmap:
		Gdi32.DeleteDC(memory_dc)
		User32.ReleaseDC(hwnd, window_dc)
		return None

	old_bitmap = Gdi32.SelectObject(memory_dc, bitmap)
	try:
		if not User32.PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT):
			if not User32.PrintWindow(hwnd, memory_dc, 0):
				return None

		bitmap_info = BITMAPINFO()
		bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
		bitmap_info.bmiHeader.biWidth = window_width
		bitmap_info.bmiHeader.biHeight = -window_height
		bitmap_info.bmiHeader.biPlanes = 1
		bitmap_info.bmiHeader.biBitCount = 32
		bitmap_info.bmiHeader.biCompression = BI_RGB
		bitmap_info.bmiHeader.biSizeImage = window_width * window_height * 4

		image_size = window_width * window_height * 4
		buffer = (ctypes.c_ubyte * image_size)()
		scan_lines = Gdi32.GetDIBits(
			memory_dc,
			bitmap,
			0,
			window_height,
			buffer,
			ctypes.byref(bitmap_info),
			DIB_RGB_COLORS,
		)
		if scan_lines == 0:
			return None

		full_bgra = np.ctypeslib.as_array(buffer).reshape((window_height, window_width, 4))
		roi_bgr = full_bgra[top:bottom, left:right, :3].copy()
		if roi_bgr.size == 0:
			return None
		return roi_bgr
	finally:
		Gdi32.SelectObject(memory_dc, old_bitmap)
		Gdi32.DeleteObject(bitmap)
		Gdi32.DeleteDC(memory_dc)
		User32.ReleaseDC(hwnd, window_dc)


def _get_window_scale(window_handle):
	if hasattr(User32, "GetDpiForWindow"):
		try:
			dpi = User32.GetDpiForWindow(window_handle)
			if dpi > 0:
				return dpi / 96.0
		except OSError:
			pass

	return 1.0


def _to_qt_logical_rect(window_handle, x, y, w, h):
	scale = _get_window_scale(window_handle)
	if scale <= 0:
		scale = 1.0

	logical_x = int(round(x / scale))
	logical_y = int(round(y / scale))
	logical_w = max(1, int(round(w / scale)))
	logical_h = max(1, int(round(h / scale)))
	return logical_x, logical_y, logical_w, logical_h
  
def get_current_window_position(window_selected, overlay: "WindowOverlay"):
		if not window_selected or not overlay:
			return False
		return sync_overlay_to_target_window(window_selected, overlay)

# Constantes para SetWindowPos / GetWindow
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_NOOWNERZORDER = 0x0200

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

GW_HWNDPREV = 3
HWND_TOP = 0

User32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
User32.GetWindow.restype = wintypes.HWND
User32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
User32.GetWindowLongW.restype = ctypes.c_long
User32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
User32.SetWindowLongW.restype = ctypes.c_long

User32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT
]
User32.SetWindowPos.restype = wintypes.BOOL


def _get_insert_after_for_overlay(target_hwnd):
	# Insertar "despues" de la ventana previa equivale a quedar sobre target.
	prev_hwnd = User32.GetWindow(wintypes.HWND(target_hwnd), GW_HWNDPREV)
	if prev_hwnd:
		return prev_hwnd
	return wintypes.HWND(HWND_TOP)


def _hwnd_to_int(hwnd):
	if hwnd is None:
		return 0
	if isinstance(hwnd, int):
		return hwnd
	value = getattr(hwnd, "value", None)
	if isinstance(value, int):
		return value
	try:
		return int(hwnd)
	except (TypeError, ValueError):
		return 0

def place_overlay_above_window(overlay: "WindowOverlay", target_hwnd):
	overlay_hwnd = wintypes.HWND(int(overlay.winId()))
	insert_after = _get_insert_after_for_overlay(target_hwnd)
	result = User32.SetWindowPos(
		overlay_hwnd,
		insert_after,
		0, 0, 0, 0,
		SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_NOOWNERZORDER
	)
	if not result:
		print(f"SetWindowPos fallo al anclar overlay (target={target_hwnd}).")
		return False
	return True


def move_resize_and_anchor_overlay(overlay: "WindowOverlay", target_hwnd, x, y, w, h):
	overlay_hwnd = _get_overlay_hwnd(overlay)
	if not overlay_hwnd:
		return False
	return _move_resize_and_anchor_overlay_hwnd(int(overlay_hwnd.value), target_hwnd, x, y, w, h)


def _move_resize_and_anchor_overlay_hwnd(overlay_hwnd, target_hwnd, x, y, w, h):
	overlay_hwnd = wintypes.HWND(int(overlay_hwnd))

	insert_after = _get_insert_after_for_overlay(target_hwnd)
	insert_after_int = _hwnd_to_int(insert_after)
	overlay_hwnd_int = _hwnd_to_int(overlay_hwnd)

	flags = SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_NOOWNERZORDER
	# Si ya estamos justo encima del target, no tocar Z-order: solo mover/redimensionar.
	if insert_after_int == overlay_hwnd_int and overlay_hwnd_int != 0:
		insert_after = wintypes.HWND(HWND_TOP)
		flags |= SWP_NOZORDER

	result = User32.SetWindowPos(
		overlay_hwnd,
		insert_after,
		int(x),
		int(y),
		int(w),
		int(h),
		flags,
	)
	if not result:
		print(
			f"SetWindowPos fallo al mover/ajustar overlay (target={target_hwnd}, "
			f"insert_after={insert_after_int}, flags=0x{flags:04X})."
		)
		return False
	return True


def _get_target_window_rect(target_hwnd):
	if not target_hwnd or not User32.IsWindow(target_hwnd):
		return None

	rect = wintypes.RECT()
	hr = 1
	try:
		hr = Dwmapi.DwmGetWindowAttribute(
			target_hwnd,
			DWMWA_EXTENDED_FRAME_BOUNDS,
			ctypes.byref(rect),
			ctypes.sizeof(rect),
		)
	except OSError:
		hr = 1

	if hr != 0:
		if not User32.GetWindowRect(target_hwnd, ctypes.byref(rect)):
			return None

	x = rect.left
	y = rect.top
	w = rect.right - rect.left
	h = rect.bottom - rect.top
	if w <= 0 or h <= 0:
		return None
	return x, y, w, h


def sync_overlay_to_target_window(target_hwnd, overlay: "WindowOverlay"):
	overlay_hwnd = _get_overlay_hwnd(overlay)
	if not overlay_hwnd:
		return False
	return sync_overlay_to_target_hwnd(target_hwnd, int(overlay_hwnd.value))


def sync_overlay_to_target_hwnd(target_hwnd, overlay_hwnd):
	rect = _get_target_window_rect(target_hwnd)
	if not rect:
		print("La ventana objetivo se ha cerrado o no se puede acceder.")
		return False
	x, y, w, h = rect
	return _move_resize_and_anchor_overlay_hwnd(overlay_hwnd, target_hwnd, x, y, w, h)


class _NativeOverlayTracker:
	def __init__(self, target_hwnd, overlay_hwnd, poll_interval_ms=16, force_reanchor_ms=800):
		self.target_hwnd = int(target_hwnd)
		self.overlay_hwnd = int(overlay_hwnd)
		self.poll_interval_sec = max(10, int(poll_interval_ms)) / 1000.0
		self.force_reanchor_sec = max(100, int(force_reanchor_ms)) / 1000.0
		self._stop_event = threading.Event()
		self._thread = None
		self._last_rect = None
		self._last_reanchor_at = 0.0

	def start(self):
		if self._thread and self._thread.is_alive():
			return
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()

	def stop(self):
		self._stop_event.set()
		if self._thread and self._thread.is_alive():
			self._thread.join(timeout=0.3)

	def _run(self):
		while not self._stop_event.is_set():
			if not User32.IsWindow(self.target_hwnd) or not User32.IsWindow(self.overlay_hwnd):
				break

			rect = _get_target_window_rect(self.target_hwnd)
			now = time.monotonic()

			should_force_reanchor = (now - self._last_reanchor_at) >= self.force_reanchor_sec
			if rect and (rect != self._last_rect or should_force_reanchor):
				x, y, w, h = rect
				_move_resize_and_anchor_overlay_hwnd(self.overlay_hwnd, self.target_hwnd, x, y, w, h)
				self._last_rect = rect
				self._last_reanchor_at = now

			self._stop_event.wait(self.poll_interval_sec)


def start_native_overlay_tracking(target_hwnd, overlay: "WindowOverlay", poll_interval_ms=16, force_reanchor_ms=800):
	global _ACTIVE_TRACKER

	if not target_hwnd or not overlay:
		return False

	overlay_hwnd = _get_overlay_hwnd(overlay)
	if not overlay_hwnd:
		return False

	with _TRACKER_LOCK:
		if _ACTIVE_TRACKER:
			_ACTIVE_TRACKER.stop()
			_ACTIVE_TRACKER = None

		tracker = _NativeOverlayTracker(
			target_hwnd,
			int(overlay_hwnd.value),
			poll_interval_ms=poll_interval_ms,
			force_reanchor_ms=force_reanchor_ms,
		)
		tracker.start()
		_ACTIVE_TRACKER = tracker

	# Sincronizacion inicial inmediata.
	return sync_overlay_to_target_hwnd(target_hwnd, int(overlay_hwnd.value))


def stop_native_overlay_tracking():
	global _ACTIVE_TRACKER
	with _TRACKER_LOCK:
		if _ACTIVE_TRACKER:
			_ACTIVE_TRACKER.stop()
			_ACTIVE_TRACKER = None


def _get_overlay_hwnd(overlay):
	if overlay is None:
		return None
	try:
		hwnd_value = int(overlay.winId())
	except Exception:
		return None
	if hwnd_value <= 0:
		return None
	return wintypes.HWND(hwnd_value)


def enable_overlay_full_click_through(overlay: "WindowOverlay"):
	"""Activa click-through total del overlay a nivel Win32."""
	overlay_hwnd = _get_overlay_hwnd(overlay)
	if not overlay_hwnd:
		return False

	current_style = User32.GetWindowLongW(overlay_hwnd, GWL_EXSTYLE)
	new_style = current_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
	if new_style != current_style:
		User32.SetWindowLongW(overlay_hwnd, GWL_EXSTYLE, new_style)

	User32.SetWindowPos(
		overlay_hwnd,
		wintypes.HWND(HWND_TOP),
		0,
		0,
		0,
		0,
		SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
	)

	updated_style = User32.GetWindowLongW(overlay_hwnd, GWL_EXSTYLE)
	is_click_through = (updated_style & WS_EX_TRANSPARENT) != 0
	if not is_click_through:
		print("No se pudo activar full click-through en overlay.")
	return is_click_through


def disable_overlay_full_click_through(overlay: "WindowOverlay"):
	"""Desactiva click-through total del overlay a nivel Win32."""
	overlay_hwnd = _get_overlay_hwnd(overlay)
	if not overlay_hwnd:
		return False

	current_style = User32.GetWindowLongW(overlay_hwnd, GWL_EXSTYLE)
	new_style = current_style & ~WS_EX_TRANSPARENT
	if new_style != current_style:
		User32.SetWindowLongW(overlay_hwnd, GWL_EXSTYLE, new_style)

	User32.SetWindowPos(
		overlay_hwnd,
		wintypes.HWND(HWND_TOP),
		0,
		0,
		0,
		0,
		SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
	)

	updated_style = User32.GetWindowLongW(overlay_hwnd, GWL_EXSTYLE)
	is_click_through = (updated_style & WS_EX_TRANSPARENT) != 0
	if is_click_through:
		print("No se pudo desactivar full click-through en overlay.")
	return not is_click_through

   
