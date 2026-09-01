# -*- coding: utf-8 -*-
"""Audit legacy sequence overrides by layer without applying them."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
LEGACY = ROOT / "夜莺B" / "work" / "拆分规则.yaml"
INVENTORY = PROJECT / "02_规范拆分" / "历史序列覆写迁移盘点_待验收.yaml"
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
ROOTS = PROJECT / "01_根集" / "根集_待完整性复核.yaml"
OUT = PROJECT / "02_规范拆分"


def load_table(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if len(rows) != 8105 or len({x["汉字"] for x in rows}) != 8105:
        raise ValueError("current canonical table is not 8105 unique glyphs")
    return {x["汉字"]: x for x in rows}


def main() -> None:
    legacy_doc = yaml.safe_load(LEGACY.read_text(encoding="utf-8"))
    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    current = load_table(CURRENT)
    roots = yaml.safe_load(ROOTS.read_text(encoding="utf-8"))
    hosts = common.canonical_host_map(roots)
    aliases = {"一": "横", "丨": "竖", "丿": "撇", "丶": "点", "㇕": "折"}
    legacy_overrides = legacy_doc.get("sequence_overrides") or {}
    structural = [str(x) for x in inventory.get("structural_candidates") or []]
    quarantine = {str(k): str(v) for k, v in (inventory.get("encoding_layer_quarantine") or {}).items()}
    if set(structural) | set(quarantine) != set(map(str, legacy_overrides)):
        missing = set(map(str, legacy_overrides)) - set(structural) - set(quarantine)
        extra = set(structural) | set(quarantine) - set(map(str, legacy_overrides))
        raise ValueError(f"legacy override partition mismatch: missing={sorted(missing)} extra={sorted(extra)}")

    def tokens(raw: str) -> list[str]:
        return raw.split(" ＋ ")

    def canon(seq: list[str]) -> list[str]:
        return [hosts.get(aliases.get(x, x), aliases.get(x, x)) for x in seq]

    def expand(seq: list[str], stack: tuple[str, ...] = ()) -> list[str]:
        result = []
        for token in seq:
            normalized = aliases.get(token, token)
            if normalized in hosts:
                result.append(token)
                continue
            if token in stack:
                raise ValueError("cyclic expansion: " + " -> ".join(stack + (token,)))
            row = current.get(token)
            if row is None:
                raise KeyError(token)
            child = tokens(row["最终规范拆分"])
            if child == [token]:
                raise KeyError(token)
            result.extend(expand(child, stack + (token,)))
        return result

    already_owned = set(map(str, (inventory.get("already_owned_by_new_rule") or {})))
    rows = []
    counts = {"current_semantically_aligned": 0, "aligned_and_owned_by_new_rule": 0,
              "suspected_missing": 0, "incompatible_unresolved": 0}
    for char in structural:
        raw_expected = [str(x) for x in legacy_overrides[char]]
        unresolved = []
        try:
            expanded = expand(raw_expected)
        except KeyError as exc:
            expanded = []
            unresolved = [str(exc.args[0])]
        current_seq = tokens(current[char]["最终规范拆分"])
        if unresolved:
            status = "incompatible_unresolved"
        elif canon(expanded) == canon(current_seq):
            status = "aligned_and_owned_by_new_rule" if char in already_owned else "current_semantically_aligned"
        else:
            status = "suspected_missing"
        counts[status] += 1
        rows.append({
            "汉字": char,
            "旧目标": " ＋ ".join(raw_expected),
            "按当前根集展开": " ＋ ".join(expanded) if expanded else "—",
            "当前拆分": " ＋ ".join(current_seq),
            "状态": status,
            "无法解析": " ".join(unresolved),
        })

    fields = ["汉字", "旧目标", "按当前根集展开", "当前拆分", "状态", "无法解析"]
    with (OUT / "历史序列覆写迁移审计.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    payload = {
        "generated_at": datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes"),
        "mode": "audit_only_do_not_apply",
        "counts": counts,
        "structural_rows": rows,
        "encoding_layer_quarantine": quarantine,
        "inputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [LEGACY, INVENTORY, CURRENT, ROOTS, Path(__file__)]},
    }
    (OUT / "历史序列覆写迁移审计.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    labels = {
        "aligned_and_owned_by_new_rule": "已由新版规则接管且一致",
        "current_semantically_aligned": "当前已语义一致，无需迁移",
        "suspected_missing": "疑似漏迁，待人工裁决",
        "incompatible_unresolved": "旧元素无法按当前根集解析",
    }
    md = ["# 历史序列覆写迁移审计", "", "- 当前表未修改。", ""]
    for key, value in counts.items():
        md.append(f"- {labels[key]}：{value}")
    md.extend(["", "|字|旧目标|当前根集展开|当前拆分|状态|", "|---|---|---|---|---|"])
    md.extend(f"|{x['汉字']}|{x['旧目标']}|{x['按当前根集展开']}|{x['当前拆分']}|{labels[x['状态']]}|" for x in rows)
    md.extend(["", "## 编码层隔离", ""])
    md.extend(f"- {char}：{reason}" for char, reason in quarantine.items())
    (OUT / "历史序列覆写迁移审计.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
