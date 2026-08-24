name: Bug report
about: 报告 WinAgent-Lite 的问题
title: "[bug] "
labels: bug
assignees: ''
body:
  - type: markdown
    attributes:
      value: |
        感谢报告！请先跑 `winagent doctor` 并贴出结果。
  - type: textarea
    id: what-happened
    attributes:
      label: 发生了什么
      description: 预期行为 vs 实际行为
    validations:
      required: true
  - type: textarea
    id: doctor
    attributes:
      label: winagent doctor 输出
      render: shell
    validations:
      required: true
  - type: textarea
    id: trace
    attributes:
      label: 轨迹/截图
      description: runs/<task>/run<k>/trace.json 与 final.png，失败复现的关键证据
      render: shell
  - type: input
    id: env
    attributes:
      label: 环境
      placeholder: "Windows 11 24H2, Python 3.13, Ollama 0.3.x, qwen2.5vl:7b"
    validations:
      required: true
