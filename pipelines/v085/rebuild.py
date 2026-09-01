#!/usr/bin/env python3
"""夜莺0.8.5派生发布物的稳定顶层入口。

当前委托给已经验证的兼容实现；以后迁移内部脚本时，用户命令无需变化。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
IMPLEMENTATION = REPO / "work" / "夜莺0.85" / "scripts" / "rebuild_v085_attachments.py"
REQUIRED = (
    REPO / "schema" / "v0.8.5" / "manifest.yaml",
    REPO / "releases" / "v0.8.5" / "01_正式码表" / "夜莺码v0.8.5单字版.txt",
    REPO / "releases" / "v0.8.5" / "01_正式码表" / "夜莺0.8.5字词表.txt",
    REPO / "symbo.txt",
    IMPLEMENTATION,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="从两张0.8.5主表重建输入法挂接表")
    parser.add_argument("--skip-palm", action="store_true", help="不重建手心文件")
    parser.add_argument("--check-only", action="store_true", help="只检查入口与必需真源是否齐全")
    args = parser.parse_args()
    missing = [path for path in REQUIRED if not path.is_file()]
    if missing:
        raise FileNotFoundError("缺少必需文件：\n" + "\n".join(str(path) for path in missing))
    if args.check_only:
        print(f"0.8.5构建入口检查通过：{len(REQUIRED)}项必需文件齐全")
        return
    command = [sys.executable, str(IMPLEMENTATION)]
    if args.skip_palm:
        command.append("--skip-palm")
    subprocess.run(command, cwd=REPO, check=True)


if __name__ == "__main__":
    main()
