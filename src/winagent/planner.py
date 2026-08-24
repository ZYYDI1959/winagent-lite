"""planner：把自然语言目标分解为可执行步骤 JSON（本地文本模型）。

云 API 适配器预留（openai 兼容接口），拿到 Key 后在 config 里加 planner_api_url /
planner_api_key / planner_cloud_model 即可切换，接口签名不变。
"""
from __future__ import annotations

import json
import re

from winagent.config import Config
from winagent.vision import generate_text

_PLAN_PROMPT = """你是 Windows GUI 自动化规划器。把用户目标分解为步骤 JSON 数组，每个元素只含一个主键：
- launch: 只能是 "notepad"|"notepad_note"|"calc"|"explorer"|"taskmgr" 之一（白名单）
- wait: 秒数（数字）
- type: 要输入的文本（可中文）
- key: 按键，如 "enter"/"ctrl+s"/"win+r"，可与 "focus"（等待出现的窗口标题词）同用
- click: {{"target": 目标元素的屏幕描述，越具体越好}}
示例:
[{{"launch":"notepad_note","focus":"Notepad"}},{{"wait":0.5}},{{"type":"你好"}},{{"key":"ctrl+s"}},{{"wait":1.0}}]
只输出 JSON 数组本身，不要解释、不要代码块标记。
用户目标: {goal}"""

_MAIN_KEYS = {"launch", "wait", "type", "key", "click"}


def _validate(steps: list) -> list[dict]:
    if not isinstance(steps, list) or not steps:
        raise ValueError("planner 输出不是非空数组")
    from winagent.agent import LAUNCHERS

    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            raise TypeError(f"步骤{i}不是对象: {s!r}")
        mains = [k for k in s if k in _MAIN_KEYS]
        if len(mains) != 1:
            raise ValueError(f"步骤{i}主键数量不为1: {s!r}")
        if mains[0] == "launch" and str(s["launch"]).lower() not in LAUNCHERS:
            raise ValueError(f"步骤{i} launch 不在白名单: {s['launch']!r}")
        if mains[0] == "wait":
            float(s["wait"])
        if mains[0] == "click" and "target" not in s["click"]:
            raise ValueError(f"步骤{i} click 缺 target: {s!r}")
    return steps


def plan(goal: str, model: str | None = None, cfg: Config | None = None) -> list[dict]:
    """目标 -> 步骤列表（已校验：白名单/结构/类型）。"""
    cfg = cfg or Config()
    model = model or getattr(cfg, "planner_model", "qwen3-8b-fast")
    raw = generate_text(_PLAN_PROMPT.format(goal=goal), model=model,
                        base_url=cfg.ollama_url, timeout=cfg.request_timeout)
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ValueError(f"planner 未输出 JSON 数组: {raw[:150]!r}")
    return _validate(json.loads(m.group(0)))
