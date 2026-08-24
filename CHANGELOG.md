# Changelog

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
