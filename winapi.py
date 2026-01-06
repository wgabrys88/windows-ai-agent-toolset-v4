from __future__ import annotations

import ctypes
import struct
import time
import zlib
from ctypes import wintypes
if not hasattr(wintypes, "HCURSOR"):
    wintypes.HCURSOR = wintypes.HANDLE
if not hasattr(wintypes, "HICON"):
    wintypes.HICON = wintypes.HANDLE
if not hasattr(wintypes, "HBITMAP"):
    wintypes.HBITMAP = wintypes.HANDLE
if not hasattr(wintypes, "HGDIOBJ"):
    wintypes.HGDIOBJ = wintypes.HANDLE
if not hasattr(wintypes, "HBRUSH"):
    wintypes.HBRUSH = wintypes.HANDLE
if not hasattr(wintypes, "HDC"):
    wintypes.HDC = wintypes.HANDLE
if not hasattr(wintypes, "ULONG_PTR"):
    wintypes.ULONG_PTR = ctypes.c_size_t
from typing import Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

SM_CXSCREEN = 0
SM_CYSCREEN = 1

CURSOR_SHOWING = 0x00000001
DI_NORMAL = 0x0003

BI_RGB = 0
DIB_RGB_COLORS = 0

HALFTONE = 4
SRCCOPY = 0x00CC0020

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HCURSOR),
        ("ptScreenPos", POINT),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


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
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUT_I(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", INPUT_I)]


user32.GetSystemMetrics.argtypes = [wintypes.INT]
user32.GetSystemMetrics.restype = wintypes.INT

user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL

user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
user32.GetIconInfo.restype = wintypes.BOOL

user32.DrawIconEx.argtypes = [
    wintypes.HDC,
    wintypes.INT,
    wintypes.INT,
    wintypes.HICON,
    wintypes.INT,
    wintypes.INT,
    wintypes.UINT,
    wintypes.HBRUSH,
    wintypes.UINT,
]
user32.DrawIconEx.restype = wintypes.BOOL

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = wintypes.INT

user32.SetCursorPos.argtypes = [wintypes.INT, wintypes.INT]
user32.SetCursorPos.restype = wintypes.BOOL

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

user32.SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC

gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP

gdi32.StretchBlt.argtypes = [
    wintypes.HDC,
    wintypes.INT,
    wintypes.INT,
    wintypes.INT,
    wintypes.INT,
    wintypes.HDC,
    wintypes.INT,
    wintypes.INT,
    wintypes.INT,
    wintypes.INT,
    wintypes.DWORD,
]
gdi32.StretchBlt.restype = wintypes.BOOL

gdi32.SetStretchBltMode.argtypes = [wintypes.HDC, wintypes.INT]
gdi32.SetStretchBltMode.restype = wintypes.INT

gdi32.SetBrushOrgEx.argtypes = [wintypes.HDC, wintypes.INT, wintypes.INT, ctypes.POINTER(POINT)]
gdi32.SetBrushOrgEx.restype = wintypes.BOOL


def init_dpi() -> None:
    user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)


def get_screen_size() -> Tuple[int, int]:
    w = int(user32.GetSystemMetrics(SM_CXSCREEN))
    h = int(user32.GetSystemMetrics(SM_CYSCREEN))
    if w <= 0:
        w = 1920
    if h <= 0:
        h = 1080
    return w, h


def norm_to_screen_px(xn: float, yn: float, screen_w: int, screen_h: int) -> Tuple[int, int]:
    if xn < 0.0:
        xn = 0.0
    elif xn > 1000.0:
        xn = 1000.0
    if yn < 0.0:
        yn = 0.0
    elif yn > 1000.0:
        yn = 1000.0
    x = int(round((xn / 1000.0) * (screen_w - 1)))
    y = int(round((yn / 1000.0) * (screen_h - 1)))
    return x, y


def _draw_cursor_on_dc(hdc_mem: int, screen_w: int, screen_h: int, dst_w: int, dst_h: int) -> None:
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if not user32.GetCursorInfo(ctypes.byref(ci)):
        return
    if not (ci.flags & CURSOR_SHOWING):
        return

    ii = ICONINFO()
    if not user32.GetIconInfo(ci.hCursor, ctypes.byref(ii)):
        return

    try:
        cur_x = int(ci.ptScreenPos.x) - int(ii.xHotspot)
        cur_y = int(ci.ptScreenPos.y) - int(ii.yHotspot)
        dx = int(round(cur_x * (dst_w / float(screen_w))))
        dy = int(round(cur_y * (dst_h / float(screen_h))))
        user32.DrawIconEx(hdc_mem, dx, dy, ci.hCursor, 0, 0, 0, None, DI_NORMAL)
    finally:
        if ii.hbmMask:
            gdi32.DeleteObject(ii.hbmMask)
        if ii.hbmColor:
            gdi32.DeleteObject(ii.hbmColor)


