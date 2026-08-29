# -*- coding: utf-8 -*-
"""独立复算并反向核对最终 code.txt 的一／二／三码所有权。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CodeRow:
    index: int
    word: str
    full: str
    full_rank: int
    short: str
    short_rank: int


def load_code(path: Path) -> list[CodeRow]:
    rows: list[CodeRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) < 5:
            raise ValueError(f"code.txt 第{line_no}行不足5列")
        try:
            rows.append(CodeRow(len(rows), fields[0], fields[1], int(fields[2]),
                                fields[3], int(fields[4])))
        except ValueError as exc:
            raise ValueError(f"code.txt 第{line_no}行候选序号不是整数") from exc
    return rows


def short_schemes(config: dict) -> list[tuple[int, int, set[str]]]:
    encoder = config["encoder"]
    global_keys = list(encoder.get("select_keys") or [])
    encoder_schemes = encoder.get("short_code_schemes")
    form_schemes = config.get("form", {}).get("short_code_schemes")
    if encoder_schemes is not None and form_schemes is not None and encoder_schemes != form_schemes:
        raise ValueError("encoder与form的short_code_schemes冲突")
    schemes = encoder_schemes if encoder_schemes is not None else form_schemes
    configured_rules = encoder.get("short_code")
    if configured_rules is not None:
        one_char_schemes = []
        for rule in configured_rules:
            applies = rule.get("length_equal") == 1
            if "length_in_range" in rule:
                lower, upper = rule["length_in_range"]
                applies = int(lower) <= 1 <= int(upper)
            if applies:
                one_char_schemes.extend(rule.get("schemes") or [])
        if schemes is not None and schemes != one_char_schemes:
            raise ValueError("short_code与short_code_schemes的单字规则冲突")
        schemes = one_char_schemes
    result = []
    for scheme in schemes or []:
        prefix = int(scheme["prefix"])
        keys = list(scheme.get("select_keys") or global_keys)
        # libchai的简码模式缺省只开放一个候选，不等于全局选择键总数。
        count = int(scheme.get("count", 1))
        if prefix < 1 or count < 1 or not keys:
            raise ValueError(f"非法简码方案：{scheme}")
        result.append((prefix, count, set(keys)))
    return result


def expected_slots(elements: list[dict], rows: list[CodeRow], config: dict) -> list[str]:
    """按libchai的分配顺序，独立推导每一资产行的逻辑简码位。"""
    if len(elements) != len(rows):
        raise ValueError(f"elements/code行数不一致：{len(elements)} != {len(rows)}")
    for index, (item, row) in enumerate(zip(elements, rows)):
        if str(item["词"]) != row.word:
            raise ValueError(f"elements/code第{index + 1}行错位：{item['词']} != {row.word}")

    schemes = short_schemes(config)
    full_space = Counter(row.full for row in rows)
    short_space: Counter[str] = Counter()
    expected = [row.full for row in rows]
    if any(item.get("排序序号") is not None for item in elements):
        order = sorted(range(len(elements)), key=lambda i: (
            int(elements[i]["排序序号"])
            if elements[i].get("排序序号") is not None else 2**63 - 1,
            i,
        ))
    else:
        order = sorted(range(len(elements)), key=lambda i: (-int(elements[i].get("频率", 0)), i))

    for index in order:
        item, row = elements[index], rows[index]
        if "简码长度" not in item:
            continue
        level = int(item["简码长度"])
        if level < 1 or level > len(row.full):
            raise ValueError(f"第{index + 1}行简码长度越界：{row.word}/{level}/{row.full}")
        slot = row.full[:level]
        expected[index] = slot
        short_space[slot] += 1

    for index in order:
        item, row = elements[index], rows[index]
        if "简码长度" in item:
            continue
        for prefix, capacity, _ in schemes:
            # 与libchai的“原始编码 < radix**prefix则跳过”等价：
            # 自然三码占全码空间，但不会再登记成一次三码简码。
            if len(row.full) <= prefix:
                continue
            slot = row.full[:prefix]
            if full_space[slot] + short_space[slot] >= capacity:
                continue
            expected[index] = slot
            short_space[slot] += 1
            break
    return expected


def actual_matches_slot(row: CodeRow, slot: str, select_keys: set[str]) -> bool:
    if slot == row.full:
        return row.short == row.full
    return row.short == slot or (
        len(row.short) == len(slot) + 1
        and row.short.startswith(slot)
        and row.short[-1] in select_keys
    )


def audit(elements: list[dict], rows: list[CodeRow], config: dict) -> dict:
    expected = expected_slots(elements, rows, config)
    all_select_keys = set(config["encoder"].get("select_keys") or [])
    mismatches = []
    for row, slot in zip(rows, expected):
        if not actual_matches_slot(row, slot, all_select_keys):
            mismatches.append({
                "index": row.index, "word": row.word, "full": row.full,
                "expected": slot, "actual": row.short,
            })

    expected_reverse: dict[str, list[int]] = defaultdict(list)
    for index, slot in enumerate(expected):
        if slot != rows[index].full:
            expected_reverse[slot].append(index)
    return {"expected": expected, "reverse": dict(expected_reverse), "mismatches": mismatches}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", type=Path)
    ap.add_argument("--elements", type=Path, default=BASE / "work/analysis_elements.yaml")
    ap.add_argument("--config", type=Path, default=BASE / "work/analysis_config.yaml")
    ap.add_argument("--out", type=Path, default=BASE / "work/v07_unlocked_audit/最终简码逐项核对.md")
    args = ap.parse_args()

    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    rows = load_code(args.code)
    result = audit(elements, rows, config)
    expected = result["expected"]
    mismatches = result["mismatches"]
    counts = Counter(len(slot) for slot in expected)
    report = [
        "# 最终简码所有权双向核对", "",
        f"- 资产行：{len(rows)}（同字多码不合并）",
        f"- 反向码位：{len(result['reverse'])}",
        f"- 独立复算分布：一简 {counts[1]}、二简 {counts[2]}、三码 {counts[3]}、全码 {counts[4]}",
        f"- 所有权不符：{len(mismatches)}", "", "## 不符明细", "",
    ]
    report += ([
        f"- 行 {x['index'] + 1} {x['word']}：全码 `{x['full']}`，应属 `{x['expected']}`，实为 `{x['actual']}`"
        for x in mismatches
    ] or ["- 无"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:7]))
    print(args.out)
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
