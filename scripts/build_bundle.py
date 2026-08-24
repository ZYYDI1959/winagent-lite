"""构建多格式发行包：wheel + 便携 zip（Windows/macOS/Linux 通用）。

用法: python scripts/build_bundle.py [版本号，默认读 pyproject]
产物:
  dist/winagent-<v>-py3-none-any.whl          # pip 直接安装（任意平台）
  dist/winagent-<v>-portable.zip              # 解压 -> 运行一健安装脚本 -> 即用/可作 MCP 插件
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DIST = REPO / "dist"


def main() -> int:
    import tomllib

    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]

    DIST.mkdir(exist_ok=True)
    for f in DIST.iterdir():
        if f.is_file():
            f.unlink()

    print("== 1/2 构建 wheel (py3-none-any) ==")
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(DIST)],
        cwd=REPO, check=True,
    )
    wheel = next(DIST.glob("winagent-*.whl"))
    print("  ->", wheel.name)

    print("== 2/2 组装便携 zip ==")
    zip_path = DIST / f"winagent-{version}-portable.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(wheel, wheel.name)
        z.write(REPO / "scripts" / "install.bat", "install.bat")
        z.write(REPO / "scripts" / "install.sh", "install.sh")
        z.write(REPO / "config.example.yaml", "config.example.yaml")
        z.write(REPO / "README.md", "README.md")
        z.write(REPO / "docs" / "PLUGINS.md", "docs/PLUGINS.md")
    print(f"  -> {zip_path.name} ({zip_path.stat().st_size / 1024:.0f} KB)")
    print("完成：pip install 或解压 zip 后运行 install.bat / install.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())