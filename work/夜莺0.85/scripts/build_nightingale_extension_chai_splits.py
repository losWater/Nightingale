#!/usr/bin/env python3
"""用夜莺现行根集与结构规则，为扩展字符生成隔离的 Chai 拆分实验。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "work" / "重开工程"
sys.path.insert(0, str(PROJECT / "scripts"))
import audit_manual_split_propagation as audit  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_extension_characters(path: Path) -> list[str]:
    """只读取旧文件第一列的字符；其余列（尤其旧码）永不解析。"""
    result: list[str] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        char = raw.split("\t", 1)[0].strip()
        if len(char) != 1:
            raise ValueError(f"扩展字符源第 {line_no} 行首列不是单字：{char!r}")
        if char not in seen:
            seen.add(char)
            result.append(char)
    return result


def chai_repertoire_characters(baseline: dict) -> set[str]:
    rows = json.loads(zlib.decompress(audit.REPERTOIRE_PATH.read_bytes()))
    chars = {chr(row["unicode"]) for row in rows if row.get("unicode") is not None}
    chars.update(str(x) for x in (baseline.get("data", {}).get("repertoire", {}) or {}))
    return chars


def write_tsv(path: Path, rows: list[tuple[str, list[str], str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["汉字", "最终规范拆分", "编码首根", "编码末根"])
        for char, seq, head, tail in rows:
            writer.writerow([char, " ＋ ".join(seq), head, tail])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--sample", help="仅生成所列字符的小样本，例如：愛臺灣")
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.output_root = args.output_root.resolve()

    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = args.output_root / now.strftime("%Y%m%d_%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=False)

    roots = yaml.safe_load(audit.ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(audit.RULES_PATH.read_text(encoding="utf-8"))
    structural = yaml.safe_load(audit.STRUCTURAL_OVERRIDES_PATH.read_text(encoding="utf-8"))
    frames = yaml.safe_load(audit.FRAME_RULES_PATH.read_text(encoding="utf-8"))
    legacy = yaml.safe_load(audit.LEGACY_STRUCTURAL_RULES_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(audit.BASELINE_PATH.read_text(encoding="utf-8"))
    base_chars, _ = audit.load_table()
    base_set = set(base_chars)

    source_chars = read_extension_characters(args.source)
    if args.sample:
        wanted = set(args.sample)
        source_chars = [char for char in source_chars if char in wanted]
        absent_from_source = sorted(wanted - set(source_chars))
        if absent_from_source:
            raise ValueError("样本字符不在扩展字符源中：" + " ".join(absent_from_source))
    extension = [char for char in source_chars if char not in base_set]
    repertoire = chai_repertoire_characters(baseline)
    available = [char for char in extension if char in repertoire]
    unavailable = [char for char in extension if char not in repertoire]

    by_name, labels = audit.repertoire_maps(baseline)
    config = audit.compile_config(
        baseline, roots, rules_doc.get("component_splits") or {}, by_name
    )
    # 必须连同正式 8105 字运行，保证所有逐字保护规则仍接受完整校验。
    raw = audit.invoke("EXTENSION_WITH_8105", config, base_chars + available, run_dir)
    normalization = audit.normalization_map(roots, by_name, labels)
    normalized = {
        char: [normalization.get(x, labels.get(x, x)) for x in raw.get(char, [])]
        for char in base_chars + available
    }
    normalized, structural_hits = audit.apply_propagating_structural_overrides(
        normalized, structural, roots
    )
    normalized, frame_hits = audit.apply_guarded_frame_rules(normalized, frames, roots)
    normalized, legacy_hits = audit.apply_guarded_legacy_structural_rules(
        normalized, legacy, roots
    )

    hosts = audit.canonical_host_map(roots)
    rows: list[tuple[str, list[str], str, str]] = []
    unresolved_roots: list[dict[str, object]] = []
    for char in available:
        seq = normalized.get(char, [])
        head = hosts.get(seq[0]) if seq else None
        tail = hosts.get(seq[-1]) if seq else None
        if not seq or head is None or tail is None:
            unresolved_roots.append({"汉字": char, "拆分": seq, "首根": head, "末根": tail})
            continue
        rows.append((char, seq, head, tail))

    output_tsv = run_dir / "扩展字规范拆分_候选.tsv"
    write_tsv(output_tsv, rows)
    (run_dir / "Chai字库缺字.txt").write_text("\n".join(unavailable) + ("\n" if unavailable else ""), encoding="utf-8")
    (run_dir / "未解析编码根.json").write_text(
        json.dumps(unresolved_roots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    inputs = [
        args.source, audit.ROOTS_PATH, audit.RULES_PATH, audit.STRUCTURAL_OVERRIDES_PATH,
        audit.FRAME_RULES_PATH, audit.LEGACY_STRUCTURAL_RULES_PATH,
        audit.NAME_ALIASES_PATH, audit.BASELINE_PATH, audit.RUNNER_PATH,
        Path(__file__),
    ]
    manifest = {
        "generated_at": now.isoformat(timespec="seconds"),
        "status": "isolated_candidate_not_for_release",
        "safety": {
            "release_files_written": False,
            "canonical_8105_files_written": False,
            "legacy_source_columns_used": ["first_character_column_only"],
        },
        "counts": {
            "source_unique": len(source_chars),
            "excluded_existing_8105": len(source_chars) - len(extension),
            "extension_requested": len(extension),
            "chai_available": len(available),
            "chai_unavailable": len(unavailable),
            "resolved": len(rows),
            "unresolved_roots": len(unresolved_roots),
        },
        "rule_hits": {
            "propagating": {k: [c for c in v if c in set(available)] for k, v in structural_hits.items()},
            "guarded_frames": {k: [c for c in v if c in set(available)] for k, v in frame_hits.items()},
            "guarded_legacy": [c for c in legacy_hits if c in set(available)],
        },
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "outputs": {
            output_tsv.name: sha256(output_tsv),
            "Chai字库缺字.txt": sha256(run_dir / "Chai字库缺字.txt"),
            "未解析编码根.json": sha256(run_dir / "未解析编码根.json"),
        },
    }
    (run_dir / "生成清单.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_dir": str(run_dir), **manifest["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
