#!/usr/bin/env python3
"""从C19完整解生成只改变词重目标的夜莺0.85配对配置。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remove_allowed_changes(config: dict) -> dict:
    result = copy.deepcopy(config)
    info = result.get("info", {})
    info.pop("name", None)
    info.pop("version", None)
    objective = result["optimization"]["objective"]
    objective.pop("words_full", None)
    result["optimization"]["metaheuristic"]["parameters"].pop("steps", None)
    return result


def words_full(tiers: list[tuple[int, float]], overall: float) -> dict:
    if overall < 0 or any(top <= 0 or weight < 0 for top, weight in tiers):
        raise ValueError("词重层级和全体权重必须非负，top必须为正")
    tops = [top for top, _ in tiers]
    if tops != sorted(set(tops)):
        raise ValueError("词重top必须严格递增且不得重复")
    return {
        "tiers": [{"top": top, "duplication": weight} for top, weight in tiers],
        "duplication": overall,
        "levels": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--mapping-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--a1-weight", type=float, default=10.0)
    parser.add_argument("--a2-weight", type=float, default=25.0)
    args = parser.parse_args()

    if args.steps <= 0 or args.a1_weight < 0 or args.a2_weight < 0:
        raise ValueError("步数须为正，权重须非负")
    if args.a1_weight >= args.a2_weight:
        raise ValueError("A1弱权重必须小于A2中权重")
    if args.output_dir.exists():
        raise ValueError("输出目录必须不存在")

    baseline = yaml.safe_load(args.base_config.read_text(encoding="utf-8"))
    mapping_source = yaml.safe_load(args.mapping_source.read_text(encoding="utf-8"))
    if not isinstance(baseline.get("form", {}).get("mapping"), dict):
        raise ValueError("输入缺少form.mapping")
    if not isinstance(baseline.get("generated_mapping_space"), dict):
        raise ValueError("基础配置缺少generated_mapping_space，不能续跑")
    champion_mapping = mapping_source.get("form", {}).get("mapping")
    if not isinstance(champion_mapping, dict) or set(champion_mapping) != set(baseline["form"]["mapping"]):
        raise ValueError("结果解映射缺失或元素集合与基础配置不同")
    baseline["form"]["mapping"] = copy.deepcopy(champion_mapping)
    if not isinstance(baseline.get("optimization", {}).get("objective"), dict):
        raise ValueError("输入缺少optimization.objective")
    if not isinstance(baseline["optimization"].get("metaheuristic", {}).get("parameters"), dict):
        raise ValueError("输入缺少退火参数")

    plans = [
        ("A0_no_words", None),
        ("A1_top20000_weak", words_full([(20000, args.a1_weight)], 0.0)),
        ("A2_top20000_medium", words_full([(20000, args.a2_weight)], 0.0)),
        ("A3_historical", words_full([(2000, 150.0), (20000, 40.0)], 15.0)),
    ]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    normalized_baseline = remove_allowed_changes(baseline)
    rows = []
    for card_number, (label, word_objective) in enumerate(plans, start=1):
        config = copy.deepcopy(baseline)
        config.setdefault("info", {})["name"] = f"夜莺0.85-{label}"
        config["info"]["version"] = "v0.85-parameter-calibration-0001"
        objective = config["optimization"]["objective"]
        objective.pop("words_full", None)
        if word_objective is not None:
            objective["words_full"] = word_objective
        config["optimization"]["metaheuristic"]["parameters"]["steps"] = args.steps
        if remove_allowed_changes(config) != normalized_baseline:
            raise AssertionError(f"{label}出现允许范围外的配置变化")
        card_dir = args.output_dir / label
        card_dir.mkdir()
        path = card_dir / "config.yaml"
        path.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000),
            encoding="utf-8",
        )
        rows.append({
            "card": card_number,
            "label": label,
            "directory": str(card_dir.resolve()),
            "config": str(path.resolve()),
            "config_sha256": sha256(path),
            "words_full": word_objective,
            "status": "pending",
        })

    manifest = {
        "schema_version": 1,
        "design": "v085-0001",
        "base_config": str(args.base_config.resolve()),
        "base_config_sha256": sha256(args.base_config),
        "mapping_source": str(args.mapping_source.resolve()),
        "mapping_source_sha256": sha256(args.mapping_source),
        "steps": args.steps,
        "allowed_changes": [
            "info.name",
            "info.version",
            "optimization.objective.words_full",
            "optimization.metaheuristic.parameters.steps",
        ],
        "cards": rows,
        "status": "built_pending_validation_and_run",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    audit = [
        "# 配置差异审计",
        "",
        f"- 工程基线：`{args.base_config.resolve()}`",
        f"- 工程基线 SHA-256：`{sha256(args.base_config)}`",
        f"- 冠军映射来源：`{args.mapping_source.resolve()}`",
        f"- 冠军映射来源 SHA-256：`{sha256(args.mapping_source)}`",
        f"- 每档步数：{args.steps}",
        "- 结果：四档配置删除允许变化项后，均与 C19 基线逐对象相等。",
        "- 第二—第三键分离率：本轮只在结果报告中测试，未写入目标函数。",
        "",
        "|档位|词重目标|配置 SHA-256|",
        "|---|---|---|",
    ]
    for row in rows:
        text = "关闭" if row["words_full"] is None else json.dumps(row["words_full"], ensure_ascii=False)
        audit.append(f"|{row['label']}|`{text}`|`{row['config_sha256']}`|")
    (args.output_dir / "配置差异审计.md").write_text("\n".join(audit) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
