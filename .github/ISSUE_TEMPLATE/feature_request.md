name: Feature request
about: 提议新功能/新评测任务
title: "[feat] "
labels: enhancement
body:
  - type: textarea
    id: idea
    attributes:
      label: 你的想法
      description: 想要什么能力/任务？解决什么问题？
    validations:
      required: true
  - type: textarea
    id: how
    attributes:
      label: 实现思路（可选）
      description: 涉及哪个模块（vision/hand/agent/bench/planner/mcp_server）？
  - type: checkboxes
    id: rules
    attributes:
      label: 已读项目七条经验
      options:
        - label: 我读过 docs/baseline_v0.2.md 的七条发现（对话框雷区/坐标容差/IME 分流等）
          required: true
