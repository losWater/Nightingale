# -*- coding: utf-8 -*-
"""C 阶段第一步：从四家机读数据源提取字根清单，生成投票矩阵。

选民：
  jd1  简单鹤1.0   data/jdhe/简单鹤初稿20240512.yaml  form.mapping/grouping（主根+附属根，权威）
  jd93 简单鹤9.3   data/jdhe/拆分表_解码.txt          每字首末根
  moqi 墨奇音形    data/raw/moqi_chaifen.txt          每字完整部件序列
  hu   虎码        data/raw/hu_cf.txt                 每字完整部件序列

统计口径：参照字集 = 简单鹤1.0 纯单版的单字集合（约7791字）。
每家对每个部件记两个数：
  chars   参照字集内、该家拆分中用到此部件的字数
  fl      参照字集内、此部件出现在首/末位置的字数（对音形方案这才是有效负担）
"""
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
JDHE = BASE / "data" / "jdhe"
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)


# 同根异码别名表：笔画根三家记法互认 + 无争议的 Unicode 字形变体
ALIASES = {
    "1": "一", "2": "丨", "3": "丿", "4": "丶", "5": "乙", "6": "乙",
    "横": "一", "竖": "丨", "撇": "丿", "点": "丶", "折": "乙",
    "乚": "乙", "㇀": "一",
    "⺝": "月", "リ": "刂", "⺍": "⺌", "⺧": "牜", "⺩": "王",
    "⻊": "足", "〢": "刂", "⺀": "冫", "⺫": "罒", "⺜": "曰",
}


def norm(c: str) -> str:
    """部件字形归一化：康熙部首/兼容字符折叠到统一区 + 别名归并。"""
    if not c:
        return c
    n = unicodedata.normalize("NFKC", c)
    n = n if n else c
    return ALIASES.get(n, n)


def cps(c: str) -> str:
    return "+".join(f"U+{ord(x):04X}" for x in c)


