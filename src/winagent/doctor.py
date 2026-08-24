"""环境自检：一条命令诊断 WinAgent-Lite 的运行条件（被动检查，不动键鼠）。"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from winagent.config import Config


def run_checks(cfg: Config | None = None) -> list[tuple[bool, str]]:
    cfg = cfg or Config()
    checks: list[tuple[bool, str]] = []

    checks.append((sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}（需 >=3.10）"))

    try:
        from winagent import hand

        checks.append((True, f"输入后端: {hand.BACKEND}（本平台自动选择）"))
    except Exception as exc:  # noqa: BLE001 自检要求吞掉一切异常转为 FAIL 行
        checks.append((False, f"输入后端加载失败: {exc}"))

    try:
        from winagent import vision

        img, mon = vision.capture_screen()
        checks.append((img.width > 0,
                       f"屏幕采集 {mon['width']}x{mon['height']} @ 偏移({mon['left']},{mon['top']})"))
    except Exception as exc:  # noqa: BLE001 自检要求吞掉一切异常转为 FAIL 行
        checks.append((False, f"屏幕采集失败: {exc}"))

    try:
        from winagent import vision

        names = vision.list_models(cfg)
        if cfg.vision_model in names:
            checks.append((True, f"Ollama 可达，视觉模型 {cfg.vision_model} 在列"))
        else:
            vision_models = [n for n in names if "vl" in n.lower()]
            tip = f"Ollama 可达但 {cfg.vision_model} 不在列；可用视觉模型: {vision_models or names}（改 config.yaml）"
            checks.append((False, tip))
    except Exception as exc:  # noqa: BLE001
        checks.append((False, f"Ollama 不可达（{cfg.ollama_url}）: {exc}"))

    try:
        probe = Path(tempfile.gettempdir()) / "winagent_doctor_probe.txt"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append((True, f"临时目录可写: {tempfile.gettempdir()}"))
    except Exception as exc:  # noqa: BLE001
        checks.append((False, f"临时目录不可写: {exc}"))

    from winagent.agent import LAUNCHERS

    checks.append((True, f"启动白名单: {', '.join(sorted(LAUNCHERS))}"))
    return checks


def main(cfg: Config | None = None) -> int:
    print("WinAgent-Lite 环境自检")
    print("=" * 40)
    all_ok = True
    for ok, msg in run_checks(cfg):
        mark = "PASS" if ok else "FAIL"
        all_ok = all_ok and ok
        print(f"[{mark}] {msg}")
    print("=" * 40)
    print("结论: " + ("环境就绪" if all_ok else "存在未通过项，按上方提示修复"))
    return 0 if all_ok else 1
