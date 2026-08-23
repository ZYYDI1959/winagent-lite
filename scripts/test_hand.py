"""hand.py 验收测试：真实鼠标 + 真实键盘全链路。

用法（务必用 -u 无缓冲）:
  python -u scripts/test_hand.py mouse   # M1 移动光标 + M2 点击时钟(像素差分验证)
  python -u scripts/test_hand.py keys    # K1 记事本打字 -> Ctrl+S -> 输入路径 -> Enter -> 验证文件
  python -u scripts/test_hand.py all

进度实时写入 runs/test_hand.log，任何时刻被中断都能从日志定位停在哪一步。
全程不调用视觉模型（弹窗验证用像素差分，秒级完成）。
会移动鼠标/开关记事本，无持久副作用（临时文件用完即删）。
"""
import subprocess
import sys
import time
from pathlib import Path

from PIL import ImageChops

from winagent import hand, vision

REPO = Path(__file__).resolve().parent.parent
LOG_PATH = REPO / "runs" / "test_hand.log"
TEMP_FILE = Path("C:/Users/ZY/AppData/Local/Temp/winagent_hand_test.txt")
MARKER = "WinAgent-hand-test-12345 你好世界"
FLYOUT_REGION = (1300, 400, 1920, 1030)  # 时钟/日历弹窗出现的大致区域

LOG_PATH.parent.mkdir(exist_ok=True)
_log = LOG_PATH.open("a", encoding="utf-8")


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    _log.write(line + "\n")
    _log.flush()


def _diff_ratio(img_a, img_b, region) -> float:
    """区域内变化像素占比（亮度差>20 视为变化）。"""
    a = img_a.crop(region).convert("L")
    b = img_b.crop(region).convert("L")
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    changed = sum(hist[21:])
    return changed / (diff.width * diff.height)


def test_move() -> None:
    log("[M1] begin: move_to(960,540) + get_cursor_pos")
    hand.move_to(960, 540)
    pos = hand.get_cursor_pos()
    assert pos == (960, 540), f"光标位置不符: {pos}"
    log(f"[M1] PASS: cursor={pos}")


def test_click_clock() -> None:
    log("[M2] begin: 截取点击前画面")
    before = vision.capture_screen()[0]
    log("[M2] click(1824,1056) 点击时钟（任务栏内安全坐标，视觉报的1026差6px落在栏外）")
    hand.click(1824, 1056)
    time.sleep(1.2)
    after = vision.capture_screen()[0]
    opened_ratio = _diff_ratio(before, after, FLYOUT_REGION)
    log(f"[M2] 弹出区域变化比例: {opened_ratio:.3f} (阈值 0.05)")
    assert opened_ratio > 0.05, "点击后弹窗区域几乎无变化，点击可能未生效"
    log("[M2] 按 Esc 关闭弹窗")
    hand.press(hand.VK_ESCAPE)
    time.sleep(0.8)
    closed = vision.capture_screen()[0]
    closed_ratio = _diff_ratio(before, closed, FLYOUT_REGION)
    log(f"[M2] 关闭后残留变化: {closed_ratio:.3f} (阈值 0.05)")
    assert closed_ratio < 0.05, "Esc 后弹窗区域仍有较大变化，可能未关闭"
    log("[M2] PASS: 点击弹出了面板且 Esc 正确关闭")


def test_notepad_chain() -> None:
    log("[K1] begin: 启动记事本")
    if TEMP_FILE.exists():
        TEMP_FILE.unlink()
    p = subprocess.Popen(["notepad.exe"])
    time.sleep(2.5)
    try:
        log("[K1] type_text 输入中英文标记")
        hand.type_text(MARKER)
        time.sleep(0.5)
        log("[K1] Ctrl+S 打开另存为")
        hand.hotkey(hand.VK_CONTROL, ord("S"))
        time.sleep(1.5)
        log("[K1] 输入完整保存路径")
        hand.type_text(str(TEMP_FILE))
        time.sleep(0.3)
        log("[K1] Enter 确认保存")
        hand.press(hand.VK_RETURN)
        time.sleep(1.5)
        assert TEMP_FILE.exists(), "保存的文件不存在"
        content = TEMP_FILE.read_text(encoding="utf-8", errors="replace")
        assert MARKER in content, f"文件内容不含标记文本: {content!r}"
        log(f"[K1] PASS: 文件已保存且含中英文标记 ({len(content)} chars)")
    finally:
        p.terminate()
        if TEMP_FILE.exists():
            TEMP_FILE.unlink()
        log("[K1] cleaned: 记事本已关, 临时文件已删")


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    log(f"===== test_hand part={part} =====")
    if part in ("mouse", "all"):
        test_move()
        test_click_clock()
    if part in ("keys", "all"):
        test_notepad_chain()
    log(f"===== RESULT: part={part} ALL-PASS =====")
