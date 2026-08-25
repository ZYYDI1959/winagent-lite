"""配置：默认值 + 可选 config.yaml 覆盖（不存在的键继续用默认值）。"""
from __future__ import annotations

import sys
from dataclasses import dataclass, fields
from pathlib import Path

import yaml


@dataclass
class Config:
    ollama_url: str = "http://localhost:11434"
    # 0825 三代同场实测定版：qwen3-vl:8b-instruct 在 7b 全灭的开始按钮上 2/2 命中（±3px），
    # 大目标持平、同速、输出格式零适配；27b 太慢(2-3tok/s)、3b 纯盲、思考版默认 tag 有陷阱。
    # 注意必须用 -instruct 后缀 tag，Ollama 裸 `qwen3-vl:8b` 是思考版（答一字烧 1334 token）。
    vision_model: str = "qwen3-vl:8b-instruct"
    # 性能与资源开销
    max_image_width: int = 1600          # 截图降采样宽度：越小传输越快、模型处理越快
    image_format: str = "png"            # png | jpeg（jpeg 体积小约 10 倍，UI 截图无损观感）
    capture_monitor: int = 0             # 0=全部显示器并集；1..n=仅指定主/次显示器（省抓屏开销）
    # 模型常驻请在 Ollama 服务器端设 OLLAMA_KEEP_ALIVE（如 "10m"），
    # 全局生效且无需每请求传参（经安全审查后不再走请求体注入）。
    typing_interval_ms: int = 10         # 打字间隔：越大越稳，越小越快（IME 环境建议 >=10）
    request_timeout: int = 240

    def __post_init__(self) -> None:
        if self.image_format not in ("png", "jpeg"):
            self.image_format = "png"
        self.typing_interval_ms = max(int(self.typing_interval_ms), 1)


def load_config(path: str | None = None) -> Config:
    cfg = Config()
    p = Path(path) if path else Path("config.yaml")
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        names = {f.name for f in fields(Config)}
        for key, value in data.items():
            if key in names:
                setattr(cfg, key, value)
    return cfg


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    return sys.platform == "darwin"