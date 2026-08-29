# -*- coding: utf-8 -*-
"""生成终局候选的可读碰撞、隐藏词位与手感诊断报告。"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
WORK = BASE / "work"


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_code(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        rows.append({"char": fields[0], "full": fields[1], "short": fields[3]})
    return rows


def groups(codes, order, top, field):
    by_code = defaultdict(list)
    for rank, index in enumerate(order[:top], 1):
        by_code[codes[index][field]].append((rank, codes[index]["char"]))
    return {code: values for code, values in by_code.items() if len(values) > 1}


def format_groups(found, limit=30):
    ordered = sorted(found.items(), key=lambda item: (min(x[0] for x in item[1]), item[0]))
    return [f"- `{code}`：" + "、".join(f"{char}({rank})" for rank, char in values)
            for code, values in ordered[:limit]]


def trace(mapping, element):
    value = mapping[str(element)]
    while isinstance(value, dict): value = mapping[str(value["element"])]
    return value


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run", type=Path); ap.add_argument("validation", type=Path)
    args = ap.parse_args()
    output_dir = next(args.run.glob("output-*"))
    prior = WORK / "ab_slot_runs" / "frequency_vs_novel_20260825_025020" / "B_core10000_novel5000" / "formal_12x100000"
    prior_output = next(prior.glob("output-*"))
    candidates = {
        "长跑线程9（三码／训练）": output_dir / "9",
        "长跑线程10（单字）": output_dir / "10",
        "长跑线程2（手感／泛化）": output_dir / "2",
        "短跑B6（隐藏极值）": prior_output / "6",
    }
    elements = yaml.safe_load((WORK / "analysis_elements.yaml").read_text(encoding="utf-8"))
    order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))
    validation = {row["code"]: row for row in read_tsv(args.validation)}
    report = ["# 夜莺 B 终局候选具体诊断", "",
              "排名为当前 `analysis_elements.yaml` 的读音资产频率序；同一多音字可能有多个资产。", ""]
    for name, directory in candidates.items():
        codes = load_code(directory / "code.txt")
        mapping = yaml.safe_load((directory / "config.yaml").read_text(encoding="utf-8"))["form"]["mapping"]
        full3500 = groups(codes, order, 3500, "full")
        full6000 = groups(codes, order, 6000, "full")
        short3500 = groups(codes, order, 3500, "short")
        hidden = []
        for rank, index in enumerate(order[:5000], 1):
            row = validation.get(codes[index]["full"])
            if row:
                hidden.append((rank, codes[index]["char"], codes[index]["full"], row["two_top_rank"], row["two_words"]))
        loads = Counter(); total = 0
        for item in elements:
            frequency = int(item.get("频率", 0))
            for slot in item["元素序列"][2:4]:
                key = trace(mapping, slot["element"]); loads[key] += frequency; total += frequency
        pinky = sum(loads[key] for key in "qazp") / total * 100
        report += [f"## {name}", "",
                   f"- 前3500全码重码组：{len(full3500)} 组；重复项：{sum(len(v)-1 for v in full3500.values())}",
                   f"- 前6000全码重码组：{len(full6000)} 组；重复项：{sum(len(v)-1 for v in full6000.values())}",
                   f"- 前3500简码重码组：{len(short3500)} 组；重复项：{sum(len(v)-1 for v in short3500.values())}",
                   f"- 隐藏集碰撞：前1500 {sum(x[0] <= 1500 for x in hidden)}，前3500 {sum(x[0] <= 3500 for x in hidden)}，前5000 {len(hidden)}",
                   f"- Q/A/Z/P 形码频率负担：{pinky:.3f}%（Q {loads['q']/total*100:.3f}%／A {loads['a']/total*100:.3f}%／Z {loads['z']/total*100:.3f}%／P {loads['p']/total*100:.3f}%）",
                   "", "### 前3500全部全码重码", ""]
        report += format_groups(full3500, 100) or ["- 无"]
        report += ["", "### 前3500全部简码重码", ""]
        report += format_groups(short3500, 100) or ["- 无"]
        report += ["", "### 最高频的20项隐藏词位碰撞", ""]
        report += [f"- {char}（字序 {rank}）`{code}` ↔ {words}（词序 {word_rank}）"
                   for rank, char, code, word_rank, words in hidden[:20]] or ["- 无"]
        report.append("")
    out = args.run / "终局候选具体诊断.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(out)


if __name__ == "__main__": main()
