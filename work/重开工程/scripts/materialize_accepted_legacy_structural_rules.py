# -*- coding: utf-8 -*-
"""Materialize 27 accepted historical structural decisions as guarded rules."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
RUN_ROOT = PROJECT / "05_退火实验" / "历史结构裁决候选表"
INVENTORY = PROJECT / "02_规范拆分" / "历史序列覆写迁移盘点_待验收.yaml"
OUT = PROJECT / "02_规范拆分" / "正式历史结构裁决规则.yaml"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main() -> None:
    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    decisions = inventory.get("accepted_structural_decisions") or {}
    deferred = (inventory.get("deferred_encoding_layer_decisions") or {}).get("entries") or {}
    if len(decisions) != 27:
        raise ValueError(f"expected 27 accepted decisions, got {len(decisions)}")
    if set(decisions) & set(deferred):
        raise ValueError("structural decisions overlap deferred encoding decisions")

    runs = sorted(
        [x for x in RUN_ROOT.iterdir() if x.is_dir() and (x / "生成清单.json").exists()],
        reverse=True,
    )[:2]
    if len(runs) != 2:
        raise ValueError("need two completed candidate runs")
    manifests = [json.loads((x / "生成清单.json").read_text(encoding="utf-8")) for x in runs]
    for manifest in manifests:
        if manifest.get("status") != "candidate_only_not_authoritative":
            raise ValueError("candidate manifest has wrong status")
        if manifest.get("accepted_structural_decisions") != 27:
            raise ValueError("candidate manifest has wrong decision count")
        delta = manifest.get("structural_candidate_delta") or {}
        if any(delta.get(k) for k in ("新增", "消失", "成员变化")):
            raise ValueError(f"candidate has unresolved same-split delta: {delta}")
    candidate_hashes = {m["outputs"]["历史结构裁决候选8105.tsv"] for m in manifests}
    delta_hashes = {m["outputs"]["历史结构裁决变化27字.tsv"] for m in manifests}
    if len(candidate_hashes) != 1 or len(delta_hashes) != 1:
        raise ValueError("latest two candidate runs are not reproducible")

    changes = rows(runs[0] / "历史结构裁决变化27字.tsv")
    if len(changes) != 27 or {x["汉字"] for x in changes} != set(decisions):
        raise ValueError("candidate delta does not equal accepted decision set")
    rewrites = {}
    for row in changes:
        char = row["汉字"]
        expected_after = [str(x) for x in decisions[char]["canonical_sequence"]]
        actual_after = row["候选拆分"].split(" ＋ ")
        if actual_after != expected_after:
            raise ValueError(f"candidate differs from accepted sequence for {char}")
        rewrites[char] = {
            "expected_before": row["当前拆分"].split(" ＋ "),
            "canonical_after": actual_after,
            "decision_at": decisions[char]["decision_at"],
            "reason": decisions[char]["reason"],
        }
    doc = {
        "schema_version": 1,
        "status": "accepted_guarded_structural_rules",
        "description": "27条逐字验收的历史结构裁决；精确前态守卫，禁止token子串传播。",
        "candidate_sha256": next(iter(candidate_hashes)),
        "delta_sha256": next(iter(delta_hashes)),
        "guarded_rewrites": rewrites,
        "excluded_encoding_layer_decisions": sorted(deferred),
        "sources": {
            str(INVENTORY.relative_to(ROOT)): common.sha256(INVENTORY),
            "candidate_runs": [x.name for x in runs],
        },
    }
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "rewrites": len(rewrites), "candidate_sha256": doc["candidate_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
