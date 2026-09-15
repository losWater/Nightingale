# -*- coding: utf-8 -*-
"""语料实战单字测评：一万句逐字打，有简打简，双口径选重。

每字取码表最短码（同长取真实位靠前者）。候选位双口径：
  真实位   —— 码表原样（词/符号占位计入）
  纯单字位 —— 同码下仅单字排位（中和“四码字默认次选”类字词分离设计）
上屏键：位≤3计1键（空格或选重键），位>3计2键（翻页）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from typing_simulation import load_table

HANCHAR = re.compile(r"^[一-鿿]$")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("table", type=Path)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--format", choices=["xinxin", "sogou", "plain"], default="xinxin")
    ap.add_argument("--policy", choices=["shortest", "avoid-select"], default="shortest",
                    help="shortest=无脑最短码；avoid-select=优先能上首选的最短码，无首选码才认选重")
    args = ap.parse_args()

    code_cands, word_codes = load_table(args.table, args.format)
    chars_at_code = {code: [c for _, c in cands if HANCHAR.fullmatch(c)]
                     for code, cands in code_cands.items()}

    lookup: dict[str, tuple] = {}

    def char_info(ch: str):
        if ch in lookup:
            return lookup[ch]
        entries = word_codes.get(ch)
        if not entries:
            lookup[ch] = None
            return None
        if args.policy == "avoid-select":
            firsts = [e for e in entries if e[1] == 1]
            code, real_pos = min(firsts, key=lambda t: len(t[0])) if firsts                 else min(entries, key=lambda t: (len(t[0]), t[1]))
        else:
            code, real_pos = min(entries, key=lambda t: (len(t[0]), t[1]))
        pure = chars_at_code.get(code, [])
        pure_pos = pure.index(ch) + 1 if ch in pure else real_pos
        info = (len(code), real_pos, pure_pos)
        lookup[ch] = info
        return info

    n_chars = keys_net = 0
    sel_real = sel_pure = 0.0
    first_real = first_pure = three_ok = 0
    keys_real = keys_pure = 0
    pos_real_sum = pos_pure_sum = 0
    by_src = defaultdict(lambda: [0, 0, 0])   # chars, keys_real, sel_real
    skipped = 0
    for line in args.corpus.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        source, text = parts[1], parts[3]
        infos = [char_info(c) for c in text]
        if any(i is None for i in infos):
            skipped += 1
            continue
        for L, rp, pp in infos:
            n_chars += 1
            keys_net += L
            kr = L + (1 if rp <= 3 else 2)
            kp = L + (1 if pp <= 3 else 2)
            keys_real += kr
            keys_pure += kp
            first_real += rp == 1
            first_pure += pp == 1
            sel_real += rp > 1
            sel_pure += pp > 1
            three_ok += L <= 3
            pos_real_sum += rp
            pos_pure_sum += pp
            by_src[source][0] += 1
            by_src[source][1] += kr
            by_src[source][2] += rp > 1

    report = {
        "table": str(args.table.resolve()),
        "语料": str(args.corpus.resolve()),
        "跳过句": skipped, "总字次": n_chars,
        "净码长": keys_net / n_chars,
        "码长_含上屏_真实位": keys_real / n_chars,
        "码长_含上屏_纯单字位": keys_pure / n_chars,
        "首选率_真实位": first_real / n_chars,
        "首选率_纯单字位": first_pure / n_chars,
        "选重率_真实位": sel_real / n_chars,
        "选重率_纯单字位": sel_pure / n_chars,
        "字词分离税": (sel_real - sel_pure) / n_chars,
        "三码内比例": three_ok / n_chars,
        "平均真实位": pos_real_sum / n_chars,
        "平均纯单字位": pos_pure_sum / n_chars,
        "分体裁": {s: {"字次": v[0], "码长真实位": v[1] / v[0], "选重率真实位": v[2] / v[0]}
                   for s, v in sorted(by_src.items())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "分体裁"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
