"""MCP 协议一致性测试：stdio 握手 + 工具清单 + 无副作用工具调用。

不依赖 GUI 与 Ollama（doctor/discover 被动检查；screenshot 在无显示环境自动跳过）。
用法: python -u scripts/test_mcp_protocol.py
"""
import json
import subprocess
import sys
from pathlib import Path

# Windows CI 控制台默认 cp1252，中文输出会崩——强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = sys.executable


def send(proc, payload: dict) -> dict:
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        stderr = proc.stderr.read() if proc.stderr else ""
        raise AssertionError(f"server 未返回任何内容；stderr:\n{stderr[:2000]}")
    return json.loads(line)


def main() -> int:
    proc = subprocess.Popen(
        [str(PY), "-m", "winagent.mcp_server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    try:
        # 1) initialize 握手：版本协商 + 能力声明
        r = send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
        assert r["result"]["protocolVersion"] == "2024-11-05", r
        assert "tools" in r["result"]["capabilities"], r
        print("[1] initialize 握手 OK")

        # 2) notifications/initialized：无响应是正确行为（后续请求仍正常即可证明）
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        # 3) tools/list：9 个工具、schema 含必填字段
        r = send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        if "result" not in r:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise AssertionError(f"tools/list 响应异常: {r}\nserver stderr:\n{stderr[:2000]}")
        tools = {t["name"]: t for t in r["result"]["tools"]}
        assert len(tools) == 9, tools.keys()
        assert tools["look"]["inputSchema"]["required"] == ["target"]
        print("[2] tools/list OK:", ", ".join(tools))

        # 4) tools/call doctor（无 GUI 无 Ollama）
        r = send(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "doctor", "arguments": {}}})
        text = r["result"]["content"][0]["text"]
        assert "结论" in text
        print("[3] doctor 工具 OK")

        # 5) tools/call discover（环境报告）
        r = send(proc, {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                        "params": {"name": "discover", "arguments": {}}})
        import json as j
        env = j.loads(r["result"]["content"][0]["text"])
        assert env["platform"]
        print(f"[4] discover OK: {env['platform']} / {env['hand_backend']}")

        # 6) 未知方法 -> 规范错误码
        r = send(proc, {"jsonrpc": "2.0", "id": 5, "method": "bogus/method"})
        assert r["error"]["code"] == -32601, r
        print("[5] 错误处理 OK")

        # 7) screenshot（有显示环境才断言调通；无显示应收到 ERROR 而非崩 server）
        r = send(proc, {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                        "params": {"name": "screenshot", "arguments": {"width": 320}}})
        kinds = [c["type"] for c in r["result"]["content"]]
        if "image" in kinds:
            assert r["result"]["content"][1]["mimeType"] == "image/png"
            print("[6] screenshot 图像返回 OK")
        else:
            assert r["result"].get("isError"), r
            print("[6] screenshot 无显示环境，按预期返回错误（server 存活）")
    finally:
        proc.terminate()

    print("\nMCP 协议测试 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())