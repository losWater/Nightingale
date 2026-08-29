# -*- coding: utf-8 -*-
"""给字词撞车 CSV 追加复审状态备注。"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml

from build_v07_release import load_default_word_first_codes


BROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = BROOT / "work/v07_unlocked_audit/当前复审基线_卩y_讠m_媚无理"
DEFAULT_CSV = BROOT / "work/v07_unlocked_audit/最终字词相撞明细_复审后_实际四码口径.csv"

# 已逐项过堂并决定保留单字首选的码位。
RETAINED = {
    "fuve": "附着误音且覆辙多见于长词，保留父",
    "uize": "实则／失责偏书面，保留使",
    "llzd": "俩是高频口语单字，靓仔地域性较强",
    "vlxp": "壮是高频常用单字，装卸使用场景较窄",
    "jimb": "jim 必须给急解除急／箕重码，保留计",
    "jmzo": "间作生僻，保留健",
    "yzbj": "二字词生僻且仅撞弱四字词，保留右",
    "xmyl": "仅撞四字简词，保留陷",
    "ybyv": "仅撞四字简词，保留隐",
    "jnhe": "相撞二字词排名较后，保留狡",
    "qitn": "保护姓名用字琦",
    "jkqr": "保护姓名用字菁",
    "bwqj": "仅撞四字简词，保留蓓",
    "qmmo": "阡陌偏文学且常嵌长语境，保留谴",
}

SHORT_TRANSFER = {
    "vihg": "已处理：三码 vih 改给致，释放制衡",
    "jitv": "已处理：三码 jit 改给忌，释放击退／鸡腿",
}

FALSE_COLLISION = {
    "ddzq": "已处理：假撞；弹电子琴首字应读 tán，不是 dàn",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--code", type=Path, default=DEFAULT_DIR / "code_应用全部谕旨_复核.txt")
    ap.add_argument("--elements", type=Path, default=DEFAULT_DIR / "elements.yaml")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    manual = yaml.safe_load((BROOT / "work/简码资产.yaml").read_text(encoding="utf-8"))
    code_rows = [line.split("\t") for line in args.code.read_text(encoding="utf-8").splitlines()]
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    explicit = {str(code) for code in (manual.get("sogou_candidate_offsets") or {})}
    compensation = {
        str(code): str(char)
        for code, char in (manual.get("word_yield_three_secondaries") or {}).items()
    }
    automatic = load_default_word_first_codes(code_rows, elements, manual)

    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("撞车 CSV 为空")

    counts = {"人工让词": 0, "自动让词": 0, "改简码": 0, "保留": 0, "假撞": 0, "未处理": 0}
    for row in rows:
        code = str(row.get("全码", ""))
        if code in explicit:
            note = "已处理：人工让词；单字后移"
            if compensation.get(code) == str(row.get("单字", "")):
                note += "；已加入对应的三码次选"
            elif code == "yian":
                note += "；椅另有独立主码 yiav"
            elif code == "yivj":
                note += "；怡另有独立主码 yivk"
            elif code == "xkfa":
                note += "；省另有高频读音三码 ugf，冷门音不补三码"
            elif code == "wwyr":
                note += "；三码 wwy 已从微转给卫"
            counts["人工让词"] += 1
        elif code in SHORT_TRANSFER:
            note = SHORT_TRANSFER[code]
            counts["改简码"] += 1
        elif code in FALSE_COLLISION:
            note = FALSE_COLLISION[code]
            counts["假撞"] += 1
        elif code in RETAINED:
            note = "已处理：确认保留；" + RETAINED[code]
            counts["保留"] += 1
        elif code in automatic:
            note = "已处理：3762名后撞前30000二字词，自动让词"
            counts["自动让词"] += 1
        else:
            note = ""
            counts["未处理"] += 1
        row["备注"] = note

    output = args.output or args.csv
    fields = list(rows[0])
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(" ".join(f"{key}={value}" for key, value in counts.items()))
    print(output)


if __name__ == "__main__":
    main()
