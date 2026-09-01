# -*- coding: utf-8 -*-
"""Audit propagation of manual structural split rules with Chai counterfactuals.

Runs AUTO, one ONLY-P run per rule, and ALL. It never edits authoritative
inputs. Reports are written to 02_规范拆分 and complete run artifacts are kept
under 05_退火实验/人工拆分传播核验.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import zlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
ROOTS_PATH = PROJECT / "01_根集" / "根集_待完整性复核.yaml"
RULES_PATH = PROJECT / "02_规范拆分" / "人工规范拆分_待验收.yaml"
STRUCTURAL_OVERRIDES_PATH = PROJECT / "02_规范拆分" / "传播式整字结构覆写_待验收.yaml"
FRAME_RULES_PATH = PROJECT / "02_规范拆分" / "正式字架规则.yaml"
LEGACY_STRUCTURAL_RULES_PATH = PROJECT / "02_规范拆分" / "正式历史结构裁决规则.yaml"
NAME_ALIASES_PATH = PROJECT / "02_规范拆分" / "Chai部件名称别名.yaml"
TABLE_PATH = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
BASELINE_PATH = PROJECT / "04_Chai输入" / "结构分析基线_待审计.yaml"
RUNNER_PATH = PROJECT / "scripts" / "chai_split_runner.ts"
WEBCHAI = ROOT / "repos" / "webchai"
REPERTOIRE_PATH = WEBCHAI / "packages" / "hanzi-chai" / "src" / "data" / "repertoire.json.deflate"
OUT_DIR = PROJECT / "02_规范拆分"
RUN_ROOT = PROJECT / "05_退火实验" / "人工拆分传播核验"
STROKES = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}
KEYS = "abcdefghijklmnopqrstuvwxyz"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run_text(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
    cp = subprocess.run(args, cwd=cwd, check=check, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return cp.stdout.strip()


def load_table() -> tuple[list[str], dict[str, list[str]]]:
    chars: list[str] = []
    expected: dict[str, list[str]] = {}
    with TABLE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"汉字", "最终规范拆分", "编码首根", "编码末根"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"8105 table missing columns: {sorted(required)}")
        for row in reader:
            char = row["汉字"].strip()
            seq = [x.strip() for x in row["最终规范拆分"].split("＋") if x.strip()]
            chars.append(char)
            expected[char] = seq
    if len(chars) != 8105 or len(set(chars)) != 8105:
        raise ValueError(f"expected 8105 unique glyphs, got rows={len(chars)} unique={len(set(chars))}")
    return chars, expected


def repertoire_maps(baseline: dict) -> tuple[dict[str, str], dict[str, str]]:
    rows = json.loads(zlib.decompress(REPERTOIRE_PATH.read_bytes()))
    by_name: dict[str, str] = {}
    labels: dict[str, str] = {}
    for row in rows:
        if row.get("unicode") is None:
            continue
        char = chr(row["unicode"])
        if row.get("name"):
            by_name[row["name"]] = char
            labels[char] = row["name"]
    for char, row in (baseline.get("data", {}).get("repertoire", {}) or {}).items():
        name = row.get("name") if isinstance(row, dict) else None
        if name:
            by_name[str(name)] = str(char)
            labels[str(char)] = str(name)
    return by_name, labels


def resolve(value: object, by_name: dict[str, str]) -> str:
    text = str(value)
    aliases_doc = yaml.safe_load(NAME_ALIASES_PATH.read_text(encoding="utf-8"))
    if aliases_doc.get("status") != "accepted_repertoire_name_aliases":
        raise ValueError("Chai repertoire name aliases are not accepted")
    spec = (aliases_doc.get("aliases") or {}).get(text)
    if spec:
        chai_name = str(spec["chai_name"])
        actual = by_name.get(chai_name)
        if actual is None:
            raise ValueError(f"Chai repertoire alias target absent: {text} -> {chai_name}")
        expected = str(spec["expected_glyph_id"]).removeprefix("U+")
        if len(actual) != 1 or f"{ord(actual):04X}" != expected.upper():
            raise ValueError(f"Chai repertoire alias identity changed: {text} -> {actual!r}")
        return actual
    return STROKES.get(text, by_name.get(text, text))


def compile_config(baseline: dict, roots: dict, rules: dict[str, list[str]], by_name: dict[str, str]) -> dict:
    # Round-trip through YAML to make a deep copy without importing legacy code.
    cfg = yaml.safe_load(yaml.safe_dump(baseline, allow_unicode=True, sort_keys=False))
    mapping: dict[str, object] = {}
    mains: list[str] = []
    for root in roots["roots"]:
        item = resolve(root, by_name)
        if item not in mains:
            mains.append(item)
    for i, item in enumerate(mains):
        mapping[item] = KEYS[i % len(KEYS)]
    for root, attached in roots["roots"].items():
        host = resolve(root, by_name)
        for item in attached or []:
            child = resolve(item, by_name)
            if child != host:
                mapping[child] = {"element": host}
    for root, anchored in (roots.get("anchors") or {}).items():
        host = resolve(root, by_name)
        for item in anchored or []:
            mapping[resolve(item, by_name)] = {"element": host}
    mapping["6"] = {"element": "5"}
    cfg.setdefault("form", {})["mapping"] = mapping
    cfg["form"]["mapping_space"] = {}
    cfg["form"]["alphabet"] = KEYS
    cfg.setdefault("analysis", {})["customize"] = {
        resolve(part, by_name): [resolve(x, by_name) for x in split]
        for part, split in rules.items()
    }
    cfg["analysis"]["dynamic_customize"] = {}
    cfg["info"] = {
        "name": "夜莺0.8人工拆分传播核验",
        "author": "nightingale",
        "version": "audit-0001",
        "description": "generated counterfactual; not a release config",
    }
    return cfg


def normalization_map(roots: dict, by_name: dict[str, str], labels: dict[str, str]) -> dict[str, str]:
    result = {v: k for k, v in STROKES.items()}
    result["6"] = "折"
    # The full split column preserves the concrete root shape (亦、㐅、门…),
    # while host-root folding belongs only to the separate head/tail coding
    # columns. Folding attachments here would create thousands of false diffs.
    for root in roots["roots"]:
        result[resolve(root, by_name)] = str(root)
    for _, attached in roots["roots"].items():
        for item in attached or []:
            result[resolve(item, by_name)] = str(item)
    for _, anchored in (roots.get("anchors") or {}).items():
        for item in anchored or []:
            result[resolve(item, by_name)] = str(item)
    for char, name in labels.items():
        result.setdefault(char, name)
    return result


def canonical_host_map(roots: dict) -> dict[str, str]:
    """Fold visible root shapes to coding roots for equivalence checks only."""
    result = {name: name for name in STROKES}
    for root, attached in roots["roots"].items():
        result[str(root)] = str(root)
        for item in attached or []:
            result[str(item)] = str(root)
    for _, anchored in (roots.get("anchors") or {}).items():
        for item in anchored or []:
            result[str(item)] = str(item)
    return result


def apply_propagating_structural_overrides(
    rows: dict[str, list[str]], overrides_doc: dict, roots: dict
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Apply validated structural subsequence rewrites and return hit glyphs."""
    output = {char: list(seq) for char, seq in rows.items()}
    hits: dict[str, list[str]] = {}
    known = set(canonical_host_map(roots))
    for component, spec in (overrides_doc.get("propagating_structural_overrides") or {}).items():
        old = [str(x) for x in spec.get("chai_sequence") or []]
        new = [str(x) for x in spec.get("canonical_sequence") or []]
        if not old or not new:
            raise ValueError(f"empty structural override: {component}")
        unknown = [x for x in new if x not in known]
        if unknown:
            raise ValueError(f"structural override {component} uses unknown roots: {unknown}")
        changed = []
        for char, seq in output.items():
            positions = [i for i in range(len(seq) - len(old) + 1) if seq[i:i + len(old)] == old]
            if len(positions) > 1 and any(b < a + len(old) for a, b in zip(positions, positions[1:])):
                raise ValueError(f"overlapping structural override matches: {component} in {char}")
            if not positions:
                continue
            for i in reversed(positions):
                seq = seq[:i] + new + seq[i + len(old):]
            output[char] = seq
            changed.append(char)
        direct = str(spec.get("expected_direct_glyph") or component)
        if direct not in changed:
            raise ValueError(f"structural override {component} did not hit direct glyph {direct}")
        hits[str(component)] = changed
    return output, hits


