# WinAgent-Lite 🤖🖱️

**本地视觉模型驱动的 GUI Agent，还是一个即插即用的 MCP 插件——让任何 AI 平台拥有"眼睛"和"手"。**

![demo](docs/demo.gif)

[![CI](https://github.com/ZYYDI1959/winagent-lite/actions/workflows/ci.yml/badge.svg)](https://github.com/ZYYDI1959/winagent-lite/actions/workflows/ci.yml)
[![Release v0.6.0](https://img.shields.io/badge/release-v0.6.0-blue)](https://github.com/ZYYDI1959/winagent-lite/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 🎯 目标驱动（v0.6.0 新增，端到端实测）

只说目标，Agent 自己规划、自己动手：

```bash
winagent plan "打开记事本，输入你好世界" --execute
```

本地文本模型把目标分解为步骤 JSON（白名单校验）→ 闭环执行 → 真实窗口输入中文。全程本地推理、零云 API。MCP 宿主同样可调用 `plan` 工具拿到步骤再自行编排。

## 安装（Windows / macOS / Linux）

- **便携整合包**：下载 Release 里的 `winagent-*-portable.zip` → 解压 → 运行 `install.bat`（Win）/ `sh install.sh`（macOS/Linux）→ 自动装好并自检
- **pip 直装**：`pip install <Release 里的 .whl 下载链接>`（py3-none-any，全平台通用）
- 接入 ZCode / Claude / Cursor 等 MCP 平台：见 [docs/PLUGINS.md](docs/PLUGINS.md)
- 详细安装与硬件矩阵：见 [docs/INSTALL.md](docs/INSTALL.md)

> 一台没有独立显卡的普通电脑：本地小模型当眼睛（识别屏幕元素）＋ 真实键鼠事件当手（像人一样操作任何软件），再用评测集把成功率量化。从"能演示"到"能度量"，再到"能被任何平台调用"。

## 它能做什么

| 能力 | 说明 |
|------|------|
| 🧿 **看** | 截屏 → 本地 VLM（Ollama）→ 返回元素坐标 / 屏幕问答 |
| 🖐️ **点** | user32 / XTest / Quartz 真实输入，支持中文打字、组合键 |
| 🔁 **闭环** | 定位→点击→验证→容差偏移重试（实证自愈视觉坐标 1~3% 偏差） |
| 📊 **度量** | 10 个评测任务、A/B 两级验证、轨迹+截图存档、成功率报告 |
| 🧠 **规划** | 自然语言目标 → 步骤序列（本地文本模型） |
| 🔌 **插件化** | MCP stdio server：ZCode / Claude Desktop / Cursor 等即插即用 |

**像插件一样按需调用**：平台把 10 个工具挂进自己的工具列表（`plan / look / click / type_text / key / act / run_scenario / doctor / screenshot / discover`），业务需要"点哪个按钮"就调 `act`，需要"看屏幕"就调 `screenshot`，需要"从目标生成步骤"就调 `plan`——多软件协作由宿主编排，WinAgent 只负责真实的"眼"、"手"和"脑干"。接入方法见 [docs/PLUGINS.md](docs/PLUGINS.md)。

## 架构

```
vision.py    眼睛: 截屏 -> 降采样 -> Ollama VLM -> 坐标/问答      （跨平台）
hand/        手:   win32(user32) | x11(XTest) | macos(Quartz)   （平台后端分发）
agent.py     脑干: 闭环 + 步骤解释器 + 焦点等待 + 容差自愈
bench.py     度量: 任务 YAML(含 setup/teardown) -> 成功率报告
planner.py   规划: 目标 -> 步骤 JSON（本地模型，云 API 适配器预留）
mcp_server.py 插件: MCP stdio server，9 工具，协议一致性 CI 验证
```

## 快速开始

```bash
git clone https://github.com/ZYYDI1959/winagent-lite && cd winagent-lite
python -m venv .venv && .venv/Scripts/pip install -e .
# 需要本机 Ollama（默认模型 qwen2.5vl:7b）
cp config.example.yaml config.yaml

winagent doctor                          # 环境自检（一条命令诊断一切）
winagent look "任务栏右下角的时钟"         # 眼睛：FOUND x,y
winagent click 1824 1056                 # 手：真实点击
winagent run scenarios/notepad_save.yaml # 闭环：YAML 步骤
winagent bench                           # 评测：全任务成功率报告
winagent plan "打开记事本输入你好并保存"     # 规划：目标 -> 步骤
winagent-mcp                             # 以 MCP 插件模式运行
```

## 作为 MCP 插件使用（30 秒接入）

```json
{ "mcpServers": { "winagent": {
    "command": "D:\\winagent-lite\\.venv\\Scripts\\python.exe",
    "args": ["-m", "winagent.mcp_server"] } } }
```

之后你的 AI 平台就能：`screenshot` 看你的屏幕 → `act` 点击任何软件 → `type_text` 打字。
各平台详细配置、安全边界、排障：** [docs/PLUGINS.md](docs/PLUGINS.md)**。

## 平台支持

| 平台 | 状态 | 说明 |
|------|------|------|
| Windows 10/11 | ✅ 完整 | 中文直输，评测基准所在；CI 真实 GUI 冒烟（py3.10/3.13） |
| Linux (X11) | ✅ 可用 | XTest 后端；ASCII 直输（中文走剪贴板方案）；CI xvfb 真实输入测试 |
| macOS | 🚧 代码就绪 | Quartz CGEvent 后端，待实机验证转正 |

## 评测结果与实测发现

- 基线 v0.2：健康环境下 **7/10 任务 100%**，其余 3 个是诚实的模型能力边界数据点
- 完整报告：** [docs/baseline_v0.2.md](docs/baseline_v0.2.md)**；每次运行轨迹可复现（`winagent bench`）
- 核心结论（七条，全部有对照实验）：
  1. 另存为类对话框对合成键盘输入免疫 → 交互设计走"无对话框"路线
  2. 视觉坐标有 1~3% 系统性偏差 → 闭环"验证+容差重试"实证自愈
  3. 打字按字符类分流：字母数字中文走 UNICODE（绕 IME），标点运算符走虚拟键原子提交
  4. 固定 sleep 赌窗口就绪必输 → 轮询前台标题（focus wait）
  5. Win11 记事本会话恢复会复活旧标签 → 评测 setup 清 TabState
  6. 提权窗口对非提权 agent 免疫 → 评测必须清场
  7. 眼睛模型梯度：3b 盲 / 7b+容差=性价比甜点 / 27b 慢且偏（无独显机器）

## 性能与配置

- `image_format: jpeg` 请求体小约 10 倍；`capture_monitor` 单屏省抓屏；`typing_interval_ms` 调速
- 模型常驻用服务器端 `OLLAMA_KEEP_ALIVE`（全局生效）
- 完整配置项见 [config.example.yaml](config.example.yaml)，非法值载入即兜底

## 安全边界

- 网络请求仅限本机/内网（SSRF 防护），subprocess 全白名单字面量，文件操作限 Temp 目录
- 动作工具操纵真实键鼠——宿主应鉴权后调用；`doctor/discover/screenshot` 全程被动

## 项目状态

- 版本历史与变更：** [CHANGELOG.md](CHANGELOG.md)**（v0.1 → v0.4）
- 社区文件：贡献指南 / Issue 模板 / PR 模板 / 行为准则 / 安全政策 —— 健康分 100
- 学生作品：从一台没有 N 卡的电脑、一个"不知道 AI 方向"的问题开始，到 4 个版本的可度量 Agent 项目

## License

MIT