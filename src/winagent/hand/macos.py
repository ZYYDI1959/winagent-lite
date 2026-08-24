"""macos 后端：Quartz CGEvent 模拟真实输入（ApplicationServices）。

⚠️ 代码就绪但未在本机实机验证（开发机为 Windows）——CI 只做导入冒烟，
首个 macOS 用户在真机上跑过后再修正键码表细节。
能力：
- 鼠标：CGWarpMouseCursorPosition + CGEvent 按下/抬起
- 键盘：CGEventCreateKeyboardEvent（ASCII 直输）+ CGEventKeyboardSetUnicodeString（中文）
- 前台窗口标题：AppleScript 代价高，返回 ""（wait_foreground 将超时，属已知限制）
"""
from __future__ import annotations

import ctypes
import time

_core = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
_app = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")

# --- 常量 ---
kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp = 5, 1, 2
kCGEventRightMouseDown, kCGEventRightMouseUp = 3, 4
kCGEventKeyDown, kCGEventKeyUp = 10, 11
kCGHIDEventTap = 0
kCGMouseEventDeltaX = 24
kCGEventSourceStateHIDSystemState = 1

_core.CGEventCreateMouseEvent.restype = ctypes.c_void_p
_core.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
_core.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
_core.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_ushort, ctypes.c_bool]
_core.CGEventSetIntegerValueField.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int64]
_core.CGEventKeyboardSetUnicodeString.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint16)]
_core.CGEventPost.argtypes = [ctypes.c_uint, ctypes.c_void_p]
_core.CGEventGetLocation.argtypes = [ctypes.c_void_p]
_core.CGWarpMouseCursorPosition.argtypes = [ctypes.c_void_p]
_core.CGEventCreate.argtypes = [ctypes.c_void_p]
_core.CGEventSetLocation.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

# --- 键码表（macOS 虚拟键码，常用子集）---
_KCODE = {
    "a": 0x00, "s": 0x01, "d": 0x02, "f": 0x03, "h": 0x04, "g": 0x05, "z": 0x06,
    "x": 0x07, "c": 0x08, "v": 0x09, "b": 0x0B, "q": 0x0C, "w": 0x0D, "e": 0x0E,
    "r": 0x0F, "y": 0x10, "t": 0x11, "1": 0x12, "2": 0x13, "3": 0x14, "4": 0x15,
    "6": 0x16, "5": 0x17, "=": 0x18, "9": 0x19, "7": 0x1A, "-": 0x1B, "8": 0x1C,
    "0": 0x1D, "]": 0x1E, "o": 0x1F, "u": 0x20, "[": 0x21, "i": 0x22, "p": 0x23,
    "l": 0x25, "j": 0x26, "'": 0x27, "k": 0x28, ";": 0x29, "\\": 0x2A, ",": 0x2B,
    "/": 0x2C, "n": 0x2D, "m": 0x2E, ".": 0x2F, "`": 0x32, "space": 0x31,
    "Return": 0x24, "Tab": 0x30, "Delete": 0x33, "Escape": 0x35, "Control_L": 0x3B,
    "Shift_L": 0x38, "Alt_L": 0x3A, "Super_L": 0x37, "Home": 0x73, "End": 0x77,
    **{f"F{i}": 0x70 + i - 1 for i in range(1, 13)},
}
_SHIFTED_PUNCT = set('~!@#$%^&*()_+{}|:"<>?')

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
    "back": VK_BACK, "tab": VK_TAB, "enter": VK_RETURN, "shift": VK_SHIFT,
    "ctrl": VK_CONTROL, "alt": VK_MENU, "esc": VK_ESCAPE, "win": VK_LWIN,
    "home": VK_HOME, "end": VK_END,
}
for _i in range(1, 25):
    _KEY_NAMES[f"f{_i}"] = 0x70 + _i - 1

