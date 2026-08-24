"""最小 MCP stdio server：把 winagent 的眼/手/闭环暴露为 6 个工具。

零第三方依赖，按 MCP stdio 传输（换行分隔 JSON-RPC 2.0）实现。
客户端配置示例（ZCode 等）:
  command: <repo>/.venv/Scripts/python.exe
  args: ["-m", "winagent.mcp_server"]
工具: look / click / type_text / key / act / run_scenario
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout

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
        "description": "真实鼠标点击指定屏幕坐标",
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
        "description": "向当前焦点窗口输入文本（支持中文，绕过输入法）",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
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
        "description": "闭环操作：视觉定位->真实点击->像素差分验证->容差偏移重试",
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
        "description": "执行一个 YAML 场景/评测任务文件（launch/click/type/key 步骤序列）",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "YAML 文件路径"}},
            "required": ["path"],
        },
    },
]


def _handle(name: str, args: dict) -> str:
    from winagent import agent, hand, vision
    from winagent.config import load_config

    cfg = load_config()
    if name == "look":
        pos = vision.locate(str(args["target"]), cfg)
        return "NOT_FOUND" if pos is None else f"FOUND {pos[0]},{pos[1]}"
    if name == "click":
        hand.click(int(args["x"]), int(args["y"]),
                   double=bool(args.get("double", False)), right=bool(args.get("right", False)))
        return f"CLICKED {args['x']},{args['y']}"
    if name == "type_text":
        hand.type_text(str(args["text"]))
        return f"TYPED {len(str(args['text']))} chars"
    if name == "key":
        hand.combo(str(args["keys"]))
        return f"KEY {args['keys']}"
    if name == "act":
        result = agent.act(str(args["target"]), cfg=cfg,
                           max_tries=int(args.get("max_tries", 5)),
                           wait_s=float(args.get("wait_s", 1.5)))
        return json.dumps(result, ensure_ascii=False)[:2000]
    if name == "run_scenario":
        from pathlib import Path

        import yaml as _yaml

        data = _yaml.safe_load(Path(str(args["path"])).read_text(encoding="utf-8"))
        buf = io.StringIO()  # 步骤日志不能混进 stdio 协议流
        with redirect_stdout(buf):
            result = agent.run_steps(data.get("steps", []), cfg)
        result = dict(result)
        result["log"] = buf.getvalue()
        return json.dumps(result, ensure_ascii=False)[:4000]
    raise ValueError(f"unknown tool: {name}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method", "")
        rid = req.get("id")
        if rid is None:  # notification
            continue
        if method == "initialize":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "winagent", "version": "0.1.0"},
            }}
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {"tools": _TOOLS}}
        elif method == "tools/call":
            try:
                text = _handle(req["params"]["name"], req["params"].get("arguments", {}))
                resp = {"jsonrpc": "2.0", "id": rid,
                        "result": {"content": [{"type": "text", "text": text}]}}
            except Exception as exc:  # noqa: BLE001 协议边界：错误必须转成文本响应而非崩掉 server
                resp = {"jsonrpc": "2.0", "id": rid,
                        "result": {"content": [{"type": "text", "text": f"ERROR: {exc}"}],
                                   "isError": True}}
        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {}}
        else:
            resp = {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"method not found: {method}"}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
