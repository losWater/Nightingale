#!/usr/bin/env python3
"""从C19生成夜莺0.85字词交叉碰撞软权重配对实验。"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(config: dict) -> dict:
    result = copy.deepcopy(config)
    result.get("info", {}).pop("name", None)
    result.get("info", {}).pop("version", None)
    result["optimization"]["objective"].pop("character_word_collision", None)
    result["optimization"]["metaheuristic"]["parameters"].pop("steps", None)
    return result


def word_factor(rank: int) -> float:
    if rank <= 2000:
        return 1.0
    if rank <= 10000:
        return 0.5
    return 0.2


def load_targets(path: Path) -> tuple[dict, dict]:
    targets: dict[str, dict] = {}
    tier_counts = {"1-2000": 0, "2001-10000": 0, "10001-20000": 0}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            raw = row.get("two_top_rank", "")
            if not raw:
                continue
            rank = int(raw)
            if rank > 20000:
                continue
            code = row.get("code", "")
            if len(code) != 4:
                raise ValueError(f"目标词库存在非四码：{code!r}")
            targets[code] = {"soft": word_factor(rank), "hard": False, "hard_character_top": 0}
            tier = "1-2000" if rank <= 2000 else "2001-10000" if rank <= 10000 else "10001-20000"
            tier_counts[tier] += 1
    if not targets:
        raise ValueError("前20000二字词目标为空")
    return targets, tier_counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-config", type=Path, required=True)
    ap.add_argument("--mapping-source", type=Path, required=True)
    ap.add_argument("--target-lexicon", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--weights", type=float, nargs="*", default=None,
                    help="显式软权重；省略时生成B0及0.01/0.03/0.05")
    args = ap.parse_args()
    if args.steps <= 0 or args.output_dir.exists():
        raise ValueError("步数须为正，输出目录必须不存在")

    baseline = yaml.safe_load(args.base_config.read_text(encoding="utf-8"))
    result = yaml.safe_load(args.mapping_source.read_text(encoding="utf-8"))
    mapping = result.get("form", {}).get("mapping")
    if not isinstance(baseline.get("generated_mapping_space"), dict):
        raise ValueError("基础配置缺少generated_mapping_space")
    if not isinstance(mapping, dict) or set(mapping) != set(baseline["form"]["mapping"]):
        raise ValueError("冠军映射与基础配置元素集合不同")
    baseline["form"]["mapping"] = copy.deepcopy(mapping)
    baseline["optimization"]["objective"].pop("words_full", None)
    targets, tier_counts = load_targets(args.target_lexicon)
    base_normalized = normalized(baseline)
    if args.weights is None:
        plans = [("B0_off", 0.0), ("B1_soft_001", 0.01),
                 ("B2_soft_003", 0.03), ("B3_soft_005", 0.05)]
    else:
        if not args.weights or any(weight <= 0 for weight in args.weights):
            raise ValueError("显式软权重必须非空且全部为正")
        if len(set(args.weights)) != len(args.weights):
            raise ValueError("显式软权重不得重复")
        plans = [(f"C{index}_soft_{str(weight).replace('.', 'p')}", weight)
                 for index, weight in enumerate(args.weights, 1)]

    args.output_dir.mkdir(parents=True, exist_ok=False)
    cards = []
    for number, (label, weight) in enumerate(plans, 1):
        cfg = copy.deepcopy(baseline)
        cfg.setdefault("info", {})["name"] = f"夜莺0.85-{label}"
        cfg["info"]["version"] = "v0.85-cross-calibration-0002"
        objective = cfg["optimization"]["objective"]
        objective.pop("character_word_collision", None)
        if weight:
            objective["character_word_collision"] = {
                "weight": weight,
                "hard_penalty": 0.0,
                "hard_character_top": 0,
                "character_tiers": [
                    {"top": 1674, "factor": 1.0},
                    {"top": 3527, "factor": 0.5},
                    {"top": 6000, "factor": 0.2},
                ],
                "targets": targets,
            }
        cfg["optimization"]["metaheuristic"]["parameters"]["steps"] = args.steps
        if normalized(cfg) != base_normalized:
            raise AssertionError(f"{label}出现允许范围外变化")
        directory = args.output_dir / label
        directory.mkdir()
        config_path = directory / "config.yaml"
        config_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
        cards.append({"card": number, "label": label, "weight": weight,
                      "directory": str(directory.resolve()), "config": str(config_path.resolve()),
                      "config_sha256": sha256(config_path), "status": "pending"})

    manifest = {
        "schema_version": 1, "design": "v085-0002",
        "base_config": str(args.base_config.resolve()), "base_config_sha256": sha256(args.base_config),
        "mapping_source": str(args.mapping_source.resolve()), "mapping_source_sha256": sha256(args.mapping_source),
        "target_lexicon": str(args.target_lexicon.resolve()), "target_lexicon_sha256": sha256(args.target_lexicon),
        "target_codes": len(targets), "target_tiers": tier_counts, "steps": args.steps,
        "cards": cards, "status": "built_pending_validation_and_run",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 配置差异审计", "", f"- 前20000唯一目标码位：{len(targets)}",
             f"- 目标分层：`{json.dumps(tier_counts, ensure_ascii=False)}`",
             "- 硬罚：关闭。", "- `words_full`：关闭。",
             "- 四档删除允许变化项后，均与C19可续跑基线逐对象相等。", "",
             "|档位|交叉碰撞权重|配置SHA-256|", "|---|---:|---|"]
    lines.extend(f"|{x['label']}|{x['weight']}|`{x['config_sha256']}`|" for x in cards)
    (args.output_dir / "配置差异审计.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
