# 安装指南（Windows / macOS / Linux）

三种安装方式，任选其一：

## 方式 A：便携整合包（推荐，无需先装 Python 管理工具）

从 GitHub Release 下载 `winagent-<版本>-portable.zip`，解压后：

- **Windows**：双击 `install.bat`
- **macOS / Linux**：`sh install.sh`

脚本自动创建 `.venv`、安装 wheel、运行 `winagent doctor` 自检。
完成后按脚本输出的 MCP 配置片段接入你的平台（ZCode / Claude Desktop / Cursor 等）。

## 方式 B：pip 直接安装（任何平台）

```bash
# 从 GitHub Release 资产安装（无需 PyPI）
pip install https://github.com/ZYYDI1959/winagent-lite/releases/download/v0.5.0/winagent-0.5.0-py3-none-any.whl
# 或源码安装
git clone https://github.com/ZYYDI1959/winagent-lite && cd winagent-lite
pip install -e .
```

## 方式 C：作为 MCP 插件接入（所有平台统一）

无论 A/B 哪种安装，接入方式一致（详见 [docs/PLUGINS.md](docs/PLUGINS.md)）：

```json
{ "mcpServers": { "winagent": {
    "command": "<venv路径>/python(.exe)",
    "args": ["-m", "winagent.mcp_server"] } } }
```

## 硬件兼容矩阵

| 硬件 | 兼容性 | 说明 |
|------|--------|------|
| Intel / AMD CPU（x86_64） | ✅ | Ollama CPU 推理开箱即用；老机器建议 `max_image_width: 1024` |
| Apple Silicon / ARM64 | ✅ | Ollama 原生支持（Metal 加速） |
| NVIDIA 显卡 | ✅ | Ollama CUDA 后端自动启用（`nvidia-smi` 可检出） |
| AMD 显卡 | ✅ | Ollama ROCm / Vulkan 后端自动启用（`doctor` 可检出） |
| Intel 核显/独显（Arc） | ✅ | Ollama Vulkan 后端 |
| 无独立显卡 | ✅ | 全部走 CPU（本项目基线即无独显机器实测：7/10 任务 100%） |

`winagent doctor` 会报告 CPU 型号与 GPU 列表，一眼确认推理后端选择。

## 内存与性能

- 视觉链路有 CI 内存稳定性测试（30 轮 RSS 增长 <30MB 即阈值，当前实测约 1MB）
- 模型常驻内存（Ollama 侧）用 `OLLAMA_KEEP_ALIVE` 控制：设 `0` 用完即卸载，设如 `10m` 保持常驻
- 老机器提速三件套：`max_image_width: 1024` + `image_format: jpeg` + `capture_monitor: 1`