def load_refset():
    chars = set()
    for line in open(JDHE / "简单鹤V1.0纯单版.txt", encoding="utf-8-sig"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and len(parts[0]) == 1:
            chars.add(parts[0])
    return chars


def extract_jd1():
    """1.0 权威根表：yaml 的 mapping（主根）+ grouping（附属根→主根）。无用字统计，只有名单。"""
    import yaml
    cfg = yaml.safe_load(open(JDHE / "简单鹤初稿20240512.yaml", encoding="utf-8"))
    mapping = cfg["form"]["mapping"]
    grouping = cfg["form"].get("grouping", {})
    rep = cfg.get("data", {}).get("repertoire", {})
    names = {k: v.get("name", "") for k, v in rep.items()}
    main, attached = {}, {}
    for k, v in mapping.items():
        if isinstance(k, str) and (k.startswith("szm-") or k.startswith("mzm-")):
            continue
        main[norm(str(k))] = {"key": v, "name": names.get(k, "")}
    for k, v in grouping.items():
        attached[norm(str(k))] = {"to": norm(str(v)), "name": names.get(k, "")}
    return main, attached


def extract_jd93(refset):
    """9.3 拆分表：字→首末根。"""
    chars_of = defaultdict(set)
    fl_of = defaultdict(set)
    pat = re.compile(r"^(.)\t〔(.+?)¦")
    for line in open(JDHE / "拆分表_解码.txt", encoding="utf-8"):
        m = pat.match(line)
        if not m:
            continue
        ch, comps = m.group(1), m.group(2)
        if ch not in refset:
            continue
        for c in comps:
            chars_of[norm(c)].add(ch)
        if comps:
            fl_of[norm(comps[0])].add(ch)
            fl_of[norm(comps[-1])].add(ch)
    return chars_of, fl_of


def extract_moqi(refset):
    chars_of = defaultdict(set)
    fl_of = defaultdict(set)
    for line in open(RAW / "moqi_chaifen.txt", encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3 or len(parts[0]) != 1:
            continue
        ch, comps = parts[0], parts[2]
        if ch not in refset:
            continue
        for c in comps:
            chars_of[norm(c)].add(ch)
        if comps:
            fl_of[norm(comps[0])].add(ch)
            fl_of[norm(comps[-1])].add(ch)
    return chars_of, fl_of


def extract_hu(refset):
    chars_of = defaultdict(set)
    fl_of = defaultdict(set)
    pat = re.compile(r"^(.)\t〔(.+?)(?:&nbsp;)*·(?:&nbsp;)*[a-z]+〕")
    for line in open(RAW / "hu_cf.txt", encoding="utf-8"):
        m = pat.match(line)
        if not m:
            continue
        ch = m.group(1)
        comps = m.group(2).replace("&nbsp;", "").strip()
        if ch not in refset:
            continue
        for c in comps:
            chars_of[norm(c)].add(ch)
        if comps:
            fl_of[norm(comps[0])].add(ch)
            fl_of[norm(comps[-1])].add(ch)
    return chars_of, fl_of


def main():
    refset = load_refset()
    print(f"参照字集: {len(refset)} 字")

    jd1_main, jd1_att = extract_jd1()
    print(f"jd1: {len(jd1_main)} 主根 + {len(jd1_att)} 附属根")

    schemes = {}
    for name, fn in [("jd93", extract_jd93), ("moqi", extract_moqi), ("hu", extract_hu)]:
        chars_of, fl_of = fn(refset)
        schemes[name] = (chars_of, fl_of)
        cover = len(set().union(*chars_of.values())) if chars_of else 0
        print(f"{name}: {len(chars_of)} 部件, 覆盖参照字集 {cover} 字")

    # 各家清单落盘
    for name, (chars_of, fl_of) in schemes.items():
        with open(WORK / f"roots_{name}.tsv", "w", encoding="utf-8") as f:
            f.write("部件\tcodepoint\t用字数\t首末位用字数\n")
            for c in sorted(chars_of, key=lambda x: -len(chars_of[x])):
                f.write(f"{c}\t{cps(c)}\t{len(chars_of[c])}\t{len(fl_of.get(c, ()))}\n")
    with open(WORK / "roots_jd1.tsv", "w", encoding="utf-8") as f:
        f.write("部件\tcodepoint\t键\t类型\t备注\n")
        for c, info in jd1_main.items():
            f.write(f"{c}\t{cps(c)}\t{info['key']}\t主根\t{info['name']}\n")
        for c, info in jd1_att.items():
            f.write(f"{c}\t{cps(c)}\t→{info['to']}\t附属根\t{info['name']}\n")

    # 投票矩阵：jd1 只按名单投票（主根1票/附属根0.5票），其余按“首末位用字数>=阈值”投票
    THRESH = 3  # 首末位用字数低于此的部件视为边角料，不计票
    all_comps = set(jd1_main) | set(jd1_att)
    for chars_of, fl_of in schemes.values():
        all_comps |= {c for c in fl_of if len(fl_of[c]) >= THRESH}

    rows = []
    for c in all_comps:
        votes = 0.0
        cells = []
        if c in jd1_main:
            votes += 1; cells.append("主")
        elif c in jd1_att:
            votes += 0.5; cells.append("附")
        else:
            cells.append("")
        usage = []
        for name in ("jd93", "moqi", "hu"):
            fl = len(schemes[name][1].get(c, ()))
            usage.append(fl)
            if fl >= THRESH:
                votes += 1
                cells.append(str(fl))
            else:
                cells.append(f"({fl})" if fl else "")
        total_fl = sum(usage)
        rows.append((votes, total_fl, c, cells))

    rows.sort(key=lambda r: (-r[0], -r[1]))
    with open(WORK / "vote_matrix.tsv", "w", encoding="utf-8") as f:
        f.write("部件\tcodepoint\t票数\tjd1\tjd93首末\tmoqi首末\thu首末\t首末合计\n")
        for votes, total_fl, c, cells in rows:
            f.write(f"{c}\t{cps(c)}\t{votes}\t" + "\t".join(cells) + f"\t{total_fl}\n")

    # 汇总
    tiers = defaultdict(int)
    for votes, *_ in rows:
        tiers[votes] += 1
    print("\n票数分布:")
    for v in sorted(tiers, reverse=True):
        print(f"  {v} 票: {tiers[v]} 个部件")
    print(f"\n输出: {WORK}/vote_matrix.tsv 及 roots_*.tsv")


if __name__ == "__main__":
    main()
