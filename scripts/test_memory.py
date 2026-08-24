"""视觉链路内存稳定性测试：连续 30 轮 截屏+降采样+base64 编码。

用于发现内存泄漏（RSS 应保持平稳）。用法: python -u scripts/test_memory.py
CI 的 Windows GUI job 会执行。
"""
import time

import psutil

from winagent import vision
from winagent.config import Config


def main() -> int:
    cfg = Config()
    proc = psutil.Process()
    vision.capture_screen(cfg)  # 预热（载入 mss/解码器）
    time.sleep(0.3)
    rss0 = proc.memory_info().rss
    for i in range(30):
        img, _ = vision.capture_screen(cfg)
        small = vision.downscale(img, cfg.max_image_width)
        b64 = vision._to_b64(small, cfg.image_format)
        del img, small, b64
        if i % 10 == 9:
            print(f"  [{i+1}/30] RSS={(proc.memory_info().rss - rss0) / 1e6:+.1f} MB", flush=True)
    growth = (proc.memory_info().rss - rss0) / 1e6
    print(f"30 轮后 RSS 增长: {growth:.1f} MB（阈值 30MB）")
    assert growth < 30, f"疑似内存泄漏: {growth:.1f}MB"
    print("MEMORY-TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())