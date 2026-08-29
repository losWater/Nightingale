# -*- coding: utf-8 -*-
"""Freeze the approved 1/2/3-code ownership from an encoded code table."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    entries: list[tuple[str, str, int, str]] = []
    occurrences: dict[tuple[str, str], int] = {}
    for line in args.code.read_text(encoding="utf-8").splitlines():
        row = line.split("\t")
        if len(row) < 4:
            continue
        char, full, short = row[0], row[1], row[3]
        key = (char, full)
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        entries.append((char, full, occurrence, short))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "字\t全码\t同项序号\t核定简码\n"
        + "".join(
            f"{char}\t{full}\t{occurrence}\t{short}\n"
            for char, full, occurrence, short in entries
        ),
        encoding="utf-8",
    )
    short_count = sum(len(short) < len(full) for char, full, occurrence, short in entries)
    print(f"frozen_rows={len(entries)} frozen_short_codes={short_count} output={args.output}")


if __name__ == "__main__":
    main()
