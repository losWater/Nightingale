# -*- coding: utf-8 -*-
"""Build a non-authoritative 8105 candidate from 27 re-accepted structural decisions."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common
import audit_same_split_characters as same_split


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
INVENTORY = PROJECT / "02_规范拆分" / "历史序列覆写迁移盘点_待验收.yaml"
ROOTS = PROJECT / "01_根集" / "根集_待完整性复核.yaml"
RUN_ROOT = PROJECT / "05_退火实验" / "历史结构裁决候选表"


def load_table(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    order = [x["汉字"] for x in rows]
    if len(rows) != 8105 or len(set(order)) != 8105:
        raise ValueError(f"invalid 8105 table: {path}")
    return order, {x["汉字"]: x for x in rows}


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S_%f%z")
    run_dir.mkdir(parents=True, exist_ok=False)

    order, current = load_table(CURRENT)
    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    decisions = inventory.get("accepted_structural_decisions") or {}
    deferred = (inventory.get("deferred_encoding_layer_decisions") or {}).get("entries") or {}
    if len(decisions) != 27:
        raise ValueError(f"expected exactly 27 accepted structural decisions, got {len(decisions)}")
    overlap = set(decisions) & set(deferred)
    if overlap:
        raise ValueError(f"structural/encoding layer overlap: {sorted(overlap)}")
    bad_status = [c for c, s in decisions.items() if s.get("status") != "accepted_pending_candidate_build"]
    if bad_status:
        raise ValueError(f"decisions not ready for candidate build: {bad_status}")

    roots = yaml.safe_load(ROOTS.read_text(encoding="utf-8"))
    hosts = common.canonical_host_map(roots)
    candidate = {char: dict(row) for char, row in current.items()}
    changes: list[dict[str, str]] = []
    for char, spec in decisions.items():
        if char not in current:
            raise ValueError(f"accepted target absent from 8105: {char}")
        before = current[char]["最终规范拆分"].split(" ＋ ")
        after = [str(x) for x in spec.get("canonical_sequence") or []]
        if not after:
            raise ValueError(f"empty accepted sequence: {char}")
        unknown = [x for x in after if x not in hosts]
        if unknown:
            raise ValueError(f"accepted sequence uses unknown roots for {char}: {unknown}")
        if before == after:
            raise ValueError(f"accepted decision produces no change: {char}")
        head, tail = hosts[after[0]], hosts[after[-1]]
        candidate[char] = {
            "汉字": char,
            "最终规范拆分": " ＋ ".join(after),
            "编码首根": head,
            "编码末根": tail,
        }
        changes.append({
            "汉字": char,
            "当前拆分": " ＋ ".join(before),
            "候选拆分": " ＋ ".join(after),
            "候选首根": head,
            "候选末根": tail,
        })
    if len(changes) != 27 or {x["汉字"] for x in changes} != set(decisions):
        raise ValueError("candidate change-set mismatch")

    candidate_path = run_dir / "历史结构裁决候选8105.tsv"
    fields = ["汉字", "最终规范拆分", "编码首根", "编码末根"]
    write_rows(candidate_path, fields, [candidate[x] for x in order])
    check_order, check_rows = load_table(candidate_path)
    if check_order != order or set(check_rows) != set(current):
        raise ValueError("candidate glyph order/set changed")

    delta_path = run_dir / "历史结构裁决变化27字.tsv"
    delta_fields = ["汉字", "当前拆分", "候选拆分", "候选首根", "候选末根"]
    write_rows(delta_path, delta_fields, changes)

    collision = same_split.audit(
        current=candidate_path,
        previous=CURRENT,
        json_path=run_dir / "结构同拆候选检查.json",
        exact_tsv=run_dir / "结构同拆候选检查_候选组.tsv",
        skeleton_tsv=run_dir / "结构同拆候选检查_同首末骨架.tsv",
        md_path=run_dir / "结构同拆候选检查.md",
    )
    manifest = {
        "generated_at": now.isoformat(timespec="seconds"),
        "status": "candidate_only_not_authoritative",
        "glyphs": 8105,
        "accepted_structural_decisions": len(decisions),
        "encoding_layer_decisions_excluded": sorted(deferred),
        "inputs": {
            str(p.relative_to(ROOT)): common.sha256(p)
            for p in [CURRENT, INVENTORY, ROOTS, Path(__file__)]
        },
        "outputs": {
            candidate_path.name: common.sha256(candidate_path),
            delta_path.name: common.sha256(delta_path),
        },
        "structural_candidate_delta": collision["structural_candidate_delta"],
    }
    manifest_path = run_dir / "生成清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "run_dir": str(run_dir),
        "changes": len(changes),
        "candidate_sha256": manifest["outputs"][candidate_path.name],
        "delta_sha256": manifest["outputs"][delta_path.name],
        "same_split_delta": manifest["structural_candidate_delta"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
