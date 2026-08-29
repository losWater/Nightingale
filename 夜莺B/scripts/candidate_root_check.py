# -*- coding: utf-8 -*-
"""候选根“有根 / 无根拆开”全局反事实检查（hanzi-chai 正式分析双跑）。

用法：python 夜莺B/scripts/candidate_root_check.py 虍 [三简最低频万]

无根案读取根集与拆分规则生成正式基线；有根案把候选加入独立根，并移除该
部件的强制拆分，再由 hanzi-chai 重新分析。覆盖 readings.json 的全部字音。
"""
import io
import json
import subprocess
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import yaml
from build_analysis import apply_postprocess
from reading_frequencies import aggregate_syllable_frequencies, load_readings, primary_readings

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).resolve().parent.parent
BASE = HERE.parent
WORK = HERE / "work"


def load_names():
    rows = json.loads(zlib.decompress(
        (BASE / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes()
    ))
    by_name = {x.get("name"): chr(x["unicode"]) for x in rows if x.get("name") and x.get("unicode")}
    names = {chr(x["unicode"]): x.get("name") for x in rows if x.get("unicode") and x.get("name")}
    return by_name, names


BY_NAME, NAMES = load_names()
RULES = yaml.safe_load((WORK / "拆分规则.yaml").read_text(encoding="utf-8"))
CUSTOM_ELEMENTS = {str(k): str(v) for k, v in RULES.get("custom_elements", {}).items()}
CUSTOM_LABELS = {v: k for k, v in CUSTOM_ELEMENTS.items()}
STROKES = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}


def resolve(x):
    value = STROKES.get(str(x), str(x))
    return CUSTOM_ELEMENTS.get(value, BY_NAME.get(value, value))


def label(x):
    return CUSTOM_LABELS.get(x, NAMES.get(x, x))


def load_host(candidate=None, exclude=None):
    roots = yaml.safe_load((WORK / "根集.yaml").read_text(encoding="utf-8"))
    host = {}
    for root, attached in roots["roots"].items():
        rr = resolve(root)
        if rr == exclude:
            continue
        host[rr] = str(root)
        for item in attached:
            child = resolve(item)
            if child != exclude:
                host[child] = str(root)
    for root, anchored in roots.get("anchors", {}).items():
        for item in anchored:
            host[resolve(item)] = str(item)
    if candidate is not None:
        group = candidate if isinstance(candidate, (list, tuple)) else [candidate]
        # 组首若已属于正式宿主（尤其 1~5 笔画家），必须沿用该宿主名；
        # 否则会把“弓挂折”误算成独立的“5”键，虚报三码分流收益。
        group_name = host.get(group[0], label(group[0]))
        aliases = {label(item) for item in group} | {str(item) for item in group}
        for child, parent in list(host.items()):
            if parent in aliases:
                host[child] = group_name
        for item in group:
            host[item] = group_name
    host.update({"1": "横", "一": "横", "2": "竖", "丨": "竖", "3": "撇", "丿": "撇",
                 "4": "点", "丶": "点", "5": "折", "6": "折", "乙": "折"})
    return host


def parse_splits(path, host):
    result = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        c, _, raw = line.partition("\t")
        seq = raw.split()
        if seq:
            result[c] = (host.get(seq[0], label(seq[0])), host.get(seq[-1], label(seq[-1])))
    return result


def assemble_config(cfg, temp_dir, title):
    cfg["info"]["name"] = title
    config_path = Path(temp_dir) / "candidate.yaml"
    output_path = Path(temp_dir) / "candidate.tsv"
    config_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    cmd = ["bun", str(BASE / "scripts/assemble.ts"), str(config_path), str(output_path),
           str(WORK / "analysis_charset.txt")]
    subprocess.run(cmd, cwd=BASE, check=True)
    split_path = Path(str(output_path) + ".splits.tsv")
    apply_postprocess(split_path, config_path, RULES)
    return split_path


def assemble_candidate(candidate, temp_dir):
    cfg = yaml.safe_load((WORK / "analysis_config.yaml").read_text(encoding="utf-8"))
    cfg["form"]["mapping"][candidate] = "a"
    custom = cfg.get("analysis", {}).get("customize", {})
    custom.pop(candidate, None)
    custom.pop(label(candidate), None)
    return assemble_config(cfg, temp_dir, f"夜莺B候选根检查-{label(candidate)}")


