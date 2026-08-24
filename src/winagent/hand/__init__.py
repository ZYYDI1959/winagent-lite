"""手：真实鼠标与键盘输入的跨平台后端分发（v0.3 起）。

公开 API 稳定（与旧 hand.py 完全一致）：
move_to / click / type_text / press / hotkey / combo / key_by_name /
foreground_title / wait_foreground + VK_* 常量。

后端按平台自动选择：
- win32:  user32 + SendInput（全功能，含中文 UNICODE 直输，老 Windows 10 兼容）
- x11:    XTest 扩展（libXtst；ASCII 直输，中文需剪贴板方案；显示连接惰性）
- macos:  Quartz CGEvent（代码就绪，待实机验证）

后端加载失败时导入仍可用：导入期不抛错，调用任一功能时给出清晰错误。
"""
from __future__ import annotations

import sys as _sys

_IMPL_ERROR: Exception | None = None

try:
    if _sys.platform.startswith("win"):
        from . import win32 as _impl
    elif _sys.platform.startswith("linux"):
        from . import x11 as _impl
    elif _sys.platform == "darwin":
        from . import macos as _impl
    else:
        raise RuntimeError(f"尚不支持的系统平台: {_sys.platform}")
except Exception as exc:  # noqa: BLE001 导入期兜底：无图形库/无系统组件时不挡导入
    _IMPL_ERROR = exc
    _impl = None

BACKEND = _impl.__name__.split(".")[-1] if _impl is not None else f"error({type(_IMPL_ERROR).__name__})"


def _raise_unavailable(*_args, **_kwargs) -> None:
    raise RuntimeError(f"hand 后端不可用（{BACKEND}）：{_IMPL_ERROR}")


if _impl is None:
    move_to = _raise_unavailable
    click = _raise_unavailable
    type_text = _raise_unavailable
    press = _raise_unavailable
    hotkey = _raise_unavailable
    combo = _raise_unavailable
    key_by_name = _raise_unavailable
    foreground_title = _raise_unavailable
    wait_foreground = _raise_unavailable
else:
    for _name in dir(_impl):
        if not _name.startswith("_"):
            globals()[_name] = getattr(_impl, _name)