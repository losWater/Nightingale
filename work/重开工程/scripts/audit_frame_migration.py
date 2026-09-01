# -*- coding: utf-8 -*-
"""Inventory legacy frame semantics without applying them to the current table."""
from __future__ import annotations

import csv
import hashlib
import json
import zlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common


ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parents[1]
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
INVENTORY = PROJECT / "02_规范拆分" / "字架迁移盘点_待验收.yaml"
LEGACY = ROOT / "夜莺B" / "work" / "最终规范拆分表_人工阅读.tsv"
REPERTOIRE = ROOT / "repos" / "webchai" / "packages" / "hanzi-chai" / "src" / "data" / "repertoire.json.deflate"
ROOTS = PROJECT / "01_根集" / "根集_待完整性复核.yaml"
OUT = PROJECT / "02_规范拆分"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if len(rows) != 8105 or len({x["汉字"] for x in rows}) != 8105:
        raise ValueError(f"not an 8105 unique-glyph table: {path}")
    return {x["汉字"]: x for x in rows}


def selected_glyph(row: dict | None) -> dict | None:
    glyphs = row.get("glyphs", []) if row else []
    return next(
        (g for g in glyphs if g.get("type") == "compound" and "G" in g.get("tags", [])),
        next((g for g in glyphs if g.get("type") == "compound"), None),
    )


