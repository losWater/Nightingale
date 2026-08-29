#!/usr/bin/env python3
"""生成夜莺0.85全码二三键换手权重配对校准套件。"""
from __future__ import annotations

import sys
from pathlib import Path

# 复用已有、已审计的随机网格生成器，只替换本实验的参数档。
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_v085_random_grid_suite as grid  # noqa: E402


grid.PROFILES = [
    ("H0_sep0", 0.1, -90.0, 0.0),
    ("H1_sep0p25", 0.1, -90.0, 0.25),
    ("H2_sep0p5", 0.1, -90.0, 0.5),
    ("H3_sep1", 0.1, -90.0, 1.0),
]


if __name__ == "__main__":
    grid.main()
