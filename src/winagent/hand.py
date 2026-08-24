"""手：真实鼠标与键盘输入（user32，isTrusted=true 级系统事件）。

鼠标部分移植自 tools/click.ps1（SetCursorPos + mouse_event）；
键盘部分为本项目新增：SendInput + KEYEVENTF_UNICODE，按字符直输，
天然支持中文等任意 Unicode，不经过输入法。
坐标一律为虚拟屏幕物理像素。
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

_user32 = ctypes.windll.user32

try:
    _user32.SetProcessDPIAware()  # 多显示器/缩放下坐标一致性
except Exception:  # noqa: BLE001, S110 旧系统无此 API 时降级，无需处理
    pass

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

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

_user32_vk = ctypes.windll.user32
_VkKeyScanW = _user32_vk.VkKeyScanW
_VkKeyScanW.restype = ctypes.c_short
_VkKeyScanW.argtypes = [ctypes.c_wchar]

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
for _i in range(1, 25):  # F1-F24 (VK_F1=0x70 起)
    _KEY_NAMES[f"f{_i}"] = 0x70 + _i - 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _send_key(wVk: int = 0, wScan: int = 0, flags: int = 0) -> None:
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(wVk=wVk, wScan=wScan, dwFlags=flags)
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def press(vk: int, times: int = 1, hold_ms: int = 20) -> None:
    """按下并释放一个虚拟键，可重复。"""
    for _ in range(times):
        _send_key(wVk=vk)
        time.sleep(hold_ms / 1000)
        _send_key(wVk=vk, flags=KEYEVENTF_KEYUP)
        time.sleep(hold_ms / 1000)


def hotkey(*vks: int, hold_ms: int = 30) -> None:
    """组合键：依次按下、逆序释放，如 hotkey(VK_CONTROL, 0x53) = Ctrl+S。"""
    for vk in vks:
        _send_key(wVk=vk)
        time.sleep(hold_ms / 1000)
    for vk in reversed(vks):
        _send_key(wVk=vk, flags=KEYEVENTF_KEYUP)
        time.sleep(hold_ms / 1000)


def _send_inputs(inputs: list[INPUT]) -> None:
    """一次 SendInput 提交多个事件（原子性：Shift+字符不会被应用拆开误读）。"""
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    _user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def _key_input(wVk: int = 0, wScan: int = 0, flags: int = 0) -> INPUT:
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(wVk=wVk, wScan=wScan, dwFlags=flags)
    return inp


def _type_char_vk(ch: str, hold_ms: int = 10) -> None:
    """ASCII 可打印字符走虚拟键路径（WinUI 应用如计算器不认 UNICODE 注入的运算符）。

    Shift 与字符键在同一次 SendInput 里原子按下/抬起，避免高速打字时的 Shift 竞态
    （实测竞态症状：LINE-2-WinAgent 打成 line-2-WinAGENT）。
    """
    code = _VkKeyScanW(ch)
    vk = code & 0xFF
    shift = bool((code >> 8) & 1)
    downs, ups = [], []
    if shift:
        downs.append(_key_input(wVk=VK_SHIFT))
    downs.append(_key_input(wVk=vk))
    ups.append(_key_input(wVk=vk, flags=KEYEVENTF_KEYUP))
    if shift:
        ups.append(_key_input(wVk=VK_SHIFT, flags=KEYEVENTF_KEYUP))
    _send_inputs(downs)
    time.sleep(hold_ms / 1000)
    _send_inputs(ups)
    time.sleep(hold_ms / 1000)


def type_text(text: str, interval_ms: int = 10, mode: str = "auto") -> None:
    """向当前焦点窗口逐字符输入。

    实测结论（详见 docs/baseline_v0.1.md）：
    - UNICODE 直输绕过中文 IME，字母/数字/中文都正确，但 WinUI 计算器不认运算符；
    - 虚拟键路径会被中文 IME 劫持（大小写漂移），但运算符必须走它。
    auto 模式：字母/数字/空格/非ASCII 走 UNICODE，仅 ASCII 标点运算符走虚拟键。
    mode="unicode"/"vk" 可强制全量走某一路径。
    """
    for ch in text:
        if mode == "vk":
            use_vk = True
        elif mode == "unicode":
            use_vk = False
        else:  # auto
            use_vk = ch.isascii() and ch.isprintable() and not (ch.isalnum() or ch == " ")
        if use_vk:
            _type_char_vk(ch, interval_ms)
        else:
            _send_inputs([
                _key_input(wScan=ord(ch), flags=KEYEVENTF_UNICODE),
            ])
            time.sleep(interval_ms / 1000)
            _send_inputs([
                _key_input(wScan=ord(ch), flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
            ])
            time.sleep(interval_ms / 1000)


def move_to(x: int, y: int) -> None:
    _user32.SetCursorPos(int(x), int(y))


def get_cursor_pos() -> tuple[int, int]:
    pt = wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def click(
    x: int | None = None,
    y: int | None = None,
    *,
    double: bool = False,
    right: bool = False,
    settle_ms: int = 120,
) -> None:
    """真实鼠标点击；给定坐标则先移动再点。"""
    if x is not None and y is not None:
        move_to(x, y)
        time.sleep(settle_ms / 1000)
    down, up = (
        (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)
        if right
        else (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP)
    )
    for i in range(2 if double else 1):
        _user32.mouse_event(down, 0, 0, 0, 0)
        _user32.mouse_event(up, 0, 0, 0, 0)
        if double and i == 0:
            time.sleep(0.06)


def key_by_name(name: str) -> int:
    """把 'enter'/'ctrl'/'s' 这类名字解析成虚拟键码。"""
    low = name.lower()
    if low in _KEY_NAMES:
        return _KEY_NAMES[low]
    if len(low) == 1 and "a" <= low <= "z":
        return ord(low.upper())
    if len(low) == 1 and low.isdigit():
        return ord(low)
    raise ValueError(f"无法识别的按键名: {name!r}")


def combo(keys: str) -> None:
    """按 'enter' / 'ctrl+s' 这类字符串执行单键或组合键。"""
    vks = [key_by_name(part) for part in keys.split("+")]
    if len(vks) == 1:
        press(vks[0])
    else:
        hotkey(*vks)


def foreground_title() -> str:
    """当前前台窗口标题。"""
    hwnd = _user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def wait_foreground(substr: str, timeout: float = 10.0, interval: float = 0.15) -> bool:
    """轮询等待前台窗口标题包含 substr；替代固定 sleep，消除启动竞态。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if substr.lower() in foreground_title().lower():
            return True
        time.sleep(interval)
    return False
