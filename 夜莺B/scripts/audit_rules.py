# -*- coding: utf-8 -*-
"""夜莺B根集与人工规则自动审计（只读报告，不修改裁决）。

用法：python 夜莺B/scripts/audit_rules.py
1. 重建当前正式拆分；2. 另跑一份移除 customize 的纯自动拆分；
3. 对比人工规则；4. 统计全部根及附属/锚定形的就业量。
"""
import io
import json
import subprocess
import sys
import zlib
from collections import Counter
from pathlib import Path

import yaml
from build_analysis import frame_match, selected_glyph

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).resolve().parent.parent
BASE = HERE.parent
WORK = HERE / "work"
AUDIT = WORK / ".rule_audit"


def names():
    rows = json.loads(zlib.decompress(
        (BASE / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes()
    ))
    by_name = {x.get("name"): chr(x["unicode"]) for x in rows if x.get("name") and x.get("unicode")}
    labels = {chr(x["unicode"]): x.get("name") for x in rows if x.get("unicode") and x.get("name")}
    return by_name, labels


BY_NAME, LABELS = names()
CUSTOM_ELEMENTS = {}


def resolve(x):
    return CUSTOM_ELEMENTS.get(str(x), BY_NAME.get(str(x), str(x)))


def label(x):
    custom_labels = {v: k for k, v in CUSTOM_ELEMENTS.items()}
    return custom_labels.get(x, LABELS.get(x, x))


def read_splits(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        c, _, raw = line.partition("\t")
        if raw:
            out[c] = raw.split()
    return out


def host_map(roots):
    host = {"1": "横", "一": "横", "2": "竖", "丨": "竖", "3": "撇", "丿": "撇",
            "4": "点", "丶": "点", "5": "折", "6": "折", "乙": "折"}
    for root, attached in roots["roots"].items():
        host[resolve(root)] = str(root)
        for item in attached:
            host[resolve(item)] = str(root)
    for root, anchored in roots.get("anchors", {}).items():
        for item in anchored:
            host[resolve(item)] = str(item)
    return host


def main():
    subprocess.run([sys.executable, str(HERE / "scripts/build_analysis.py"), "--run"], cwd=HERE, check=True)
    formal = read_splits(WORK / "analysis.tsv.splits.tsv")
    rules = yaml.safe_load((WORK / "拆分规则.yaml").read_text(encoding="utf-8"))
    CUSTOM_ELEMENTS.update({str(k): str(v) for k, v in rules.get("custom_elements", {}).items()})
    roots = yaml.safe_load((WORK / "根集.yaml").read_text(encoding="utf-8"))
    hosts = host_map(roots)

    # 同一根集，移除所有强制拆分，观察 chai 会自动给出什么。
    AUDIT.mkdir(exist_ok=True)
    cfg = yaml.safe_load((WORK / "analysis_config.yaml").read_text(encoding="utf-8"))
    cfg.setdefault("analysis", {})["customize"] = {}
    auto_cfg = AUDIT / "auto.yaml"
    auto_out = AUDIT / "auto.tsv"
    auto_cfg.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    subprocess.run([
        "bun", str(BASE / "scripts/assemble.ts"), str(auto_cfg), str(auto_out),
        str(WORK / "analysis_charset.txt")
    ], cwd=BASE, check=True)
    automatic = read_splits(Path(str(auto_out) + ".splits.tsv"))

    mapping = cfg["form"]["mapping"]
    print("\n== 人工拆分审计")
    for part, declared in rules.get("component_splits", {}).items():
        p = resolve(part)
        wanted = [resolve(x) if str(x) not in ("横", "竖", "撇", "点", "折") else
                  {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}[str(x)] for x in declared]
        missing = [label(x) for x in wanted if x not in mapping and x not in ("1", "2", "3", "4", "5", "6")]
        manual_seq = formal.get(p, [])
        auto_seq = automatic.get(p, [])
        manual_canon = [hosts.get(x, label(x)) for x in manual_seq]
        auto_canon = [hosts.get(x, label(x)) for x in auto_seq]
        state = "同自动" if manual_canon == auto_canon else "覆盖自动"
        print(f"  {part}: {state}")
        print("    人工=" + " ".join(label(x) for x in manual_seq))
        print("    自动=" + " ".join(label(x) for x in auto_seq))
        if missing:
            print("    ⚠ 引用了非当前元素: " + " ".join(missing))

    print("\n== 字架审计")
    frame_rows = []
    for char, seq in formal.items():
        for kind, spec in rules.get("frames", {}).items():
            if frame_match(str(kind), selected_glyph(char)):
                # 完整成根者（如襄）优先，是合法的边界保护。
                expected = str(spec.get("host", kind))
                actual = hosts.get(seq[0], label(seq[0])) if seq else "—"
                state = "整字根优先" if seq == [char] and char in hosts else (
                    "已接管" if actual == expected else "⚠ 未接管")
                frame_rows.append((char, str(kind), actual, state))
                break
    active_frames = {str(kind): spec for kind, spec in rules.get("frames", {}).items()
                     if not spec.get("structural_only")}
    counts = Counter(kind for _, kind, _, state in frame_rows if state == "已接管")
    protected = [char for char, _, _, state in frame_rows if state == "整字根优先"]
    failed = [(char, kind, actual) for char, kind, actual, state in frame_rows if state.startswith("⚠")]
    print("  已接管: " + " ".join(f"{kind}{counts[kind]}" for kind in active_frames))
    conceptual = [str(kind) for kind, spec in rules.get("frames", {}).items()
                  if spec.get("structural_only")]
    if conceptual:
        print("  概念字架（暂无用户）: " + " ".join(conceptual))
    if protected:
        print("  整字根优先: " + " ".join(protected))
    if failed:
        print("  ⚠ 未接管: " + " ".join(f"{c}({kind}→{actual})" for c, kind, actual in failed))

    # 直接元素就业：既统计主根自身，也统计挂靠形和锚定形。
    use = Counter(x for seq in formal.values() for x in seq)
    print("\n== 根就业审计")
    rows = []
    for root, attached in roots["roots"].items():
        forms = [resolve(root), *(resolve(x) for x in attached)]
        total = sum(use[x] for x in forms)
        rows.append((total, str(root), [(str(x), use[resolve(x)]) for x in attached]))
    for host, anchored in roots.get("anchors", {}).items():
        for item in anchored:
            rows.append((use[resolve(item)], f"{item}(锚→{host})", []))
    rows.sort(key=lambda x: (x[0], x[1]))
    zero = [name for n, name, _ in rows if n == 0]
    print(f"  根/锚定项 {len(rows)}；零就业 {len(zero)}")
    if zero:
        print("  零就业: " + " ".join(zero))
    print("  最低就业:")
    for total, root, attached in rows[:20]:
        detail = " ".join(f"{x}:{n}" for x, n in attached if n)
        print(f"    {root}: {total}" + (f" ({detail})" if detail else ""))

    boundaries = rules.get("boundary_candidates", {})
    if boundaries:
        print("\n== 人工边界记录")
        for part, rule in boundaries.items():
            print(f"  {part}: head={rule.get('head','—')} tail={rule.get('tail','—')} "
                  f"decision={rule.get('decision','待定')}")


if __name__ == "__main__":
    main()
