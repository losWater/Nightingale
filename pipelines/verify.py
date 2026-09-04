#!/usr/bin/env python3
"""仓库级快速门禁：检查正式入口并运行受保护单元测试。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=REPO, check=True)


def main() -> None:
    run(str(REPO / "pipelines" / "v09" / "rebuild.py"), "--check-only")
    run("-m", "unittest", "discover", "-s", "tests", "-q")
    print("仓库快速门禁通过")


if __name__ == "__main__":
    main()
