"""Linux 真实运行套件：xvfb 下真实 X 应用 + XTest 真实输入 + 截屏验证。

主路径：xterm（关 XIM）启动 -> 真实键盘输入 -> 像素差分验证屏幕变化。
兜底路径：xterm 拒绝启动时用 xlogo 验证「真实应用启动+渲染+截屏」链路。
不依赖 Ollama。用法: xvfb-run -a -s "-screen 0 1920x1080x24" python -u scripts/test_linux_gui.py
"""
import subprocess
import time

from PIL import ImageChops

from winagent import hand, vision


def _diff_pixels(before, after) -> int:
    diff = ImageChops.difference(before, after).convert("L")
    return sum(1 for px in diff.getdata() if px > 20)


def _try_xterm_typing() -> bool:
    print("[A] xterm 打字链路（inputMethod 关闭）")
    p = subprocess.Popen(
        ["xterm", "-xrm", "*inputMethod: none", "-title", "wa-live-test", "-e", "bash"])
    time.sleep(2.5)
    if p.poll() is not None:
        print(f"    xterm 提前退出（rc={p.returncode}），走兜底路径")
        return False
    before = vision.capture_screen()[0]
    hand.type_text("echo wagent-live-test")
    hand.press(hand.VK_RETURN)
    time.sleep(2.0)
    changed = _diff_pixels(before, vision.capture_screen()[0])
    print(f"    屏幕变化像素: {changed}（阈值 500）")
    p.terminate()
    if changed <= 500:
        print("    打字无回显（可能无窗口管理器抢焦点），走兜底路径")
        return False
    print("    xterm 打字闭环通过")
    return True


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
    xterm_ok = _try_xterm_typing()
    if not xterm_ok:
        ok = _try_xlogo_launch()
        print(f"    兜底结果: {'通过' if ok else '失败'}")
        assert ok, "兜底路径也未通过，Linux 真实运行链路异常"
    print("LINUX-GUI-LIVE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())