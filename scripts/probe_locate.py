"""调试探针：给定目标描述，打印定位结果与模型原始回答。

用法（在仓库根目录，用 venv 的 python）:
  python scripts/probe_locate.py "目标描述" [--width 1600] [--model qwen2.5vl:7b]
"""
import argparse

from winagent import vision
from winagent.config import Config
from winagent.vision import _FOUND_RE, _LOCATE_PROMPT, _generate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    cfg = Config()
    cfg.max_image_width = a.width
    if a.model:
        cfg.vision_model = a.model

    img, mon = vision.capture_screen()
    small = vision.downscale(img, cfg.max_image_width)
    ans = _generate(
        _LOCATE_PROMPT.format(w=small.width, h=small.height, target=a.target),
        small,
        cfg,
    )
    m = _FOUND_RE.search(ans)
    print(f"model={cfg.vision_model} width={small.width} target={a.target!r}")
    print(f"raw={ans!r}")
    if m:
        rx, ry = float(m[1]), float(m[2])
        if rx > 1:
            rx /= 100
        if ry > 1:
            ry /= 100
        x = round(rx * img.width) + mon["left"]
        y = round(ry * img.height) + mon["top"]
        print(f"rel=({rx:.3f},{ry:.3f}) abs=({x},{y})")


if __name__ == "__main__":
    main()
