# -*- coding: utf-8 -*-
"""四元组重码评分器。

输入：assemble.ts 的输出 TSV + 提供音码键位的配置 yaml。
序列视角：(键1, 键2, 首根, 末根)——音码层小鹤双拼固定，先折算成实际按键；
字根保留元素名（键位未定）。

指标：
  零阶重码  同 (键1,键2,首根,末根) 的条目——任何键位安排都无解的硬重码
  一阶估计  差一个字根位的碰撞压力（边际分布平方和 / 2*25），排键位前可算
  加权零阶  按字频加权的选重损失（组内按频率降序，次位以后计入）

用法: python score.py <assembled.tsv> <config.yaml> [--charset 文件] [--name 标签]
"""
import argparse
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

def load_phonetic_keys(config_path):
    cfg = yaml.safe_load(open(config_path, encoding="utf-8"))
    keys = {}
    for k, v in cfg["form"]["mapping"].items():
        k = str(k)
        if (k.startswith("szm-") or k.startswith("mzm-")) and isinstance(v, str):
            keys[k] = v
    return keys

def load_entries(tsv_path, phon, charset=None):
    """返回 [(字, 键1键2, 首根, 末根, 频率)]，每个（字,序列）唯一。"""
    entries = []
    seen = set()
    for line in open(tsv_path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3 or len(p[0]) != 1:
            continue
        ch = p[0]
        if charset and ch not in charset:
            continue
        elems = []
        for tok in p[1].split(" "):
            try:
                e = json.loads(tok)
            except json.JSONDecodeError:
                continue
            elems.append(e["element"] if isinstance(e, dict) else str(e))
        if len(elems) != 4:
            continue
        e1, e2, r3, r4 = elems
        if e1 not in phon or e2 not in phon:
            continue  # 无读音或异常条目
        sig = (ch, phon[e1], phon[e2], r3, r4)
        if sig in seen:
            continue
        seen.add(sig)
        entries.append((ch, phon[e1] + phon[e2], r3, r4, int(p[2])))
    return entries

def score(entries, name="方案", top_show=12):
    n = len(entries)
    zero = defaultdict(list)
    for ch, pp, r3, r4, freq in entries:
        zero[(pp, r3, r4)].append((freq, ch))
    z_groups = {k: sorted(v, reverse=True) for k, v in zero.items() if len(v) > 1}
    z_count = sum(len(v) - 1 for v in z_groups.values())
    z_weight = sum(f for v in z_groups.values() for f, _ in v[1:])
    total_freq = sum(e[4] for e in entries) or 1

    # 一阶估计：固定 (键1键2, 首根) 边际 与 (键1键2, 末根) 边际
    KEYS = 25
    m_last = defaultdict(int)   # (pp, r3) -> 计数（末根位待化解）
    m_first = defaultdict(int)  # (pp, r4) -> 计数（首根位待化解）
    for ch, pp, r3, r4, freq in entries:
        m_last[(pp, r3)] += 1
        m_first[(pp, r4)] += 1
    d1_last = sum(c * (c - 1) for c in m_last.values()) / (2 * KEYS)
    d1_first = sum(c * (c - 1) for c in m_first.values()) / (2 * KEYS)
    d1 = d1_last + d1_first - 2 * sum(len(v) * (len(v) - 1) / 2 for v in z_groups.values()) / (2 * KEYS)

    print(f"== {name} ==")
    print(f"条目数: {n}")
    print(f"零阶重码(硬): 选重 {z_count} 条 / {len(z_groups)} 组; 频率加权损失 {z_weight/total_freq*100:.3f}%")
    print(f"一阶估计(键位压力): {d1:.0f}  (末根位 {d1_last:.0f} + 首根位 {d1_first:.0f} - 零阶扣除)")
    worst = sorted(z_groups.items(), key=lambda kv: -sum(f for f, _ in kv[1][1:]))[:top_show]
    print("高频零阶组 top:")
    for (pp, r3, r4), v in worst:
        chars = "".join(c for _, c in v)
        print(f"  {pp}+{r3}{r4}: {chars}  (损失频率 {sum(f for f,_ in v[1:])})")
    return {"n": n, "zero": z_count, "zero_w": z_weight / total_freq, "d1": d1}

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv")
    ap.add_argument("config")
    ap.add_argument("--charset", default=None, help="限定字集的码表文件(取每行首列单字)")
    ap.add_argument("--name", default="方案")
    a = ap.parse_args()
    charset = None
    if a.charset:
        charset = set()
        for line in open(a.charset, encoding="utf-8-sig"):
            p = line.rstrip("\n").split("\t")
            if p and len(p[0]) == 1:
                charset.add(p[0])
    phon = load_phonetic_keys(a.config)
    entries = load_entries(a.tsv, phon, charset)
    score(entries, a.name)
