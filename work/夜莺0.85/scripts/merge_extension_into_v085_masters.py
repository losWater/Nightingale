#!/usr/bin/env python3
"""把已审计扩展字写入0.8.5两张主表；运行前隔离备份原表。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_plain(path: Path) -> list[tuple[str, str]]:
    rows = []
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{number}: 非法主表行")
        rows.append((parts[0], parts[1]))
    return rows


def merge(rows: list[tuple[str, str]], extension: list[tuple[str, str]]) -> list[tuple[str, str]]:
    extension_chars = {char for char, _ in extension}
    retained = [(text, code) for text, code in rows if text not in extension_chars]
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for text, code in retained:
        grouped.setdefault(code, []).append(text)
    for char, code in extension:
        grouped.setdefault(code, []).append(char)
    return [(text, code) for code, texts in grouped.items() for text in texts]


def write_plain(path: Path, rows: list[tuple[str, str]]) -> None:
    path.write_bytes(("\n".join(f"{text}\t{code}" for text, code in rows) + "\n").encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()
    for name in ("single", "combined", "extension", "backup_root"):
        setattr(args, name, getattr(args, name).resolve())

    with args.extension.open(encoding="utf-8-sig", newline="") as stream:
        extension = [(row["字"], row["码"]) for row in csv.DictReader(stream, delimiter="\t")]
    if len(extension) != 18770 or len({char for char, _ in extension}) != 18770:
        raise ValueError("扩展表必须恰有18770个不重复字符")
    if any(len(code) != 4 for _, code in extension):
        raise ValueError("扩展表混入非全码")

    stamp = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y%m%d_%H%M%S%z")
    backup = args.backup_root / stamp
    backup.mkdir(parents=True, exist_ok=False)
    before = {"single": sha256(args.single), "combined": sha256(args.combined)}
    shutil.copy2(args.single, backup / args.single.name)
    shutil.copy2(args.combined, backup / args.combined.name)

    single_before = read_plain(args.single)
    combined_before = read_plain(args.combined)
    single_after = merge(single_before, extension)
    combined_after = merge(combined_before, extension)
    write_plain(args.single, single_after)
    write_plain(args.combined, combined_after)

    extension_chars = {char for char, _ in extension}
    for label, rows in (("single", single_after), ("combined", combined_after)):
        actual = [(text, code) for text, code in rows if text in extension_chars]
        if len(actual) != 18770 or set(actual) != set(extension):
            raise ValueError(f"{label}扩展字写入校验失败")
    report = {
        "backup": str(backup),
        "before": before,
        "after": {"single": sha256(args.single), "combined": sha256(args.combined)},
        "counts": {
            "single_before": len(single_before), "single_after": len(single_after),
            "combined_before": len(combined_before), "combined_after": len(combined_after),
            "extension": len(extension),
        },
    }
    (backup / "合并清单.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
