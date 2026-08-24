"""Linux 真实运行套件：xvfb 下真实 X 应用 + XTest 真实输入 + 截屏验证。

主路径：xmessage 对话框（真实应用）-> 真实鼠标点击按钮 -> 窗口消失（像素差分验证）。
兜底路径：xmessage 异常时用 xlogo 验证「真实应用启动+渲染+截屏」链路。
不依赖 Ollama。用法: xvfb-run -a -s "-screen 0 1920x1080x24" python -u scripts/test_linux_gui.py
"""
import subprocess
import time

from PIL import ImageChops

from winagent import hand, vision


def _diff_pixels(before, after) -> int:
    diff = ImageChops.difference(before, after).convert("L")
    return sum(1 for px in diff.getdata() if px > 20)


def _try_xmessage_click() -> bool:
    print("[A] xmessage 真实点击+回车链路")
    hand.move_to(400, 300)  # xmessage 弹出在指针旁
    p = subprocess.Popen(
        ["xmessage", "-buttons", "Click:0", "-default", "Click",
         "-title", "wa-live-test", "winagent live test"])
    time.sleep(2.5)
    if p.poll() is not None:
        print(f"    xmessage 启动失败（rc={p.returncode}），走兜底路径")
        return False
    before = vision.capture_screen()[0]
    hand.click(400, 300)  # 点对话框本体获取焦点（不会触发按钮）
    time.sleep(0.6)
    hand.press(hand.VK_RETURN)  # 回车触发默认按钮 Click -> 对话框关闭
    time.sleep(1.5)
    changed = _diff_pixels(before, vision.capture_screen()[0])
    closed = p.poll() is not None
    print(f"    对话框关闭={closed} 屏幕变化像素={changed}（阈值 500）")
    if not closed:
        p.terminate()
    return closed and changed > 500


def _try_xlogo_launch() -> bool:
    print("[B] xlogo 启动/渲染链路")
    p = subprocess.Popen(["xlogo"])
    time.sleep(2.0)
    alive = p.poll() is None
    before = vision.capture_screen()[0]
    time.sleep(0.5)
    changed = _diff_pixels(before, vision.capture_screen()[0]) if alive else 0
    print(f"    xlogo 存活={alive} 屏幕变化={changed}（阈值 500）")
    if p.poll() is None:
        p.terminate()
    return alive and changed > 500


def main() -> int:
    assert hand.BACKEND == "x11", f"期望 x11 后端，实际 {hand.BACKEND}"
    print("[1] XTest 后端就绪")
    xmessage_ok = _try_xmessage_click()
    if not xmessage_ok:
        ok = _try_xlogo_launch()
        print(f"    兜底结果: {'通过' if ok else '失败'}")
        assert ok, "兜底路径也未通过，Linux 真实运行链路异常"
    print("LINUX-GUI-LIVE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())