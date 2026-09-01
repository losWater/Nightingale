# -*- coding: utf-8 -*-
"""Materialize the fully accepted, guarded frame rewrite asset."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
RUN_ROOT = PROJECT / "05_退火实验" / "字架历史语义候选表"
INVENTORY = PROJECT / "02_规范拆分" / "字架迁移盘点_待验收.yaml"
AUDIT = PROJECT / "02_规范拆分" / "字架迁移审计.json"
OUT = PROJECT / "02_规范拆分" / "正式字架规则.yaml"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main() -> None:
    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    required = ["衣", "行", "辡", "玨", "赢"]
    bad = [x for x in required if inventory["frames"][x].get("migration_status") != "candidate_accepted_pending_formal_compiler"]
    if bad:
        raise ValueError(f"frames not fully accepted: {bad}")
    runs = sorted([x for x in RUN_ROOT.iterdir() if x.is_dir() and (x / "生成清单.json").exists()], reverse=True)[:2]
    if len(runs) != 2:
        raise ValueError("need two completed candidate runs")
    manifests = [json.loads((x / "生成清单.json").read_text(encoding="utf-8")) for x in runs]
    for manifest in manifests:
        if manifest.get("status") != "candidate_only_not_authoritative" or manifest.get("semantic_changes") != 37:
            raise ValueError("candidate manifest status/count mismatch")
    candidate_hashes = {x["outputs"]["字架历史语义候选8105.tsv"] for x in manifests}
    delta_hashes = {x["outputs"]["字架历史语义变化37字.tsv"] for x in manifests}
    if len(candidate_hashes) != 1 or len(delta_hashes) != 1:
        raise ValueError("two latest candidate runs are not reproducible")
    latest = runs[0]
    changes = rows(latest / "字架历史语义变化37字.tsv")
    if len(changes) != 37 or {x["汉字"] for x in changes} & {"斑", "癍"}:
        raise ValueError("unexpected accepted change set")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    frame_by_char = {}
    for kind, chars in audit["direct_hits"].items():
        for char in chars:
            frame_by_char[char] = kind
    for item in audit["nested_structural_hits"]:
        frame_by_char[item["汉字"]] = item["字架"]
    rewrite = {}
    for row in changes:
        char = row["汉字"]
        if char not in frame_by_char:
            raise ValueError(f"change outside audited frame scope: {char}")
        rewrite[char] = {
            "frame": frame_by_char[char],
            "expected_before": row["当前拆分"].split(" ＋ "),
            "canonical_after": row["候选拆分"].split(" ＋ "),
        }
    doc = {
        "schema_version": 1,
        "status": "accepted_guarded_structural_rules",
        "description": "字架由结构树审计确认范围；正式生成仅应用逐字验收的精确前后序列，禁止token子串传播。",
        "candidate_sha256": next(iter(candidate_hashes)),
        "delta_sha256": next(iter(delta_hashes)),
        "unchanged_equivalent": ["斑", "癍"],
        "complete_root_precedence": ["襄"],
        "frames": {k: inventory["frames"][k] for k in required},
        "guarded_rewrites": rewrite,
        "sources": {
            str(INVENTORY.relative_to(ROOT)): common.sha256(INVENTORY),
            str(AUDIT.relative_to(ROOT)): common.sha256(AUDIT),
            "candidate_runs": [x.name for x in runs],
        },
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "rewrites": len(rewrite), "candidate_sha256": doc["candidate_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