def assemble_group(group, temp_dir):
    cfg = yaml.safe_load((WORK / "analysis_config.yaml").read_text(encoding="utf-8"))
    host = group[0]
    cfg["form"]["mapping"][host] = "a"
    for item in group[1:]:
        cfg["form"]["mapping"][item] = {"element": host}
    custom = cfg.get("analysis", {}).get("customize", {})
    for item in group:
        custom.pop(item, None)
        custom.pop(label(item), None)
    title = "+".join(label(x) for x in group)
    return assemble_config(cfg, temp_dir, f"夜莺B候选根组检查-{title}")


def assemble_custom_split(part, split, temp_dir):
    cfg = yaml.safe_load((WORK / "analysis_config.yaml").read_text(encoding="utf-8"))
    cfg.setdefault("analysis", {}).setdefault("customize", {})[part] = split
    title = label(part) + "=" + "+".join(label(x) for x in split)
    return assemble_config(cfg, temp_dir, f"夜莺B候选拆分检查-{title}")


def forms(splits, readings):
    out = {}
    for c, rs in readings.items():
        if c not in splits:
            continue
        for _, code in rs:
            out[(c, code[:2])] = splits[c]
    return out


def short_state(form, freq, minimum, reading_freq=None):
    reading_freq = reading_freq or {(c, syl): freq[c] for c, syl in form}
    # 每个音节先拿掉唯一的二简字 ab；余下每个首根堆只有一个三码位 abx。
    two_code = {}
    for c, syl in form:
        if reading_freq[(c, syl)] < minimum:
            continue
        preferred = RULES.get("two_code_overrides", {}).get(str(syl))
        if preferred == c:
            two_code[syl] = c
        elif preferred != two_code.get(syl) and (syl not in two_code or
              (reading_freq[(c, syl)], c) > (reading_freq[(two_code[syl], syl)], two_code[syl])):
            two_code[syl] = c
    piles = defaultdict(set)
    for (c, syl), (head, _) in form.items():
        if reading_freq[(c, syl)] >= minimum and c != two_code.get(syl):
            piles[(syl, head)].add(c)
    losers = set()
    for (syl, head), chars in piles.items():
        preferred = RULES.get("short_code_overrides", {}).get(str(syl), {}).get(str(head))
        ordered = sorted(chars, key=lambda c: (c != preferred, -reading_freq[(c, syl)], -freq[c]))
        losers.update((c, syl) for c in ordered[1:])
    return losers, piles


def full_pairs(form):
    slots = defaultdict(set)
    for (c, syl), ht in form.items():
        slots[(syl, *ht)].add(c)
    pairs = set()
    for (syl, _, _), chars in slots.items():
        ordered = sorted(chars)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                pairs.add((syl, a, b))
    return pairs


def by_char(items, pair_mode=False):
    """把字音级问题汇总到整字；全码字对则给双方各登记一次。"""
    out = defaultdict(set)
    if pair_mode:
        for syl, a, b in items:
            out[a].add((syl, b))
            out[b].add((syl, a))
    else:
        for char, syl in items:
            out[char].add(syl)
    return out


def show_char_summary(title, old_items, new_items, pair_mode=False):
    old = by_char(old_items, pair_mode)
    new = by_char(new_items, pair_mode)
    clean_to_bad = sorted(c for c in new if c not in old)
    fully_saved = sorted(c for c in old if c not in new)
    partial_better = sorted(c for c in old.keys() & new.keys() if new[c] < old[c])
    partial_worse = sorted(c for c in old.keys() & new.keys() if new[c] > old[c])
    print(f"{title}整字新增风险：{len(clean_to_bad)}" +
          ("  " + " ".join(clean_to_bad[:20]) if clean_to_bad else ""))
    print(f"{title}整字完全获救：{len(fully_saved)}" +
          ("  " + " ".join(fully_saved[:20]) if fully_saved else ""))
    print(f"{title}整字部分改善（仍有其他读音/对象碰撞）：{len(partial_better)}" +
          ("  " + " ".join(partial_better[:20]) if partial_better else ""))
    print(f"{title}整字部分恶化（原本已有问题）：{len(partial_worse)}" +
          ("  " + " ".join(partial_worse[:20]) if partial_worse else ""))


