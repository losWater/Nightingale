# -*- coding: utf-8 -*-
"""在夜莺 0.7 终局布局附近枚举单个根家族搬移，供贪心微调筛选。"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import yaml

from short_code_overrides import apply_overrides


KEYS = "abcdefghijklmnopqrstuvwxyz"


def duplicates(codes: list[str], order: list[int], top: int) -> tuple[int, int]:
    counts = Counter(codes[i] for i in order[:top])
    return (
        sum(n - 1 for n in counts.values() if n > 1),
        sum((n - 1) ** 2 for n in counts.values() if n > 1),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("code", type=Path)
    ap.add_argument("elements", type=Path)
    ap.add_argument("--owners", nargs="+", help="只审计指定的根家族")
    ap.add_argument(
        "--all-owners", action="store_true",
        help="审计实际出现在首末位的全部直属根家族",
    )
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--emit-dir", type=Path, help="输出排名靠前候选的完整配置")
    ap.add_argument("--emit-top", type=int, default=0)
    ap.add_argument(
        "--aux-weight", type=float,
        help="生成候选配置时覆盖五码辅助权重；统计资产仍然保留",
    )
    ap.add_argument("--space-config", type=Path, help="提供 checkpoint 中省略的决策空间")
    args = ap.parse_args()

    # Windows 控制台在部分代码页下会把个别汉字根参数替换为 U+FFFD；
    # 允许用 U+XXXX 形式稳定指定 Unicode 根名。
    if args.owners:
        args.owners = [
            chr(int(owner[2:], 16))
            if owner.upper().startswith("U+")
            else owner
            for owner in args.owners
        ]

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    mapping = config["form"]["mapping"]
    # 输出方案/检查点可能省略决策空间；合法候选必须以原始输入配置为准。
    space_source = config
    if args.space_config:
        space_source = yaml.safe_load(args.space_config.read_text(encoding="utf-8"))
    generated_space = space_source.get("generated_mapping_space") or {}
    form_space = space_source.get("form", {}).get("mapping_space") or {}
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    rows = [line.split("\t") for line in args.code.read_text(encoding="utf-8").splitlines()]
    manual_three_winners = apply_overrides(rows)
    if len(rows) != len(elements):
        raise ValueError("code/elements 行数不一致")
    for item, row in zip(elements, rows):
        if str(item["词"]) != row[0]:
            raise ValueError(f"code/elements 错位: {item['词']} != {row[0]}")

    if any(item.get("排序序号") is not None for item in elements):
        order = sorted(range(len(elements)), key=lambda i: (
            int(elements[i].get("排序序号", 10**12)), i
        ))
    else:
        order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))

    def trace(element: str) -> tuple[str | None, str | None]:
        current, seen = str(element), set()
        while current not in seen:
            seen.add(current)
            value = mapping.get(current)
            if isinstance(value, str):
                return current, value
            if isinstance(value, dict) and "element" in value:
                current = str(value["element"])
                continue
            return None, None
        return None, None

    owners: list[tuple[str | None, str | None]] = []
    for item in elements:
        pair = []
        for slot in item["元素序列"][2:4]:
            pair.append(trace(slot["element"])[0])
        owners.append((pair[0], pair[1]))

    if args.all_owners:
        requested_owners = sorted({
            owner for pair in owners for owner in pair if owner is not None
        })
    elif args.owners:
        requested_owners = args.owners
    else:
        ap.error("必须提供 --owners 或 --all-owners")

    full_base = [row[1] for row in rows]
    # 一、二简是人工资产，形根移动不影响；其余字音重新竞争三码位。
    fixed_short = {i: rows[i][3] for i in range(len(rows)) if len(rows[i][3]) < 3}
    order_rank = {index: rank for rank, index in enumerate(order)}
    competition_order = sorted(
        order, key=lambda i: (i not in manual_three_winners, order_rank[i])
    )

    objective = config["optimization"]["objective"]
    cross = objective["character_word_collision"]
    targets = cross["targets"]
    tiers = cross.get("character_tiers", [])

    def factor(rank: int) -> float:
        for tier in tiers:
            if rank <= int(tier["top"]):
                return float(tier["factor"])
        return 0.0

    def evaluate(full: list[str]) -> dict[str, float | int]:
        prefix_winner: dict[str, int] = {}
        for i in competition_order:
            if i not in fixed_short:
                prefix_winner.setdefault(full[i][:3], i)
        short = []
        for i, code in enumerate(full):
            if i in fixed_short:
                short.append(fixed_short[i])
            elif prefix_winner[code[:3]] == i:
                short.append(code[:3])
            else:
                short.append(code)

        hard = 0
        soft = 0.0
        for rank, i in enumerate(order[:5000], 1):
            # 与正式评估器保持一致：只有实际仍以四码输出的单字，
            # 才会占据四码词槽；一、二、三码字不能拿理论全码撞词。
            if short[i] != full[i]:
                continue
            target = targets.get(full[i])
            if not target:
                continue
            if bool(target.get("hard")) and rank <= int(target.get("hard_character_top", 0)):
                hard += 1
            soft += factor(rank) * float(target.get("soft", 0.0))
        f1800 = duplicates(full, order, 1800)
        f3761 = duplicates(full, order, 3761)
        f6000 = duplicates(full, order, 6000)
        s1800 = duplicates(short, order, 1800)
        s3761 = duplicates(short, order, 3761)
        return {
            "hard": hard, "soft": round(soft, 6),
            "full1800": f1800[0], "full1800_sq": f1800[1],
            "full3761": f3761[0], "full3761_sq": f3761[1],
            "full6000": f6000[0], "full6000_sq": f6000[1],
            "short1800": s1800[0], "short1800_sq": s1800[1],
            "short3761": s3761[0], "short3761_sq": s3761[1],
            "three1800": sum(len(short[i]) == 3 for i in order[:1800]),
            "three3761": sum(len(short[i]) == 3 for i in order[:3761]),
        }

    baseline = evaluate(full_base)
    print("baseline", baseline)
    candidates = []
    legal_move_count = 0
    for owner in requested_owners:
        source = trace(owner)[1]
        if source not in KEYS:
            print(f"skip owner={owner!r}: source={source!r}")
            continue
        descriptions = generated_space.get(owner, form_space.get(owner, []))
        def conditions_hold(item: dict) -> bool:
            for condition in item.get("condition") or []:
                if condition.get("op") != "不是":
                    return False
                other_key = trace(str(condition.get("element")))[1]
                if other_key == condition.get("value"):
                    return False
            return True

        allowed_keys = {
            item.get("value")
            for item in descriptions
            if isinstance(item, dict)
            and isinstance(item.get("value"), str)
            and len(item["value"]) == 1
            and item["value"] in KEYS
            and conditions_hold(item)
        }
        if not allowed_keys:
            print(f"skip owner={owner!r}: no unconditional direct-key arrangement")
            continue
        movable_keys = sorted(allowed_keys - {source})
        if not movable_keys:
            print(f"fixed owner={owner!r}: only legal key is {source!r}")
            continue
        legal_move_count += len(movable_keys)
        for destination in movable_keys:
            if destination == source:
                continue
            full = []
            for code, pair in zip(full_base, owners):
                changed = list(code)
                if pair[0] == owner:
                    changed[2] = destination
                if pair[1] == owner:
                    changed[3] = destination
                full.append("".join(changed))
            metric = evaluate(full)
            if metric["hard"]:
                continue
            candidates.append({"owner": owner, "from": source, "to": destination, **metric})

    candidates.sort(key=lambda x: (
        x["short1800"], x["short3761"], x["full1800"], x["full3761"],
        -x["three1800"], -x["three3761"], x["full6000"], x["soft"],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(candidates[0]) if candidates else [])
        if candidates:
            writer.writeheader(); writer.writerows(candidates)
    print(
        f"owners={len(requested_owners)} legal_moves={legal_move_count} "
        f"hard_feasible={len(candidates)} output={args.output}"
    )
    for row in candidates[:30]:
        print(row)
    if args.emit_dir and args.emit_top:
        args.emit_dir.mkdir(parents=True, exist_ok=True)
        for rank, row in enumerate(candidates[:args.emit_top], 1):
            candidate_config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
            if args.space_config:
                space_config = yaml.safe_load(args.space_config.read_text(encoding="utf-8"))
                candidate_config["form"]["mapping_space"] = space_config["form"].get("mapping_space")
                candidate_config["generated_mapping_space"] = space_config.get("generated_mapping_space")
            if args.aux_weight is not None:
                auxiliary = candidate_config["optimization"]["objective"].get("auxiliary_two_char")
                if auxiliary is not None:
                    auxiliary["weight"] = args.aux_weight
            candidate_config["form"]["mapping"][row["owner"]] = row["to"]
            path = args.emit_dir / f"{rank:02d}_{ord(row['owner']) if len(row['owner']) == 1 else row['owner']}_{row['from']}_to_{row['to']}.yaml"
            path.write_text(yaml.safe_dump(candidate_config, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
