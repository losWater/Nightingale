# -*- coding: utf-8 -*-
"""Verify sequential split-fix persistence from saved experiment artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


EXPECTED_WO = ["撇", "横", "折", "横", "戈"]
EXPECTED_HU = ["卜", "厂", "匕"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path: Path) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if len(rows) != 8105 or len({r["汉字"] for r in rows}) != 8105:
        raise ValueError(f"not an 8105 unique-glyph table: {path}")
    return {r["汉字"]: [x.strip() for x in r["最终规范拆分"].split("＋")] for r in rows}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", type=Path)
    args = ap.parse_args()
    exp = args.experiment.resolve()
    a_path = exp / "A_修复我" / "最终规范拆分表_待核验.tsv"
    b_path = exp / "B_再修虎字头" / "最终规范拆分表_待核验.tsv"
    r_path = exp / "C_最终复现" / "最终规范拆分表_待核验.tsv"
    a, b, reproduced = table(a_path), table(b_path), table(r_path)
    if a.get("我") != EXPECTED_WO:
        raise ValueError(f"A did not fix 我: {a.get('我')}")
    if b.get("我") != EXPECTED_WO or reproduced.get("我") != EXPECTED_WO:
        raise ValueError("我 regressed after the second fix or final regeneration")
    changed_ab = sorted(c for c in a if a[c] != b[c])
    if not changed_ab:
        raise ValueError("the 虍 fix did not propagate to any of the 8105 glyphs")
    if digest(b_path) != digest(r_path):
        raise ValueError("final regeneration is not byte-identical to B")
    audit_payload = json.loads((exp / "B_再修虎字头" / "人工拆分传播核验.json").read_text(encoding="utf-8"))
    hu = next((x for x in audit_payload["rules"] if x["part"] == "虍"), None)
    if hu is None or hu["state"] != "ok" or hu["only_direct"] != EXPECTED_HU or hu["hit_count"] == 0:
        raise ValueError(f"虍 direct/propagation verification failed: {hu}")
    result = {
        "status": "passed",
        "A_我": a["我"],
        "B_我": b["我"],
        "B_虍_direct": hu["only_direct"],
        "B_虍_hit_count": hu["hit_count"],
        "A_to_B_changed_count": len(changed_ab),
        "A_to_B_changed_glyphs": changed_ab,
        "B_tsv_sha256": digest(b_path),
        "reproduced_tsv_sha256": digest(r_path),
    }
    (exp / "验收结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