def show_short(title, items, form, piles, freq):
    print(f"{title}：{len(items)}")
    for c, syl in sorted(items, key=lambda x: -freq[x[0]])[:16]:
        head, tail = form[(c, syl)]
        pile = sorted(piles[(syl, head)], key=lambda x: -freq[x])
        print(f"  {syl} {c}{freq[c]//10000} {head}-{tail} 堆=" +
              "/".join(f"{x}{freq[x]//10000}" for x in pile))


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: candidate_root_check.py 候选根 [三简最低频万]")
    raw_spec = sys.argv[1]
    custom_split = None
    if "=" in raw_spec:
        raw_part, raw_split = raw_spec.split("=", 1)
        group = [resolve(raw_part)]
        custom_split = [resolve(x) for x in raw_split.split("+")]
    else:
        group = [resolve(x) for x in raw_spec.split("+")]
    candidate = group[0]
    minimum = int(float(sys.argv[2]) * 10000) if len(sys.argv) > 2 else 10000

    # 每次先重建正式无根基线，杜绝规则文件更新后误用旧缓存。
    subprocess.run([sys.executable, str(HERE / "scripts/build_analysis.py"), "--run"], cwd=HERE, check=True)
    temp_dir = WORK / ".candidate_check"
    temp_dir.mkdir(exist_ok=True)
    current_cfg = yaml.safe_load((WORK / "analysis_config.yaml").read_text(encoding="utf-8"))
    current_mapping = current_cfg["form"]["mapping"]
    if custom_split is not None:
        base_splits = parse_splits(WORK / "analysis.tsv.splits.tsv", load_host())
        rooted_path = assemble_custom_split(candidate, custom_split, temp_dir)
        rooted_splits = parse_splits(rooted_path, load_host())
    elif len(group) == 1 and candidate in current_mapping:
        # 候选已落地：当前正式拆分是有根案，反向移除候选生成无根案。
        rooted_splits = parse_splits(WORK / "analysis.tsv.splits.tsv", load_host())
        current_mapping.pop(candidate, None)
        for key, value in list(current_mapping.items()):
            if isinstance(value, dict) and value.get("element") == candidate:
                current_mapping.pop(key)
        custom = current_cfg.get("analysis", {}).get("customize", {})
        for key, value in list(custom.items()):
            if candidate in value:
                custom.pop(key)
        base_path = assemble_config(current_cfg, temp_dir, f"夜莺B移除根检查-{label(candidate)}")
        base_splits = parse_splits(base_path, load_host(exclude=candidate))
    elif len(group) == 1:
        base_splits = parse_splits(WORK / "analysis.tsv.splits.tsv", load_host())
        rooted_path = assemble_candidate(candidate, temp_dir)
        rooted_splits = parse_splits(rooted_path, load_host(candidate))
    else:
        base_splits = parse_splits(WORK / "analysis.tsv.splits.tsv", load_host())
        rooted_path = assemble_group(group, temp_dir)
        rooted_splits = parse_splits(rooted_path, load_host(group))

    readings = load_readings(BASE / "work/v08/assets/readings.json")
    freq, _ = primary_readings(readings)
    reading_freq = aggregate_syllable_frequencies(readings)
    base = forms(base_splits, readings)
    rooted = forms(rooted_splits, readings)
    common = set(base) & set(rooted)
    changed = sorted((x for x in common if base[x] != rooted[x]), key=lambda x: -freq[x[0]])

    title = (label(candidate) + "=" + "+".join(label(x) for x in custom_split)
             if custom_split is not None else "+".join(label(x) for x in group))
    print(f"\n== {title}：无根拆开 vs 同键立根（全部字音；三简≥{minimum//10000}万）")
    print(f"边界改变：{len({c for c,_ in changed})}字 / {len(changed)}字音")
    for c, syl in changed[:24]:
        print(f"  {syl} {c}{freq[c]//10000}: {base[(c,syl)][0]}-{base[(c,syl)][1]} → "
              f"{rooted[(c,syl)][0]}-{rooted[(c,syl)][1]}")

    old_losers, old_piles = short_state(base, freq, minimum, reading_freq)
    new_losers, new_piles = short_state(rooted, freq, minimum, reading_freq)
    show_short("三简新增掉全码", new_losers - old_losers, rooted, new_piles, freq)
    show_short("三简获救", old_losers - new_losers, rooted, new_piles, freq)
    show_char_summary("三简", old_losers, new_losers)

    old_pairs = full_pairs(base)
    new_pairs = full_pairs(rooted)
    added, removed = new_pairs - old_pairs, old_pairs - new_pairs
    print(f"全码新增重码字对：{len(added)}")
    for syl, a, b in sorted(added, key=lambda x: -(freq[x[1]] + freq[x[2]]))[:16]:
        print(f"  {syl} {a}{freq[a]//10000}/{b}{freq[b]//10000} @{rooted[(a,syl)][0]}-{rooted[(a,syl)][1]}")
    print(f"全码解除重码字对：{len(removed)}")
    for syl, a, b in sorted(removed, key=lambda x: -(freq[x[1]] + freq[x[2]]))[:16]:
        print(f"  {syl} {a}{freq[a]//10000}/{b}{freq[b]//10000}")
    show_char_summary("全码", old_pairs, new_pairs, pair_mode=True)


if __name__ == "__main__":
    main()
