"""x11 后端：XTest 扩展模拟真实输入（libXtst，多数 Linux 发行版自带）。

能力边界（诚实声明）：
- 鼠标：XTestFakeMotionEvent / XTestFakeButtonEvent（完整）
- 键盘：XTestFakeKeyEvent 走 keysym->keycode（ASCII 直输，含大小写与符号）
- 中文等非 ASCII：XTest 无 UNICODE 注入通道，抛 NotImplementedError
  （可用剪贴板+Ctrl+V 方案替代，见 docs/baseline_v0.2.md 的 IME 讨论）
- 前台窗口标题：XGetInputFocus + XFetchName（只有部分窗口支持 WM_NAME，空则 ""）
"""
from __future__ import annotations

import ctypes
import time

_x11 = ctypes.CDLL("libX11.so.6")
_xtst = ctypes.CDLL("libXtst.so.6")

_x11.XOpenDisplay.restype = ctypes.c_void_p
_x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
_x11.XStringToKeysym.restype = ctypes.c_ulong
_x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
_x11.XKeysymToKeycode.restype = ctypes.c_ubyte
_x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
_x11.XFlush.argtypes = [ctypes.c_void_p]
_x11.XDefaultRootWindow.restype = ctypes.c_ulong
_x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
_x11.XGetInputFocus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int)]
_x11.XFetchName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_char_p)]
_x11.XFree.argtypes = [ctypes.c_void_p]
_xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
_xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
_xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
_x11.XQueryPointer.argtypes = [
    ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint),
]

_display = _x11.XOpenDisplay(None)
if not _display:
    raise RuntimeError("无法打开 X display（需要图形会话；无头环境请用 xvfb-run）")
_root = _x11.XDefaultRootWindow(_display)

# 与 win32 相同的 VK 编号，保证跨后端 API 一致
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_ESCAPE = 0x1B
VK_LWIN = 0x5B
VK_HOME = 0x24
VK_END = 0x23

_KEY_NAMES = {
    "back": VK_BACK,
    "tab": VK_TAB,
    "enter": VK_RETURN,
    "shift": VK_SHIFT,
    "ctrl": VK_CONTROL,
    "alt": VK_MENU,
    "esc": VK_ESCAPE,
    "win": VK_LWIN,
    "home": VK_HOME,
    "end": VK_END,
}
for _i in range(1, 25):
    _KEY_NAMES[f"f{_i}"] = 0x70 + _i - 1

_VK_TO_KEYSYM = {
    VK_BACK: "BackSpace",
    VK_TAB: "Tab",
    VK_RETURN: "Return",
    VK_SHIFT: "Shift_L",
    VK_CONTROL: "Control_L",
    VK_MENU: "Alt_L",
    VK_ESCAPE: "Escape",
    VK_LWIN: "Super_L",
    VK_HOME: "Home",
    VK_END: "End",
    **{0x70 + i - 1: f"F{i}" for i in range(1, 25)},
}

_SHIFTED_PUNCT = set('~!@#$%^&*()_+{}|:"<>?')  # 需要 Shift 的 ASCII 标点


def _vk_name(vk: int) -> str:
    if vk in _VK_TO_KEYSYM:
        return _VK_TO_KEYSYM[vk]
    if 0x41 <= vk <= 0x5A:  # A-Z
        return chr(vk).lower()
    if 0x30 <= vk <= 0x39:  # 0-9
        return chr(vk)
    if 0x20 == vk:
        return "space"
    raise ValueError(f"x11 后端不支持该键码: 0x{vk:X}")


def _key_event(name: str, down: bool) -> None:
    keysym = _x11.XStringToKeysym(name.encode())
    if not keysym:
        raise ValueError(f"未知 keysym: {name!r}")
    kc = _x11.XKeysymToKeycode(_display, keysym)
    _xtst.XTestFakeKeyEvent(_display, kc, 1 if down else 0, 0)
    _x11.XFlush(_display)


