# -*- coding: utf-8 -*-
"""Build the pure structural 8105-glyph split table from current inputs."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as audit
import audit_same_split_characters as same_split_audit


PROJECT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT / "02_规范拆分"
HISTORY = PROJECT / "99_历史参考"
RUN_ROOT = PROJECT / "05_退火实验" / "生成8105规范拆分表"
TSV = OUT_DIR / "最终规范拆分表_待核验.tsv"
TXT = OUT_DIR / "最终规范拆分表_待核验.txt"
HTML = OUT_DIR / "最终规范拆分表_待核验.html"
MANIFEST = OUT_DIR / "最终规范拆分表_生成清单.json"


def engine_fingerprint() -> dict:
    commit = audit.run_text(["git", "rev-parse", "HEAD"], audit.WEBCHAI)
    status = audit.run_text(["git", "status", "--short"], audit.WEBCHAI)
    diff = subprocess.run(
        ["git", "diff", "--binary"], cwd=audit.WEBCHAI,
        stdout=subprocess.PIPE, check=True,
    ).stdout
    return {
        "repository": str(audit.WEBCHAI),
        "commit": commit,
        "dirty": bool(status),
        "status": status.splitlines(),
        "diff_sha256": hashlib.sha256(diff).hexdigest(),
    }


def write_tsv(path: Path, rows: list[tuple[str, list[str], str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["汉字", "最终规范拆分", "编码首根", "编码末根"])
        for char, seq, head, tail in rows:
            writer.writerow([char, " ＋ ".join(seq), head, tail])


def write_html(path: Path, rows: list[tuple[str, list[str], str, str]], generated: str) -> None:
    body = []
    for char, seq, head, tail in rows:
        body.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(char), html.escape(" ＋ ".join(seq)),
                html.escape(head), html.escape(tail),
            )
        )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>夜莺 8105 字规范拆分表</title>
<style>body{{font-family:"Microsoft YaHei",sans-serif;margin:24px;color:#172033}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3df;padding:6px 9px;text-align:left}}
thead{{position:sticky;top:0;background:#eef3f8}}tr:nth-child(even){{background:#fafbfd}}</style></head>
<body><h1>夜莺 8105 字规范拆分表（待核验）</h1>
<p>生成时间：{html.escape(generated)}。仅含当前根集、结构基线与人工结构拆分；未应用无理码和编码层裁决。</p>
<table><thead><tr><th>汉字</th><th>最终规范拆分</th><th>编码首根</th><th>编码末根</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></body></html>"""
    path.write_text(document, encoding="utf-8")


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    stamp = now.strftime("%Y%m%d_%H%M%S%z")
    generated = now.isoformat(timespec="minutes")
    run_dir = RUN_ROOT / stamp
    run_dir.mkdir(parents=True, exist_ok=False)

    roots = yaml.safe_load(audit.ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(audit.RULES_PATH.read_text(encoding="utf-8"))
    structural_overrides = yaml.safe_load(audit.STRUCTURAL_OVERRIDES_PATH.read_text(encoding="utf-8"))
    frame_rules = yaml.safe_load(audit.FRAME_RULES_PATH.read_text(encoding="utf-8"))
    legacy_structural_rules = yaml.safe_load(
        audit.LEGACY_STRUCTURAL_RULES_PATH.read_text(encoding="utf-8")
    )
    rules = rules_doc.get("component_splits") or {}
    baseline = yaml.safe_load(audit.BASELINE_PATH.read_text(encoding="utf-8"))
    chars, _ = audit.load_table()
    by_name, labels = audit.repertoire_maps(baseline)
    exact_names = audit.normalization_map(roots, by_name, labels)
    hosts = audit.canonical_host_map(roots)
    config = audit.compile_config(baseline, roots, rules, by_name)
    raw = audit.invoke("CANONICAL_ALL", config, chars, run_dir)

    normalized = {
        char: [exact_names.get(x, labels.get(x, x)) for x in raw.get(char, [])]
        for char in chars
    }
    normalized, structural_hits = audit.apply_propagating_structural_overrides(
        normalized, structural_overrides, roots
    )
    normalized, frame_hits = audit.apply_guarded_frame_rules(normalized, frame_rules, roots)
    normalized, legacy_structural_hits = audit.apply_guarded_legacy_structural_rules(
        normalized, legacy_structural_rules, roots
    )

    rows: list[tuple[str, list[str], str, str]] = []
    missing: list[str] = []
    for char in chars:
        seq = normalized.get(char, [])
        if not seq:
            missing.append(char)
            continue
        head = hosts.get(seq[0])
        tail = hosts.get(seq[-1])
        if head is None or tail is None:
            raise ValueError(f"unresolved coding root for {char}: {seq[0]} / {seq[-1]}")
        rows.append((char, seq, head, tail))
    if missing:
        raise ValueError("empty Chai splits: " + " ".join(missing))
    if len(rows) != 8105 or len({x[0] for x in rows}) != 8105 or {x[0] for x in rows} != set(chars):
        raise ValueError("8105 output cardinality or glyph set mismatch")

    staged_tsv = run_dir / "最终规范拆分表_待核验.tsv"
    staged_txt = run_dir / "最终规范拆分表_待核验.txt"
    staged_html = run_dir / "最终规范拆分表_待核验.html"
    write_tsv(staged_tsv, rows)
    shutil.copy2(staged_tsv, staged_txt)
    write_html(staged_html, rows, generated)
    with staged_tsv.open("r", encoding="utf-8-sig", newline="") as f:
        if sum(1 for _ in csv.reader(f, delimiter="\t")) != 8106:
            raise ValueError("TSV row-count validation failed")
    if staged_html.read_text(encoding="utf-8").count("<tr>") != 8106:
        raise ValueError("HTML row-count validation failed")

    archive = HISTORY / f"历次8105表_{stamp}"
    archive.mkdir(parents=True, exist_ok=False)
    for old in (TSV, TXT, HTML):
        if old.exists():
            shutil.move(str(old), str(archive / old.name))
    shutil.copy2(staged_tsv, TSV)
    shutil.copy2(staged_txt, TXT)
    shutil.copy2(staged_html, HTML)

    previous_tsv = archive / TSV.name
    same_split_audit.audit(
        current=TSV,
        previous=previous_tsv if previous_tsv.exists() else None,
    )

    inputs = [
        audit.ROOTS_PATH, audit.RULES_PATH, audit.STRUCTURAL_OVERRIDES_PATH, audit.FRAME_RULES_PATH,
        audit.LEGACY_STRUCTURAL_RULES_PATH, audit.NAME_ALIASES_PATH,
        audit.BASELINE_PATH, audit.RUNNER_PATH, Path(__file__), Path(same_split_audit.__file__),
    ]
    audit_outputs = [
        same_split_audit.DEFAULT_JSON,
        same_split_audit.DEFAULT_EXACT_TSV,
        same_split_audit.DEFAULT_SKELETON_TSV,
        same_split_audit.DEFAULT_MD,
    ]
    manifest = {
        "generated_at": generated,
        "status": "pending_validation",
        "glyphs": 8105,
        "rules": len(rules),
        "run_dir": str(run_dir),
        "archived_previous_table": str(archive),
        "inputs": {str(p.relative_to(audit.ROOT)): audit.sha256(p) for p in inputs},
        "outputs": {
            str(p.relative_to(audit.ROOT)): audit.sha256(p)
            for p in [TSV, TXT, HTML, *audit_outputs]
        },
        "engine": engine_fingerprint(),
        "known_pending_rule_issues": ["RULE-0001", "RULE-0002"],
        "structural_override_hits": structural_hits,
        "frame_rule_hits": frame_hits,
        "legacy_structural_rule_hits": legacy_structural_hits,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"glyphs": 8105, "rules": len(rules), "archive": str(archive)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
