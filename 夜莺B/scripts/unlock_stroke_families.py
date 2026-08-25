# -*- coding: utf-8 -*-
"""把五大笔画家族从固定键解锁为普通的 26 键决策变量。"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


STROKES = "12345"
PINKY_KEYS = set("qazp")
PINKY_STRENGTH = 2.5
FORMER_FIXED_COLLISIONS = {
    "wjhv": 3761,
    "iruu": 1800,
    "yuhh": 1800,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("elements", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--steps", type=int, default=4_200_000)
    ap.add_argument("--report-after", type=float, default=0.95)
    args = ap.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    alphabet = config["form"].get("alphabet", "abcdefghijklmnopqrstuvwxyz")

    contribution = {stroke: 0 for stroke in STROKES}
    total_shape_frequency = 0
    for item in elements:
        frequency = int(item.get("频率", 0))
        for slot in item["元素序列"][2:4]:
            element = str(slot["element"])
            total_shape_frequency += frequency
            if element in contribution:
                contribution[element] += frequency

    for stroke in STROKES:
        choices = [
            {
                "value": key,
                "score": (
                    PINKY_STRENGTH * contribution[stroke] / total_shape_frequency
                    if key in PINKY_KEYS else 0.0
                ),
            }
            for key in alphabet
        ]
        config["form"]["mapping_space"][stroke] = choices
        config["generated_mapping_space"][stroke] = choices

    # 这些词位过去因固定笔画而免责；解锁后恢复为硬约束。
    targets = config["optimization"]["objective"]["character_word_collision"]["targets"]
    for code, hard_top in FORMER_FIXED_COLLISIONS.items():
        if code in targets:
            targets[code]["hard"] = True
            targets[code]["hard_character_top"] = hard_top

    meta = config["optimization"]["metaheuristic"]
    meta["parameters"]["steps"] = args.steps
    meta["report_after"] = args.report_after

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000),
        encoding="utf-8",
    )
    print("stroke_contribution=", contribution)
    print("total_shape_frequency=", total_shape_frequency)
    print("restored_hard_targets=", FORMER_FIXED_COLLISIONS)
    print("output=", args.output)


if __name__ == "__main__":
    main()
