#!/usr/bin/env python3
"""用“高频词＋新音节组合补集”离线复评第二届256张候选。

只读取既有退火结果，不运行退火，不修改任何正式码表或发布资产。
"""
from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import sys
from pathlib import Path

import yaml


def load_auditor(repo: Path):
    path = repo / "夜莺B" / "scripts" / "audit_cross_collision.py"
    spec = importlib.util.spec_from_file_location("nightingale_cross_audit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rank(rows: list[dict], key: str) -> None:
    ordered = sorted(rows, key=lambda row: (row[key], row["name"]))
    value = None
    current = 0
    for position, row in enumerate(ordered, 1):
        if row[key] != value:
            current = position
            value = row[key]
        row[f"{key}_rank"] = current


def target_config(base: dict, targets: dict[str, dict]) -> dict:
    result = copy.deepcopy(base)
    cross = result["optimization"]["objective"]["character_word_collision"]
    cross["targets"] = targets
    cross["hard_penalty"] = 0.0
    cross["hard_character_top"] = 0
    return result


def simple_targets(codes, soft=1.0):
    return {code: {"soft": soft, "hard": False, "hard_character_top": 0} for code in codes}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--high-words", type=int, default=40_000)
    ap.add_argument("--novel-slots", type=int, default=10_000)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    repo = args.repo.resolve()
    tournament = repo / "work" / "夜莺0.85" / "03_第二届32强" / "tournament"
    lexicon = repo / "夜莺B" / "work" / "lexicon" / "二字词_精选60000.tsv"
    elements_path = repo / "work" / "重开工程" / "04_Chai输入" / "夜莺0.8退火元素表_一简c为才.yaml"
    auditor = load_auditor(repo)
    elements = yaml.safe_load(elements_path.read_text(encoding="utf-8"))

    with lexicon.open(encoding="utf-8-sig", newline="") as handle:
        words = list(csv.DictReader(handle, delimiter="\t"))
    if len(words) < args.high_words:
        raise ValueError(f"词库只有{len(words)}词，不足{args.high_words}")

    high_rows = words[: args.high_words]
    high_codes = {row["code"] for row in high_rows}
    novel_rows = []
    novel_codes = set()
    for row in words[args.high_words :]:
        code = row["code"]
        if code in high_codes or code in novel_codes:
            continue
        novel_codes.add(code)
        novel_rows.append(row)
        if len(novel_rows) == args.novel_slots:
            break
    if len(novel_rows) < args.novel_slots:
        raise ValueError(f"尾部只能补出{len(novel_rows)}个新音节组合")

    first_card = tournament / "group_01" / "card_01_seed_861000" / "config.yaml"
    if not first_card.is_file():
        first_card = next((tournament / "group_01").glob("card_*/config.yaml"))
    base_config = yaml.safe_load(first_card.read_text(encoding="utf-8"))
    old_targets = base_config["optimization"]["objective"]["character_word_collision"]["targets"]
    configs = {
        "old": target_config(base_config, old_targets),
        "high": target_config(base_config, simple_targets(high_codes)),
        "novel": target_config(base_config, simple_targets(novel_codes)),
        "coverage": target_config(base_config, simple_targets(high_codes | novel_codes)),
    }

    rows = []
    for group in range(1, 17):
        manifest = json.loads((tournament / f"group_{group:02d}" / "manifest.json").read_text(encoding="utf-8"))
        for card in manifest["cards"]:
            output = Path(card["output_directory"])
            code_rows = auditor.load_code(output / "code.txt")
            values = {}
            for label, config in configs.items():
                result = auditor.audit(config, elements, code_rows)
                values[label] = {"soft": result["soft"], "hits": len(result["hits"])}
            rows.append({
                "name": f"G{group}C{int(card['card']):02d}",
                "group": group,
                "card": int(card["card"]),
                "seed": int(card["seed"]),
                "old_soft": values["old"]["soft"],
                "old_hits": values["old"]["hits"],
                "high_soft": values["high"]["soft"],
                "high_hits": values["high"]["hits"],
                "novel_soft": values["novel"]["soft"],
                "novel_hits": values["novel"]["hits"],
                "coverage_soft": values["coverage"]["soft"],
                "coverage_hits": values["coverage"]["hits"],
            })

    for key in ("old_soft", "high_soft", "novel_soft", "coverage_soft"):
        rank(rows, key)
    rows.sort(key=lambda row: row["coverage_soft_rank"])
    g8c12 = next(row for row in rows if row["name"] == "G8C12")
    report = {
        "schema_version": 1,
        "status": "read_only_experiment",
        "release_assets_modified": False,
        "selection": {
            "source_words": len(words),
            "high_words": len(high_rows),
            "high_unique_slots": len(high_codes),
            "novel_slots": len(novel_codes),
            "combined_slots": len(high_codes | novel_codes),
            "novel_scan_range": [args.high_words + 1, args.high_words + len(words[args.high_words:])],
        },
        "candidate_count": len(rows),
        "g8c12": g8c12,
        "ranking": rows,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "复评结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(rows[0])
    with (args.output / "256候选复评.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    top = rows[:20]
    lines = [
        "# 0.9.1 音节覆盖选词只读复评",
        "",
        "> 本实验不修改、不建议修改已经发布的0.9.1；只复评当年的256张候选。",
        "",
        "## 词位构造",
        "",
        f"- 高频核心：前{len(high_rows):,}词，聚合为{len(high_codes):,}个音节码位。",
        f"- 音节补集：从后续词中顺序选取{len(novel_codes):,}个首次出现的新码位。",
        f"- 合计覆盖：{len(high_codes | novel_codes):,}个不同码位。",
        "- 复评指标：沿用原字频层系数（前1674字=1、前3527字=0.5、前6000字=0.2），每个覆盖码位等权。",
        "",
        "## G8C12",
        "",
        f"- 原退火词目标：{g8c12['old_soft']:.3f}，256张中第{g8c12['old_soft_rank']}。",
        f"- 前4万高频词位：{g8c12['high_soft']:.3f}，第{g8c12['high_soft_rank']}。",
        f"- 新增1万音节位：{g8c12['novel_soft']:.3f}，第{g8c12['novel_soft_rank']}。",
        f"- 高频＋补集总覆盖：{g8c12['coverage_soft']:.3f}，第{g8c12['coverage_soft_rank']}。",
        "",
        "## 总覆盖指标前20",
        "",
        "|排名|候选|总覆盖|高频核心|音节补集|旧目标排名|",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in top:
        lines.append(f"|{row['coverage_soft_rank']}|{row['name']}|{row['coverage_soft']:.3f}|{row['high_soft']:.3f}|{row['novel_soft']:.3f}|{row['old_soft_rank']}|")
    (args.output / "结果摘要.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output.resolve()), "g8c12": g8c12}, ensure_ascii=False))


if __name__ == "__main__":
    main()
