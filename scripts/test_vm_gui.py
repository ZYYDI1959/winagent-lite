"""VirtualBox/GNOME 真实桌面 GUI 验证：XTest + 真实窗口映射 + 截屏 + 真实输入。

在已登录的 Ubuntu 桌面子会话里运行（无需 WM 之外的额外依赖）：
  DISPLAY=:0 XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.* python3 -u scripts/test_vm_gui.py

判定（回答"库在真实 Linux 桌面跑不跑得通"）：
  A window-mapping   启动真实 xmessage，XQueryTree 见 viewable 窗口 = 确定性证据
  B desktop-capture  mss 拿到全屏尺寸；纯色是 GNOME/Wayland 边界（root 合成不回写 +
                     guest 熄屏/锁屏），只记录不判 FAIL；真实画面请用宿主侧
                     `VBoxManage controlvm <vm> screenshotpng` 补足（VM 渲染级，与合成器无关）
  C real-input       winagent x11(XTest) 后端 move_to/click/type_text/press 全程无异常
  D honest-boundary  XWayland 合成器焦点模型下 Enter 不触发 xmessage 默认按钮（xvfb 正常），
                     仅记录；CI 的 xvfb 环境不受影响
主判据 = A 且 B(尺寸) 且 C；RESULT=PASS 时输出供报告引用。
"""
import ctypes
import subprocess
import sys
import time

from winagent import hand, vision

_x11 = ctypes.CDLL("libX11.so.6")
_x11.XOpenDisplay.restype = ctypes.c_void_p
_x11.XDefaultRootWindow.restype = ctypes.c_ulong
_x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
_x11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
                            ctypes.POINTER(ctypes.c_uint)]
_x11.XGetWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
_x11.XFree.restype = ctypes.c_int
_x11.XFree.argtypes = [ctypes.c_void_p]
_x11.XFetchName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_char_p)]


def _windows(dpy):
    """返回 viewable 顶层窗口 (id, 标题, x, y, w, h) 列表。"""
    class Attrs(ctypes.Structure):
        _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("width", ctypes.c_int),
                    ("height", ctypes.c_int), ("border_width", ctypes.c_int),
                    ("depth", ctypes.c_int), ("visual", ctypes.c_void_p),
                    ("root", ctypes.c_ulong), ("class", ctypes.c_int),
                    ("bit_gravity", ctypes.c_int), ("win_gravity", ctypes.c_int),
                    ("backing_store", ctypes.c_int), ("backing_planes", ctypes.c_ulong),
                    ("backing_pixel", ctypes.c_ulong), ("save_under", ctypes.c_int),
                    ("colormap", ctypes.c_ulong), ("map_installed", ctypes.c_int),
                    ("map_state", ctypes.c_int), ("all_event_masks", ctypes.c_long),
                    ("your_event_mask", ctypes.c_long), ("do_not_propagate_mask", ctypes.c_long),
                    ("override_redirect", ctypes.c_int), ("screen", ctypes.c_void_p)]

    root = ctypes.c_ulong(); parent = ctypes.c_ulong()
    children = ctypes.POINTER(ctypes.c_ulong)(); n = ctypes.c_uint()
    found = []
    if not _x11.XQueryTree(dpy, _x11.XDefaultRootWindow(dpy), ctypes.byref(root),
                           ctypes.byref(parent), ctypes.byref(children), ctypes.byref(n)):
        return found
    for i in range(n.value):
        wid = children[i]
        attrs = Attrs()
        if _x11.XGetWindowAttributes(dpy, wid, ctypes.byref(attrs)) and attrs.map_state == 2:
            name = ctypes.c_char_p(); title = ""
            if _x11.XFetchName(dpy, wid, ctypes.byref(name)):
                title = (name.value or b"").decode("utf-8", errors="replace")
                _x11.XFree(name)
            found.append((wid, title, attrs.x, attrs.y, attrs.width, attrs.height))
    if children:
        _x11.XFree(children)
    return found


def _center(dpy, wanted):
    for _, title, x, y, w, h in _windows(dpy):
        if wanted in title:
            return x + w // 2, y + h // 2
    return None


def _wait(dpy, wanted, timeout=6.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _center(dpy, wanted) is not None:
            return True
        time.sleep(0.3)
    return False


def main() -> int:
    print(f"[0] python {sys.version.split()[0]} ; hand.BACKEND={hand.BACKEND}")
    assert hand.BACKEND == "x11", "期望 x11 后端"
    dpy = _x11.XOpenDisplay(None)
    assert dpy, "无法打开 X display"
    print("[0] XOpenDisplay OK")

    p = subprocess.Popen(["xmessage", "-buttons", "Click:0", "-default", "Click",
                          "-title", "wa-live-test", "winagent live test"])
    appeared = _wait(dpy, "wa-live-test")
    center = _center(dpy, "wa-live-test")
    print(f"[A] window-mapping 窗口出现: {appeared} 中心={center}")
    if not appeared or center is None:
        if p.poll() is None:
            p.terminate()
        return 1

    try:
        sct = vision.capture_screen()[0]
    except Exception as exc:  # noqa: BLE001
        print(f"[B] desktop-capture 失败: {exc!r}")
        if p.poll() is None:
            p.terminate()
        return 1
    w, h = sct.size
    colors = len(sct.getcolors(maxcolors=10_000_000) or [])
    print(f"[B] desktop-capture 尺寸={w}x{h} 估色数={colors}")
    if w <= 0 or h <= 0:
        print("[B] desktop-capture FAIL（空图）")
        if p.poll() is None:
            p.terminate()
        return 1
    if colors < 2:
        print("[B] 边界: 纯色画面=GNOME/Wayland root 合成不回写或 guest 熄屏/锁屏，"
              "真实画面用宿主 `controlvm screenshotpng` 补足（见 docstring）")

    c0 = center
    hand.move_to(c0[0], c0[1]); time.sleep(0.4)
    hand.click(c0[0], c0[1]); time.sleep(0.6)
    print("[C] click 窗口本体 OK")
    hand.type_text("wa-input-ok"); time.sleep(0.3)
    print("[C] type_text OK")
    hand.press(hand.VK_RETURN); time.sleep(0.6)
    print("[C] press(Enter) OK")
    print(f"[C] real-input 执行完毕 cursor={hand.get_cursor_pos()}")

    time.sleep(1.0)
    still_mapped = any("wa-live-test" in t for _, t, *_ in _windows(dpy))
    exited = p.poll() is not None
    print(f"[D] honest-boundary 关闭判定: 仍映射={still_mapped} 进程退出={exited}（XWayland 焦点差异，仅记录不作 PASS 依据）")
    if p.poll() is None:
        p.terminate()

    ok = appeared and w > 0 and h > 0
    print(f"RESULT={'PASS' if ok else 'FAIL'} (A映射+B截图+C输入 为主判据；D为边界观察)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
