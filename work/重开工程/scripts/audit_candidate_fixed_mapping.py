#!/usr/bin/env python3
"""验证候选只移动允许移动的主根，固定音码及附属关系不得漂移。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = yaml.safe_load(args.baseline.read_text(encoding="utf-8"))
    candidate = yaml.safe_load(args.candidate.read_text(encoding="utf-8"))
    base_mapping = base["form"]["mapping"]
    candidate_mapping = candidate["form"]["mapping"]
    space = base.get("generated_mapping_space")
    if not isinstance(space, dict) or set(space) != set(base_mapping):
        raise ValueError("基础配置决策空间不完整")
    if set(candidate_mapping) != set(base_mapping):
        raise ValueError("候选映射元素集合漂移")
    fixed_drift, out_of_space, phonetic_drift, changed = [], [], [], []
    for element, base_value in base_mapping.items():
        value = candidate_mapping[element]
        allowed = [item["value"] for item in space[element]]
        if not any(canonical(value) == canonical(x) for x in allowed):
            out_of_space.append(element)
        if len(allowed) == 1 and canonical(value) != canonical(base_value):
            fixed_drift.append(element)
        if element.startswith(("szm-", "mzm-")) and canonical(value) != canonical(base_value):
            phonetic_drift.append(element)
        if canonical(value) != canonical(base_value):
            changed.append(element)
    if fixed_drift or out_of_space or phonetic_drift:
        raise ValueError(f"映射漂移：fixed={fixed_drift}, out={out_of_space}, phonetic={phonetic_drift}")
    lines = ["# 候选固定映射与无飞键审计", "",
             f"- 映射元素：{len(base_mapping)}", f"- 允许移动且实际变化的主根：{len(changed)}",
             "- 固定元素漂移：0", "- 音码漂移（飞键）：0", "- 决策空间越界：0", "",
             "变化元素：" + ("、".join(changed) if changed else "无"), ""]
    args.output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
