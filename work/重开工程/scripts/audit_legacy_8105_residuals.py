# -*- coding: utf-8 -*-
"""Read-only classification of residual differences against the legacy 8105 table."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
LEGACY = ROOT / "夜莺B" / "work" / "最终规范拆分表_人工阅读.tsv"
ROOTS = PROJECT / "01_根集" / "根集_待完整性复核.yaml"
INVENTORY = PROJECT / "02_规范拆分" / "历史序列覆写迁移盘点_待验收.yaml"
FORMAL_LEGACY = PROJECT / "02_规范拆分" / "正式历史结构裁决规则.yaml"
FORMAL_FRAMES = PROJECT / "02_规范拆分" / "正式字架规则.yaml"
MANIFEST = PROJECT / "02_规范拆分" / "最终规范拆分表_生成清单.json"
OUT_TSV = PROJECT / "02_规范拆分" / "历史8105残差结构审计.tsv"
OUT_JSON = PROJECT / "02_规范拆分" / "历史8105残差结构审计.json"
OUT_MD = PROJECT / "02_规范拆分" / "历史8105残差结构审计.md"


def load(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    order = [x["汉字"] for x in rows]
    if len(rows) != 8105 or len(set(order)) != 8105:
        raise ValueError(f"invalid 8105 table: {path}")
    return order, {x["汉字"]: x for x in rows}


def seq(row: dict[str, str]) -> list[str]:
    return row["最终规范拆分"].split(" ＋ ")


def main() -> None:
    order, current = load(CURRENT)
    old_order, legacy = load(LEGACY)
    if set(order) != set(old_order):
        raise ValueError("current and legacy glyph sets differ")

    roots = yaml.safe_load(ROOTS.read_text(encoding="utf-8"))
    hosts = common.canonical_host_map(roots)
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    _, labels = common.repertoire_maps(baseline)
    aliases = {"一": "横", "丨": "竖", "丿": "撇", "丶": "点", "㇒": "撇", "㇆": "折", "㇕": "折", "竖弯钩": "折"}

    def visible(token: str) -> str:
        return aliases.get(labels.get(token, token), labels.get(token, token))

    def canonical(tokens: list[str]) -> list[str]:
        normalized = [visible(x) for x in tokens]
        return [hosts.get(x, x) for x in normalized]

    def replace_all(tokens: list[str], old: list[str], new: list[str]) -> list[str]:
        result: list[str] = []
        i = 0
        while i < len(tokens):
            if tokens[i:i + len(old)] == old:
                result.extend(new)
                i += len(old)
            else:
                result.append(tokens[i])
                i += 1
        return result

    def accepted_manual_semantic_equivalent(now: list[str], old: list[str]) -> bool:
        """Recognize propagation of three already accepted corrections to old manual rules."""
        target = [visible(x) for x in old]
        current = [visible(x) for x in now]
        rewrites = [
            (["戈"], ["撇", "横", "折", "横", "戈"]),
            (["横", "折", "二", "竖"], ["横", "肀"]),
            (["折", "夫"], ["争字底", "人"]),
        ]
        for before, after in rewrites:
            target = replace_all(target, before, after)
        return target == current

    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    deferred = set(((inventory.get("deferred_encoding_layer_decisions") or {}).get("entries") or {}))
    formal_legacy = yaml.safe_load(FORMAL_LEGACY.read_text(encoding="utf-8"))
    accepted = set(formal_legacy.get("guarded_rewrites") or {})
    frames = yaml.safe_load(FORMAL_FRAMES.read_text(encoding="utf-8"))
    frame_targets = set(frames.get("guarded_rewrites") or {}) | set(frames.get("unchanged_equivalent") or [])
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    propagated = {c for chars in (manifest.get("structural_override_hits") or {}).values() for c in chars}

    result = []
    for char in order:
        now, old = seq(current[char]), seq(legacy[char])
        if now == old:
            continue
        if char in deferred:
            category = "deferred_encoding_layer"
        elif char in accepted:
            category = "accepted_27_structural"
        elif char in frame_targets:
            category = "accepted_frame_semantics"
        elif char in propagated:
            category = "accepted_propagating_structural"
        elif canonical(now) == canonical(old):
            category = "canonical_host_equivalent"
        elif accepted_manual_semantic_equivalent(now, old):
            category = "accepted_manual_rule_semantics"
        else:
            category = "unexplained_residual"
        result.append({
            "汉字": char,
            "分类": category,
            "当前拆分": " ＋ ".join(now),
            "历史拆分": " ＋ ".join(old),
            "当前宿主序列": " ＋ ".join(canonical(now)),
            "历史宿主序列": " ＋ ".join(canonical(old)),
        })
    counts = Counter(x["分类"] for x in result)
    if sum(counts.values()) != len(result):
        raise ValueError("classification count mismatch")

    fields = ["汉字", "分类", "当前拆分", "历史拆分", "当前宿主序列", "历史宿主序列"]
    with OUT_TSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(result)
    unexplained = [x for x in result if x["分类"] == "unexplained_residual"]
    payload = {
        "status": "read_only_audit",
        "raw_differences": len(result),
        "counts": dict(sorted(counts.items())),
        "unexplained_count": len(unexplained),
        "unexplained": unexplained,
        "inputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [CURRENT, LEGACY, ROOTS, common.BASELINE_PATH, INVENTORY, FORMAL_LEGACY, FORMAL_FRAMES, MANIFEST, Path(__file__)]},
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 历史8105残差结构审计", "", "- 状态：只读审计，不修改权威8105。",
        f"- 原始文本差异：{len(result)}字。", f"- 尚不能解释：{len(unexplained)}字。", "", "## 分类计数", "",
    ]
    lines.extend(f"- `{k}`：{v}" for k, v in sorted(counts.items()))
    lines.extend(["", "## 尚不能解释的残差", ""])
    lines.extend(f"- {x['汉字']}：当前`{x['当前拆分']}`；历史`{x['历史拆分']}`。" for x in unexplained)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"raw_differences": len(result), "counts": dict(counts), "unexplained": len(unexplained)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
