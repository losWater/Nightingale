# -*- coding: utf-8 -*-
"""把夜莺B根集与人工规则编译为 hanzi-chai 配置，并导出正式拆分序列。

用法：python 夜莺B/scripts/build_analysis.py [--run]
默认只生成 work/analysis_config.yaml 与 work/analysis_charset.txt；--run 继续调用
bun scripts/assemble.ts，输出 work/analysis.tsv(.splits.tsv)。
"""
import argparse
import io
import json
import subprocess
import sys
import zlib
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).resolve().parent.parent
BASE = HERE.parent
WORK = HERE / "work"
STROKES = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}
PLACEHOLDER_KEYS = "abcdefghijklmnopqrstuvwxyz"

rep = json.loads(zlib.decompress(
    (BASE / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes()
))
BY_NAME = {
    row.get("name"): chr(row["unicode"])
    for row in rep
    if row.get("name") and row.get("unicode")
}
CUSTOM_ELEMENTS = {}


def element(x):
    value = STROKES.get(str(x), str(x))
    return CUSTOM_ELEMENTS.get(value, BY_NAME.get(value, value))


def apply_sequence_overrides(path, rules):
    """Override final split sequences for crossing-stroke structures chai cannot express."""
    overrides = {
        str(char): [element(x) for x in split]
        for char, split in rules.get("sequence_overrides", {}).items()
    }
    if not overrides:
        return 0
    lines = []
    applied = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        char, sep, _ = line.partition("\t")
        if sep and char in overrides:
            line = char + "\t" + " ".join(overrides[char])
            applied.add(char)
        lines.append(line)
    missing = set(overrides) - applied
    if missing:
        raise ValueError("sequence_overrides 字符不在分析字集: " + " ".join(sorted(missing)))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(applied)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()

    roots = yaml.safe_load((WORK / "根集.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((WORK / "拆分规则.yaml").read_text(encoding="utf-8"))
    CUSTOM_ELEMENTS.update({str(k): str(v) for k, v in rules.get("custom_elements", {}).items()})
    cfg = yaml.safe_load((BASE / "work/seed.yaml").read_text(encoding="utf-8"))
    cfg["info"] = {
        "name": "夜莺B分析配置",
        "author": "nightingale",
        "version": "b-analysis",
        "description": "由夜莺B根集与拆分规则自动生成；键位仅为分析占位",
    }

    old_mapping = cfg["form"]["mapping"]
    mapping = {str(k): v for k, v in old_mapping.items()
               if str(k).startswith("szm-") or str(k).startswith("mzm-")}
    mains = []
    for root in roots["roots"]:
        e = element(root)
        if e not in mains:
            mains.append(e)
    for i, root in enumerate(mains):
        mapping[root] = PLACEHOLDER_KEYS[i % len(PLACEHOLDER_KEYS)]

    for root, attached in roots["roots"].items():
        host = element(root)
        for item in attached:
            child = element(item)
            if child != host:
                mapping[child] = {"element": host}
    for root, anchored in roots.get("anchors", {}).items():
        host = element(root)
        for item in anchored:
            mapping[element(item)] = {"element": host}
    # seed 分类器把部分复合折笔归到第六类；夜莺仍统一挂折。
    mapping["6"] = {"element": "5"}
    cfg["form"]["mapping"] = mapping
    cfg["form"]["alphabet"] = PLACEHOLDER_KEYS

    customize = {}
    for part, split in rules.get("component_splits", {}).items():
        customize[str(part)] = [element(x) for x in split]
    cfg.setdefault("analysis", {})["customize"] = customize

    config_path = WORK / "analysis_config.yaml"
    config_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    readings = json.loads((BASE / "work/readings.json").read_text(encoding="utf-8"))
    charset_path = WORK / "analysis_charset.txt"
    with open(charset_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(readings))
    print(f"根元素 {len(mains)}；附属/锚定 {len(mapping)-len(mains)-sum(1 for k in mapping if k.startswith(('szm-','mzm-')))}")
    print(f"人工部件拆分 {len(customize)} → {config_path}")

    if args.run:
        output = WORK / "analysis.tsv"
        cmd = ["bun", str(BASE / "scripts/assemble.ts"), str(config_path), str(output), str(charset_path)]
        subprocess.run(cmd, cwd=BASE, check=True)
        count = apply_sequence_overrides(Path(str(output) + ".splits.tsv"), rules)
        if count:
            print(f"整字序列覆写 {count} → {output}.splits.tsv")


if __name__ == "__main__":
    main()
