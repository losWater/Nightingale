#!/usr/bin/env python3
"""从0.9两张主表一键重建搜狗与手心派生表。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.9"
SCRIPTS = ROOT / "work" / "夜莺0.85" / "scripts"
TABLES = RELEASE / "01_正式码表"
ATTACHMENTS = RELEASE / "02_输入法挂接"


def run(arguments: list[str]) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-palm", action="store_true",
        help="只重建搜狗派生表，不重建手心文件",
    )
    args = parser.parse_args()
    run([
        str(SCRIPTS / "build_v085_code_first_mirror.py"),
        "--source", str(TABLES / "夜莺0.9字词表.txt"),
        "--output", str(TABLES / "夜莺0.9字词表_码前.txt"),
    ])
    common = [
        "--single", str(TABLES / "夜莺码v0.9单字版.txt"),
        "--combined", str(TABLES / "夜莺0.9字词表.txt"),
        "--quick", str(ROOT / "symbo.txt"),
        "--short-words", str(TABLES / "夜莺码v0.9简词表.tsv"),
        "--extension-characters", str(TABLES / "夜莺码v0.9扩展字表.tsv"),
    ]
    run([
        str(SCRIPTS / "build_v085_derived_tables_from_masters.py"),
        *common, "--release-dir", str(RELEASE),
        "--output-dir", str(ATTACHMENTS / "搜狗输入法"),
    ])
    run([
        str(SCRIPTS / "build_v085_sogou_wubi_table.py"),
        "--combined", str(TABLES / "夜莺0.9字词表.txt"),
        "--extension-characters", str(TABLES / "夜莺码v0.9扩展字表.tsv"),
        "--quick", str(ROOT / "symbo.txt"),
        "--output", str(ATTACHMENTS / "搜狗输入法" / "夜莺码v0.9搜狗五笔版.txt"),
    ])
    run([
        str(SCRIPTS / "build_v085_bingling_table.py"),
        "--combined", str(TABLES / "夜莺0.9字词表.txt"),
        "--extension-characters", str(TABLES / "夜莺码v0.9扩展字表.tsv"),
        "--quick", str(ROOT / "symbo.txt"),
        "--output", str(ATTACHMENTS / "冰凌输入法" / "夜莺码v0.9冰凌词库.txt"),
    ])
    if not args.skip_palm:
        run([
            str(SCRIPTS / "build_v085_palm_tables.py"),
            *common, "--output-dir", str(ATTACHMENTS / "手心输入法"),
        ])
        run([str(SCRIPTS / "build_v085_palm_modular_tables.py")])
    print("0.9挂接表已由两张主表重建完成")


if __name__ == "__main__":
    main()
