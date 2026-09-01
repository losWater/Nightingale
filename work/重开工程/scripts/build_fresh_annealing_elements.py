# -*- coding: utf-8 -*-
"""Build fresh four-element annealing rows without any historical element asset."""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
READINGS = PROJECT / "03_字音频率" / "全新字音频率表_待核验.tsv"
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
OUT_DIR = PROJECT / "04_Chai输入"
ELEMENTS = OUT_DIR / "全新退火元素表_待核验.yaml"
CONFIG = OUT_DIR / "全新退火基础配置_待核验.yaml"
MANIFEST = OUT_DIR / "全新退火元素表_生成清单.json"


def apply_algebra(rules: list[dict], value: str) -> str:
    result = value
    for rule in rules:
        if rule.get("type") != "xform":
            raise ValueError(f"unsupported algebra rule type: {rule}")
        replacement = re.sub(r"\$(\d+)", r"\\g<\1>", str(rule["to"]))
        result = re.sub(str(rule["from"]), replacement, result)
    return result


def main() -> None:
    with READINGS.open("r", encoding="utf-8-sig", newline="") as f:
        reading_rows = list(csv.DictReader(f, delimiter="\t"))
    with CURRENT.open("r", encoding="utf-8-sig", newline="") as f:
        structure_rows = list(csv.DictReader(f, delimiter="\t"))
    structures = {x["汉字"]: x for x in structure_rows}
    if len(reading_rows) != 8454 or len(structures) != 8105:
        raise ValueError(f"unexpected fresh input counts: readings={len(reading_rows)} structures={len(structures)}")

    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    by_name, _ = common.repertoire_maps(baseline)
    algebra = baseline.get("algebra") or {}
    if not algebra.get("szm") or not algebra.get("mzm"):
        raise ValueError("baseline lacks szm/mzm algebra")

    # Fresh optimizer config: preserve only current sound mappings, then add current roots.
    cfg = yaml.safe_load(yaml.safe_dump(baseline, allow_unicode=True, sort_keys=False))
    old_mapping = cfg["form"]["mapping"]
    mapping = {str(k): v for k, v in old_mapping.items() if str(k).startswith(("szm-", "mzm-"))}
    mains = []
    for root in roots["roots"]:
        element = common.resolve(root, by_name)
        if element not in mains:
            mains.append(element)
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for i, element in enumerate(mains):
        mapping[element] = alphabet[i % len(alphabet)]
    for host_name, attached in roots["roots"].items():
        host = common.resolve(host_name, by_name)
        for name in attached or []:
            child = common.resolve(name, by_name)
            if child != host:
                mapping[child] = {"element": host}
    for host_name, anchored in (roots.get("anchors") or {}).items():
        host = common.resolve(host_name, by_name)
        for name in anchored or []:
            mapping[common.resolve(name, by_name)] = {"element": host}
    mapping["6"] = {"element": "5"}
    cfg["form"]["mapping"] = mapping
    cfg["form"]["alphabet"] = alphabet
    cfg["form"]["mapping_space"] = {}
    cfg["info"] = {
        "name": "夜莺0.8全新退火基础配置",
        "author": "nightingale",
        "version": "fresh-elements-pending-validation",
        "description": "从当前8105与Chai词典全新生成；不含历史简码、无理码或旧元素。",
    }

    items = []
    seen = set()
    for row in reading_rows:
        char, pinyin = row["汉字"], row["拼音"]
        key = (char, pinyin)
        if key in seen:
            raise ValueError(f"duplicate fresh reading key: {key}")
        seen.add(key)
        source = pinyin + "5"
        initial = "szm-" + apply_algebra(algebra["szm"], source)
        final = "mzm-" + apply_algebra(algebra["mzm"], source)
        structure = structures.get(char)
        if structure is None:
            raise ValueError(f"reading glyph absent from current 8105: {char}")
        head = common.resolve(structure["编码首根"], by_name)
        tail = common.resolve(structure["编码末根"], by_name)
        sequence = [initial, final, head, tail]
        unknown = [x for x in sequence if x not in mapping]
        if unknown:
            raise ValueError(f"unmapped fresh elements for {char}/{pinyin}: {unknown}")
        items.append({
            "词": char,
            "拼音": pinyin,
            "元素序列": [{"element": x, "index": 0} for x in sequence],
            "频率": int(row["频率"]),
        })
    if len(items) != len(reading_rows) or {x["词"] for x in items} != set(structures):
        raise ValueError("fresh element coverage mismatch")
    if any(len(x["元素序列"]) != 4 for x in items):
        raise ValueError("fresh element row length mismatch")

    ELEMENTS.write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    CONFIG.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    check = yaml.safe_load(ELEMENTS.read_text(encoding="utf-8"))
    if len(check) != len(items) or {(x["词"], x["拼音"]) for x in check} != seen:
        raise ValueError("written fresh element table validation failed")

    now = datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes")
    manifest = {
        "generated_at": now,
        "status": "fresh_annealing_elements_pending_validation",
        "glyphs": 8105,
        "reading_items": len(reading_rows),
        "element_rows": len(items),
        "zero_frequency_rows": sum(x["频率"] == 0 for x in items),
        "rows_with_short_code_metadata": sum("简码长度" in x for x in items),
        "inputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [READINGS, CURRENT, common.ROOTS_PATH, common.NAME_ALIASES_PATH, common.BASELINE_PATH, Path(__file__)]},
        "outputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [ELEMENTS, CONFIG]},
        "historical_assets_read": [],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
