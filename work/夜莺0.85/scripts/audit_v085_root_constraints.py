#!/usr/bin/env python3
"""直接以正式根集审计0.9.1布局中的主根、附属与锚定约束。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "work" / "重开工程"
sys.path.insert(0, str(PROJECT / "scripts"))
import audit_manual_split_propagation as common  # noqa: E402


def key_of(mapping: dict[str, object], element: str) -> str | None:
    seen: set[str] = set()
    while element not in seen:
        seen.add(element)
        value = mapping.get(element)
        if isinstance(value, str):
            return value if len(value) == 1 else None
        if isinstance(value, dict) and value.get("element") is not None:
            element = str(value["element"])
            continue
        return None
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    layout = yaml.safe_load(args.layout.read_text(encoding="utf-8"))
    by_name, _ = common.repertoire_maps(baseline)
    mapping = {str(k): v for k, v in layout["form"]["mapping"].items()}

    mains = {str(name) for name in roots["roots"]}
    attached_hosts: dict[str, list[str]] = defaultdict(list)
    anchored_hosts: dict[str, list[str]] = defaultdict(list)
    unresolved = []
    violations = []

    def audit_relation(kind: str, host_name: object, child_name: object) -> None:
        host_label, child_label = str(host_name), str(child_name)
        host_element = common.resolve(host_label, by_name)
        child_element = common.resolve(child_label, by_name)
        host_key = key_of(mapping, host_element)
        child_key = key_of(mapping, child_element)
        row = {
            "类型": kind, "宿主": host_label, "成员": child_label,
            "宿主元素": host_element, "成员元素": child_element,
            "宿主键": host_key, "成员键": child_key,
        }
        if host_key is None or child_key is None:
            unresolved.append(row)
        elif host_key != child_key:
            violations.append(row)

    for host, children in roots["roots"].items():
        for child in children or []:
            attached_hosts[str(child)].append(str(host))
            audit_relation("附属", host, child)
    for host, children in (roots.get("anchors") or {}).items():
        for child in children or []:
            anchored_hosts[str(child)].append(str(host))
            audit_relation("锚定", host, child)

    main_keys = {}
    for name in mains:
        element = common.resolve(name, by_name)
        main_keys[name] = key_of(mapping, element)
        if main_keys[name] is None:
            unresolved.append({"类型": "主根", "宿主": name, "成员": name,
                               "宿主元素": element, "成员元素": element,
                               "宿主键": None, "成员键": None})

    identity_conflicts = {
        "主根兼附属": sorted(mains & set(attached_hosts)),
        "主根兼锚定": sorted(mains & set(anchored_hosts)),
        "附属兼锚定": sorted(set(attached_hosts) & set(anchored_hosts)),
        "多重附属宿主": {k: v for k, v in sorted(attached_hosts.items()) if len(v) > 1},
        "多重锚定宿主": {k: v for k, v in sorted(anchored_hosts.items()) if len(v) > 1},
    }
    report = {
        "layout": str(args.layout.resolve()),
        "counts": {
            "main_roots": len(mains),
            "attachment_relations": sum(map(len, attached_hosts.values())),
            "anchor_relations": sum(map(len, anchored_hosts.values())),
            "unresolved": len(unresolved),
            "constraint_violations": len(violations),
        },
        "violations": violations,
        "unresolved": unresolved,
        "identity_conflicts": identity_conflicts,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 夜莺0.9.1根约束审计", "",
        f"- 主根：{len(mains)}",
        f"- 附属关系：{report['counts']['attachment_relations']}",
        f"- 锚定关系：{report['counts']['anchor_relations']}",
        f"- 无法解析：{len(unresolved)}",
        f"- 键位违约：{len(violations)}", "",
        "## 键位违约", "",
        "|类型|宿主|宿主键|成员|成员键|", "|---|---|:---:|---|:---:|",
    ]
    lines.extend(
        f"|{x['类型']}|{x['宿主']}|{x['宿主键'] or '—'}|{x['成员']}|{x['成员键'] or '—'}|"
        for x in violations
    )
    lines.extend(["", "## 身份交叉", ""])
    for label, values in identity_conflicts.items():
        lines.append(f"- {label}：{json.dumps(values, ensure_ascii=False)}")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
