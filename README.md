# WinAgent-Lite

本地视觉模型驱动的 Windows GUI Agent，附带可复现的 10 任务评测集。

## 这是什么

用本地小模型当"眼睛"（qwen2.5vl via Ollama）看屏幕、返回目标元素坐标，用真实鼠标键盘事件当"手"操控 Windows，再用一套评测集客观度量成功率——让 GUI 自动化从"能演示"变成"能度量"。

## 状态

🚧 开发中（P0 骨架阶段）

## 快速开始

<!-- P2 bench runner 完成后填写：python -m winagent bench -->

## 路线图

- [x] P0 项目骨架
- [ ] P1 眼睛（vision）/ 手（hand）/ 闭环（agent）
- [ ] P2 评测集 + bench runner + baseline 报告
- [ ] P3 planner 接入 + MCP server
- [ ] P4 发布（中英 README / 眼睛模型对比实验 / GitHub）

## License

MIT
