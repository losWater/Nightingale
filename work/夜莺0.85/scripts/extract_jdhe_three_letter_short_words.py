#!/usr/bin/env python3
"""提取简单鹤三码简词，并按夜莺既定飞键规则初筛。"""

from __future__ import annotations

import argparse
from pathlib import Path


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def read_attachment(path: Path) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for line_number, raw in enumerate(read_text_auto(path).splitlines(), 1):
        left, comma, text = raw.partition(",")
        code, equals, rank_text = left.partition("=")
        if not comma or not equals or not rank_text.isdigit():
            raise ValueError(f"{path}:{line_number}: 非法手心挂接行")
        if len(code) == 3 and code.isascii() and code.islower() and code.isalpha() and len(text) > 1:
            rows.append((code, int(rank_text), text))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attachment", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--filtered-output", type=Path, required=True)
    args = parser.parse_args()

    rows = read_attachment(args.attachment)
    audit = ["简码\t简单鹤候选位\t简单鹤词语\t适配状态\t排除理由"]
    filtered = ["词\t简码\t简单鹤候选位\t来源"]
    excluded = 0
    for code, rank, text in sorted(rows):
        yi_fly = code.startswith("e") and text.startswith("一")
        if yi_fly:
            excluded += 1
        else:
            filtered.append(f"{text}\t{code}\t{rank}\t简单鹤三简")
        audit.append(
            f"{code}\t{rank}\t{text}\t{'排除' if yi_fly else '保留'}\t"
            + ("简单鹤 yi→e 飞键；夜莺不采用飞键，一开头词打全码" if yi_fly else "")
        )

    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text("\n".join(audit) + "\n", encoding="utf-8")
    args.filtered_output.write_text("\n".join(filtered) + "\n", encoding="utf-8")
    print(
        f"rows={len(rows)} codes={len({code for code, _, _ in rows})} "
        f"excluded={excluded} kept={len(rows) - excluded} max_rank={max(rank for _, rank, _ in rows)}"
    )


if __name__ == "__main__":
    main()
