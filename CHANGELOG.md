# Changelog

## v0.5.1 - 2026-08-24

### Added

- **Linux 真实运行套件** `scripts/test_linux_gui.py`：xvfb 下启动真实 X 应用（xmessage）+ XTest 真实点击/回车 + XQueryTree 窗口生命周期确定性验证（不依赖像素与 Ollama）
- **macOS 真实输入冒烟** `scripts/test_macos_input.py` + CI job（macos-15 真机跑 Quartz CGEvent）
- CI Linux job 升级：真实 X 应用 + 真实输入的端到端闭环验证

### Fixed（全部由实弹测试发现）

- xvfb 下 xterm 缺字体（xfonts-base）、8-bit 深度 BadWindow（24-bit 屏幕）、XIM 探测崩溃、pty 依赖 → 稳定性套件改为 xmessage（零依赖）
- **x11 后端 XQueryTree ctypes 原型缺参数 → 段错误**（补全 6 参数声明）
- **macOS 后端 CGPoint 按值/按引用 ABI 错误 → arm64 段错误**（CGWarpMouseCursorPosition / CGEventCreateMouseEvent / CGEventGetLocation 全部改按值 + 完整原型）
- 测试脚本 UTF-8 输出（Windows cp1252 控制台，两个测试各踩一次）

## v0.5.0 - 2026-08-24

### Added

- **硬件兼容**：`winagent doctor` 新增 CPU/GPU 探测（AMD/Intel CPU、NVIDIA/AMD/Intel GPU；
  Windows 走 PowerShell CIM，Linux 走 lspci，macOS 友好）；推理后端说明（Ollama 自动选择 CUDA/ROCm/Vulkan/CPU）
- **内存稳定性测试** `scripts/test_memory.py`（30 轮视觉链路，RSS 增长 <30MB 阈值；本机实测约 1.2MB，无泄漏），纳入 CI
- **多格式发行包**：
  - `scripts/build_bundle.py` 生成 wheel（py3-none-any，全平台）+ 便携 zip（解压→`install.bat`/`install.sh` 一键安装）
  - `scripts/install.bat` / `scripts/install.sh` 一键安装脚本（自动 venv + 装 wheel + doctor 自检）
  - `docs/INSTALL.md`：三平台三种安装方式 + 硬件兼容矩阵 + 内存/性能调优
  - CI `release.yml`：推送 v* 标签自动构建 wheel/sdist 并上传到 GitHub Release
- README 增补硬件矩阵与安装入口

### Changed

- mcp_server 强制 UTF-8 I/O（修复 Windows cp1252 控制台写崩协议流）；每消息异常隔离（单条坏消息不再杀 server）

## v0.4.0 - 2026-08-24

### Added

- **MCP 插件化**：server 协议硬化（initialize 版本协商 / notifications / 规范错误码），工具 6→9 个（新增 `doctor` / `screenshot` / `discover`），`screenshot` 走 MCP image content 原生返回（宿主直接渲染）
- **docs/PLUGINS.md**：ZCode / Claude Desktop / Cursor 等平台的接入配置、工具目录、安全边界与排障
- **协议一致性测试** `scripts/test_mcp_protocol.py`（stdio 握手/工具清单/错误处理/image 返回，CI 三平台跑）
- README 介绍页全面优化：能力表 / 架构图 / 插件接入段 / 平台表 / 评测结论 / 安全边界

### Changed

- mcp_server 工具 schema 全部带类型与描述，`run_scenario` 日志与协议流隔离

## v0.3.0 - 2026-08-24

### Added

- **跨平台输入后端**：hand 拆为平台分发器——win32（user32/SendInput，全功能）/ x11（XTest，ASCII 直输）/ macos（Quartz CGEvent，待实机验证），API 与 VK 常量三端一致
- **老 Windows 兼容**：requires-python >=3.10，CI 覆盖 py3.10/3.13
- **CI 三平台矩阵**：Windows(3.10/3.13) 真实 GUI 冒烟 + Ubuntu xvfb 下 XTest 后端真实输入测试 + macOS 导入冒烟
- 性能配置：`image_format: png|jpeg`（jpeg 请求体小约 10 倍）、`capture_monitor`（单屏省抓屏）、`max_image_width` 可降、`typing_interval_ms` 可调
- 模型常驻：改用服务器端 `OLLAMA_KEEP_ALIVE` 环境变量（全局生效，不再每请求传参）
- bench 进程操作改 psutil（跨平台），任务支持 `platforms:` 门控（非本平台任务自动跳过）

### Changed

- config 载入即校验（image_format/typing_interval 非法值兜底）
- doctor 新增输入后端检测项
- 性能基线（实测）：jpeg 编码体积约为 png 的 1/10，识别无感

## v0.2.0 - 2026-08-24

### Added

- **bench 评测引擎**：10 个评测任务（YAML 定义 setup/teardown/steps/verify），A/B 两级验证（确定性判定 / VLM 看图判定），每次运行存 trace.json + final.png
- **planner 本地规划器**：自然语言目标 → 步骤 JSON（白名单校验），云 API 适配器预留
- **MCP server**：`winagent-mcp` 把 look/click/type_text/key/act/run_scenario 六个工具暴露给任意 harness
- **`winagent doctor` 环境自检**：Python/屏幕采集/Ollama/模型在列/临时目录，被动检查不动键鼠
- **CI**：ruff 静态检查 + windows-latest 真实 GUI 冒烟（鼠标/键盘，不依赖 Ollama）
- 基线报告 v0.2：10 任务中 7 个 100%，七大发现（docs/baseline_v0.2.md）

### Fixed

- WinUI 应用（计算器）不接受 UNICODE 注入的运算符 → ASCII 标点走虚拟键原子提交（单次 SendInput）
- 中文 IME 劫持虚拟键路径（大小写漂移）→ 打字按字符类分流：字母/数字/中文走 UNICODE，标点运算符走虚拟键
- Win11 记事本会话恢复复活未保存标签 → bench 新增 `clear_notepad_session` 动词
- tasklist 的 GBK 输出按 UTF-8 解码崩溃 → 字节捕获 + 宽容解码
- 视觉点击把光标放在点击处 → 打字步骤前置 Ctrl+End（任务内声明）

### Changed

- mss 弃用警告清理（`mss.MSS` 新 API）
- type 步骤支持 `{text, mode: unicode|vk|auto}` 显式指定输入通道

## v0.1.0 - 2026-08-24

- 首个可用版本：vision（眼）/ hand（手）/ agent（闭环+容差自愈）/ 场景引擎
