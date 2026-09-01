#!/usr/bin/env python3
"""报告抽卡后的三项附加手感指标；不参与退火。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml


KEY_INFO = {
    **{k: ("L", f) for k, f in zip("qwert", ("P", "R", "M", "I", "I"))},
    **{k: ("R", f) for k, f in zip("yuiop", ("I", "I", "M", "R", "P"))},
    **{k: ("L", f) for k, f in zip("asdfg", ("P", "R", "M", "I", "I"))},
    **{k: ("R", f) for k, f in zip("hjkl", ("I", "I", "M", "R"))},
    **{k: ("L", f) for k, f in zip("zxcv", ("P", "R", "M", "I"))},
    # 用户个人指法：B归右手食指，而不是Chai/常规映射中的左食指。
    **{k: ("R", f) for k, f in zip("bnm", ("I", "I", "I"))},
}
TIERS = (300, 500, 1500, 6000, 8454)


def load_records(elements: list[dict], code_path: Path) -> list[dict]:
    lines = code_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != len(elements):
        raise ValueError(f"{code_path}: code/elements行数不一致")
    records = []
    for index, (item, line) in enumerate(zip(elements, lines)):
        fields = line.split("\t")
        if len(fields) != 5 or fields[0] != str(item["词"]):
            raise ValueError(f"{code_path}: 第{index + 1}行错位或不是5列")
        full, actual = fields[1], fields[3]
        if len(full) != 4 or not 1 <= len(actual) <= 4:
            raise ValueError(f"{code_path}: 第{index + 1}行码长异常")
        records.append({
            "index": index, "word": fields[0], "pinyin": str(item["拼音"]),
            "frequency": int(item["频率"]), "full": full, "actual": actual,
            "order": int(item.get("排序序号", index)),
        })
    records.sort(key=lambda row: (row["order"], row["index"]))
    return records


def rate(value: int, total: int) -> float:
    return value / total if total else 0.0


def analyze(records: list[dict]) -> dict:
    transition_weight = identity_weight = 0
    micro_events = pinky_ring_events = pinky_middle_events = 0
    micro_affected_weight = pinky_affected_weight = 0
    micro_affected_count = pinky_affected_count = 0
    micro_pairs, pinky_pairs = Counter(), Counter()
    micro_chars, pinky_chars = Counter(), Counter()
    # 两种口径必须分开保留：
    # 1. full_*：所有身份按四码全码的第 2→3 键，适合观察字根布局本身；
    # 2. actual_*：只统计实际码长 >= 3 的身份，与 Chai 退火指标严格同口径。
    boundary_weight = lr = rl = same = 0
    actual_boundary_weight = actual_lr = actual_rl = actual_same = 0

    for row in records:
        freq, actual, full = row["frequency"], row["actual"], row["full"]
        identity_weight += freq
        transition_weight += freq * max(0, len(actual) - 1)
        has_micro = has_pinky = False
        for a, b in zip(actual, actual[1:]):
            ha, fa = KEY_INFO[a]
            hb, fb = KEY_INFO[b]
            if a != b and ha == hb and fa == fb:
                micro_events += freq
                micro_pairs[a + b] += freq
                micro_chars[f"{row['word']}({actual})"] += freq
                has_micro = True
            if ha == hb and {fa, fb} in ({"P", "R"}, {"P", "M"}):
                if {fa, fb} == {"P", "R"}:
                    pinky_ring_events += freq
                else:
                    pinky_middle_events += freq
                pinky_pairs[a + b] += freq
                pinky_chars[f"{row['word']}({actual})"] += freq
                has_pinky = True
        if has_micro:
            micro_affected_count += 1
            micro_affected_weight += freq
        if has_pinky:
            pinky_affected_count += 1
            pinky_affected_weight += freq

        second_hand, third_hand = KEY_INFO[full[1]][0], KEY_INFO[full[2]][0]
        boundary_weight += freq
        if second_hand == "L" and third_hand == "R":
            lr += freq
        elif second_hand == "R" and third_hand == "L":
            rl += freq
        else:
            same += freq

        if len(actual) >= 3:
            actual_second_hand, actual_third_hand = KEY_INFO[actual[1]][0], KEY_INFO[actual[2]][0]
            actual_boundary_weight += freq
            if actual_second_hand == "L" and actual_third_hand == "R":
                actual_lr += freq
            elif actual_second_hand == "R" and actual_third_hand == "L":
                actual_rl += freq
            else:
                actual_same += freq

    pinky_total = pinky_ring_events + pinky_middle_events
    return {
        "identities": len(records),
        "identity_weight": identity_weight,
        "weighted_transitions": transition_weight,
        "single_finger_move": {
            "weighted_events": micro_events,
            "event_rate": rate(micro_events, transition_weight),
            "affected_identities": micro_affected_count,
            "affected_identity_rate": rate(micro_affected_count, len(records)),
            "weighted_affected_identity_rate": rate(micro_affected_weight, identity_weight),
            "top_pairs": micro_pairs.most_common(10),
            "top_characters": micro_chars.most_common(12),
        },
        "pinky_linkage": {
            "weighted_events": pinky_total,
            "event_rate": rate(pinky_total, transition_weight),
            "pinky_ring_rate": rate(pinky_ring_events, transition_weight),
            "pinky_middle_rate": rate(pinky_middle_events, transition_weight),
            "affected_identities": pinky_affected_count,
            "affected_identity_rate": rate(pinky_affected_count, len(records)),
            "weighted_affected_identity_rate": rate(pinky_affected_weight, identity_weight),
            "top_pairs": pinky_pairs.most_common(10),
            "top_characters": pinky_chars.most_common(12),
        },
        "phonetic_shape_hand_separation": {
            "scope": "full_code_all_identities",
            "boundary_weight": boundary_weight,
            "left_to_right_rate": rate(lr, boundary_weight),
            "right_to_left_rate": rate(rl, boundary_weight),
            "separation_rate": rate(lr + rl, boundary_weight),
            "same_hand_rate": rate(same, boundary_weight),
        },
        "phonetic_shape_hand_separation_actual": {
            "scope": "actual_code_length_at_least_3_chai_compatible",
            "boundary_weight": actual_boundary_weight,
            "left_to_right_rate": rate(actual_lr, actual_boundary_weight),
            "right_to_left_rate": rate(actual_rl, actual_boundary_weight),
            "separation_rate": rate(actual_lr + actual_rl, actual_boundary_weight),
            "same_hand_rate": rate(actual_same, actual_boundary_weight),
        },
    }


def pct(value: float) -> str:
    return f"{value * 100:.3f}%"


def render(data: dict) -> str:
    names = list(data["candidates"])
    lines = ["# 抽卡后附加手感三指标（B=右手食指）", "",
             "只读诊断，不参与退火。采用用户个人指法B=右手食指；前两项越低越好，音形左右分离率越高越好。", ""]
    for tier in TIERS:
        label = "全体8454" if tier == 8454 else f"前{tier}"
        lines += [f"## {label}", "",
                  "| 候选 | 单指微移事件率 | 微移影响身份 | 小指联动合计 | 小↔无名 | 小↔中指 | 联动影响身份 | 音形分离 | 左→右 | 右→左 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name in names:
            row = data["candidates"][name][str(tier)]
            micro, pinky, split = row["single_finger_move"], row["pinky_linkage"], row["phonetic_shape_hand_separation"]
            lines.append(f"| {name} | {pct(micro['event_rate'])} | {micro['affected_identities']} ({pct(micro['weighted_affected_identity_rate'])}) | {pct(pinky['event_rate'])} | {pct(pinky['pinky_ring_rate'])} | {pct(pinky['pinky_middle_rate'])} | {pinky['affected_identities']} ({pct(pinky['weighted_affected_identity_rate'])}) | {pct(split['separation_rate'])} | {pct(split['left_to_right_rate'])} | {pct(split['right_to_left_rate'])} |")
        lines.append("")
    lines += ["## 全体主要贡献", ""]
    for name in names:
        row = data["candidates"][name]["8454"]
        micro, pinky = row["single_finger_move"], row["pinky_linkage"]
        lines += [f"### {name}", "",
                  "- 单指微移键对：" + "、".join(f"`{p}` {v}" for p, v in micro["top_pairs"]),
                  "- 单指微移字：" + "、".join(f"{c} {v}" for c, v in micro["top_characters"]),
                  "- 小指联动键对：" + "、".join(f"`{p}` {v}" for p, v in pinky["top_pairs"]),
                  "- 小指联动字：" + "、".join(f"{c} {v}" for c, v in pinky["top_characters"]), ""]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--candidate", action="append", required=True,
                        help="名称=code.txt，可重复")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    candidates = {}
    for spec in args.candidate:
        name, sep, raw_path = spec.partition("=")
        if not sep or not name:
            raise ValueError("candidate必须为名称=code.txt")
        records = load_records(elements, Path(raw_path))
        candidates[name] = {str(tier): analyze(records[:tier]) for tier in TIERS}
    data = {"schema_version": 1, "design": "0056", "candidates": candidates}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render(data), encoding="utf-8")
    print(json.dumps({"status": "pass", "candidates": list(candidates)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