def _encode_bgra_to_png(bgra: bytes, w: int, h: int) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)

    def chunk(t: bytes, d: bytes) -> bytes:
        return (
            struct.pack(">I", len(d))
            + t
            + d
            + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        )

    row = w * 3
    stride = row + 1
    raw = bytearray(stride * h)

    for y in range(h):
        out = y * stride
        raw[out] = 0
        src = y * w * 4
        dst = out + 1
        for _ in range(w):
            b = bgra[src]
            g = bgra[src + 1]
            r = bgra[src + 2]
            raw[dst] = r
            raw[dst + 1] = g
            raw[dst + 2] = b
            src += 4
            dst += 3

    comp = zlib.compress(bytes(raw), 6)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


def capture_screenshot_png(target_w: int, target_h: int) -> Tuple[bytes, int, int]:
    screen_w, screen_h = get_screen_size()
    hdc_screen = user32.GetDC(None)
    if not hdc_screen:
        raise RuntimeError("GetDC failed")

    hdc_mem = wintypes.HDC()
    hbmp = wintypes.HBITMAP()
    old = wintypes.HGDIOBJ()
    bits = ctypes.c_void_p()

    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        if not hdc_mem:
            raise RuntimeError("CreateCompatibleDC failed")

        bmi = BITMAPINFO()
        ctypes.memset(ctypes.byref(bmi), 0, ctypes.sizeof(bmi))
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = target_w
        bmi.bmiHeader.biHeight = -target_h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        hbmp = gdi32.CreateDIBSection(
            hdc_mem, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), 0, 0
        )
        if not hbmp or not bits.value:
            raise RuntimeError("CreateDIBSection failed")

        old = gdi32.SelectObject(hdc_mem, hbmp)
        if not old:
            raise RuntimeError("SelectObject failed")

        gdi32.SetStretchBltMode(hdc_mem, HALFTONE)
        pt = POINT()
        gdi32.SetBrushOrgEx(hdc_mem, 0, 0, ctypes.byref(pt))

        if not gdi32.StretchBlt(
            hdc_mem,
            0,
            0,
            target_w,
            target_h,
            hdc_screen,
            0,
            0,
            screen_w,
            screen_h,
            SRCCOPY,
        ):
            raise RuntimeError("StretchBlt failed")

        _draw_cursor_on_dc(hdc_mem, screen_w, screen_h, target_w, target_h)

        size = target_w * target_h * 4
        bgra = ctypes.string_at(bits, size)
        return _encode_bgra_to_png(bgra, target_w, target_h), screen_w, screen_h

    finally:
        if hdc_mem and old:
            gdi32.SelectObject(hdc_mem, old)
        if hbmp:
            gdi32.DeleteObject(hbmp)
        if hdc_mem:
            gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)


def _send_inputs(*inps: INPUT) -> None:
    n = len(inps)
    if n <= 0:
        return
    arr = (INPUT * n)(*inps)
    user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def _mi(flags: int, data: int = 0, dx: int = 0, dy: int = 0) -> INPUT:
    i = INPUT()
    i.type = INPUT_MOUSE
    i.ii.mi = MOUSEINPUT(dx, dy, data, flags, 0, 0)
    return i


def _ki(scan: int, flags: int) -> INPUT:
    i = INPUT()
    i.type = INPUT_KEYBOARD
    i.ii.ki = KEYBDINPUT(0, scan, flags, 0, 0)
    return i


def move_mouse_norm(xn: float, yn: float) -> Tuple[int, int]:
    screen_w, screen_h = get_screen_size()
    x, y = norm_to_screen_px(xn, yn, screen_w, screen_h)
    user32.SetCursorPos(x, y)
    return screen_w, screen_h


def click_mouse() -> None:
    _send_inputs(_mi(MOUSEEVENTF_LEFTDOWN), _mi(MOUSEEVENTF_LEFTUP))


def scroll_down() -> None:
    _send_inputs(_mi(MOUSEEVENTF_WHEEL, (-120) & 0xFFFFFFFF))


def type_text(text: str) -> None:
    text = text.encode("ascii", "ignore").decode("ascii")
    for ch in text:
        code = ord(ch)
        _send_inputs(_ki(code, KEYEVENTF_UNICODE), _ki(code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        time.sleep(0.005)
