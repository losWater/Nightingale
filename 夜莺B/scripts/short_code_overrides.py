# -*- coding: utf-8 -*-
"""应用人工三码所有权（“谕旨”），避免重建码表时被频率排序覆盖。"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
SHORT_BASELINE = BASE / "work/简码所有权基线.tsv"


def apply_short_code_baseline(
    rows: list[list[str]], baseline_path: Path | None = None
) -> set[int]:
    """Restore approved short-code ownership before applying newer decrees."""
    path = baseline_path or SHORT_BASELINE
    if not path.exists():
        return set()

    approved: dict[tuple[str, str, int], str] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) >= 4:
            approved[(fields[0], fields[1], int(fields[2]))] = fields[3]

    current_counts = Counter((row[0], row[1]) for row in rows)
    baseline_counts = Counter((char, full) for char, full, occurrence in approved)
    if current_counts != baseline_counts:
        missing = list((baseline_counts - current_counts).elements())[:8]
        added = list((current_counts - baseline_counts).elements())[:8]
        raise ValueError(
            "字音全码集合偏离简码基线；必须先人工复审并更新基线。"
            f" missing={missing} added={added}"
        )

    # The encoder may recalculate ownership nondeterministically or from a rebuilt
    # frequency asset. Clear that derived state and restore the approved snapshot.
    for row in rows:
        row[3] = row[1]
        if len(row) > 4:
            row[4] = row[2] if len(row) > 2 else "0"

    restored: set[int] = set()
    occurrences: dict[tuple[str, str], int] = {}
    for i, row in enumerate(rows):
        key = (row[0], row[1])
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        short = approved.get((row[0], row[1], occurrence))
        if short is None:
            continue
        row[3] = short
        if len(row) > 4:
            row[4] = "0" if len(short) < len(row[1]) else (row[2] if len(row) > 2 else "0")
        if len(short) < len(row[1]):
            restored.add(i)
    return restored


def load_winners(rules_path: Path | None = None) -> dict[str, set[str]]:
    path = rules_path or BASE / "work/拆分规则.yaml"
    rules = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result: dict[str, set[str]] = {}
    for sound, groups in (rules.get("short_code_overrides") or {}).items():
        result[str(sound)] = {str(char) for char in (groups or {}).values()}
    return result


def load_two_code_winners(rules_path: Path | None = None) -> dict[str, str]:
    path = rules_path or BASE / "work/拆分规则.yaml"
    rules = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(sound): str(char)
        for sound, char in (rules.get("two_code_overrides") or {}).items()
    }


def apply_two_code_overrides(
    rows: list[list[str]], rules_path: Path | None = None
) -> set[int]:
    """Apply manual two-code ownership before allocating manual three-code slots."""
    manual_winners: set[int] = set()
    for sound, winner in load_two_code_winners(rules_path).items():
        matches = [
            i for i, row in enumerate(rows)
            if row[0] == winner and row[1].startswith(sound)
        ]
        if len(matches) != 1:
            raise ValueError(f"二简赢家定位失败：{sound}/{winner} 命中 {len(matches)} 行")
        chosen = matches[0]
        if len(rows[chosen][1]) < 2:
            raise ValueError(f"二简赢家编码不足两码：{winner} {rows[chosen][1]}")
        # 原二简赢家先退回全码；稍后的三码谕旨仍可接着给它安排三码。
        for i, row in enumerate(rows):
            if i != chosen and row[3] == sound:
                row[3] = row[1]
                if len(row) > 4:
                    row[4] = row[2] if len(row) > 2 else "0"
        rows[chosen][3] = sound
        if len(rows[chosen]) > 4:
            rows[chosen][4] = "0"
        manual_winners.add(chosen)
    return manual_winners


def apply_candidate_order(
    entries: list[tuple], rules_path: Path | None = None
) -> list[tuple]:
    """对同码候选应用人工先后谕旨；元组第0项为码、第4项为字。"""
    path = rules_path or BASE / "work/拆分规则.yaml"
    rules = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    overrides = rules.get("candidate_order_overrides") or {}
    grouped: dict[str, list[tuple]] = {}
    code_order: list[str] = []
    for entry in entries:
        code = str(entry[0])
        if code not in grouped:
            grouped[code] = []
            code_order.append(code)
        grouped[code].append(entry)
    result: list[tuple] = []
    for code in code_order:
        rows = grouped[code]
        wanted = [str(x) for x in overrides.get(code, [])]
        priority = {char: index for index, char in enumerate(wanted)}
        original = {id(entry): index for index, entry in enumerate(rows)}
        rows.sort(key=lambda entry: (
            priority.get(str(entry[4]), len(priority)), original[id(entry)]
        ))
        result.extend(rows)
    return result


def apply_overrides(
    rows: list[list[str]], rules_path: Path | None = None
) -> set[int]:
    """原地调整 code.txt 行，返回被谕旨指定为三码的行号集合。"""
    # 顺序很重要：冻结基线，再由新谕旨有意识地覆盖旧所有权。
    apply_short_code_baseline(rows)
    manual_winners: set[int] = apply_two_code_overrides(rows, rules_path)
    for sound, winners in load_winners(rules_path).items():
        for winner in winners:
            matches = [
                i for i, row in enumerate(rows)
                if row[0] == winner and row[1].startswith(sound)
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"人工三码赢家定位失败：{sound}/{winner} 命中 {len(matches)} 行"
                )
            chosen = matches[0]
            full = rows[chosen][1]
            prefix = full[:3]
            if len(full) != 4:
                raise ValueError(f"人工三码赢家不是四码字：{winner} {full}")
            # 同一码位原赢家退回完整码；一、二简资产不应进入该分支。
            for i, row in enumerate(rows):
                if i != chosen and row[3] == prefix:
                    if len(row[3]) < 3:
                        raise ValueError(f"人工三码覆盖了一／二简：{row[0]} {row[3]}")
                    row[3] = row[1]
                    if len(row) > 4:
                        row[4] = row[2] if len(row) > 2 else "0"
            rows[chosen][3] = prefix
            if len(rows[chosen]) > 4:
                rows[chosen][4] = "0"
            manual_winners.add(chosen)
    return manual_winners


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", type=Path)
    ap.add_argument("--rules", type=Path, default=BASE / "work/拆分规则.yaml")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = [line.split("\t") for line in args.code.read_text(encoding="utf-8").splitlines()]
    winners = apply_overrides(rows, args.rules)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join("\t".join(row) for row in rows) + "\n", encoding="utf-8"
    )
    print(f"manual_three_winners={len(winners)} output={args.output}")


if __name__ == "__main__":
    main()