def _char_event(ch: str, down: bool) -> None:
    """单字符按键事件（大写/符号自动带 Shift）。"""
    needs_shift = ch.isupper() or ch in _SHIFTED_PUNCT
    if needs_shift and down:
        _key_event("Shift_L", True)
    _key_event(ch.lower() if ch.isalpha() else ch, down)
    if needs_shift and not down:
        _key_event("Shift_L", False)


def press(vk: int, times: int = 1, hold_ms: int = 20) -> None:
    name = _vk_name(vk)
    for _ in range(times):
        _key_event(name, True)
        time.sleep(hold_ms / 1000)
        _key_event(name, False)
        time.sleep(hold_ms / 1000)


def hotkey(*vks: int, hold_ms: int = 30) -> None:
    for vk in vks:
        _key_event(_vk_name(vk), True)
        time.sleep(hold_ms / 1000)
    for vk in reversed(vks):
        _key_event(_vk_name(vk), False)
        time.sleep(hold_ms / 1000)


def type_text(text: str, interval_ms: int = 10, mode: str = "auto") -> None:
    for ch in text:
        if not ch.isascii():
            raise NotImplementedError(
                "x11 后端仅支持 ASCII 直接输入；中文请走剪贴板+Ctrl+V 方案"
            )
        _char_event(ch, True)
        time.sleep(interval_ms / 1000)
        _char_event(ch, False)
        time.sleep(interval_ms / 1000)


def move_to(x: int, y: int) -> None:
    _xtst.XTestFakeMotionEvent(_display, -1, int(x), int(y), 0)  # -1 = 当前屏幕
    _x11.XFlush(_display)


def get_cursor_pos() -> tuple[int, int]:
    rr, cr = ctypes.c_ulong(), ctypes.c_ulong()
    rx, ry, wx, wy = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
    mask = ctypes.c_uint()
    _x11.XQueryPointer(_display, _root, ctypes.byref(rr), ctypes.byref(cr),
                       ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx),
                       ctypes.byref(wy), ctypes.byref(mask))
    return wx.value, wy.value


def click(x: int | None = None, y: int | None = None, *, double: bool = False,
          right: bool = False, settle_ms: int = 120) -> None:
    if x is not None and y is not None:
        move_to(x, y)
        time.sleep(settle_ms / 1000)
    btn = 3 if right else 1
    for i in range(2 if double else 1):
        _xtst.XTestFakeButtonEvent(_display, btn, 1, 0)
        _x11.XFlush(_display)
        _xtst.XTestFakeButtonEvent(_display, btn, 0, 0)
        _x11.XFlush(_display)
        if double and i == 0:
            time.sleep(0.06)


def key_by_name(name: str) -> int:
    low = name.lower()
    if low in _KEY_NAMES:
        return _KEY_NAMES[low]
    if len(low) == 1 and "a" <= low <= "z":
        return ord(low.upper())
    if len(low) == 1 and low.isdigit():
        return ord(low)
    raise ValueError(f"无法识别的按键名: {name!r}")


def combo(keys: str) -> None:
    vks = [key_by_name(part) for part in keys.split("+")]
    if len(vks) == 1:
        press(vks[0])
    else:
        hotkey(*vks)


def foreground_title() -> str:
    """X 输入焦点窗口的 WM_NAME（部分窗口/环境为空串，属正常）。"""
    win = ctypes.c_ulong()
    revert = ctypes.c_int()
    _x11.XGetInputFocus(_display, ctypes.byref(win), ctypes.byref(revert))
    if not win.value:
        return ""
    name = ctypes.c_char_p()
    if not _x11.XFetchName(_display, win.value, ctypes.byref(name)):
        return ""
    try:
        return name.value.decode("utf-8", errors="replace")
    finally:
        if name.value:
            _x11.XFree(name)


def wait_foreground(substr: str, timeout: float = 10.0, interval: float = 0.15) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if substr.lower() in foreground_title().lower():
            return True
        time.sleep(interval)
    return False