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

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).resolve().parent.parent
BASE = HERE.parent
WORK = HERE / "work"
STROKES = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}
PLACEHOLDER_KEYS = "abcdefghijklmnopqrstuvwxyz"

rep = json.loads(zlib.decompress(
    (BASE / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes()
))
REP_BY_CHAR = {chr(row["unicode"]): row for row in rep if row.get("unicode")}
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


def selected_glyph(char):
    row = REP_BY_CHAR.get(char)
    glyphs = row.get("glyphs", []) if row else []
    return next((g for g in glyphs if g.get("type") == "compound" and "G" in g.get("tags", [])),
                next((g for g in glyphs if g.get("type") == "compound"), None))


def read_sequences(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        char, sep, raw = line.partition("\t")
        if sep and raw:
            out[char] = raw.split()
    return out


def write_sequences(path, sequences):
    Path(path).write_text("\n".join(c + "\t" + " ".join(seq) for c, seq in sequences.items()) + "\n",
                          encoding="utf-8")


def frame_match(kind, glyph):
    if not glyph:
        return None
    ops = [x for x in glyph.get("operandList", []) if x]
    op = glyph.get("operator")
    if kind == "赢":
        # 赢／嬴／羸／蠃／臝：吂在上，月-X-凡在下；X 是字架中的换芯。
        if op != "⿱" or len(ops) != 2 or ops[0] != element("吂"):
            return None
        bottom = selected_glyph(ops[1])
        bottom_ops = [x for x in (bottom or {}).get("operandList", []) if x]
        if ((bottom or {}).get("operator") == "⿲" and len(bottom_ops) == 3 and
                bottom_ops[0] == element("月") and bottom_ops[2] == element("凡")):
            return bottom_ops[1]
        return None
    patterns = {
        "衣": ("⿳", element("亠"), element("衣省")),
        "行": ("⿲", element("彳"), element("亍")),
        "辡": ("⿲", element("辛旁"), element("辛")),
        "玨": ("⿲", element("王"), element("王")),
    }
    expected = patterns.get(kind)
    if not expected or len(ops) != 3:
        return None
    operator, left, right = expected
    return ops[1] if op == operator and ops[0] == left and ops[2] == right else None


def apply_frames(path, config_path, rules):
    """把 ⿳/⿲ 外框改写为“字架 + 中间件”，并传播到嵌套用户。"""
    frames = rules.get("frames", {})
    if not frames:
        return 0
    sequences = read_sequences(path)
    mapping = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))["form"]["mapping"]
    matches = []
    for char in sequences:
        glyph = selected_glyph(char)
        for kind in frames:
            middle = frame_match(str(kind), glyph)
            if middle:
                matches.append((char, str(kind), middle))
                break

    # 从显式样例反推出该字架在 chai 序列中的前后缀。这样 PUA 中间件也能
    # 直接从原字序列剥出，无需让 assemble.ts 单独接受 PUA 字符集。
    affixes = {}
    for kind, spec in frames.items():
        for sample, declared in spec.get("examples", {}).items():
            if sample not in sequences:
                continue
            declared_seq = []
            for token in str(declared).split("+"):
                e = element(token)
                declared_seq.extend(sequences.get(e, [e]))
            old = sequences[sample]
            for i in range(len(old) - len(declared_seq) + 1):
                if old[i:i + len(declared_seq)] == declared_seq:
                    affixes[str(kind)] = (old[:i], old[i + len(declared_seq):])
                    break
            if str(kind) in affixes:
                break

    replacements = []
    direct = {}
    for char, kind, middle in matches:
        old = sequences[char]
        # 完整字已经成根时，根边界优先于字架（例如襄）。
        if len(old) == 1 and old[0] == char and char in mapping:
            continue
        declared = frames[kind].get("examples", {}).get(char)
        if declared is not None:
            middle_seq = [element(x) for x in str(declared).split("+")]
        else:
            prefix, suffix = affixes.get(kind, ([], []))
            if (len(old) >= len(prefix) + len(suffix) and old[:len(prefix)] == prefix and
                    (not suffix or old[-len(suffix):] == suffix)):
                end = len(old) - len(suffix) if suffix else len(old)
                middle_seq = old[len(prefix):end]
            else:
                middle_seq = sequences.get(middle, [middle])
        new = [element(frames[kind].get("host", kind)), *middle_seq]
        direct[char] = new
        if old != new:
            replacements.append((old, new))

    # 先传播至蓑、蘅、癍等嵌套用户，再覆盖顶层字本身。
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)
    for char, seq in list(sequences.items()):
        if char in direct:
            continue
        for old, new in replacements:
            i = 0
            while len(old) and i <= len(seq) - len(old):
                if seq[i:i + len(old)] == old:
                    seq = seq[:i] + new + seq[i + len(old):]
                    i += len(new)
                else:
                    i += 1
        sequences[char] = seq
    sequences.update(direct)
    write_sequences(path, sequences)
    return len(direct)


def apply_postprocess(path, config_path, rules):
    frame_count = apply_frames(path, config_path, rules)
    override_count = apply_sequence_overrides(path, rules)
    return frame_count, override_count


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
        frame_count, count = apply_postprocess(Path(str(output) + ".splits.tsv"), config_path, rules)
        if frame_count:
            print(f"字架改写 {frame_count} → {output}.splits.tsv")
        if count:
            print(f"整字序列覆写 {count} → {output}.splits.tsv")


if __name__ == "__main__":
    main()
