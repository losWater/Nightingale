#!/usr/bin/env python3
"""从基础 readings 资产和别名规则纯函数式生成新资产。"""
from __future__ import annotations
import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
import yaml
from reading_frequencies import normalize_reading_order, validate_readings


def apply_rules(readings: Any, rules: dict[str, Any]) -> dict[str, list[list[Any]]]:
    result = deepcopy(validate_readings(readings))
    for char, aliases in rules.get("reading_aliases", {}).items():
        if char not in result:
            raise KeyError(f"读音别名字不在基础资产: {char}")
        suffixes = {code[2:] for _, code in result[char]}
        existing = {code[:2] for _, code in result[char]}
        for alias in aliases:
            if "frequency" not in alias:
                raise ValueError(f"读音别名必须显式提供frequency: {char}={alias}")
            code = str(alias.get("code", ""))
            if len(code) != 2:
                raise ValueError(f"音码必须恰为两键: {char}={code!r}")
            if code in existing:
                continue
            explicit_suffix = alias.get("suffix")
            if explicit_suffix is None:
                if len(suffixes) != 1:
                    raise ValueError(f"{char}有多个形码后缀，别名{code}必须显式指定suffix")
                suffix = next(iter(suffixes))
            else:
                suffix = str(explicit_suffix)
            frequency = alias["frequency"]
            if not isinstance(frequency, int) or frequency < 0:
                raise ValueError(f"别名频率必须是非负整数: {char}={frequency!r}")
            result[char].append([frequency, code + suffix])
            existing.add(code)
    for char, overrides in rules.get("reading_frequency_overrides", {}).items():
        if char not in result:
            raise KeyError(f"读音频率覆写字不在基础资产: {char}")
        found = set()
        for reading in result[char]:
            code = reading[1][:2]
            if code in overrides:
                frequency = overrides[code]
                if not isinstance(frequency, int) or frequency < 0:
                    raise ValueError(f"频率覆写必须是非负整数: {char}/{code}={frequency!r}")
                reading[0] = frequency
                found.add(code)
        missing = set(overrides) - found
        if missing:
            raise KeyError(f"读音频率覆写入口不存在: {char}={sorted(missing)}")
    return normalize_reading_order(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError("禁止原地改写readings；output必须与input不同")
    readings = json.loads(args.input.read_text(encoding="utf-8"))
    rules = yaml.safe_load(args.rules.read_text(encoding="utf-8"))
    if not isinstance(rules, dict):
        raise ValueError("rules必须是映射")
    result = apply_rules(readings, rules)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"生成 {len(result)} 字: {args.output}")


if __name__ == "__main__":
    main()
