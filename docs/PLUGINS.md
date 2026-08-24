# 作为 MCP 插件接入（v0.4）

WinAgent-Lite 是一个标准的 MCP（Model Context Protocol）stdio server——任何支持 MCP 的
平台（ZCode、Claude Desktop、Cursor、VS Code Copilot 等）都可以把它当插件装上，
按需调用它的"眼睛"与"手"。

## 工具目录

| 工具 | 作用 | 无 GUI 环境 |
|------|------|------------|
| `look` | 视觉定位屏幕元素 → 像素坐标 | ✗（需要显示+Ollama） |
| `click` | 真实鼠标点击 | ✗ |
| `type_text` | 向焦点窗口输入文本（中文可） | ✗ |
| `key` | 按键/组合键（enter/ctrl+s/win+r…） | ✗ |
| `act` | 闭环：定位→点击→验证→容差重试 | ✗ |
| `run_scenario` | 执行 YAML 步骤/评测任务 | ✗ |
| `doctor` | 环境自检 | ✓ |
| `screenshot` | 截屏并以图像返回（宿主可渲染） | 视显示而定 |
| `discover` | 环境报告（平台/后端/模型） | ✓ |

## 通用配置（JSON 片段）

```json
{
  "mcpServers": {
    "winagent": {
      "command": "D:\\path\\to\\winagent-lite\\.venv\\Scripts\\python.exe",
      "args": ["-m", "winagent.mcp_server"]
    }
  }
}
```

> 建议用项目 venv 里的 `python.exe` 绝对路径（Windows），或 `python3 -m winagent.mcp_server`（Linux/macOS）。
> 需要先 `pip install -e .`（或 `pip install winagent`，发布 PyPI 后）。

## 各平台接入

### ZCode

用户设置 → MCP → 添加 server，填入上面的 command/args；或写入 MCP 配置 JSON 后重启。

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`：

```json
{ "mcpServers": { "winagent": { "command": "...python.exe", "args": ["-m", "winagent.mcp_server"] } } }
```

### Cursor / VS Code

设置 → MCP → Add new MCP server（stdio 类型），填 command/args 即可。

## 行为说明与安全

- 动作类工具操纵的是**真实鼠标键盘**——宿主应鉴权后再调用（ZCode 可用权限钩子确认）。
- Windows 下运行要求：普通用户权限即可；macOS 首次使用需授予「辅助功能」权限。
- `doctor` / `discover` 永远被动；`screenshot` 只读屏幕。
- 视觉模型走本机 Ollama（默认 qwen2.5vl:7b），无任何外网请求。

## 排障

1. 先跑 `winagent doctor` —— 任何 FAIL 先解决对应项。
2. 协议层问题：`python scripts/test_mcp_protocol.py` 全绿即 server 本身正常。
3. 工具调用报 `hand 后端不可用`：检查平台与显示环境（Linux 无头需 xvfb-run；macOS 需辅助功能权限）。
4. 模型相关报错：确认 Ollama 在跑、`config.yaml` 的模型名在 `ollama list` 里。