#!/usr/bin/env python3
"""从最终母配置构建16份可复现、合法且互异的随机主根起点。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--seed-start", type=int, default=800001)
    args = parser.parse_args()
    if args.count <= 0 or args.output_dir.exists():
        raise ValueError("count须为正，且输出目录必须不存在")
    master = yaml.safe_load(args.master.read_text(encoding="utf-8"))
    mapping = master["form"]["mapping"]
    space = master.get("generated_mapping_space")
    if not isinstance(space, dict) or set(space) != set(mapping):
        raise ValueError("母配置决策空间不完整")
    variable = [name for name, choices in space.items() if len(choices) > 1]
    fixed = [name for name, choices in space.items() if len(choices) == 1]
    if not variable or any(not choices for choices in space.values()):
        raise ValueError("决策空间没有可变主根或含空项")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cards, layout_hashes = [], set()
    for offset in range(args.count):
        seed = args.seed_start + offset
        rng = random.Random(seed)
        config = copy.deepcopy(master)
        candidate_mapping = {}
        for element, choices in space.items():
            selected = rng.choice(choices)["value"] if len(choices) > 1 else choices[0]["value"]
            candidate_mapping[element] = copy.deepcopy(selected)
        # 固定音码与所有单选决策必须等于母配置。
        for element in fixed:
            if canonical(candidate_mapping[element]) != canonical(mapping[element]):
                raise AssertionError(f"固定元素漂移：{element}")
        for element in mapping:
            if element.startswith(("szm-", "mzm-")) and canonical(candidate_mapping[element]) != canonical(mapping[element]):
                raise AssertionError(f"音码飞键：{element}")
        layout_hash = hashlib.sha256(canonical(candidate_mapping).encode("utf-8")).hexdigest()
        if layout_hash in layout_hashes:
            raise ValueError(f"随机起点重复：seed={seed}")
        layout_hashes.add(layout_hash)
        config["form"]["mapping"] = candidate_mapping
        card_dir = args.output_dir / f"card_{offset + 1:02d}_seed_{seed}"
        card_dir.mkdir()
        config_path = card_dir / "config.yaml"
        config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
        cards.append({"card": offset + 1, "seed": seed, "directory": str(card_dir.resolve()),
                      "config_sha256": sha256(config_path), "layout_sha256": layout_hash,
                      "status": "pending"})
    manifest = {"schema_version": 1, "design": "0048", "status": "built_pending_validation_and_run",
                "master": str(args.master.resolve()), "master_sha256": sha256(args.master),
                "elements": str(args.elements.resolve()), "elements_sha256": sha256(args.elements),
                "count": args.count, "variable_elements": len(variable), "fixed_elements": len(fixed),
                "unique_layouts": len(layout_hashes), "cards": cards}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

