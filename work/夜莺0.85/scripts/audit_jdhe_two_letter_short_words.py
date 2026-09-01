#!/usr/bin/env python3
"""提取简单鹤全部二码简词，并审计夜莺快符与临时简词冲突。"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def read_attachment(path: Path) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for line_number, raw in enumerate(read_text_auto(path).splitlines(), 1):
        left, separator, text = raw.partition(",")
        code, equals, rank_text = left.partition("=")
        if not separator or not equals or not rank_text.isdigit():
            raise ValueError(f"{path}:{line_number}: 非法手心挂接行")
        if len(code) == 2 and code.isascii() and code.islower() and code.isalpha() and len(text) > 1:
            rows.append((code, int(rank_text), text))
    return rows


def read_quick(path: Path) -> dict[tuple[str, int], str]:
    output: dict[tuple[str, int], str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        left, separator, text = raw.partition("=")
        code, comma, rank_text = left.rpartition(",")
        if not separator or not comma or not rank_text.isdigit():
            raise ValueError(f"{path}:{line_number}: 非法快符行")
        output[(code, int(rank_text))] = text
    return output


def read_nightingale(path: Path) -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for line_number, raw in enumerate(lines[1:], 2):
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            raise ValueError(f"{path}:{line_number}: 非法夜莺简词行")
        text, code = parts[:2]
        if len(code) == 2:
            output[code].append(text)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attachment", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--nightingale", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--filtered-output", type=Path)
    args = parser.parse_args()

    rows = read_attachment(args.attachment)
    quick = read_quick(args.quick)
    nightingale = read_nightingale(args.nightingale)
    output = ["简码\t简单鹤候选位\t简单鹤词语\t适配状态\t排除理由\t同位快符\t夜莺临时同码词\t冲突类型"]
    filtered = ["词\t简码\t简单鹤候选位\t来源"]
    excluded_count = 0
    quick_conflicts = 0
    nightingale_conflicts = 0
    for code, rank, text in sorted(rows):
        excluded = code.startswith("e") and text.startswith("一")
        exclusion_reason = "简单鹤 yi→e 飞键；夜莺不采用飞键，一开头词打全码" if excluded else ""
        if excluded:
            excluded_count += 1
        else:
            filtered.append(f"{text}\t{code}\t{rank}\t简单鹤二简")
        quick_text = quick.get((code, rank), "")
        nightingale_texts = nightingale.get(code, [])
        different = [item for item in nightingale_texts if item != text]
        conflicts: list[str] = []
        if quick_text and not excluded:
            conflicts.append("快符同位")
            quick_conflicts += 1
        if different and not excluded:
            conflicts.append("夜莺同码异词")
            nightingale_conflicts += 1
        output.append(
            "\t".join(
                (
                    code,
                    str(rank),
                    text,
                    "排除" if excluded else "保留",
                    exclusion_reason,
                    quick_text,
                    " ".join(nightingale_texts),
                    "、".join(conflicts),
                )
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    if args.filtered_output:
        args.filtered_output.parent.mkdir(parents=True, exist_ok=True)
        args.filtered_output.write_text("\n".join(filtered) + "\n", encoding="utf-8")
    print(
        f"rows={len(rows)} codes={len({code for code, _, _ in rows})} "
        f"excluded={excluded_count} kept={len(rows) - excluded_count} "
        f"quick_conflicts={quick_conflicts} nightingale_conflict_rows={nightingale_conflicts}"
    )


if __name__ == "__main__":
    main()