def apply_guarded_frame_rules(
    rows: dict[str, list[str]], frame_doc: dict, roots: dict
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Apply accepted per-glyph frame rewrites; never search token subsequences."""
    if frame_doc.get("status") != "accepted_guarded_structural_rules":
        raise ValueError("formal frame rules are not in accepted status")
    output = {char: list(seq) for char, seq in rows.items()}
    known = set(canonical_host_map(roots))
    hits: dict[str, list[str]] = {}
    for char, spec in (frame_doc.get("guarded_rewrites") or {}).items():
        if char not in output:
            raise ValueError(f"formal frame target absent from glyph set: {char}")
        before = [str(x) for x in spec.get("expected_before") or []]
        after = [str(x) for x in spec.get("canonical_after") or []]
        if not before or not after:
            raise ValueError(f"empty formal frame rewrite: {char}")
        if output[char] != before:
            raise ValueError(f"formal frame guard mismatch for {char}: expected {before}, got {output[char]}")
        unknown = [x for x in after if x not in known]
        if unknown:
            raise ValueError(f"formal frame rewrite {char} uses unknown roots: {unknown}")
        output[char] = after
        hits.setdefault(str(spec.get("frame")), []).append(str(char))
    if sum(map(len, hits.values())) != 37:
        raise ValueError(f"formal frame rewrite count mismatch: {sum(map(len, hits.values()))}")
    for char in frame_doc.get("unchanged_equivalent") or []:
        if char not in output:
            raise ValueError(f"unchanged frame-equivalent glyph absent: {char}")
    for char in frame_doc.get("complete_root_precedence") or []:
        if output.get(char) != [char]:
            raise ValueError(f"complete-root precedence lost for {char}: {output.get(char)}")
    return output, hits


def apply_guarded_legacy_structural_rules(
    rows: dict[str, list[str]], rule_doc: dict, roots: dict
) -> tuple[dict[str, list[str]], list[str]]:
    """Apply the 27 accepted per-glyph historical structural rewrites."""
    if rule_doc.get("status") != "accepted_guarded_structural_rules":
        raise ValueError("formal historical structural rules are not accepted")
    rewrites = rule_doc.get("guarded_rewrites") or {}
    if len(rewrites) != 27:
        raise ValueError(f"formal historical structural rewrite count mismatch: {len(rewrites)}")
    excluded = set(rule_doc.get("excluded_encoding_layer_decisions") or [])
    overlap = set(rewrites) & excluded
    if overlap:
        raise ValueError(f"formal structural rules contain encoding-layer targets: {sorted(overlap)}")
    output = {char: list(seq) for char, seq in rows.items()}
    known = set(canonical_host_map(roots))
    hits: list[str] = []
    for char, spec in rewrites.items():
        if char not in output:
            raise ValueError(f"formal historical structural target absent: {char}")
        before = [str(x) for x in spec.get("expected_before") or []]
        after = [str(x) for x in spec.get("canonical_after") or []]
        if not before or not after:
            raise ValueError(f"empty formal historical structural rewrite: {char}")
        if output[char] != before:
            raise ValueError(
                f"formal historical structural guard mismatch for {char}: "
                f"expected {before}, got {output[char]}"
            )
        unknown = [x for x in after if x not in known]
        if unknown:
            raise ValueError(f"formal historical structural rewrite {char} uses unknown roots: {unknown}")
        output[char] = after
        hits.append(str(char))
    if len(hits) != 27 or len(set(hits)) != 27:
        raise ValueError("formal historical structural rules did not hit exactly 27 unique glyphs")
    return output, hits


def invoke(label: str, cfg: dict, charset: list[str], run_dir: Path) -> dict[str, list[str]]:
    safe = label.replace("/", "_").replace("\\", "_")
    cfg_path = run_dir / f"{safe}.yaml"
    charset_path = run_dir / f"{safe}.charset.txt"
    out_path = run_dir / f"{safe}.json"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    charset_path.write_text("\n".join(charset) + "\n", encoding="utf-8")
    cp = subprocess.run(
        ["bun", str(RUNNER_PATH), str(cfg_path), str(charset_path), str(out_path)],
        cwd=ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    (run_dir / f"{safe}.stdout.txt").write_text(cp.stdout, encoding="utf-8")
    (run_dir / f"{safe}.stderr.txt").write_text(cp.stderr, encoding="utf-8")
    if cp.returncode:
        raise RuntimeError(f"Chai run {label} failed ({cp.returncode}): {cp.stderr.strip()}")
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    if payload["requested"] != len(charset) or len(payload["rows"]) != len(set(charset)):
        raise ValueError(f"Chai run {label} incomplete: requested={payload['requested']} rows={len(payload['rows'])}")
    return payload["rows"]


def main() -> int:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=False)
    roots_doc = yaml.safe_load(ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(BASELINE_PATH.read_text(encoding="utf-8"))
    structural_overrides = yaml.safe_load(STRUCTURAL_OVERRIDES_PATH.read_text(encoding="utf-8"))
    rules: dict[str, list[str]] = rules_doc.get("component_splits") or {}
    chars, expected = load_table()
    by_name, labels = repertoire_maps(baseline)
    norm = normalization_map(roots_doc, by_name, labels)
    hosts = canonical_host_map(roots_doc)

    resolved_parts: dict[str, str] = {}
    for part, split in rules.items():
        rp = resolve(part, by_name)
        if rp not in by_name.values() and len(rp) != 1:
            raise ValueError(f"unresolved rule left side: {part}")
        for item in split:
            ri = resolve(item, by_name)
            if ri not in by_name.values() and len(ri) != 1 and ri not in set(STROKES.values()):
                raise ValueError(f"unresolved rule element: {part} -> {item}")
        resolved_parts[part] = rp
    audit_charset = list(dict.fromkeys([*chars, *resolved_parts.values()]))

    auto_raw = invoke("AUTO", compile_config(baseline, roots_doc, {}, by_name), audit_charset, run_dir)
    all_raw = invoke("ALL", compile_config(baseline, roots_doc, rules, by_name), audit_charset, run_dir)
    only_raw: dict[str, dict[str, list[str]]] = {}
    for index, (part, split) in enumerate(rules.items(), 1):
        print(f"[{index:02d}/{len(rules):02d}] ONLY {part}", flush=True)
        only_raw[part] = invoke(f"ONLY_{index:02d}_{part}", compile_config(baseline, roots_doc, {part: split}, by_name), audit_charset, run_dir)

    def normalized(rows: dict[str, list[str]]) -> dict[str, list[str]]:
        return {char: [norm.get(x, labels.get(x, x)) for x in seq] for char, seq in rows.items()}

    auto = normalized(auto_raw)
    all_rows = normalized(all_raw)
    only = {part: normalized(rows) for part, rows in only_raw.items()}
    auto, structural_hits = apply_propagating_structural_overrides(auto, structural_overrides, roots_doc)
    all_rows, _ = apply_propagating_structural_overrides(all_rows, structural_overrides, roots_doc)
    only = {part: apply_propagating_structural_overrides(rows, structural_overrides, roots_doc)[0] for part, rows in only.items()}
    baseline_mismatches = [c for c in chars if all_rows.get(c) != expected[c]]

    detail: list[dict] = []
    summaries: list[dict] = []
    for index, (part, declared) in enumerate(rules.items(), 1):
        pchar = resolved_parts[part]
        one = only[part]
        hits = [c for c in chars if one.get(c) != auto.get(c)]
        interactions = [c for c in chars if c in hits and all_rows.get(c) != one.get(c)]
        direct_changed = one.get(pchar) != auto.get(pchar)
        state = "ok"
        if not hits and not direct_changed:
            auto_canonical = [hosts.get(x, x) for x in auto.get(pchar, [])]
            declared_canonical = [hosts.get(x, x) for x in declared]
            state = "auto_satisfies" if auto_canonical == declared_canonical else "ineffective"
        elif interactions:
            state = "interaction"
        summaries.append({
            "index": index, "part": part, "declared": declared, "state": state,
            "auto_direct": auto.get(pchar, []), "only_direct": one.get(pchar, []),
            "all_direct": all_rows.get(pchar, []), "hit_count": len(hits),
            "interaction_count": len(interactions), "hits": hits, "interactions": interactions,
        })
        for char in sorted(set(hits) | set(interactions)):
            detail.append({
                "规则": part, "声明拆分": " ＋ ".join(declared), "字": char,
                "AUTO": " ＋ ".join(auto.get(char, [])),
                "ONLY-P": " ＋ ".join(one.get(char, [])),
                "ALL": " ＋ ".join(all_rows.get(char, [])),
                "是否交互": "是" if char in interactions else "否",
            })

    commit = run_text(["git", "rev-parse", "HEAD"], WEBCHAI)
    status = run_text(["git", "status", "--short"], WEBCHAI)
    diff = subprocess.run(["git", "diff", "--binary"], cwd=WEBCHAI, stdout=subprocess.PIPE, check=True).stdout
    metadata = {
        "run_time": now.isoformat(timespec="minutes"),
        "run_dir": str(run_dir),
        "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in [ROOTS_PATH, RULES_PATH, STRUCTURAL_OVERRIDES_PATH, NAME_ALIASES_PATH, TABLE_PATH, BASELINE_PATH, RUNNER_PATH, Path(__file__)]},
        "engine": {"repository": str(WEBCHAI), "commit": commit, "dirty": bool(status), "status": status.splitlines(), "diff_sha256": hashlib.sha256(diff).hexdigest()},
        "counts": {"glyphs": len(chars), "rules": len(rules), "runs": len(rules) + 2, "baseline_mismatches": len(baseline_mismatches)},
    }
    payload = {"metadata": metadata, "rules": summaries, "structural_override_hits": structural_hits, "baseline_mismatches": [{"字": c, "当前8105": expected[c], "ALL重跑": all_rows.get(c, [])} for c in baseline_mismatches]}
    (OUT_DIR / "人工拆分传播核验.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with (OUT_DIR / "人工拆分传播核验.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["规则", "声明拆分", "字", "AUTO", "ONLY-P", "ALL", "是否交互"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(detail)
    with (OUT_DIR / "人工拆分传播核验_基线差异.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["字", "当前8105", "ALL重跑"])
        for c in baseline_mismatches:
            writer.writerow([c, " ＋ ".join(expected[c]), " ＋ ".join(all_rows.get(c, []))])

    ineffective = [x for x in summaries if x["state"] == "ineffective"]
    automatic = [x for x in summaries if x["state"] == "auto_satisfies"]
    interacting = [x for x in summaries if x["interaction_count"]]
    md = [
        "# 人工拆分传播核验", "", f"- 运行时间：{metadata['run_time']}",
        f"- 字集：{len(chars)} 个不重复字形", f"- 人工规则：{len(rules)} 条",
        f"- 反事实运行：{len(rules)+2} 次", f"- 引擎提交：`{commit}`",
        f"- 引擎工作区：{'dirty（已记录 diff 哈希）' if status else 'clean'}",
        f"- ALL 与当前 8105 表不一致：{len(baseline_mismatches)} 字", "",
        "## 规则总览", "", "|规则|状态|命中字|交互字|AUTO直接结果|ONLY-P直接结果|", "|---|---:|---:|---:|---|---|",
    ]
    for x in summaries:
        md.append(f"|{x['part']}|{x['state']}|{x['hit_count']}|{x['interaction_count']}|{' ＋ '.join(x['auto_direct']) or '—'}|{' ＋ '.join(x['only_direct']) or '—'}|")
    md += ["", "## 必须人工检查", "", f"- 无效／未落实规则：{'、'.join(x['part'] for x in ineffective) or '无'}", f"- 自动已满足的保护规则：{'、'.join(x['part'] for x in automatic) or '无'}", f"- 存在规则交互：{'、'.join(x['part'] for x in interacting) or '无'}"]
    if baseline_mismatches:
        md += ["", "## 当前基线未复现", "", "ALL 重跑与迁移来的 8105 表存在差异；在差异原因查清前，不能把本报告中的 ALL 当成新的规范拆分表。", "", "前 50 项："]
        for c in baseline_mismatches[:50]:
            md.append(f"- {c}：当前 `{' ＋ '.join(expected[c])}`；重跑 `{' ＋ '.join(all_rows.get(c, []))}`")
    (OUT_DIR / "人工拆分传播核验.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(metadata["counts"], ensure_ascii=False))
    # Findings are expected audit results, not a crash. Non-zero flags an unclean audit.
    return 2 if ineffective or interacting or baseline_mismatches else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AUDIT FAILED: {exc}", file=sys.stderr)
        raise
