#!/usr/bin/env python3
"""从规范测量基线生成可追溯的夜莺0.8退火实验配置。"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml


PROFILES = {"three-code-only", "layered-handfeel-v1", "layered-handfeel-heat-v1",
            "layered-handfeel-heat-v2", "layered-handfeel-v2",
            "layered-handfeel-v1-fullguard2", "layered-handfeel-v1-fullguard4",
            "layered-handfeel-v1-fullguard8"}


def tier_by_top(tiers: list[dict], top: int) -> dict:
    try:
        return next(x for x in tiers if x["top"] == top)
    except StopIteration as exc:
        raise ValueError(f"配置缺少前{top}分层") from exc


def set_three_code_weight(tier: dict, weight: float) -> None:
    try:
        level = next(x for x in tier["levels"] if x["length"] == 3)
    except (KeyError, StopIteration) as exc:
        raise ValueError(f"前{tier.get('top', '?')}分层缺少三码指标") from exc
    level["frequency"] = weight


def build_config(source: dict, profile: str, steps: int | None,
                 t_max: float | None, t_min: float | None,
                 search_profile: str = "mixed") -> dict:
    if profile not in PROFILES:
        raise ValueError(f"未知实验配置：{profile}")
    if (t_max is None) != (t_min is None):
        raise ValueError("最高温和最低温必须同时提供或同时省略")
    if steps is not None and steps <= 0:
        raise ValueError("步数必须大于0")
    if search_profile not in {"mixed", "move-only"}:
        raise ValueError(f"未知移动算子配置：{search_profile}")

    result = copy.deepcopy(source)
    objective = result["optimization"]["objective"]
    if profile == "three-code-only":
        tiers = objective["characters_short"]["tiers"]
        set_three_code_weight(tier_by_top(tiers, 6000), -100.0)
    elif profile in {"layered-handfeel-v1", "layered-handfeel-heat-v1",
                     "layered-handfeel-heat-v2", "layered-handfeel-v2",
                     "layered-handfeel-v1-fullguard2", "layered-handfeel-v1-fullguard4",
                     "layered-handfeel-v1-fullguard8"}:
        tiers = objective["characters_short"]["tiers"]
        # 累计层：常用层各自保三码，总层仍是主目标。
        three_code_weights = (
            ((300, -15.0), (500, -15.0), (1500, -15.0), (6000, -75.0))
            if profile == "layered-handfeel-v2"
            else ((300, -15.0), (500, -15.0), (1500, -15.0), (6000, -70.0))
        )
        for top, weight in three_code_weights:
            set_three_code_weight(tier_by_top(tiers, top), weight)
        # 指法顺序：同手、大跨、小跨、干扰、错手、三连、备用、备用。
        # 第一版只给专家明确要求的大跨/小跨选择压力；大跨为小跨5倍。
        for top in (300, 500, 1500):
            tier = tier_by_top(tiers, top)
            large_weight, small_weight = (
                (80.0, 15.0) if profile == "layered-handfeel-v2" else (100.0, 20.0)
            )
            tier["weighted_fingering"] = [0.0, large_weight, small_weight, 0.0,
                                           0.0, 0.0, 0.0, 0.0]
            if profile in {"layered-handfeel-heat-v1", "layered-handfeel-heat-v2"}:
                # 必须配合shape_heat_equivalence.txt：仅惩罚音末→首根落在z/x。
                tier["phonetic_shape_transition_equivalence"] = (
                    2.0 if profile == "layered-handfeel-heat-v1" else 0.5
                )
        if profile in {"layered-handfeel-v1-fullguard2", "layered-handfeel-v1-fullguard4",
                       "layered-handfeel-v1-fullguard8"}:
            # 只保护最常用300字的实际全码重码；有一二简保护的全码重不计。
            # 两档用于测量选择力，其他全码层及全局全码重仍保持零权重。
            full_tiers = objective["characters_full"]["tiers"]
            tier_by_top(full_tiers, 300)["effective_duplication"] = float(profile[-1])

    meta = result["optimization"]["metaheuristic"]
    meta["search_method"] = (
        {"random_move": 0.90, "random_swap": 0.09, "random_full_key_swap": 0.01}
        if search_profile == "mixed"
        else {"random_move": 1.0, "random_swap": 0.0, "random_full_key_swap": 0.0}
    )
    meta["report_after"] = 0.99
    meta["update_interval"] = 5000
    if t_max is None:
        meta.pop("parameters", None)
    else:
        if steps is None:
            raise ValueError("固定温度时必须提供步数")
        meta["parameters"] = {"t_max": t_max, "t_min": t_min, "steps": steps}
    if isinstance(result.get("info"), dict):
        result["info"]["name"] = f"夜莺0.8-{profile}"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--t-max", type=float)
    parser.add_argument("--t-min", type=float)
    parser.add_argument("--search-profile", choices=("mixed", "move-only"), default="mixed")
    args = parser.parse_args()

    source = yaml.safe_load(args.source.read_text(encoding="utf-8"))
    result = build_config(
        source, args.profile, args.steps, args.t_max, args.t_min, args.search_profile
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(result, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
