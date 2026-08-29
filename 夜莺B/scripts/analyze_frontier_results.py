# -*- coding: utf-8 -*-
"""汇总三路线退火结果并标记满足硬门槛的 Pareto 候选。"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


FULL = re.compile(r"一字全码［选重率：([\d.]+)%；组合当量：([\d.]+)；1500 选重：(\d+)；.*?3500 选重：(\d+)；.*?6000 选重：(\d+)；")
SHORT = re.compile(r"一字简码［选重率：([\d.]+)%；组合当量：([\d.]+)；1500 选重：(\d+)；.*?1500 三键：(\d+)；3500 选重：(\d+)；.*?3500 三键：(\d+)；")
CROSS = re.compile(r"字词交叉［硬碰撞：(\d+)；软碰撞当量：([\d.]+)；")


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    full, short, cross = FULL.search(text), SHORT.search(text), CROSS.search(text)
    missing = [name for name, match in (("一字全码", full), ("一字简码", short),
                                        ("字词交叉", cross)) if match is None]
    if missing:
        raise ValueError(f"metric格式不兼容，缺少或无法解析 {','.join(missing)}：{path}")
    return {
        "full_rate": float(full[1]), "full_pair": float(full[2]),
        "full1500": int(full[3]), "full3500": int(full[4]), "full6000": int(full[5]),
        "short_rate": float(short[1]), "short_pair": float(short[2]),
        "short1500": int(short[3]), "three1500": int(short[4]),
        "short3500": int(short[5]), "three3500": int(short[6]),
        "hard": int(cross[1]), "soft": float(cross[2]),
    }


def collect(suite: Path) -> list[dict]:
    manifest_path = suite / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"缺少实验manifest：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profiles = manifest.get("profiles")
    threads = manifest.get("threads")
    if not isinstance(profiles, list) or not profiles or not all(isinstance(x, str) for x in profiles):
        raise ValueError(f"manifest.profiles必须是非空字符串列表：{manifest_path}")
    if not isinstance(threads, int) or threads < 1:
        raise ValueError(f"manifest.threads必须是正整数：{manifest_path}")

    rows = []
    for profile in profiles:
        root = suite / profile
        if not root.is_dir():
            raise FileNotFoundError(f"缺少profile目录：{root}")
        output_roots = sorted(root.glob("output-*"))
        if len(output_roots) != 1:
            raise ValueError(f"profile必须恰有一个output目录，实际{len(output_roots)}个：{root}")
        output_root = output_roots[0]
        expected_threads = set(range(threads))
        actual_threads = set()
        for metric in sorted(output_root.glob("*/metric.txt")):
            try:
                thread = int(metric.parent.name)
            except ValueError as exc:
                raise ValueError(f"线程目录名不是整数：{metric.parent}") from exc
            if thread in actual_threads:
                raise ValueError(f"重复线程结果：{profile}/{thread}")
            actual_threads.add(thread)
            data = parse(metric)
            data.update({"profile": profile, "thread": thread, "directory": str(metric.parent)})
            data["valid"] = int(data["hard"] == 0 and data["full1500"] == 0
                                and data["short1500"] == 0)
            rows.append(data)
        if actual_threads != expected_threads:
            missing = sorted(expected_threads - actual_threads)
            extra = sorted(actual_threads - expected_threads)
            raise ValueError(f"线程集合不完整：{profile}；缺失={missing}；多余={extra}")
    return rows


def dominates(a, b):
    minimize = ("full3500", "full6000", "short3500", "full_pair", "short_pair", "soft")
    maximize = ("three1500", "three3500")
    no_worse = all(a[k] <= b[k] for k in minimize) and all(a[k] >= b[k] for k in maximize)
    better = any(a[k] < b[k] for k in minimize) or any(a[k] > b[k] for k in maximize)
    return no_worse and better


def mark_frontier(rows: list[dict], suite: Path) -> list[dict]:
    valid = [x for x in rows if x["valid"]]
    if not valid:
        raise ValueError(f"没有满足硬门槛的候选，拒绝生成空Pareto结论：{suite}")
    for row in rows:
        row["pareto"] = int(row in valid and not any(
            dominates(other, row) for other in valid if other is not row
        ))
    return valid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = collect(args.suite)
    valid = mark_frontier(rows, args.suite)
    rows.sort(key=lambda x: (-x["valid"], -x["pareto"], x["full3500"], x["full6000"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["profile", "thread", "valid", "pareto", "hard", "full1500", "full3500", "full6000",
              "short1500", "short3500", "three1500", "three3500", "full_pair", "short_pair",
              "full_rate", "short_rate", "soft", "directory"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    print(f"all={len(rows)} valid={len(valid)} pareto={sum(x['pareto'] for x in rows)}")
    for key, reverse in (("full3500", False), ("full6000", False), ("three1500", True),
                         ("three3500", True), ("full_pair", False), ("short_pair", False),
                         ("soft", False)):
        best = sorted(valid, key=lambda x: x[key], reverse=reverse)[0]
        print("BEST", key, best[key], best["profile"], best["thread"], best)


if __name__ == "__main__":
    main()
