# -*- coding: utf-8 -*-
"""Find one-root splits whose glyph is not itself a registered root shape."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "02_规范拆分"
EXCEPTIONS = OUT / "结构等价例外_待验收.yaml"


def main() -> None:
    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    chars, splits = common.load_table()
    by_name, _ = common.repertoire_maps(baseline)
    exception_doc = yaml.safe_load(EXCEPTIONS.read_text(encoding="utf-8")) if EXCEPTIONS.exists() else {}
    accepted = {x["glyph"] for x in exception_doc.get("accepted_implicit_equivalences", [])}

    registered: dict[str, tuple[str, str]] = {}
    for root, attached in roots["roots"].items():
        registered[common.resolve(root, by_name)] = (str(root), "主根")
        for item in attached or []:
            registered[common.resolve(item, by_name)] = (str(root), "附属根")
    for host, anchored in (roots.get("anchors") or {}).items():
        for item in anchored or []:
            registered[common.resolve(item, by_name)] = (str(host), "锚定根")

    candidates = []
    accepted_rows = []
    legal = []
    for char in chars:
        seq = splits[char]
        if len(seq) != 1:
            continue
        if char in registered:
            legal.append(char)
            continue
        result = seq[0]
        row = {
            "汉字": char,
            "单根结果": result,
            "类型": "未登记整字自成根" if result == char else "疑似被其他根吞并",
            "说明": "已接受的隐式结构等价" if char in accepted else "候选，尚未判定错误",
        }
        (accepted_rows if char in accepted else candidates).append(row)

    with (OUT / "异常短拆巡检.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["汉字", "单根结果", "类型", "说明"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(candidates + accepted_rows)

    now = datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes")
    payload = {
        "run_time": now,
        "inputs": {
            str(common.ROOTS_PATH.relative_to(common.ROOT)): common.sha256(common.ROOTS_PATH),
            str(common.TABLE_PATH.relative_to(common.ROOT)): common.sha256(common.TABLE_PATH),
            str(common.BASELINE_PATH.relative_to(common.ROOT)): common.sha256(common.BASELINE_PATH),
            str(EXCEPTIONS.relative_to(common.ROOT)): common.sha256(EXCEPTIONS),
            str(Path(__file__).relative_to(common.ROOT)): common.sha256(Path(__file__)),
        },
        "counts": {
            "glyphs": len(chars), "one_root_total": len(legal) + len(candidates) + len(accepted_rows),
            "registered_one_root": len(legal), "accepted_implicit_equivalence": len(accepted_rows),
            "suspicious_one_root": len(candidates),
        },
        "candidates": candidates, "accepted_exceptions": accepted_rows,
    }
    (OUT / "异常短拆巡检.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# 异常短拆巡检", "", f"- 运行时间：{now}", f"- 8105 字中的单根字：{len(legal)+len(candidates)+len(accepted_rows)}",
        f"- 已登记根形的合法单根字：{len(legal)}", f"- 已接受的隐式结构等价：{len(accepted_rows)}", f"- 需要人工检查的单根候选：{len(candidates)}", "",
        "候选只表示字本身未登记为根，却只得到一个根；是否错误仍需逐字判断。", "",
        "|汉字|单根结果|类型|", "|---|---|---|",
    ]
    md.extend(f"|{x['汉字']}|{x['单根结果']}|{x['类型']}|" for x in candidates)
    md += ["", "## 已接受的隐式结构等价", ""]
    md.extend(f"- {x['汉字']} → {x['单根结果']}：{x['说明']}" for x in accepted_rows)
    (OUT / "异常短拆巡检.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
