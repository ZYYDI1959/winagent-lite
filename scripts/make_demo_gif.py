"""录制一次真实评测运行并合成演示 GIF（作品集素材）。

用法: python -u scripts/make_demo_gif.py
产物: docs/demo.gif（约 30-40 帧，800px 宽）
"""
import threading
import time
from pathlib import Path

from PIL import Image

from winagent import vision
from winagent.bench import bench

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "demo.gif"


def run_bench() -> None:
    bench(task_ids=["notepad_append_save"], runs_override=1,
          out_root=REPO / "runs" / "demo")


if __name__ == "__main__":
    t = threading.Thread(target=run_bench)
    t.start()
    frames: list[Image.Image] = []
    time.sleep(0.6)
    while t.is_alive() or len(frames) < 6:
        img, _ = vision.capture_screen()
        small = vision.downscale(img, 800)
        frames.append(small.convert("P", palette=Image.Palette.ADAPTIVE))
        time.sleep(1.0)
    t.join()
    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=900, loop=0, optimize=True)
    print(f"GIF: {OUT}  {OUT.stat().st_size/1024:.0f} KB  {len(frames)} 帧")
