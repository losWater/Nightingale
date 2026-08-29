#!/usr/bin/env python3
"""独立复算 libchai 的字词交叉碰撞指标。

输入必须是同一次运行的 config.yaml、code.txt，以及与 code.txt 原始行顺序
完全一致的 elements YAML。本脚本不复用 Rust 目标函数实现，以便独立验算。
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CodeRow:
    word: str
    full: str
    full_rank: int
    short: str
    short_rank: int


@dataclass(frozen=True)
class Hit:
    internal_index: int
    original_index: int
    word: str
    code: str
    short: str
    short_rank: int
    factor: float
    soft_weight: float
    hard_top: int
    is_hard: bool


def require_mapping(parent: dict[str, Any], key: str, where: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{where}.{key} 必须是映射")
    return value


def load_code(path: Path) -> list[CodeRow]:
    rows: list[CodeRow] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 5:
            raise ValueError(f"{path}:{line_number} 应有5列，实际{len(fields)}列")
        try:
            full_rank = int(fields[2])
            short_rank = int(fields[4])
        except ValueError as error:
            raise ValueError(f"{path}:{line_number} 候选位必须是整数") from error
        rows.append(CodeRow(fields[0], fields[1], full_rank, fields[3], short_rank))
    return rows


def internal_order(elements: list[dict[str, Any]]) -> list[int]:
    has_explicit = any(item.get("排序序号") is not None for item in elements)
    if has_explicit:
        missing = [i + 1 for i, item in enumerate(elements) if item.get("排序序号") is None]
        if missing:
            preview = ", ".join(map(str, missing[:8]))
            raise ValueError(f"启用排序序号后必须全量标注；缺失行: {preview}")
        try:
            return sorted(range(len(elements)), key=lambda i: (int(elements[i]["排序序号"]), i))
        except (TypeError, ValueError) as error:
            raise ValueError("排序序号必须是整数") from error
    try:
        return sorted(range(len(elements)), key=lambda i: (-int(elements[i]["频率"]), i))
    except KeyError as error:
        raise ValueError("未启用排序序号时，每个对象必须显式提供频率") from error
    except (TypeError, ValueError) as error:
        raise ValueError("频率必须是整数") from error


def is_auto_select(code: str, encoder: dict[str, Any]) -> bool:
    max_length = encoder.get("max_length")
    if not isinstance(max_length, int):
        raise ValueError("encoder.max_length 必须是整数")
    if len(code) == max_length:
        return True
    if "auto_select_pattern" in encoder and encoder["auto_select_pattern"] is not None:
        pattern = encoder["auto_select_pattern"]
        if not isinstance(pattern, str):
            raise ValueError("encoder.auto_select_pattern 必须是字符串或null")
        try:
            return re.search(pattern, code) is not None
        except re.error as error:
            raise ValueError(f"auto_select_pattern 无法解析: {pattern!r}") from error
    if "auto_select_length" in encoder and encoder["auto_select_length"] is not None:
        length = encoder["auto_select_length"]
        if not isinstance(length, int):
            raise ValueError("encoder.auto_select_length 必须是整数或null")
        return len(code) >= length
    return True


def actual_code(raw: str, rank: int, encoder: dict[str, Any]) -> str:
    select_keys = encoder.get("select_keys")
    if not isinstance(select_keys, list) or not select_keys or not all(
        isinstance(key, str) and len(key) == 1 for key in select_keys
    ):
        raise ValueError("encoder.select_keys 必须是非空的单字符列表")
    if rank < 0:
        raise ValueError("候选位不能为负数")
    if rank == 0 and is_auto_select(raw, encoder):
        return raw
    key = select_keys[rank] if rank < len(select_keys) else select_keys[0]
    return raw + key


def validate_character_prefix(elements: list[dict[str, Any]], order: list[int]) -> int:
    flags = [len(str(elements[i].get("词", ""))) == 1 for i in order]
    count = 0
    while count < len(flags) and flags[count]:
        count += 1
    if any(flags[count:]):
        raise ValueError("内部排序后单字必须连续位于所有多字词之前")
    return count


def effective_short_code(
    row: CodeRow, item: dict[str, Any], full_actual: str, encoder: dict[str, Any]
) -> str:
    # 常规简码没有找到可用位置时，Rust 会把简码信息回退为全码：code.txt
    # 仍记录简码空间中的候选序号，但实际编码直接复制 full.实际编码。
    # 显式“简码长度”走优先简码分支，即使原始长度等于全码也必须按候选位生成。
    if item.get("简码长度") is None and row.short == row.full:
        return full_actual
    return actual_code(row.short, row.short_rank, encoder)


def audit(config: dict[str, Any], elements: list[dict[str, Any]], rows: list[CodeRow]) -> dict[str, Any]:
    if len(elements) != len(rows):
        raise ValueError(f"元素表{len(elements)}行，码表{len(rows)}行，无法对齐")
    for index, (item, row) in enumerate(zip(elements, rows), 1):
        if str(item.get("词", "")) != row.word:
            raise ValueError(f"第{index}行词不一致: elements={item.get('词')!r}, code={row.word!r}")

    encoder = require_mapping(config, "encoder", "config")
    optimization = require_mapping(config, "optimization", "config")
    objective = require_mapping(optimization, "objective", "config.optimization")
    cross = require_mapping(objective, "character_word_collision", "config.optimization.objective")
    targets = require_mapping(cross, "targets", "character_word_collision")

    global_hard_top = cross.get("hard_character_top")
    if not isinstance(global_hard_top, int) or global_hard_top < 0:
        raise ValueError("character_word_collision.hard_character_top 必须是非负整数")
    tiers = cross.get("character_tiers")
    if not isinstance(tiers, list):
        raise ValueError("character_word_collision.character_tiers 必须是列表")
    previous_top = -1
    for tier in tiers:
        if not isinstance(tier, dict) or not isinstance(tier.get("top"), int):
            raise ValueError("每个character_tier必须含整数top")
        if tier["top"] <= previous_top:
            raise ValueError("character_tiers必须按top严格升序")
        if not isinstance(tier.get("factor"), (int, float)):
            raise ValueError("每个character_tier必须含数值factor")
        previous_top = tier["top"]

    order = internal_order(elements)
    character_count = validate_character_prefix(elements, order)
    factors = [0.0] * character_count
    for index in range(character_count):
        for tier in tiers:
            if index < tier["top"]:
                factors[index] = float(tier["factor"])
                break

    hits: list[Hit] = []
    soft_total = 0.0
    hard_total = 0
    for internal_index, original_index in enumerate(order[:character_count]):
        row = rows[original_index]
        # Rust全码目标强制按首选生成；简码保留自身候选位。
        full_actual = actual_code(row.full, 0, encoder)
        short_actual = effective_short_code(row, elements[original_index], full_actual, encoder)
        if short_actual != full_actual:
            continue
        target = targets.get(full_actual)
        if target is None:
            continue
        if not isinstance(target, dict):
            raise ValueError(f"target {full_actual!r} 必须是映射")
        soft = target.get("soft")
        hard = target.get("hard")
        if not isinstance(soft, (int, float)) or not isinstance(hard, bool):
            raise ValueError(f"target {full_actual!r} 必须显式包含数值soft和布尔hard")
        override = target.get("hard_character_top")
        if override is not None and (not isinstance(override, int) or override < 0):
            raise ValueError(f"target {full_actual!r} 的hard_character_top必须是非负整数或null")
        hard_top = override if override is not None else (global_hard_top if hard else 0)
        factor = factors[internal_index]
        soft_total += factor * float(soft)
        is_hard = internal_index < hard_top
        if is_hard:
            hard_total += 1
        hits.append(
            Hit(
                internal_index=internal_index,
                original_index=original_index,
                word=row.word,
                code=full_actual,
                short=row.short,
                short_rank=row.short_rank,
                factor=factor,
                soft_weight=float(soft),
                hard_top=hard_top,
                is_hard=is_hard,
            )
        )

    return {
        "rows": len(rows),
        "characters": character_count,
        "hard": hard_total,
        "soft": soft_total,
        "hits": [asdict(hit) for hit in hits],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, help="chai的output-*目录，必须含code.txt")
    parser.add_argument(
        "--config",
        type=Path,
        help="本次运行使用的config.yaml；默认取output目录内的config.yaml",
    )
    parser.add_argument("--elements", type=Path, required=True, help="与code.txt原始顺序一致的elements YAML")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    config_path = args.config if args.config is not None else args.output / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(elements, list):
        raise ValueError("config必须是映射，elements必须是列表")
    result = audit(config, elements, load_code(args.output / "code.txt"))

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"码表行数: {result['rows']}")
    print(f"单字行数: {result['characters']}")
    print(f"独立硬碰撞: {result['hard']}")
    print(f"独立软碰撞: {result['soft']:.12g}")
    for hit in result["hits"]:
        label = "硬" if hit["is_hard"] else "软"
        print(
            f"{label}\t内部#{hit['internal_index'] + 1}\t原表#{hit['original_index'] + 1}"
            f"\t{hit['word']}\t{hit['code']}\tshort={hit['short']}#{hit['short_rank'] + 1}"
            f"\tfactor={hit['factor']:.6g}\tsoft={hit['soft_weight']:.6g}\ttop={hit['hard_top']}"
        )


if __name__ == "__main__":
    main()
