# Security Policy

## 报告漏洞

如果发现安全漏洞，请**不要开公开 issue**。

请通过 GitHub Security Advisories（仓库 Security 标签页 → Report a vulnerability）私密报告，或联系仓库所有者。

## 支持版本

| 版本 | 状态 |
|------|------|
| 0.2.x | :white_check_mark: 支持 |
| < 0.2 | :x: 不支持 |

## 本项目的安全边界（设计层面）

- **进程启动**：白名单函数映射（notepad/calc/explorer/taskmgr），任务文件无法执行任意命令
- **网络**：Ollama 请求仅限 http/https 且主机必须为本机/内网，禁重定向
- **文件**：评测动词的文件操作限制在 Temp 目录
- **真实输入**：合成键鼠只作用于前台窗口，评测任务均为非破坏性操作
