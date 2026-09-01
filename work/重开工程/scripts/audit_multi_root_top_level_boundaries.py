# -*- coding: utf-8 -*-
"""Audit top-level boundaries for splits containing three or more roots."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common
from audit_two_root_top_level_boundaries import AUDIT_NAME_EQUIVALENTS


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "02_规范拆分"
RUN_ROOT = PROJECT / "05_退火实验" / "多根顶层边界核验"


def run_chai(config: dict, charset: list[str], run_dir: Path, label: str) -> dict:
    cfg, cs, result = run_dir / f"{label}.yaml", run_dir / f"{label}.txt", run_dir / f"{label}.json"
    cfg.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    cs.write_text("\n".join(charset) + "\n", encoding="utf-8")
    cp = subprocess.run(["bun", str(common.RUNNER_PATH), str(cfg), str(cs), str(result)], cwd=common.ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (run_dir / f"{label}.stderr.txt").write_text(cp.stderr, encoding="utf-8")
    if cp.returncode:
        raise RuntimeError(cp.stderr)
    return json.loads(result.read_text(encoding="utf-8"))


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=False)
    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(common.RULES_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    rules = rules_doc.get("component_splits") or {}
    chars, splits = common.load_table()
    by_name, labels = common.repertoire_maps(baseline)
    norm = common.normalization_map(roots, by_name, labels)
    hosts = common.canonical_host_map(roots)
    registered = set()
    visible = {}
    for root, attached in roots["roots"].items():
        rr = common.resolve(root, by_name); registered.add(rr); visible[rr] = str(root)
        for item in attached or []:
            ri = common.resolve(item, by_name); registered.add(ri); visible[ri] = str(item)
    for anchored in (roots.get("anchors") or {}).values():
        for item in anchored or []:
            ri = common.resolve(item, by_name); registered.add(ri); visible[ri] = str(item)

    config = common.compile_config(baseline, roots, rules, by_name)
    first = run_chai(config, chars, run_dir, "first")
    extra_parts = []
    for char in chars:
        if len(splits[char]) < 3:
            continue
        top = first.get("top_level", {}).get(char) or {}
        extra_parts.extend(top.get("parts") or [])
    expanded_charset = list(dict.fromkeys([*chars, *extra_parts]))
    second = run_chai(config, expanded_charset, run_dir, "with_top_parts")
    observed = {
        char: [norm.get(x, labels.get(x, x)) for x in seq]
        for char, seq in second.get("rows", {}).items()
    }

    def expand(raw: str) -> tuple[list[str] | None, str]:
        display = visible.get(raw, labels.get(raw, raw))
        if display in AUDIT_NAME_EQUIVALENTS:
            return AUDIT_NAME_EQUIVALENTS[display], display
        if raw in registered:
            return [display], display
        if raw in splits:
            return splits[raw], display
        seq = observed.get(raw)
        return (seq if seq else None), display

    rows = []
    counts = {"aligned": 0, "mismatch": 0, "unresolved": 0}
    for char in chars:
        if len(splits[char]) < 3 or char in registered:
            continue
        top = first.get("top_level", {}).get(char) or {}
        parts = top.get("parts") or []
        if top.get("type") != "compound" or len(parts) < 2:
            continue
        chunks, names, unresolved = [], [], False
        for part in parts:
            seq, name = expand(part); names.append(name)
            if seq is None:
                unresolved = True; chunks.append([])
            else:
                chunks.append(seq)
        expected = [x for chunk in chunks for x in chunk]
        if unresolved:
            state = "unresolved"
        elif [hosts.get(x, x) for x in expected] == [hosts.get(x, x) for x in splits[char]]:
            state = "aligned"
        else:
            state = "mismatch"
        counts[state] += 1
        if state != "aligned":
            rows.append({
                "汉字": char, "顶层结构": str(top.get("operator", "")),
                "顶层部分": "／".join(names),
                "分段展开": " ｜ ".join(" ＋ ".join(x) if x else "?" for x in chunks),
                "拼接结果": " ＋ ".join(expected), "整字最终拆分": " ＋ ".join(splits[char]),
                "人工规则直接目标": "是" if char in rules else "否", "状态": state,
            })

    fields = ["汉字", "顶层结构", "顶层部分", "分段展开", "拼接结果", "整字最终拆分", "人工规则直接目标", "状态"]
    with (OUT / "多根顶层边界核验.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    result = {
        "run_time": now.isoformat(timespec="minutes"), "checked": sum(counts.values()), "counts": counts,
        "first_charset": len(chars), "expanded_charset": len(expanded_charset),
        "inputs": {str(p.relative_to(common.ROOT)): common.sha256(p) for p in [common.ROOTS_PATH, common.RULES_PATH, common.TABLE_PATH, common.BASELINE_PATH, common.RUNNER_PATH, Path(__file__)]},
        "exceptions": rows,
    }
    (OUT / "多根顶层边界核验.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# 多根顶层边界核验", "", f"- 检查数：{result['checked']}", f"- 一致：{counts['aligned']}", f"- 不一致候选：{counts['mismatch']}", f"- 无法解析：{counts['unresolved']}", f"- 扩展观察字集：{len(expanded_charset)}", "", "|字|结构|顶层部分|分段展开|最终拆分|人工规则|状态|", "|---|---|---|---|---|---|---|"]
    md.extend(f"|{x['汉字']}|{x['顶层结构']}|{x['顶层部分']}|{x['分段展开']}|{x['整字最终拆分']}|{x['人工规则直接目标']}|{x['状态']}|" for x in rows)
    (OUT / "多根顶层边界核验.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"checked": result["checked"], **counts, "expanded_charset": len(expanded_charset)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
