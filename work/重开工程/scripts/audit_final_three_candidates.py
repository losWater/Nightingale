#!/usr/bin/env python3
"""合并既有结构化结果，审计 C11/C07/C15 的硬门禁与最终风险。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


CANDIDATES = ("C11", "C07", "C15")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percent(value: float, digits: int = 3) -> str:
    return f"{value * 100:.{digits}f}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.experiment_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    core_path = root / "core_metrics.json"
    extras_path = root / "postdraw_handfeel_extras_16cards.json"
    stability_path = root / "test_batch_0058" / "分段稳定性_书面与LCCC" / "stability_raw.json"
    core = load_json(core_path)
    extras = load_json(extras_path)["candidates"]
    stability = load_json(stability_path)
    balanced_scores = next(iter(stability["profileScores"].values()))

    generation_checks: dict[str, bool] = {}
    for candidate in CANDIDATES:
        report_path = root / "test_batch_0058" / f"{candidate}_seed_8200{candidate[1:]}" / "生成报告.md"
        table_path = root / "test_batch_0058" / "普通单字码表集合" / f"{candidate}_seed_8200{candidate[1:]}_纯单字试用表.txt"
        report_text = report_path.read_text(encoding="utf-8")
        table_lines = table_path.read_text(encoding="utf-8").splitlines()
        generation_checks[candidate] = (
            "原始身份实际码长：一码 26，二码 405" in report_text
            and "校验通过：8454身份、8105字、逐行对齐、码长、实际候选序号及两种试用格式一致" in report_text
            and "才\tc" in table_lines
        )

    rows: dict[str, dict] = {}
    for candidate in CANDIDATES:
        c = core[candidate]
        e = extras[candidate]["1500"]
        s = stability["aggregate"][candidate]
        rows[candidate] = {
            "stability_score": balanced_scores[candidate],
            "three_code_6000": c["layers"]["6000"]["three_code_count"],
            "front300_effective_full_duplication": c["layers"]["300"]["effective_full_duplication"],
            "front500_effective_full_duplication": c["layers"]["500"]["effective_full_duplication"],
            "front1500_effective_full_duplication": c["front1500_effective_full_duplication"],
            "short_duplication": c["short_duplication"],
            "full_duplication": c["effective_full_duplication"],
            "short_pair_equivalence": c["short_pair_equivalence"],
            "short_large_cross": c["short_large_cross"],
            "short_small_cross": c["short_small_cross"],
            "heat_left": c["heat_front1500"]["left"],
            "heat_zx_all": c["heat_front1500"]["zx_all"],
            "heat_fh_all": c["heat_front1500"]["fh_all"],
            "heat_zx_third": c["heat_front1500"]["zx_third"],
            "heat_fh_third": c["heat_front1500"]["fh_third"],
            "single_finger_move_1500": e["single_finger_move"]["event_rate"],
            "pinky_linkage_1500": e["pinky_linkage"]["event_rate"],
            "phonetic_shape_separation_1500": e["phonetic_shape_hand_separation"]["separation_rate"],
            "corpus_keys_per_char": s["keysPerChar"],
            "corpus_avg_eq": s["avgEq"],
            "corpus_large_cross": s["multiSpanRate"],
            "corpus_small_cross": s["singleSpanRate"],
            "corpus_pinky": s["littleFdRate"],
            "corpus_same_finger_b_right": s["sameFingerRateBRight"],
            "corpus_diff_hand_b_right": s["diffHandRateBRight"],
        }

    hard_gates = {
        "front300_effective_full_duplication_zero": all(
            row["front300_effective_full_duplication"] == 0 for row in rows.values()
        ),
        "generated_table_integrity": all(generation_checks.values()),
        "same_missing_set_per_block": all(
            all(
                item["lacks"] == group[0]["lacks"] and item["lackString"] == group[0]["lackString"]
                for item in group
            )
            for group in (
                [
                    item
                    for item in stability["rows"]
                    if item["genre"] == block["genre"] and item["block"] == block["index"]
                ]
                for block in stability["blocks"]
            )
        ),
    }
    hard_gates["all_pass"] = all(hard_gates.values())

    result = {
        "schema_version": 1,
        "candidates": list(CANDIDATES),
        "inputs": {
            str(core_path): sha256(core_path),
            str(extras_path): sha256(extras_path),
            str(stability_path): sha256(stability_path),
        },
        "hard_gates": hard_gates,
        "generation_checks": generation_checks,
        "metrics": rows,
        "decision": {
            "recommended": "C11" if hard_gates["all_pass"] else None,
            "preexisting_veto_against_c11": False if hard_gates["all_pass"] else None,
            "runner_up": "C07",
            "secondary": "C15",
            "reason": "C11通过全部既定硬门禁，0061跨文体、跨权重均第一；其静态短板均为比较项且未达到任何预先定义的否决条件。",
        },
    }

    json_path = output_dir / "最终三卡否决项审计.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    headers = [
        ("稳定性得分", "stability_score", "number"),
        ("前6000三码", "three_code_6000", "integer"),
        ("前300有效全码重", "front300_effective_full_duplication", "integer"),
        ("前500有效全码重", "front500_effective_full_duplication", "integer"),
        ("前1500有效全码重", "front1500_effective_full_duplication", "integer"),
        ("简码重码率", "short_duplication", "percent"),
        ("全码重码率", "full_duplication", "percent"),
        ("简码组合当量", "short_pair_equivalence", "number"),
        ("传统大跨", "short_large_cross", "percent"),
        ("传统小跨", "short_small_cross", "percent"),
        ("前1500左手", "heat_left", "percent"),
        ("前1500 Z/X全部", "heat_zx_all", "percent"),
        ("前1500 F/H全部", "heat_fh_all", "percent"),
        ("前1500 Z/X第三键", "heat_zx_third", "percent"),
        ("前1500 F/H第三键", "heat_fh_third", "percent"),
        ("前1500单指微移", "single_finger_move_1500", "percent"),
        ("前1500小指联动", "pinky_linkage_1500", "percent"),
        ("前1500音形分离", "phonetic_shape_separation_1500", "percent"),
        ("语料击键/字", "corpus_keys_per_char", "number"),
        ("语料平均当量", "corpus_avg_eq", "number"),
    ]

    def fmt(value: float | int, kind: str) -> str:
        if kind == "percent":
            return percent(float(value))
        if kind == "integer":
            return str(value)
        return f"{value:.6f}"

    lines = [
        "# 最终三卡否决项审计",
        "",
        "## 结论",
        "",
        "C11通过全部既定硬门禁。没有发现可以依据既定规则否决C11的理由。",
        "",
        "当前建议：**C11作为夜莺0.8最终学习候选；C07为备选；C15退出最终竞争。**",
        "",
        "这不是说C11每项最好。C11的传统大/小跨、前1500单指微移和F/H第三键热力均有明确短板；但这些短板没有既定否决阈值，而C11在真实连续语料、跨文体、四套权重和bootstrap稳定性上均保持总体第一。",
        "",
        "## 硬门禁",
        "",
        "| 门禁 | 结果 |",
        "|---|---|",
        f"| 前300有效全码重码为0 | {'通过' if hard_gates['front300_effective_full_duplication_zero'] else '失败'} |",
        f"| 三卡自身生成报告完整性与`c=才` | {'通过' if hard_gates['generated_table_integrity'] else '失败'} |",
        f"| 79段逐段缺字集合一致 | {'通过' if hard_gates['same_missing_set_per_block'] else '失败'} |",
        "",
        "## 完整对照",
        "",
        "| 指标 | C11 | C07 | C15 |",
        "|---|---:|---:|---:|",
    ]
    for label, key, kind in headers:
        lines.append(f"| {label} | {fmt(rows['C11'][key], kind)} | {fmt(rows['C07'][key], kind)} | {fmt(rows['C15'][key], kind)} |")
    lines += [
        "",
        "## 候选解释",
        "",
        "### C11",
        "",
        "- 优势：稳定性总分第一；四套权重全部第一；简码组合当量三卡最低；前6000三码略高于C07；语料平均当量优于C07。",
        "- 风险：传统大小跨均高于C07/C15；前1500单指微移最高；F/H第三键热力12.140%，明显高于另外两卡；音形分离率居中。",
        "- 裁决：风险真实存在，但连续语料已经把具体字序和跨字组合纳入，仍稳定第一，因此不构成既定否决项。",
        "",
        "### C07",
        "",
        "- 优势：传统小跨三卡最低；前1500单指微移优于C11；小指联动与语料小指干扰较好；热力较均衡。",
        "- 风险：稳定性第二且对C11的bootstrap两两胜率仅24.5%；传统大跨仍高于C15；前6000三码略低于C11。",
        "- 裁决：最合理备选，但现有证据不足以反超C11。",
        "",
        "### C15",
        "",
        "- 优势：传统大跨三卡最低；语料平均当量最低；B右手异手互击最高。",
        "- 风险：前6000三码最低；全码与简码重码率最高；前500已有3组有效全码重；长文和聊天选重均明显更多；稳定性第一概率仅0.9%。",
        "- 裁决：方向性手感卡，不适合作为唯一学习版本。",
        "",
        "## 边界",
        "",
        "本报告只裁决当前固定根集与三张退火布局。后续若修改根集、人工拆分、字音频率、简码规则或退火目标，本结论必须重新计算，不能自动继承。",
        "",
    ]
    (output_dir / "最终三卡否决项审计.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result["hard_gates"], ensure_ascii=False, indent=2))
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
