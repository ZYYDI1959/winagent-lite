@echo off
rem WinAgent-Lite 一键安装脚本（Windows：解压便携包后双击运行）
chcp 65001 >nul
echo ============================================
echo  WinAgent-Lite 安装（Windows）
echo ============================================
if not exist .venv (
    echo [1/3] 创建虚拟环境...
    py -3 -m venv .venv || python -m venv .venv
)
echo [2/3] 安装 wheel 包...
for %%f in (winagent-0.*-py3-none-any.whl) do set WHEEL=%%f
.venv\Scripts\pip install --upgrade pip -q
.venv\Scripts\pip install "%WHEEL%"
echo [3/3] 环境自检...
.venv\Scripts\winagent doctor
echo.
echo 安装完成。作为 MCP 插件接入 ZCode/Claude/Cursor 等：
echo   command: %CD%\.venv\Scripts\python.exe
echo   args:    -m winagent.mcp_server
echo （详细见 docs/PLUGINS.md）
pause