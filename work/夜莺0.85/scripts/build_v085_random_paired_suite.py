#!/usr/bin/env python3
"""构建夜莺0.85随机开局、关闭/开启字词交叉目标的配对卡池。"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import random
from pathlib import Path

import yaml


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def word_factor(rank: int) -> float:
    return 1.0 if rank <= 2000 else 0.5 if rank <= 10000 else 0.2


def targets(path: Path) -> dict:
    result = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            raw = row.get("two_top_rank", "")
            if not raw or int(raw) > 20000:
                continue
            code, rank = row.get("code", ""), int(raw)
            if len(code) != 4:
                raise ValueError(f"非四码目标：{code!r}")
            result[code] = {"soft": word_factor(rank), "hard": False, "hard_character_top": 0}
    if not result:
        raise ValueError("目标为空")
    return result


def cross_objective(weight: float, target_map: dict) -> dict:
    return {
        "weight": weight, "hard_penalty": 0.0, "hard_character_top": 0,
        "character_tiers": [
            {"top": 1674, "factor": 1.0},
            {"top": 3527, "factor": 0.5},
            {"top": 6000, "factor": 0.2},
        ],
        "targets": target_map,
    }


def stripped(config: dict, remove_mapping: bool = False) -> dict:
    value = copy.deepcopy(config)
    value.get("info", {}).pop("name", None)
    value.get("info", {}).pop("version", None)
    value["optimization"]["objective"].pop("character_word_collision", None)
    value["optimization"]["metaheuristic"]["parameters"].pop("steps", None)
    if remove_mapping:
        value["form"].pop("mapping", None)
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-config", type=Path, required=True)
    ap.add_argument("--target-lexicon", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--pairs", type=int, default=4)
    ap.add_argument("--seed-start", type=int, default=850001)
    ap.add_argument("--steps", type=int, default=100000)
    ap.add_argument("--weight", type=float, default=0.1)
    args = ap.parse_args()
    if args.output_dir.exists() or args.pairs <= 0 or args.steps <= 0 or args.weight <= 0:
        raise ValueError("输出须不存在，pairs/steps/weight须为正")

    base = yaml.safe_load(args.base_config.read_text(encoding="utf-8"))
    space = base.get("generated_mapping_space")
    mapping = base.get("form", {}).get("mapping")
    if not isinstance(space, dict) or not isinstance(mapping, dict) or set(space) != set(mapping):
        raise ValueError("基础配置映射决策空间不完整")
    base["optimization"]["objective"].pop("words_full", None)
    base["optimization"]["objective"].pop("character_word_collision", None)
    target_map = targets(args.target_lexicon)
    fixed = {name for name, choices in space.items() if len(choices) == 1}
    base_without_mapping = stripped(base, remove_mapping=True)

    args.output_dir.mkdir(parents=True, exist_ok=False)
    cards, layout_hashes = [], set()
    card_number = 0
    for pair in range(1, args.pairs + 1):
        seed = args.seed_start + pair - 1
        rng = random.Random(seed)
        candidate = {}
        for element, choices in space.items():
            if not choices:
                raise ValueError(f"空决策空间：{element}")
            candidate[element] = copy.deepcopy(rng.choice(choices)["value"] if len(choices) > 1 else choices[0]["value"])
        for element in fixed:
            if canonical(candidate[element]) != canonical(mapping[element]):
                raise AssertionError(f"固定元素漂移：{element}")
        for element in mapping:
            if element.startswith(("szm-", "mzm-")) and canonical(candidate[element]) != canonical(mapping[element]):
                raise AssertionError(f"音码飞键：{element}")
        layout_hash = hashlib.sha256(canonical(candidate).encode("utf-8")).hexdigest()
        if layout_hash in layout_hashes:
            raise ValueError(f"随机布局重复：{seed}")
        layout_hashes.add(layout_hash)

        pair_configs = []
        for suffix, weight in (("off", 0.0), ("soft_0p1", args.weight)):
            card_number += 1
            cfg = copy.deepcopy(base)
            cfg["form"]["mapping"] = copy.deepcopy(candidate)
            cfg.setdefault("info", {})["name"] = f"夜莺0.85-R{pair}_{suffix}"
            cfg["info"]["version"] = "v0.85-random-paired-0003"
            if weight:
                cfg["optimization"]["objective"]["character_word_collision"] = cross_objective(weight, target_map)
            cfg["optimization"]["metaheuristic"]["parameters"]["steps"] = args.steps
            if stripped(cfg, remove_mapping=True) != base_without_mapping:
                raise AssertionError("允许范围外配置漂移")
            label = f"R{pair}_{suffix}"
            directory = args.output_dir / label
            directory.mkdir()
            path = directory / "config.yaml"
            path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
            cards.append({"card": card_number, "pair": pair, "seed": seed, "label": label,
                          "weight": weight, "layout_sha256": layout_hash,
                          "directory": str(directory.resolve()), "config": str(path.resolve()),
                          "config_sha256": sha256(path), "status": "pending"})
            pair_configs.append(cfg)
        if stripped(pair_configs[0]) != stripped(pair_configs[1]):
            raise AssertionError(f"第{pair}对除交叉目标外并非同配置")

    manifest = {"schema_version": 1, "design": "v085-0003", "pairs": args.pairs,
                "steps": args.steps, "weight": args.weight, "seed_start": args.seed_start,
                "base_config": str(args.base_config.resolve()), "base_config_sha256": sha256(args.base_config),
                "target_lexicon": str(args.target_lexicon.resolve()),
                "target_lexicon_sha256": sha256(args.target_lexicon), "target_codes": len(target_map),
                "unique_layouts": len(layout_hashes), "cards": cards,
                "status": "built_pending_validation_and_run"}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
