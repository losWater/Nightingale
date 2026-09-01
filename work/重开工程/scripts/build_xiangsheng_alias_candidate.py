# -*- coding: utf-8 -*-
"""Build a non-authoritative 8105 counterfactual for 襄省 == Chai 囊下."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as audit
import audit_same_split_characters as same_split


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
RUN_ROOT = PROJECT / "05_退火实验" / "襄省根名映射候选表"
EXPECTED = {
    "囊": ["囊字头", "襄省"],
    "囔": ["口", "囊字头", "襄省"],
    "攮": ["扌", "囊字头", "襄省"],
    "馕": ["饣", "囊字头", "襄省"],
    "齉": ["自", "田", "丌", "囊字头", "襄省"],
}


def load(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    order = [x["汉字"] for x in rows]
    if len(rows) != 8105 or len(set(order)) != 8105:
        raise ValueError(f"invalid 8105 table: {path}")
    return order, {x["汉字"]: x for x in rows}


def write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S_%f%z")
    run_dir.mkdir(parents=True, exist_ok=False)
    order, current = load(CURRENT)

    roots = yaml.safe_load(audit.ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(audit.RULES_PATH.read_text(encoding="utf-8"))
    structural = yaml.safe_load(audit.STRUCTURAL_OVERRIDES_PATH.read_text(encoding="utf-8"))
    frames = yaml.safe_load(audit.FRAME_RULES_PATH.read_text(encoding="utf-8"))
    historical = yaml.safe_load(audit.LEGACY_STRUCTURAL_RULES_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(audit.BASELINE_PATH.read_text(encoding="utf-8"))
    chars, _ = audit.load_table()
    by_name, labels = audit.repertoire_maps(baseline)
    if by_name.get("囊下") != "\ue83c":
        raise ValueError(f"unexpected Chai 囊下 identity: {by_name.get('囊下')!r}")
    cfg = audit.compile_config(baseline, roots, rules_doc.get("component_splits") or {}, by_name)
    mapping = cfg["form"]["mapping"]
    host = audit.resolve("衣", by_name)
    if mapping.get("襄省") != {"element": host}:
        raise ValueError(f"expected unresolved literal 襄省 mapping, got {mapping.get('襄省')!r}")
    del mapping["襄省"]
    mapping["\ue83c"] = {"element": host}

    raw = audit.invoke("XIANGSHENG_ALIAS_CANDIDATE", cfg, chars, run_dir)
    exact = audit.normalization_map(roots, by_name, labels)
    exact["\ue83c"] = "襄省"
    normalized = {c: [exact.get(x, labels.get(x, x)) for x in raw.get(c, [])] for c in chars}
    normalized, structural_hits = audit.apply_propagating_structural_overrides(normalized, structural, roots)
    normalized, frame_hits = audit.apply_guarded_frame_rules(normalized, frames, roots)
    normalized, historical_hits = audit.apply_guarded_legacy_structural_rules(normalized, historical, roots)

    hosts = audit.canonical_host_map(roots)
    candidate: dict[str, dict[str, str]] = {}
    for char in chars:
        seq = normalized.get(char) or []
        if not seq or seq[0] not in hosts or seq[-1] not in hosts:
            raise ValueError(f"invalid candidate sequence for {char}: {seq}")
        candidate[char] = {"汉字": char, "最终规范拆分": " ＋ ".join(seq), "编码首根": hosts[seq[0]], "编码末根": hosts[seq[-1]]}
    if len(candidate) != 8105 or set(candidate) != set(order):
        raise ValueError("candidate glyph set mismatch")

    changed = []
    for char in order:
        if candidate[char]["最终规范拆分"] == current[char]["最终规范拆分"]:
            continue
        changed.append({"汉字": char, "当前拆分": current[char]["最终规范拆分"], "候选拆分": candidate[char]["最终规范拆分"]})
    if {x["汉字"] for x in changed} != set(EXPECTED) or len(changed) != 5:
        raise ValueError(f"unexpected alias change set: {[x['汉字'] for x in changed]}")
    for char, expected in EXPECTED.items():
        if candidate[char]["最终规范拆分"].split(" ＋ ") != expected:
            raise ValueError(f"unexpected candidate split for {char}: {candidate[char]['最终规范拆分']}")

    candidate_path = run_dir / "襄省根名映射候选8105.tsv"
    fields = ["汉字", "最终规范拆分", "编码首根", "编码末根"]
    write(candidate_path, fields, [candidate[x] for x in order])
    load(candidate_path)
    delta_path = run_dir / "襄省根名映射变化5字.tsv"
    write(delta_path, ["汉字", "当前拆分", "候选拆分"], changed)
    collision = same_split.audit(
        current=candidate_path, previous=CURRENT,
        json_path=run_dir / "结构同拆候选检查.json",
        exact_tsv=run_dir / "结构同拆候选检查_候选组.tsv",
        skeleton_tsv=run_dir / "结构同拆候选检查_同首末骨架.tsv",
        md_path=run_dir / "结构同拆候选检查.md",
    )
    manifest = {
        "generated_at": now.isoformat(timespec="seconds"),
        "status": "candidate_only_not_authoritative",
        "glyphs": 8105,
        "changes": 5,
        "structural_override_hits": structural_hits,
        "frame_rule_hit_count": sum(map(len, frame_hits.values())),
        "historical_rule_hit_count": len(historical_hits),
        "inputs": {str(p.relative_to(ROOT)): audit.sha256(p) for p in [CURRENT, audit.ROOTS_PATH, audit.RULES_PATH, audit.STRUCTURAL_OVERRIDES_PATH, audit.FRAME_RULES_PATH, audit.LEGACY_STRUCTURAL_RULES_PATH, audit.BASELINE_PATH, audit.RUNNER_PATH, Path(__file__)]},
        "outputs": {candidate_path.name: audit.sha256(candidate_path), delta_path.name: audit.sha256(delta_path)},
        "structural_candidate_delta": collision["structural_candidate_delta"],
    }
    (run_dir / "生成清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "changes": 5, "candidate_sha256": manifest["outputs"][candidate_path.name], "delta_sha256": manifest["outputs"][delta_path.name], "same_split_delta": manifest["structural_candidate_delta"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
