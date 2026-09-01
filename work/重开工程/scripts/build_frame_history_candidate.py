# -*- coding: utf-8 -*-
"""Build a non-authoritative 8105 candidate restoring audited legacy frame semantics."""
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
AUDIT = PROJECT / "02_规范拆分" / "字架迁移审计.json"
LEGACY = ROOT / "夜莺B" / "work" / "最终规范拆分表_人工阅读.tsv"
ROOTS = PROJECT / "01_根集" / "根集_待完整性复核.yaml"
RUN_ROOT = PROJECT / "05_退火实验" / "字架历史语义候选表"


def load(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if len(rows) != 8105 or len({x["汉字"] for x in rows}) != 8105:
        raise ValueError(f"invalid 8105 table: {path}")
    return [x["汉字"] for x in rows], {x["汉字"]: x for x in rows}


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=False)
    order, current = load(CURRENT)
    old_order, legacy = load(LEGACY)
    if set(order) != set(old_order):
        raise ValueError("current and legacy glyph sets differ")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit["inputs"][str(CURRENT.relative_to(ROOT))] != common.sha256(CURRENT):
        raise ValueError("frame audit is stale for current canonical table")

    direct = {char for chars in audit["direct_hits"].values() for char in chars}
    nested = {x["汉字"] for x in audit["nested_structural_hits"]}
    frame_by_char = {}
    for kind, chars in audit["direct_hits"].items():
        for char in chars:
            frame_by_char[char] = kind
    for item in audit["nested_structural_hits"]:
        frame_by_char[item["汉字"]] = item["字架"]
    scope = direct | nested
    if len(direct) != 29 or len(nested) != 10 or len(scope) != 39:
        raise ValueError(f"unexpected audited frame scope: direct={len(direct)} nested={len(nested)} union={len(scope)}")

    roots = yaml.safe_load(ROOTS.read_text(encoding="utf-8"))
    hosts = common.canonical_host_map(roots)
    aliases = {"一": "横", "丨": "竖", "丿": "撇", "丶": "点", "㇕": "折"}

    def tokens(raw: str) -> list[str]:
        return raw.split(" ＋ ")

    def canon(seq: list[str]) -> list[str]:
        return [hosts.get(aliases.get(x, x), aliases.get(x, x)) for x in seq]

    def expand_to_current_roots(seq: list[str], stack: tuple[str, ...] = ()) -> list[str]:
        result = []
        for token in seq:
            normalized = aliases.get(token, token)
            if normalized in hosts:
                result.append(token)
                continue
            if token in stack:
                raise ValueError(f"cyclic non-root expansion in frame candidate: {' -> '.join(stack + (token,))}")
            row = current.get(token)
            if row is None:
                raise ValueError(f"frame candidate contains non-root absent from current 8105: {token}")
            child = tokens(row["最终规范拆分"])
            if child == [token]:
                raise ValueError(f"frame candidate non-root cannot be expanded: {token}")
            result.extend(expand_to_current_roots(child, stack + (token,)))
        return result

    def restore_frame_shape(char: str, seq: list[str]) -> list[str]:
        kind = frame_by_char.get(char)
        if kind == "辡":
            positions = [i for i, x in enumerate(seq) if x == "辛"]
            if len(positions) != 1:
                raise ValueError(f"expected one folded 辛 frame in {char}, got {positions}: {seq}")
            seq = list(seq); seq[positions[0]] = "辡"
        elif kind == "玨":
            positions = [i for i, x in enumerate(seq) if x == "王"]
            if len(positions) != 1:
                raise ValueError(f"expected one folded 王 frame in {char}, got {positions}: {seq}")
            seq = list(seq); seq[positions[0]] = "玨"
        return seq

    changed = []
    candidate = {char: dict(row) for char, row in current.items()}
    for char in sorted(scope):
        before = tokens(current[char]["最终规范拆分"])
        after = restore_frame_shape(char, expand_to_current_roots(tokens(legacy[char]["最终规范拆分"])))
        if canon(before) == canon(after):
            continue
        unknown = [x for x in after if aliases.get(x, x) not in hosts]
        if unknown:
            raise ValueError(f"expanded frame candidate {char} contains unknown roots: {unknown}")
        head, tail = canon(after)[0], canon(after)[-1]
        candidate[char] = {"汉字": char, "最终规范拆分": " ＋ ".join(after), "编码首根": head, "编码末根": tail}
        changed.append({"汉字": char, "当前拆分": " ＋ ".join(before), "候选拆分": " ＋ ".join(after), "候选首根": head, "候选末根": tail})
    if len(changed) != 37:
        raise ValueError(f"expected 37 semantic changes, got {len(changed)}")

    candidate_path = run_dir / "字架历史语义候选8105.tsv"
    with candidate_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["汉字", "最终规范拆分", "编码首根", "编码末根"], delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(candidate[x] for x in order)
    delta_path = run_dir / "字架历史语义变化37字.tsv"
    with delta_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["汉字", "当前拆分", "候选拆分", "候选首根", "候选末根"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(changed)

    collision = same_split.audit(
        current=candidate_path, previous=CURRENT,
        json_path=run_dir / "结构同拆候选检查.json",
        exact_tsv=run_dir / "结构同拆候选检查_候选组.tsv",
        skeleton_tsv=run_dir / "结构同拆候选检查_同首末骨架.tsv",
        md_path=run_dir / "结构同拆候选检查.md",
    )
    manifest = {
        "generated_at": now.isoformat(timespec="minutes"),
        "status": "candidate_only_not_authoritative",
        "audited_scope": len(scope), "semantic_changes": len(changed),
        "unchanged_equivalent": sorted(scope - {x["汉字"] for x in changed}),
        "inputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [CURRENT, AUDIT, LEGACY, ROOTS, Path(__file__)]},
        "outputs": {p.name: common.sha256(p) for p in run_dir.iterdir() if p.is_file()},
        "structural_candidate_delta": collision["structural_candidate_delta"],
    }
    (run_dir / "生成清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "scope": len(scope), "changes": len(changed), "unchanged": manifest["unchanged_equivalent"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
