"""录制一次真实的目标驱动运行（plan -> execute）并合成演示 GIF。

用法: python -u scripts/make_goal_gif.py
产物: docs/demo_goal.gif（录制全过程，去重后约 8-20 帧，800px 宽）
前置: 本机 Ollama 含 qwen3-8b-fast 与 qwen3-vl:8b-instruct（见 config）
"""
import threading
import time
from pathlib import Path

from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "demo_goal.gif"
GOAL = "打开记事本，输入你好世界"  # 字面量常量：演示目标固定，不接收外部输入
NOTE_PATH = Path("C:/Users/ZY/AppData/Local/Temp/winagent_note.txt")


def run_goal() -> bool:
    from winagent import agent, planner
    from winagent.bench import _do_verb
    from winagent.config import load_config

    _do_verb({"clear_notepad_session": True})  # 杀记事本+清 TabState，防会话复活弹框
    if NOTE_PATH.exists():
        NOTE_PATH.unlink()
    plannerSteps = planner.plan(GOAL, cfg=load_config())
    print("PLAN:", plannerSteps, flush=True)
    result = agent.run_steps(plannerSteps, load_config())
    print("RESULT:", result["success"], flush=True)
    return bool(result["success"])


def _diff(a: Image.Image, b: Image.Image) -> float:
    h = ImageChops.difference(a.convert("L"), b.convert("L")).histogram()
    return sum(h[21:]) / (a.width * a.height)


if __name__ == "__main__":
    from winagent import vision

    outcome: list[bool] = []
    t = threading.Thread(target=lambda: outcome.append(run_goal()))
    t.start()
    frames: list[Image.Image] = []
    time.sleep(0.5)
    t0 = time.time()
    while t.is_alive():
        img, _ = vision.capture_screen()
        small = vision.downscale(img, 800)
        d = _diff(frames[-1], small) if frames else 1.0
        print(f"  cap t={time.time()-t0:.1f}s diff={d:.4f} frames={len(frames)}", flush=True)
        if not frames or d > 0.008:  # 去掉静止重复帧
            frames.append(small.convert("P", palette=Image.Palette.ADAPTIVE))
        time.sleep(1.0)
    t.join()
    time.sleep(0.5)
    tail, _ = vision.capture_screen()  # 终态帧强制收录（打字后的记事本是演示落点）
    frames.append(vision.downscale(tail, 800).convert("P", palette=Image.Palette.ADAPTIVE))
    if len(frames) < 2 or not outcome or not outcome[0]:
        raise SystemExit(f"录制失败: frames={len(frames)} success={outcome}")
    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=1000, loop=0, optimize=True)
    print(f"GIF: {OUT}  {OUT.stat().st_size/1024:.0f} KB  {len(frames)} 帧")
