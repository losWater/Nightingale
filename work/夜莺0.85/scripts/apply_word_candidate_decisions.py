#!/usr/bin/env python3
"""Apply complete-slot F decisions to an accepted E table and produce G."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_slots(path: Path) -> OrderedDict[str, list[str]]:
    slots: OrderedDict[str, list[str]] = OrderedDict()
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                raise SystemExit(f"invalid E row {line_number}: {line!r}")
            content, code = parts
            slots.setdefault(code, []).append(content)
    return slots


def read_decisions(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"裁决编号", "码", "调整前关键候选", "调整后关键候选", "理由", "状态"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit("invalid F decision schema")
    return rows


def split_candidates(raw: str) -> list[str]:
    return [item for item in raw.split("、") if item]


def read_sogou_char_entries(path: Path) -> list[tuple[str, int, str]]:
    result = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.rstrip("\r\n")
            if not line:
                continue
            left, separator, content = line.partition("=")
            code, comma, index = left.rpartition(",")
            if not separator or not comma or not index.isdigit():
                raise SystemExit(f"invalid Sogou row {line_number}: {line!r}")
            result.append((code, int(index), content))
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-name", required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"output directory already exists: {args.output}")

    slots = read_slots(args.base)
    original = OrderedDict((code, list(items)) for code, items in slots.items())
    decisions = read_decisions(args.decisions)
    ids = [row["裁决编号"] for row in decisions]
    codes = [row["码"] for row in decisions]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate decision id")
    if len(codes) != len(set(codes)):
        raise SystemExit("duplicate decision code")

    changes = []
    changed = 0
    already_satisfied = 0
    mismatches = []
    for row in decisions:
        code = row["码"]
        before = split_candidates(row["调整前关键候选"])
        after = split_candidates(row["调整后关键候选"])
        current = slots.get(code, [])
        if current == before:
            slots[code] = list(after)
            action = "changed" if before != after else "unchanged_decision"
            if before != after:
                changed += 1
            else:
                already_satisfied += 1
        elif current == after:
            action = "already_satisfied"
            already_satisfied += 1
        else:
            mismatches.append({"decision": row["裁决编号"], "code": code, "current": current, "before": before, "after": after})
            continue
        changes.append(
            {
                "decision": row["裁决编号"],
                "code": code,
                "action": action,
                "before": current,
                "after": slots[code],
            }
        )

    if mismatches:
        print(json.dumps({"status": "interface_mismatch", "count": len(mismatches), "items": mismatches}, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    declared = set(codes)
    for code, items in original.items():
        if code not in declared and slots[code] != items:
            raise SystemExit(f"undeclared slot changed: {code}")

    args.output.mkdir(parents=True)
    normal = args.output / f"{args.release_name}.txt"
    sogou = args.output / f"{args.release_name}_搜狗词库版.txt"
    report = args.output / "F裁决验证报告.json"

    with normal.open("w", encoding="utf-8", newline="") as handle:
        for code, items in slots.items():
            for item in items:
                handle.write(f"{item}\t{code}\n")
    with sogou.open("w", encoding="utf-8", newline="") as handle:
        for code, items in slots.items():
            for index, item in enumerate(items, 1):
                if len(item) == 1:
                    handle.write(f"{code},{index}={item}\n")

    if read_slots(normal) != slots:
        raise SystemExit("normal output round-trip mismatch")
    expected_sogou = [
        (code, index, item)
        for code, items in slots.items()
        for index, item in enumerate(items, 1)
        if len(item) == 1
    ]
    if read_sogou_char_entries(sogou) != expected_sogou:
        raise SystemExit("Sogou char-only absolute-position round-trip mismatch")

    report_data = {
        "schema_version": 1,
        "status": "pass",
        "inputs": {str(args.base.resolve()): sha256(args.base), str(args.decisions.resolve()): sha256(args.decisions)},
        "base_slots": len(original),
        "base_entries": sum(map(len, original.values())),
        "result_slots": len(slots),
        "result_entries": sum(map(len, slots.values())),
        "decision_slots": len(decisions),
        "changed_slots": changed,
        "already_satisfied_or_unchanged": already_satisfied,
        "undeclared_slots_unchanged": True,
        "sogou_rule": "仅单字；保留综合表绝对候选序号；词位留空不压缩",
        "changes": changes,
        "outputs": {normal.name: sha256(normal), sogou.name: sha256(sogou)},
    }
    report.write_text(json.dumps(report_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report_data.items() if key != "changes"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
