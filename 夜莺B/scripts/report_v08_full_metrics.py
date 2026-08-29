#!/usr/bin/env python3
"""生成0.8候选完整验收报告；缺少适用指标时失败，不修改输入资产。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


TIER_TOPS = (300, 500, 1674, 3527, 6000)
FINGER_NAMES = ("同手", "大跨", "小跨", "干扰", "错手", "三连", "备用1", "备用2")
ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


@dataclass(frozen=True)
class Run:
    name: str
    directory: Path
    data: dict[str, Any]
    codes: list[tuple[str, str, str, int]]
    objective_signature: str


def require(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"缺少必需指标：{path}")
        current = current[part]
    if current is None:
        raise ValueError(f"必需指标为null：{path}")
    return current


def tier_map(group: dict[str, Any], label: str) -> dict[int, dict[str, Any]]:
    tiers = require(group, "tiers")
    if not isinstance(tiers, list):
        raise ValueError(f"{label}.tiers必须为列表")
    result = {require(item, "top"): item for item in tiers}
    if set(result) != set(TIER_TOPS) or len(result) != len(tiers):
        raise ValueError(f"{label}.tiers必须且只能包含{TIER_TOPS}，实际为{sorted(result)}")
    return result


def validate_metric(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise ValueError(f"不支持的metric.json版本：{data.get('schema_version')!r}")
    require(data, "score")
    metric = require(data, "metric")
    require(metric, "complexity")
    full = require(metric, "characters_full")
    short = require(metric, "characters_short")
    for label, group in (("characters_full", full), ("characters_short", short)):
        for key in ("duplication", "pair_equivalence", "phonetic_shape_transition_equivalence", "fingering"):
            require(group, key)
        fingers = group["fingering"]
        if not isinstance(fingers, list) or len(fingers) != 8 or any(x is None for x in fingers):
            raise ValueError(f"{label}.fingering必须包含8个非null值")
    require(full, "effective_duplication")
    require(short, "levels")
    full_tiers = tier_map(full, "characters_full")
    short_tiers = tier_map(short, "characters_short")
    for top in TIER_TOPS:
        for key in ("duplication", "duplication_squared"):
            require(full_tiers[top], key)
            require(short_tiers[top], key)
        for key in ("effective_duplication", "effective_duplication_squared"):
            require(full_tiers[top], key)
        require(short_tiers[top], "levels")
        if top != 6000:
            for tier, label in ((full_tiers[top], "full"), (short_tiers[top], "short")):
                require(tier, "weighted_fingering")
                require(tier, "phonetic_shape_transition_equivalence")
                if len(tier["weighted_fingering"]) != 8 or any(x is None for x in tier["weighted_fingering"]):
                    raise ValueError(f"{label}.tiers[{top}].weighted_fingering不完整")


def load_elements(path: Path) -> list[dict[str, Any]]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("elements必须为列表")
    return value


def load_codes(path: Path, elements: list[dict[str, Any]]) -> list[tuple[str, str, str, int]]:
    rows = [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != len(elements):
        raise ValueError(f"{path}: code.txt与elements行数不一致")
    records: list[tuple[int, dict[str, Any], tuple[str, str, str, int]]] = []
    for index, (item, row) in enumerate(zip(elements, rows)):
        char = str(item["词"])
        if len(row) < 4 or row[0] != char:
            raise ValueError(f"{path}: code/elements错位：{char}/{row[:1]}")
        records.append((index, item, (char, row[1], row[3], int(item.get("频率", 0)))))
    if any(item.get("排序序号") is not None for _, item, _ in records):
        records.sort(key=lambda x: (x[1].get("排序序号", 2**63 - 1), x[0]))
    else:
        records.sort(key=lambda x: (-x[2][3], x[0]))
    return [record for _, _, record in records]


def parse_spec(spec: str, elements: list[dict[str, Any]]) -> Run:
    name, sep, raw = spec.partition("=")
    if not sep or not name or not raw:
        raise ValueError("运行参数格式必须为名称=运行目录（或metric.json路径）")
    path = Path(raw)
    directory = path if path.is_dir() else path.parent
    metric_path = directory / "metric.json" if path.is_dir() else path
    if metric_path.name != "metric.json":
        raise ValueError(f"{path}: 文件必须名为metric.json")
    data = json.loads(metric_path.read_text(encoding="utf-8"))
    validate_metric(data)
    config = yaml.safe_load((directory / "config.yaml").read_text(encoding="utf-8"))
    objective = require(config, "optimization.objective")
    objective_signature = json.dumps(objective, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return Run(name, directory, data, load_codes(directory / "code.txt", elements), objective_signature)


def get_tier(run: Run, group: str, top: int) -> dict[str, Any]:
    return tier_map(run.data["metric"][group], group)[top]


def level_count(tier: dict[str, Any], length: int) -> int:
    levels = {item["length"]: item["frequency"] for item in tier["levels"]}
    return int(levels.get(length, 0))


def heat(records: list[tuple[str, str, str, int]], top: int = 1500) -> dict[str, float]:
    keys: Counter[str] = Counter()
    third: Counter[str] = Counter()
    total = third_total = 0
    for _, _, code, frequency in records[:top]:
        for key in code:
            keys[key] += frequency
            total += frequency
        if len(code) >= 3:
            third[code[2]] += frequency
            third_total += frequency
    if not total or not third_total:
        raise ValueError("无法计算按键热力：编码或频率总量为0")
    return {
        "左手": sum(keys[k] for k in "qwertasdfgzxcvb") / total,
        "右手": sum(keys[k] for k in "yuiophjklnm") / total,
        "Z/X全部": (keys["z"] + keys["x"]) / total,
        "F/H全部": (keys["f"] + keys["h"]) / total,
        "Z/X第三键": (third["z"] + third["x"]) / third_total,
        "F/H第三键": (third["f"] + third["h"]) / third_total,
    }


def collision_examples(records: list[tuple[str, str, str, int]], top: int) -> list[str]:
    groups: dict[str, list[str]] = {}
    for char, full, _, _ in records[:top]:
        groups.setdefault(full, []).append(char)
    return [f"`{code}`：{'/'.join(chars)}" for code, chars in groups.items() if len(chars) > 1]


def key_contributors(records: list[tuple[str, str, str, int]], keys: str, top: int = 1500) -> list[str]:
    values: Counter[str] = Counter()
    for char, _, short, frequency in records[:top]:
        if len(short) >= 3 and short[2] in keys:
            values[f"{char}({short})"] += frequency
    return [name for name, _ in values.most_common(12)]


def metrics(run: Run) -> dict[str, float]:
    metric = run.data["metric"]
    full, short = metric["characters_full"], metric["characters_short"]
    values: dict[str, float] = {
        "总分": float(run.data["score"]),
        "复杂度": float(metric["complexity"]),
        "全码重码率": float(full["duplication"]),
        "有效全码重码率": float(full["effective_duplication"]),
        "简码重码率": float(short["duplication"]),
        "全码组合当量": float(full["pair_equivalence"]),
        "简码组合当量": float(short["pair_equivalence"]),
        "全码音形过渡": float(full["phonetic_shape_transition_equivalence"]),
        "简码音形过渡": float(short["phonetic_shape_transition_equivalence"]),
    }
    for top in TIER_TOPS:
        ft, st = get_tier(run, "characters_full", top), get_tier(run, "characters_short", top)
        values[f"前{top}全码重"] = float(ft["duplication"])
        values[f"前{top}有效全码重"] = float(ft["effective_duplication"])
        values[f"前{top}简码重"] = float(st["duplication"])
        values[f"前{top}三码"] = float(level_count(st, 3))
        if top != 6000:
            values[f"前{top}简码大跨"] = float(st["weighted_fingering"][1])
            values[f"前{top}简码小跨"] = float(st["weighted_fingering"][2])
    values.update(heat(run.codes))
    return values


def fmt_value(name: str, value: float) -> str:
    if "率" in name or "跨" in name or "手" in name or "全部" in name or "第三键" in name:
        return f"{value * 100:.3f}%"
    if value.is_integer() and name not in {"总分", "复杂度"}:
        return str(int(value))
    return f"{value:.6f}"


def fmt_delta(name: str, value: float) -> str:
    if "率" in name or "跨" in name or "手" in name or "全部" in name or "第三键" in name:
        return f"{value * 100:+.3f}pp"
    return f"{value:+.3f}"


def render(runs: list[Run], baseline: Run, previous: Run | None) -> str:
    all_runs = [baseline] + ([previous] if previous else []) + runs
    values = {run.name: metrics(run) for run in all_runs}
    names = list(values[baseline.name])
    out = ["# 夜莺0.8候选完整指标报告", "", "## 完整性结论", "",
           "- PASS：全部适用字段存在，且metric.json schema_version均为1。",
           "- 词码、字词碰撞、五码辅助：N/A（本轮纯单字布局实验未配置）。", "",
           "## 全指标对比", ""]
    headers = ["指标", baseline.name] + ([previous.name] if previous else []) + [run.name for run in runs]
    out += ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for name in names:
        row = [name, fmt_value(name, values[baseline.name][name])]
        if previous:
            if name == "总分" and previous.objective_signature != baseline.objective_signature:
                row.append(fmt_value(name, values[previous.name][name]) + "（目标函数不同，不横比）")
            else:
                row.append(fmt_value(name, values[previous.name][name]))
        for run in runs:
            value = values[run.name][name]
            cell = fmt_value(name, value)
            if name == "总分" and run.objective_signature != baseline.objective_signature:
                cell += "<br>目标函数不同，不与基线横比"
            else:
                cell += "<br>基线 " + fmt_delta(name, value - values[baseline.name][name])
            if previous:
                if name == "总分" and run.objective_signature != previous.objective_signature:
                    cell += "；目标函数不同，不与前任横比"
                else:
                    cell += "；前任 " + fmt_delta(name, value - values[previous.name][name])
            row.append(cell)
        out.append("| " + " | ".join(row) + " |")
    out += ["", "## 异常与具体贡献项", ""]
    baseline_values = values[baseline.name]
    for run in runs:
        run_values = values[run.name]
        out += [f"### {run.name}", ""]
        collisions = collision_examples(run.codes, 300)
        out.append("- 前300全码重码组：" + ("；".join(collisions) if collisions else "无"))
        regressions = []
        for name in ("前300全码重", "前500全码重", "前1500简码小跨", "Z/X全部", "F/H全部"):
            if run_values[name] > baseline_values[name]:
                regressions.append(f"{name} {fmt_delta(name, run_values[name] - baseline_values[name])}")
        out.append("- 相对基线的关注退化：" + ("；".join(regressions) if regressions else "无"))
        out.append("- Z/X第三键主要贡献字：" + "、".join(key_contributors(run.codes, "zx")))
        out.append("- F/H第三键主要贡献字：" + "、".join(key_contributors(run.codes, "fh")))
        out.append("")
    out += ["", "## 数据来源", ""]
    out.extend(f"- {run.name}：`{run.directory}`" for run in all_runs)
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--baseline", required=True, help="名称=运行目录")
    parser.add_argument("--previous", help="名称=运行目录")
    parser.add_argument("--candidate", action="append", required=True, help="名称=运行目录，可重复")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    elements = load_elements(args.elements)
    baseline = parse_spec(args.baseline, elements)
    previous = parse_spec(args.previous, elements) if args.previous else None
    candidates = [parse_spec(spec, elements) for spec in args.candidate]
    names = [baseline.name] + ([previous.name] if previous else []) + [run.name for run in candidates]
    if len(set(names)) != len(names):
        raise ValueError("基线、前任与候选名称不得重复")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(candidates, baseline, previous), encoding="utf-8")


if __name__ == "__main__":
    main()
