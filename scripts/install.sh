#!/bin/sh
# WinAgent-Lite 一键安装脚本（macOS / Linux：解压便携包后运行）
# 用法: sh install.sh
set -e
echo "============================================"
echo " WinAgent-Lite 安装（$(\
uname -s 2>/dev/null || echo unknown)）"
echo "============================================"
PYTHON="${PYTHON:-python3}"
if [ ! -d .venv ]; then
    echo "[1/3] 创建虚拟环境..."
    "$PYTHON" -m venv .venv
fi
WHEEL=$(ls winagent-0.*-py3-none-any.whl 2>/dev/null | head -1)
echo "[2/3] 安装 wheel 包: $WHEEL"
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install "$WHEEL"
echo "[3/3] 环境自检..."
.venv/bin/winagent doctor
echo
echo "安装完成。作为 MCP 插件接入（见 docs/PLUGINS.md）："
echo "  command: $(pwd)/.venv/bin/python"
echo "  args:    -m winagent.mcp_server"