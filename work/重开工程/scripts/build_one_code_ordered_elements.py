#!/usr/bin/env python3
"""建立全量显式排序，只交换从/才以固定一简c=才。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import yaml


TOPS = (300, 500, 1500, 1674, 3527, 6000)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(item: dict) -> tuple[str, str]:
    return str(item["词"]), str(item["拼音"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise ValueError("输入输出不得相同")
    source = yaml.safe_load(args.source.read_text(encoding="utf-8"))
    if len(source) != 8454 or len({str(x["词"]) for x in source}) != 8105:
        raise ValueError("源资产不是8454身份/8105字")
    if any("排序序号" in item for item in source):
        raise ValueError("源资产已经含排序序号，拒绝叠加修改")

    wanted = {("从", "cong"), ("才", "cai")}
    found = {identity(item): index for index, item in enumerate(source) if identity(item) in wanted}
    if set(found) != wanted:
        raise ValueError(f"没有唯一找到从/cong与才/cai：{found}")
    from_index, cai_index = found[("从", "cong")], found[("才", "cai")]
    if not all(from_index < top and cai_index < top for top in TOPS):
        raise ValueError("从与才并非处于全部保护层的同一侧，交换会改变分层成员")

    output = copy.deepcopy(source)
    for index, item in enumerate(output):
        item["排序序号"] = index
    output[from_index]["排序序号"] = cai_index
    output[cai_index]["排序序号"] = from_index

    order = [int(item["排序序号"]) for item in output]
    if sorted(order) != list(range(len(output))):
        raise ValueError("排序序号不是完整不重复全集")
    for original, changed in zip(source, output):
        stripped = dict(changed)
        stripped.pop("排序序号")
        if stripped != original:
            raise ValueError(f"除排序序号外发生漂移：{identity(original)}")
    for top in TOPS:
        before = {identity(item) for item in source[:top]}
        after = {identity(output[i]) for i in sorted(range(len(output)), key=lambda i: order[i])[:top]}
        if before != after:
            raise ValueError(f"前{top}分层成员发生变化")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(output, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "design": "0052",
        "source": str(args.source.resolve()),
        "source_sha256": digest(args.source),
        "output": str(args.output.resolve()),
        "output_sha256": digest(args.output),
        "identities": len(output),
        "glyphs": len({str(x["词"]) for x in output}),
        "swap": {
            "from": {"identity": ["从", "cong"], "original_index": from_index},
            "cai": {"identity": ["才", "cai"], "original_index": cai_index},
        },
        "tier_membership_unchanged": list(TOPS),
        "frequency_unchanged": True,
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
