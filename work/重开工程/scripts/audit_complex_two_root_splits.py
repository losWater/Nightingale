# -*- coding: utf-8 -*-
"""Rank non-root two-root splits by Chai-selected glyph stroke count."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "02_规范拆分"
RUN_ROOT = PROJECT / "05_退火实验" / "二根复杂字巡检"


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=False)
    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(common.RULES_PATH.read_text(encoding="utf-8"))
    rules = rules_doc.get("component_splits") or {}
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    chars, splits = common.load_table()
    by_name, _ = common.repertoire_maps(baseline)

    registered = set()
    for root, attached in roots["roots"].items():
        registered.add(common.resolve(root, by_name))
        registered.update(common.resolve(x, by_name) for x in attached or [])
    for anchored in (roots.get("anchors") or {}).values():
        registered.update(common.resolve(x, by_name) for x in anchored or [])

    config = common.compile_config(baseline, roots, rules, by_name)
    cfg_path = run_dir / "config.yaml"
    charset_path = run_dir / "charset.txt"
    result_path = run_dir / "chai_result.json"
    cfg_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    charset_path.write_text("\n".join(chars) + "\n", encoding="utf-8")
    cp = subprocess.run(
        ["bun", str(common.RUNNER_PATH), str(cfg_path), str(charset_path), str(result_path)],
        cwd=common.ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    (run_dir / "stderr.txt").write_text(cp.stderr, encoding="utf-8")
    if cp.returncode:
        raise RuntimeError(cp.stderr)
    chai = json.loads(result_path.read_text(encoding="utf-8"))
    strokes = chai.get("stroke_counts", {})

    rows = []
    for char in chars:
        seq = splits[char]
        if len(seq) != 2 or char in registered:
            continue
        count = strokes.get(char)
        if count is None:
            raise ValueError(f"missing Chai stroke count: {char}")
        rows.append({
            "汉字": char, "笔画数": count, "第一根": seq[0], "第二根": seq[1],
            "人工规则直接目标": "是" if char in rules else "否",
        })
    rows.sort(key=lambda x: (-x["笔画数"], x["汉字"]))

    with (OUT / "二根复杂字巡检.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["汉字", "笔画数", "第一根", "第二根", "人工规则直接目标"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    payload = {
        "run_time": now.isoformat(timespec="minutes"),
        "counts": {"glyphs": len(chars), "two_root_non_root_glyphs": len(rows)},
        "inputs": {str(p.relative_to(common.ROOT)): common.sha256(p) for p in [common.ROOTS_PATH, common.RULES_PATH, common.TABLE_PATH, common.BASELINE_PATH, common.RUNNER_PATH, Path(__file__)]},
        "rows": rows,
    }
    (OUT / "二根复杂字巡检.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# 二根复杂字巡检", "", f"- 运行时间：{payload['run_time']}",
        f"- 非根字二根拆分总数：{len(rows)}", "- 以下列出笔画数最高的前50项；高笔画不等于错误。", "",
        "|汉字|笔画数|拆分|人工规则直接目标|", "|---|---:|---|---|",
    ]
    md.extend(f"|{x['汉字']}|{x['笔画数']}|{x['第一根']} ＋ {x['第二根']}|{x['人工规则直接目标']}|" for x in rows[:50])
    (OUT / "二根复杂字巡检.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
