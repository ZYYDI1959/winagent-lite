# Contributing to WinAgent-Lite

感谢参与！这是一个本地优先的 Windows GUI Agent 项目，欢迎任何形式的贡献。

## 开发环境

```bash
git clone https://github.com/ZYYDI1959/winagent-lite
cd winagent-lite
python -m venv .venv && .venv/Scripts/pip install -e .
.venv/Scripts/pip install ruff
cp config.example.yaml config.yaml   # 按需改模型名
winagent doctor                      # 环境自检必须全 PASS
```

- 需要 Windows 10/11（真实键鼠输入依赖 user32）
- 需要 Ollama 本地跑着视觉模型（默认 qwen2.5vl:7b）
- CI 会跑 ruff + Windows GUI 冒烟，push 前本地过一遍：`ruff check src scripts`

## 如何贡献

1. Fork / 分支：`git checkout -b feat/your-feature`
2. 提交信息用英文祈使句（`feat: ...` / `fix: ...` / `docs: ...`）
3. 涉及 GUI 行为的改动请在 PR 里说明实测结果（跑哪个任务、几次、成功几次）
4. 新增评测任务：在 `bench/tasks/` 加 YAML，必须含 setup/teardown（环境重置）和 A 级验证
5. PR 描述附 `winagent bench --tasks <你的任务>` 的输出

## 项目最重要的七条经验（写代码前读一遍，见 docs/baseline_v0.2.md）

1. 另存为类对话框对合成键盘输入免疫——交互走"无对话框"路线
2. 视觉坐标有 1~3% 系统性偏差——闭环必须带验证+容差偏移重试
3. 打字按字符类分流：字母数字中文走 UNICODE，标点运算符走虚拟键（IME 会劫持后者的大小写）
4. 固定 sleep 赌窗口就绪必输——用 focus 等待（轮询前台标题）
5. Win11 记事本会话恢复会复活旧标签——setup 清 TabState
6. 提权窗口对非提权进程免疫——评测 setup 必须清场
7. 验证分级：A 级确定性判定优先，B 级 VLM 看图只做兜底

## 安全约定

- subprocess 一律字面量参数 + 白名单函数映射（参考 agent.py 的 LAUNCHERS 模式）
- 网络请求仅限本地/内网主机（参考 vision.py 的 _request_url 校验）
- 文件操作限制在 Temp 目录下
