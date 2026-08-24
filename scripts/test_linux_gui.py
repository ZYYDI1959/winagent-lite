"""Linux 真实运行套件：xvfb 下启动真实 X 应用(xterm) + XTest 真实输入 + 截屏验证。

覆盖：X 后端加载 → 应用窗口启动 → 真实键盘输入 → 真实屏幕变化（像素差分）。
不依赖 Ollama。用法: xvfb-run -a python -u scripts/test_linux_gui.py
"""
import subprocess
import time

from PIL import ImageChops

from winagent import hand, vision


def main() -> int:
    assert hand.BACKEND == "x11", f"期望 x11 后端，实际 {hand.BACKEND}"
    print("[1] XTest 后端就绪")

    p = subprocess.Popen(["xterm", "-title", "wa-live-test", "-e", "bash"])
    time.sleep(2.5)
    print("[2] xterm 已启动:", repr(hand.foreground_title()))

    before = vision.capture_screen()[0]
    print("[3] 真实键盘输入: echo wagent-live-test + 回车")
    hand.type_text("echo wagent-live-test")
    hand.press(hand.VK_RETURN)
    time.sleep(2.0)

    after = vision.capture_screen()[0]
    diff = ImageChops.difference(before, after).convert("L")
    changed = sum(1 for px in diff.getdata() if px > 20)
    print(f"[4] 屏幕变化像素: {changed}（阈值 500）")
    assert changed > 500, "屏幕几乎无变化，真实输入链路可能失效"

    p.terminate()
    time.sleep(0.5)
    print("LINUX-GUI-LIVE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())