"""手：真实鼠标与键盘输入的跨平台后端分发（v0.3 起）。

公开 API 稳定（与旧 hand.py 完全一致）：
move_to / click / type_text / press / hotkey / combo / key_by_name /
foreground_title / wait_foreground + VK_* 常量。

后端按平台自动选择：
- win32:  user32 + SendInput（全功能，含中文 UNICODE 直输，老 Windows 10 兼容）
- x11:    XTest 扩展（libXtst，多数 Linux 发行版自带；ASCII 直输，中文需剪贴板方案）
- macos:  Quartz CGEvent（代码就绪，待实机验证）
"""
from __future__ import annotations

import sys as _sys

if _sys.platform.startswith("win"):
    from . import win32 as _impl
elif _sys.platform.startswith("linux"):
    from . import x11 as _impl
elif _sys.platform == "darwin":
    from . import macos as _impl
else:
    raise RuntimeError(f"尚不支持的系统平台: {_sys.platform}")

BACKEND = _impl.__name__.split(".")[-1]

for _name in dir(_impl):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_impl, _name)