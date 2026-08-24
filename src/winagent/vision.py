"""眼睛：截屏 -> 降采样 -> 本地视觉模型(Ollama) -> 目标坐标 / 屏幕问答。

移植自 tools/screencmd.ps1，协议不变（相对坐标 0~1，FOUND x=.. y=.. / NOT_FOUND），
修复了原脚本的 prompt 尺寸打印错误与死代码，模型名/URL 全部走 Config。

安全边界：本项目是"本地 Ollama 客户端"，请求地址只允许 http/https 且
主机必须解析为本机/内网（loopback/私有网段/链路本地），公网地址一律拒绝。
"""
from __future__ import annotations

import base64
import io
import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests
from PIL import Image

from winagent.config import Config

try:  # mss>=10 推荐 MSS 类；老版本回退到工厂函数
    from mss import MSS as _MSSFactory
except ImportError:
    from mss import mss as _MSSFactory

_LOCATE_PROMPT = (
    "这是电脑屏幕截图，尺寸 {w}x{h}。"
    "请在图中找到『{target}』这个元素（按钮/图标/文字区域）。"
    "回答它的中心位置，格式严格为：FOUND x=0.xx y=0.yy"
    "（x 和 y 是相对值，0~1，x 从左到右，y 从上到下）。"
    "如果屏幕上没有这个元素，只回答：NOT_FOUND"
)
_ASK_PROMPT = "屏幕上是否看得到『{word}』这几个字？只回答 YES 或 NO。"
_FOUND_RE = re.compile(r"FOUND\s+x=([0-9.]+)\s+y=([0-9.]+)")


def _is_local_host(hostname: str) -> bool:
    """主机是否为本机/内网：localhost、*.local，或解析结果全部是环回/私有/链路本地地址。"""
    if hostname.lower() == "localhost" or hostname.endswith(".local"):
        return True
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            return False
    return True


def _request_url(base: str) -> str:
    """校验 ollama_url 并拼出 API 地址；协议或主机不合法直接抛 ValueError。"""
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"不支持的 ollama_url: {base!r}（仅 http/https）")
    if not _is_local_host(parsed.hostname):
        raise ValueError(f"ollama_url 主机必须是本机/内网地址: {base!r}")
    return base.rstrip("/") + "/api/generate"


def _ollama_tags_url(cfg: Config) -> str:
    """经同一校验通道得到模型列表地址（doctor/list_models 用）。"""
    return _request_url(cfg.ollama_url).replace("/api/generate", "/api/tags")


def capture_screen(cfg: Config | None = None) -> tuple[Image.Image, dict]:
    """抓取屏幕，返回 (图像, mss 的 monitor 信息)。

    capture_monitor: 0=所有显示器并集；1..n=仅该显示器（老机器/单屏场景省抓屏开销）。
    """
    cfg = cfg or Config()
    with _MSSFactory() as sct:
        idx = max(0, int(cfg.capture_monitor))
        monitors = sct.monitors
        idx = min(idx, len(monitors) - 1)
        mon = monitors[idx]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        return img, mon


def downscale(img: Image.Image, max_width: int) -> Image.Image:
    """降采样到限定宽度，防止视觉模型处理超大图。"""
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    return img.resize((max_width, round(img.height * ratio)))


def _to_b64(img: Image.Image, fmt: str = "png") -> str:
    """编码为 base64。jpeg 体积约为 png 的 1/10，UI 截图无可见质量损失。"""
    buf = io.BytesIO()
    if fmt == "jpeg":
        img.convert("RGB").save(buf, format="JPEG", quality=85)
    else:
        img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _generate(prompt: str, image: Image.Image, cfg: Config) -> str:
    payload: dict = {
        "model": cfg.vision_model,
        "prompt": prompt,
        "images": [_to_b64(image, cfg.image_format)],
        "stream": False,
    }
    url = _request_url(cfg.ollama_url)
    resp = requests.post(url, json=payload, timeout=cfg.request_timeout, allow_redirects=False)
    resp.raise_for_status()
    return resp.json()["response"]


def locate(target: str, cfg: Config | None = None) -> tuple[int, int] | None:
    """定位目标元素，返回虚拟屏幕绝对像素坐标；找不到返回 None。

    模型返回相对坐标，乘以完整屏幕尺寸并加上虚拟屏幕原点偏移，
    与降采样比例无关（相对坐标天然免疫缩放）。
    """
    cfg = cfg or Config()
    full, mon = capture_screen(cfg)
    small = downscale(full, cfg.max_image_width)
    prompt = _LOCATE_PROMPT.format(w=small.width, h=small.height, target=target)
    answer = _generate(prompt, small, cfg)

    m = _FOUND_RE.search(answer)
    if not m:
        return None
    rx, ry = float(m.group(1)), float(m.group(2))
    if rx > 1:
        rx /= 100  # 兼容模型偶尔输出 0~100 百分比
    if ry > 1:
        ry /= 100
    rx = min(max(rx, 0.0), 1.0)
    ry = min(max(ry, 0.0), 1.0)
    x = round(rx * full.width) + mon["left"]
    y = round(ry * full.height) + mon["top"]
    return x, y


def list_models(cfg: Config | None = None) -> list[str]:
    """列出 Ollama 可用模型名（走与 generate 相同的受控通道）。"""
    cfg = cfg or Config()
    resp = requests.get(_ollama_tags_url(cfg), timeout=10)
    resp.raise_for_status()
    return [m["name"] for m in resp.json().get("models", [])]


def ask(word: str, cfg: Config | None = None) -> bool:
    """问模型当前屏幕上是否能看到某词（供闭环验证用，移植自 auto_gui 的 Vision-Ask）。"""
    cfg = cfg or Config()
    img, _ = capture_screen(cfg)
    small = downscale(img, cfg.max_image_width)
    answer = _generate(_ASK_PROMPT.format(word=word), small, cfg)
    return "YES" in answer.upper()


def generate_text(prompt: str, model: str, base_url: str | None = None, timeout: int = 120) -> str:
    """纯文本生成（planner 等用），走与视觉相同的受控 Ollama 通道。"""
    url = _request_url(base_url or "http://localhost:11434")
    payload = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(url, json=payload, timeout=timeout, allow_redirects=False)
    resp.raise_for_status()
    return resp.json()["response"]