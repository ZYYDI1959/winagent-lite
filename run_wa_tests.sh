#!/bin/bash
# WinAgent-Lite 在 VirtualBox Ubuntu 实机的全套测试（在桌面会话里运行）
# 用法（已登录桌面后）:
#   DISPLAY=:0 XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.* bash run_wa_tests.sh
# 自动化路径请用 scripts/test_vm_gui.py（子会话、非交互、主判据=映射+输入）。
export PATH="$HOME/.local/bin:$PATH"
REPORT=~/wa-test-report.txt
echo "======== WinAgent-Lite VM 实机测试 $(date) ========" | tee -a "$REPORT"
echo "[0] 环境: $(python3 --version) | DISPLAY=${DISPLAY:-<空>} | SESSION=${XDG_SESSION_TYPE:-<空>}" | tee -a "$REPORT"

echo "[1] doctor 环境自检（含 CPU/GPU 硬件探测）" | tee -a "$REPORT"
winagent doctor 2>&1 | tee -a "$REPORT"

echo "[2] MCP 协议一致性测试" | tee -a "$REPORT"
python3 ~/scripts/test_mcp_protocol.py 2>&1 | tail -4 | tee -a "$REPORT"

echo "[3] 视觉链路内存稳定性测试" | tee -a "$REPORT"
python3 ~/scripts/test_memory.py 2>&1 | tail -3 | tee -a "$REPORT"

echo "[4] 真实 GUI 交互（XTest + 窗口映射 + 截屏 + 真实输入）" | tee -a "$REPORT"
python3 scripts/test_vm_gui.py 2>&1 | tee -a "$REPORT"

echo "[5] 截屏链路（mss 于真实桌面）" | tee -a "$REPORT"
python3 -c "
from winagent import vision
img, mon = vision.capture_screen()
print(f'   截屏 {mon[\"width\"]}x{mon[\"height\"]} -> {img.size}')" 2>&1 | tee -a "$REPORT"

echo "======== 测试结束：完整输出见 ~/wa-test-report.txt ========" | tee -a "$REPORT"
