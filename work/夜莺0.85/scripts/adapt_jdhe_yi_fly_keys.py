#!/usr/bin/env python3
"""严格按字码位置把简单鹤简词中的“一/e”飞键适配为“一/y”。"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attachment", type=Path, required=True)
    parser.add_argument("--code-length", type=int, required=True)
    parser.add_argument("--min-text-length", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--collision-audit", type=Path, required=True)
    parser.add_argument("--ambiguous-audit", type=Path, required=True)
    args = parser.parse_args()

    raw_adapted: list[tuple[str, int, str, str, tuple[int, ...]]] = []
    ambiguous: list[tuple[str, int, str, str]] = []
    for line_number, raw in enumerate(read_text_auto(args.attachment).splitlines(), 1):
        left, comma, text = raw.partition(",")
        code, equals, rank_text = left.partition("=")
        if not comma or not equals or not rank_text.isdigit():
            raise ValueError(f"{args.attachment}:{line_number}: 非法手心挂接行")
        if (
            len(code) != args.code_length
            or not code.isascii()
            or not code.islower()
            or not code.isalpha()
            or len(text) < args.min_text_length
        ):
            continue
        positions: tuple[int, ...] = ()
        new_code = code
        if len(text) == len(code):
            positions = tuple(index for index, (character, key) in enumerate(zip(text, code)) if character == "一" and key == "e")
            if positions:
                keys = list(code)
                for index in positions:
                    keys[index] = "y"
                new_code = "".join(keys)
        elif "一" in text and "e" in code:
            ambiguous.append((code, int(rank_text), text, "词长与简码长不等，无法可靠逐位对应；不转换"))
        raw_adapted.append((new_code, int(rank_text), text, code, positions))

    by_word_code: dict[tuple[str, str], list[tuple[str, int, str, str, tuple[int, ...]]]] = defaultdict(list)
    for row in raw_adapted:
        by_word_code[(row[0], row[2])].append(row)
    adapted: list[tuple[str, int, str, str, tuple[int, ...]]] = []
    deduplicated = 0
    for variants in by_word_code.values():
        # 正常y码优先于e→y副本；其后按原候选位择优。
        chosen = min(variants, key=lambda row: (bool(row[4]), row[1], row[3]))
        adapted.append(chosen)
        deduplicated += len(variants) - 1

    slots: dict[tuple[str, int], list[tuple[str, str]]] = defaultdict(list)
    for code, rank, text, source_code, _positions in adapted:
        slots[(code, rank)].append((text, source_code))
    collisions = {slot: values for slot, values in slots.items() if len({text for text, _ in values}) > 1}

    output = ["词\t简码\t简单鹤候选位\t来源"]
    audit = ["词\t原简码\t夜莺简码\t候选位\t转换位置\t处理"]
    for code, rank, text, source_code, positions in sorted(adapted):
        converted_positions = " ".join(str(index + 1) for index in positions)
        output.append(f"{text}\t{code}\t{rank}\t简单鹤{args.code_length}简")
        audit.append(
            f"{text}\t{source_code}\t{code}\t{rank}\t{converted_positions}\t"
            + ("对应位置 e→y" if positions else "保留")
        )
    collision_lines = ["夜莺简码\t候选位\t碰撞词与原码"]
    for (code, rank), values in sorted(collisions.items()):
        rendered = " / ".join(f"{text}({source_code})" for text, source_code in values)
        collision_lines.append(f"{code}\t{rank}\t{rendered}")
    ambiguous_lines = ["简码\t候选位\t词语\t处理"] + [
        f"{code}\t{rank}\t{text}\t{reason}" for code, rank, text, reason in sorted(ambiguous)
    ]

    for path, lines in (
        (args.output, output),
        (args.audit, audit),
        (args.collision_audit, collision_lines),
        (args.ambiguous_audit, ambiguous_lines),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"rows={len(adapted)} converted={sum(bool(row[4]) for row in adapted)} "
        f"converted_positions={sum(len(row[4]) for row in adapted)} "
        f"deduplicated={deduplicated} collision_slots={len(collisions)} ambiguous={len(ambiguous)}"
    )


if __name__ == "__main__":
    main()
