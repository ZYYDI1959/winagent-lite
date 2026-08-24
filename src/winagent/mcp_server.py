"""MCP stdio server：把 winagent 的能力暴露为工具，供任意 MCP 宿主调用（v0.4 插件化）。

零第三方依赖，按 MCP stdio 传输（换行分隔 JSON-RPC 2.0）实现，协议硬化：
- initialize 协商 protocolVersion（回应用户版本；能力声明 tools）
- notifications/initialized 与空 id 请求不回复
- 未知方法/参数错误返回规范 JSON-RPC 错误对象
- image 类型返回（screenshot 工具）供宿主直接渲染

客户端配置（ZCode / Claude Desktop / Cursor 等）见 docs/PLUGINS.md。
工具目录：look / click / type_text / key / act / run_scenario / doctor / screenshot / discover
"""
from __future__ import annotations

import base64
import io
import json
import sys

# MCP 协议要求 JSON 一律 UTF-8；Windows 控制台默认 cp1252 会写崩中文 description
if hasattr(sys.stdout, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_INFO = {"name": "winagent", "version": "0.4.0"}

_TOOLS = [
    {
        "name": "look",
        "description": "视觉定位屏幕元素（本地 VLM 看图），返回像素坐标或 NOT_FOUND",
        "inputSchema": {
            "type": "object",
            "properties": {"target": {"type": "string", "description": "目标描述，越具体越好"}},
            "required": ["target"],
        },
    },
    {
        "name": "click",
        "description": "真实鼠标点击指定屏幕坐标（会移动物理鼠标）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "double": {"type": "boolean"},
                "right": {"type": "boolean"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "type_text",
        "description": "向当前焦点窗口输入文本（支持中文；按字符类自动选择输入通道）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "mode": {"enum": ["auto", "unicode", "vk"], "default": "auto"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "key",
        "description": "按键或组合键，如 enter / esc / ctrl+s / win+r",
        "inputSchema": {
            "type": "object",
            "properties": {"keys": {"type": "string"}},
            "required": ["keys"],
        },
    },
    {
        "name": "act",
        "description": "闭环操作：视觉定位->真实点击->验证->容差偏移重试（自愈视觉坐标偏差）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "max_tries": {"type": "integer", "default": 5},
                "wait_s": {"type": "number", "default": 1.5},
            },
            "required": ["target"],
        },
    },
    {
        "name": "run_scenario",
        "description": "执行 YAML 场景/评测任务文件（launch/click/type/key 步骤序列）",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "YAML 文件路径"}},
            "required": ["path"],
        },
    },
    {
        "name": "doctor",
        "description": "环境自检（Python/截屏/Ollama/模型/输入后端），被动检查不动键鼠",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "screenshot",
        "description": "截取当前屏幕并作为图像返回（宿主可直接渲染；宽默认 800 降采样）",
        "inputSchema": {
            "type": "object",
            "properties": {"width": {"type": "integer", "default": 800}},
        },
    },
    {
        "name": "discover",
        "description": "报告当前运行环境：平台/输入后端/视觉模型/Ollama 地址/Python 版本",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _handle(name: str, args: dict) -> list[dict]:
    """工具分发，返回 MCP content 列表（text 或 image）。"""
    from winagent import vision
    from winagent.config import load_config

    cfg = load_config()
    if name == "look":
        pos = vision.locate(str(args.get("target", "")), cfg)
        text = "NOT_FOUND" if pos is None else f"FOUND {pos[0]},{pos[1]}"
        return [{"type": "text", "text": text}]
    if name == "click":
        from winagent import hand

        hand.click(int(args.get("x", 0)), int(args.get("y", 0)),
                   double=bool(args.get("double", False)), right=bool(args.get("right", False)))
        return [{"type": "text", "text": f"CLICKED {args.get('x')},{args.get('y')}"}]
    if name == "type_text":
        from winagent import hand

        hand.type_text(str(args.get("text", "")), mode=str(args.get("mode", "auto")))
        return [{"type": "text", "text": f"TYPED {len(str(args.get('text', '')))} chars"}]
    if name == "key":
        from winagent import hand

        hand.combo(str(args.get("keys", "")))
        return [{"type": "text", "text": f"KEY {args.get('keys')}"}]
    if name == "act":
        from winagent import agent

        result = agent.act(str(args.get("target", "")), cfg=cfg,
                           max_tries=int(args.get("max_tries", 5)),
                           wait_s=float(args.get("wait_s", 1.5)))
        return [{"type": "text", "text": json.dumps(result, ensure_ascii=False)[:2000]}]
    if name == "run_scenario":
        from contextlib import redirect_stdout
        from pathlib import Path

        import yaml as _yaml

        from winagent import agent

        data = _yaml.safe_load(Path(str(args.get("path"))).read_text(encoding="utf-8"))
        buf = io.StringIO()
        with redirect_stdout(buf):  # 步骤日志不能混进 stdio 协议流
            result = agent.run_steps(data.get("steps", []), cfg)
        result = dict(result)
        result["log"] = buf.getvalue()
        return [{"type": "text", "text": json.dumps(result, ensure_ascii=False)[:4000]}]
    if name == "doctor":
        from winagent import doctor

        checks = doctor.run_checks(cfg)
        ok = all(c[0] for c in checks)
        lines = [f"[{'PASS' if c[0] else 'FAIL'}] {c[1]}" for c in checks]
        return [{"type": "text", "text": "\n".join(lines) + f"\n结论: {'环境就绪' if ok else '存在未通过项'}"}]
    if name == "screenshot":
        img, mon = vision.capture_screen(cfg)
        width = max(int(args.get("width", 800)), 320)
        small = vision.downscale(img, width)
        buf = io.BytesIO()
        small.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return [
            {"type": "text", "text": f"屏幕 {mon['width']}x{mon['height']}，返回 {small.width}x{small.height} 图像"},
            {"type": "image", "data": b64, "mimeType": "image/png"},
        ]
    if name == "discover":
        import platform

        from winagent import hand

        return [{"type": "text", "text": json.dumps({
            "platform": sys.platform,
            "python": platform.python_version(),
            "hand_backend": hand.BACKEND,
            "vision_model": cfg.vision_model,
            "ollama_url": cfg.ollama_url,
            "image_format": cfg.image_format,
            "capture_monitor": cfg.capture_monitor,
        }, ensure_ascii=False)}]
    raise ValueError(f"未知工具: {name}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            _dispatch(req)
        except Exception:  # noqa: BLE001 单条消息异常只记 stderr，绝不退出 server
            import traceback

            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            if req.get("id") is not None:
                resp = {"jsonrpc": "2.0", "id": req.get("id"),
                        "error": {"code": -32603, "message": "internal error"}}
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()


def _dispatch(req: dict) -> None:
    rid = req.get("id")
    method = req.get("method", "")
    if rid is None:  # notification（如 notifications/initialized）不回复
        return
    if method == "initialize":
        resp = {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": _SERVER_INFO,
        }}
    elif method == "tools/list":
        resp = {"jsonrpc": "2.0", "id": rid,
                "result": {"tools": _TOOLS, "nextCursor": None}}
    elif method == "tools/call":
        try:
            content = _handle(req["params"]["name"], req["params"].get("arguments", {}))
            resp = {"jsonrpc": "2.0", "id": rid, "result": {"content": content}}
        except Exception as exc:  # noqa: BLE001 协议边界：错误必须转成文本响应而非崩掉 server
            resp = {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": f"ERROR: {exc}"}],
                               "isError": True}}
    elif method == "ping":
        resp = {"jsonrpc": "2.0", "id": rid, "result": {}}
    else:
        resp = {"jsonrpc": "2.0", "id": rid,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}
    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()