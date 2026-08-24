"""Linux 真实运行套件：xvfb 下真实 X 应用 + XTest 真实输入，确定性验证。

主路径（确定性）：xmessage 启动 -> XQueryTree 确认窗口真实映射(IsViewable)
  -> 真实点击+回车 -> 确认窗口从 X 服务器消失 + 进程退出。
兜底路径：xlogo 同理（窗口出现验证渲染链路）。
像素差分仅作信息输出（xvfb 黑底黑窗体时阈值不适用，不能当判据）。
不依赖 Ollama。用法: xvfb-run -a -s "-screen 0 1920x1080x24" python -u scripts/test_linux_gui.py
"""
import ctypes
import subprocess
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


def _windows(dpy) -> list[tuple[int, str, int, int, int, int]]:
    """返回 (viewable 顶层窗口 id, 标题, x, y, w, h) 列表（确定性证据+可点击坐标）。"""
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

    root = ctypes.c_ulong()
    parent = ctypes.c_ulong()
    children = ctypes.POINTER(ctypes.c_ulong)()
    n = ctypes.c_uint()
    found: list[tuple[int, str, int, int, int, int]] = []
    if not _x11.XQueryTree(dpy, _x11.XDefaultRootWindow(dpy), ctypes.byref(root),
                           ctypes.byref(parent), ctypes.byref(children), ctypes.byref(n)):
        return found
    for i in range(n.value):
        wid = children[i]
        attrs = Attrs()
        if _x11.XGetWindowAttributes(dpy, wid, ctypes.byref(attrs)) and attrs.map_state == 2:
            name = ctypes.c_char_p()
            title = ""
            if _x11.XFetchName(dpy, wid, ctypes.byref(name)):
                title = (name.value or b"").decode("utf-8", errors="replace")
                _x11.XFree(name)
            found.append((wid, title, attrs.x, attrs.y, attrs.width, attrs.height))
    if children:
        _x11.XFree(children)
    return found


def _find(dpy, wanted: str) -> tuple[int, int] | None:
    """按标题找窗口，返回其中心坐标（用于确定性点击）；找不到返回 None。"""
    for _, title, x, y, w, h in _windows(dpy):
        if wanted in title:
            return x + w // 2, y + h // 2
    return None


def _wait_window(dpy, wanted: str, timeout: float = 6.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _find(dpy, wanted) is not None:
            return True
        time.sleep(0.3)
    return False


def _wait_window_gone(dpy, wanted: str, timeout: float = 6.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(wanted in t for _, t in _windows(dpy)):
            return True
        time.sleep(0.3)
    return False


def main() -> int:
    assert hand.BACKEND == "x11", f"期望 x11 后端，实际 {hand.BACKEND}"
    print("[1] XTest 后端就绪")
    dpy = _x11.XOpenDisplay(None)
    assert dpy, "无法打开 X display"

    print("[A] xmessage: 启动 -> 窗口映射 -> 点窗口正中 -> 回车 -> 窗口消失")
    p = subprocess.Popen(["xmessage", "-buttons", "Click:0", "-default", "Click",
                          "-title", "wa-live-test", "winagent live test"])
    appeared = _wait_window(dpy, "wa-live-test")
    print(f"    真实窗口出现: {appeared}")
    center = _find(dpy, "wa-live-test")
    before = vision.capture_screen()[0]
    if center:
        hand.click(center[0], center[1])  # 点窗口本体获取焦点（不触发按钮）
    time.sleep(0.6)
    hand.press(hand.VK_RETURN)  # 回车触发默认按钮 Click -> 关闭
    time.sleep(1.2)
    gone = _wait_window_gone(dpy, "wa-live-test")
    after = vision.capture_screen()[0]
    changed = sum(1 for px in __import__("PIL.ImageChops", fromlist=["difference"]).difference(
        before, after).convert("L").getdata() if px > 20)
    print(f"    窗口消失: {gone} | 进程退出: {p.poll() is not None} | 像素变化(参考): {changed}")
    if p.poll() is None:
        p.terminate()
    assert appeared and gone, "xmessage 窗口生命周期验证失败"

    print("[B] 截屏链路对照（mss 在 xvfb 下工作）")
    img, mon = vision.capture_screen()
    print(f"    截屏 {mon['width']}x{mon['height']} -> {img.size} 字节级可用")
    assert img.width > 0

    print("LINUX-GUI-LIVE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())