def main() -> None:
    current = table(CURRENT)
    legacy = table(LEGACY)
    inventory = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    roots = yaml.safe_load(ROOTS.read_text(encoding="utf-8"))
    hosts = common.canonical_host_map(roots)
    aliases = {"一": "横", "丨": "竖", "丿": "撇", "丶": "点", "㇕": "折"}

    def canonical_sequence(raw: str) -> list[str]:
        return [hosts.get(aliases.get(x, x), aliases.get(x, x)) for x in raw.split(" ＋ ")]
    rep = json.loads(zlib.decompress(REPERTOIRE.read_bytes()))
    by_char = {chr(x["unicode"]): x for x in rep if x.get("unicode")}
    by_name = {x.get("name"): chr(x["unicode"]) for x in rep if x.get("name") and x.get("unicode")}

    registered = set()
    for root, attached in roots["roots"].items():
        registered.add(by_name.get(str(root), str(root)))
        registered.update(by_name.get(str(x), str(x)) for x in (attached or []))
    for attached in (roots.get("anchors") or {}).values():
        registered.update(by_name.get(str(x), str(x)) for x in (attached or []))

    def element(name: str) -> str:
        return by_name.get(str(name), str(name))

    def match(kind: str, glyph: dict | None) -> str | None:
        if not glyph:
            return None
        ops = [x for x in glyph.get("operandList", []) if x]
        op = glyph.get("operator")
        if kind == "赢":
            if op != "⿱" or len(ops) != 2 or ops[0] != element("吂"):
                return None
            bottom = selected_glyph(by_char.get(ops[1]))
            bops = [x for x in (bottom or {}).get("operandList", []) if x]
            if (bottom or {}).get("operator") == "⿲" and len(bops) == 3 and bops[0] == element("月") and bops[2] == element("凡"):
                return bops[1]
            return None
        patterns = {
            "衣": ("⿳", element("亠"), element("衣省")),
            "行": ("⿲", element("彳"), element("亍")),
            "辡": ("⿲", element("辛旁"), element("辛")),
            "玨": ("⿲", element("王"), element("王")),
        }
        expected = patterns.get(kind)
        if expected is None or len(ops) != 3:
            return None
        operator, first, last = expected
        return ops[1] if op == operator and ops[0] == first and ops[2] == last else None

    direct_rows = []
    hit_sets: dict[str, list[str]] = defaultdict(list)
    protected_rows = []
    for char in current:
        glyph = selected_glyph(by_char.get(char))
        for kind, spec in inventory["frames"].items():
            if spec.get("structural_only"):
                continue
            middle = match(str(kind), glyph)
            if middle is None:
                continue
            if current[char]["最终规范拆分"] == char and char in hosts:
                protected_rows.append({"字架": str(kind), "汉字": char, "当前完整根宿主": hosts[char]})
                break
            hit_sets[str(kind)].append(char)
            old = legacy[char]["最终规范拆分"]
            new = current[char]["最终规范拆分"]
            semantically_equal = canonical_sequence(old) == canonical_sequence(new)
            direct_rows.append({
                "字架": str(kind), "汉字": char,
                "Chai中芯": by_char.get(middle, {}).get("name") or middle,
                "旧最终拆分": old, "当前拆分": new,
                "是否语义一致": "是" if semantically_equal else "否",
                "是否丢失旧字架结果": "否" if semantically_equal else "是",
            })
            break

    fields = ["字架", "汉字", "Chai中芯", "旧最终拆分", "当前拆分", "是否语义一致", "是否丢失旧字架结果"]
    with (OUT / "字架迁移审计.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(direct_rows)

    changed_direct = [x for x in direct_rows if x["是否丢失旧字架结果"] == "是"]

    active_kinds = [str(k) for k, v in inventory["frames"].items() if not v.get("structural_only")]

    def walk(node: str, top: str, path: tuple[str, ...], seen: frozenset[str]):
        if node in seen:
            return
        glyph = selected_glyph(by_char.get(node))
        matched = None
        for kind in active_kinds:
            middle = match(kind, glyph)
            if middle is not None:
                matched = (kind, middle)
                break
        if matched is not None:
            kind, middle = matched
            if node in registered:
                return
            if node != top:
                yield {"汉字": top, "字架": kind, "命中字架部件": by_char.get(node, {}).get("name") or node,
                       "Chai中芯": by_char.get(middle, {}).get("name") or middle,
                       "结构路径": "／".join(path + (by_char.get(node, {}).get("name") or node,))}
            # The frame owns its outer shell; recurse only into its replaceable middle.
            yield from walk(middle, top, path + (by_char.get(node, {}).get("name") or node,), seen | {node})
            return
        if node in registered or not glyph:
            return
        for child in [x for x in glyph.get("operandList", []) if x]:
            yield from walk(child, top, path + (by_char.get(node, {}).get("name") or node,), seen | {node})

    nested_rows = []
    observed_nested = set()
    for char in current:
        for item in walk(char, char, (), frozenset()):
            key = (item["汉字"], item["字架"], item["命中字架部件"], item["结构路径"])
            if key in observed_nested:
                continue
            observed_nested.add(key)
            item["旧最终拆分"] = legacy[char]["最终规范拆分"]
            item["当前拆分"] = current[char]["最终规范拆分"]
            item["是否语义一致"] = "是" if canonical_sequence(item["旧最终拆分"]) == canonical_sequence(item["当前拆分"]) else "否"
            nested_rows.append(item)

    nested_fields = ["字架", "汉字", "命中字架部件", "Chai中芯", "结构路径", "旧最终拆分", "当前拆分", "是否语义一致"]
    with (OUT / "字架迁移传播审计.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=nested_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(nested_rows)
    result = {
        "generated_at": datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes"),
        "mode": "audit_only_do_not_apply",
        "inputs": {str(p.relative_to(ROOT)): digest(p) for p in [CURRENT, INVENTORY, LEGACY, REPERTOIRE, ROOTS]},
        "direct_hits": {k: sorted(v) for k, v in hit_sets.items()},
        "direct_hit_counts": {k: len(v) for k, v in hit_sets.items()},
        "changed_from_legacy_direct_count": len(changed_direct),
        "changed_from_legacy_direct": changed_direct,
        "complete_root_precedence": protected_rows,
        "nested_structural_hits": nested_rows,
        "nested_structural_hit_count": len(nested_rows),
        "limitations": [
            "本轮只盘点直接字架匹配，不执行旧版token子串传播",
            "嵌套传播必须在新版结构树递归方案完成后另行审计",
            "旧最终表仅作历史行为参照，不自动视为无需复核的真值",
        ],
    }
    (OUT / "字架迁移审计.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# 字架迁移审计（只读）", "",
        f"- 直接命中总数：{len(direct_rows)}",
        f"- 语义上丢失旧字架结果：{len(changed_direct)}",
        f"- 完整根优先保护：{len(protected_rows)}",
        f"- 结构树确认的嵌套命中：{len(nested_rows)}",
        "- 当前表未被修改。", "- 尚未执行嵌套传播。", "",
        "|字架|直接命中字|数量|", "|---|---|---:|",
    ]
    for kind in inventory["frames"]:
        if inventory["frames"][kind].get("structural_only"):
            md.append(f"|{kind}|概念字架，完整根优先|0|")
        else:
            chars = sorted(hit_sets.get(str(kind), []))
            md.append(f"|{kind}|{'、'.join(chars) or '—'}|{len(chars)}|")
    if protected_rows:
        md.extend(["", "## 完整根优先", ""])
        md.extend(f"- {x['汉字']}：匹配{x['字架']}字架拓扑，但当前完整根挂{x['当前完整根宿主']}，不改写。" for x in protected_rows)
    md.extend(["", "## 与旧最终表不同的直接字", "", "|字架|字|旧最终拆分|当前拆分|", "|---|---|---|---|"])
    md.extend(f"|{x['字架']}|{x['汉字']}|{x['旧最终拆分']}|{x['当前拆分']}|" for x in changed_direct)
    md.extend(["", "## 结构树确认的嵌套用户", "", "|字架|字|命中字架部件|结构路径|旧最终拆分|当前拆分|", "|---|---|---|---|---|---|"])
    md.extend(f"|{x['字架']}|{x['汉字']}|{x['命中字架部件']}|{x['结构路径']}|{x['旧最终拆分']}|{x['当前拆分']}|" for x in nested_rows)
    (OUT / "字架迁移审计.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"direct_hits": len(direct_rows), "changed": len(changed_direct), "by_frame": result["direct_hit_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
