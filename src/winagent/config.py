"""配置：默认值 + 可选 config.yaml 覆盖（不存在的键继续用默认值）。"""
from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import yaml


@dataclass
class Config:
    ollama_url: str = "http://localhost:11434"
    vision_model: str = "qwen2.5vl:7b"
    max_image_width: int = 1600
    request_timeout: int = 240


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
