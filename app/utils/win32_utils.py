import ctypes
from ctypes import wintypes

from PySide6.QtGui import QImage, QPixmap

from app.ui.overlay import WindowOverlay

# Este módulo contiene funciones y estructuras para interactuar con la API de Windows

# Obtener la el hwnd de la ventana seleccionada
# Función callback que EnumWindows espera
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

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
  
def get_current_window_position(window_selected, overlay: WindowOverlay):
		if not window_selected or not overlay:
			return False

		rect = wintypes.RECT()

		hr = 1
		try:
			hr = Dwmapi.DwmGetWindowAttribute(
				window_selected,
				DWMWA_EXTENDED_FRAME_BOUNDS,
				ctypes.byref(rect),
				ctypes.sizeof(rect),
			)
		except OSError:
			hr = 1

		if hr != 0:
			if not User32.GetWindowRect(window_selected, ctypes.byref(rect)):
				print("La ventana objetivo se ha cerrado o no se puede acceder.")
				return False

		x = rect.left
		y = rect.top
		w = rect.right - rect.left
		h = rect.bottom - rect.top
		if w <= 0 or h <= 0:
			return False

		x, y, w, h = _to_qt_logical_rect(window_selected, x, y, w, h)

		overlay.setGeometry(x, y, w, h)
		return True

   