_VK_TO_NAME = {
    VK_BACK: "Delete", VK_TAB: "Tab", VK_RETURN: "Return", VK_SHIFT: "Shift_L",
    VK_CONTROL: "Control_L", VK_MENU: "Alt_L", VK_ESCAPE: "Escape", VK_LWIN: "Super_L",
    VK_HOME: "Home", VK_END: "End",
}


def _keycode(name: str) -> int:
    k = _KCODE.get(name)
    if k is None:
        raise ValueError(f"macos 后端未知键名: {name!r}")
    return k


def _key_event(name: str, down: bool) -> None:
    ev = _core.CGEventCreateKeyboardEvent(None, _keycode(name), down)
    _core.CGEventPost(kCGHIDEventTap, ev)


def _char_key(ch: str, down: bool) -> None:
    """单字符：字母/数字走键码（大写带 Shift），其余走 UNICODE 注入。"""
    low = ch.lower()
    if ch.isascii() and (low in _KCODE) and (ch.isalnum() or ch == " "):
        needs = ch.isupper()
        if needs and down:
            _key_event("Shift_L", True)
        _key_event(low, down)
        if needs and not down:
            _key_event("Shift_L", False)
        return
    buf = (ctypes.c_uint16 * 1)(ord(ch))
    ev = _core.CGEventCreateKeyboardEvent(None, 0, down)
    _core.CGEventKeyboardSetUnicodeString(ev, 1, buf)
    _core.CGEventPost(kCGHIDEventTap, ev)


def _mouse_event(kind: int, x: int, y: int) -> None:
    pt = _Point(float(x), float(y))
    ev = _core.CGEventCreateMouseEvent(None, kind, ctypes.byref(pt), 0)
    _core.CGEventPost(kCGHIDEventTap, ev)


def press(vk: int, times: int = 1, hold_ms: int = 20) -> None:
    name = _VK_TO_NAME.get(vk) or (chr(vk).lower() if 0x41 <= vk <= 0x5A else None) or (chr(vk) if 0x30 <= vk <= 0x39 else None)
    if name is None:
        raise ValueError(f"macos 后端不支持该键码: 0x{vk:X}")
    for _ in range(times):
        _key_event(name, True)
        time.sleep(hold_ms / 1000)
        _key_event(name, False)
        time.sleep(hold_ms / 1000)


def hotkey(*vks: int, hold_ms: int = 30) -> None:
    for vk in vks:
        _key_event(_VK_TO_NAME[vk], True)
        time.sleep(hold_ms / 1000)
    for vk in reversed(vks):
        _key_event(_VK_TO_NAME[vk], False)
        time.sleep(hold_ms / 1000)


def type_text(text: str, interval_ms: int = 10, mode: str = "auto") -> None:
    for ch in text:
        _char_key(ch, True)
        time.sleep(interval_ms / 1000)
        _char_key(ch, False)
        time.sleep(interval_ms / 1000)


def move_to(x: int, y: int) -> None:
    pt = _Point(float(x), float(y))
    _core.CGWarpMouseCursorPosition(ctypes.byref(pt))


def get_cursor_pos() -> tuple[int, int]:
    ev = _core.CGEventCreate(None)
    loc = _core.CGEventGetLocation(ev)
    pt = ctypes.cast(loc, ctypes.POINTER(_Point)).contents
    return int(pt.x), int(pt.y)


def click(x: int | None = None, y: int | None = None, *, double: bool = False,
          right: bool = False, settle_ms: int = 120) -> None:
    if x is not None and y is not None:
        move_to(x, y)
        time.sleep(settle_ms / 1000)
    down_kind, up_kind = (kCGEventRightMouseDown, kCGEventRightMouseUp) if right else (kCGEventLeftMouseDown, kCGEventLeftMouseUp)
    for i in range(2 if double else 1):
        _mouse_event(down_kind, x or 0, y or 0)
        _mouse_event(up_kind, x or 0, y or 0)
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
    return ""  # 见模块 docstring：已知限制


def wait_foreground(substr: str, timeout: float = 10.0, interval: float = 0.15) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if substr and substr.lower() in foreground_title().lower():
            return True
        time.sleep(interval)
    return False