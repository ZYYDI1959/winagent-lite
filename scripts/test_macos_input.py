"""macOS 真实输入冒烟：后端选择 + 光标移动 + 读位 + 组合键（GitHub macOS runner 实机跑）。

覆盖 macos 后端实机路径：Quartz CGEvent 加载 -> 真实光标移动 -> 位置读取 -> 合成按键。
若 runner 无 GUI 会话或辅助功能权限受限，将如实失败并输出诊断。
用法: python -u scripts/test_macos_input.py
"""
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    from winagent import hand

    print("backend:", hand.BACKEND)
    assert hand.BACKEND == "macos", f"期望 macos 后端，实际 {hand.BACKEND}"

    hand.move_to(150, 150)
    time.sleep(0.5)
    x, y = hand.get_cursor_pos()
    print(f"cursor: ({x}, {y})（期望靠近 150,150）")
    assert abs(x - 150) <= 40 and abs(y - 150) <= 40, (x, y)

    hand.combo("ctrl+end")
    time.sleep(0.3)
    hand.press(hand.VK_ESCAPE)
    print("MACOS-INPUT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())