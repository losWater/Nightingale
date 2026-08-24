# -*- coding: utf-8 -*-
"""整合二字词，并按完整小鹤双拼四码聚合为退火障碍位。"""
from __future__ import annotations
import csv, json, math
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
DOCS = BASE / "documents"
PUBLIC = DOCS / "public_sources"
OUT = BASE / "work" / "lexicon"
LIMIT = 60_000

def valid(w): return len(w) == 2 and all("\u3400" <= c <= "\u9fff" for c in w)

def decode(path):
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")): return raw.decode("utf-16")
    for enc in ("utf-8-sig", "gb18030"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    raise UnicodeError(path)

def ime_words(path):
    out = set()
    for line in decode(path).splitlines():
        a = line.strip().split("\t")
        w = a[1] if len(a) >= 2 and a[0].isascii() else (a[0] if a else "")
        if valid(w): out.add(w)
    return out

def ranked_counts(path, word_key="token", count_key="count"):
    d = {}
    for row in csv.DictReader(path.open(encoding="utf-8")):
        w = row.get(word_key, "")
        if valid(w): d[w] = int(float(row.get(count_key, 0)))
    return d

def rank_scores(counts):
    ordered = sorted(counts, key=lambda w: (-counts[w], w)); n = len(ordered)
    return {w: 1 - math.log(i) / math.log(n + 1) for i, w in enumerate(ordered, 1)}

def main():
    codes = {}
    for line in (ROOT / "work" / "夜莺码_大词库编码版.txt").read_text(encoding="utf-8").splitlines():
        a = line.split("\t")
        if len(a) >= 2 and valid(a[0]) and len(a[1]) == 4: codes.setdefault(a[0], a[1])

    simple = ime_words(next(DOCS.glob("简单鹤*.txt")))
    tiger = ime_words(DOCS / "冰虎词库3.0.txt")
    ice = set()
    for p in DOCS.glob("冰凌词库*.txt"): ice |= ime_words(p)

    corp = {}
    for n in ("dialogue_word_freq", "literature_word_freq", "multi_domain_total_word_freq", "news_total_word_freq"):
        corp[n] = ranked_counts(PUBLIC / n / f"{n}.txt")
    subraw = json.loads((PUBLIC / "SUBTLEX-CH-WF.json").read_text(encoding="utf-8"))["data"]
    corp["subtlex"] = {r["Word"]: int(r.get("WCount", 0)) for r in subraw if valid(r.get("Word", ""))}
    ranks = {n: rank_scores(d) for n, d in corp.items()}

    candidates = (simple | tiger | ice | set().union(*(set(d) for d in corp.values()))) & set(codes)
    rows = []
    for w in candidates:
        written = max((ranks[n].get(w, 0) for n in ("literature_word_freq", "multi_domain_total_word_freq", "news_total_word_freq")), default=0)
        dialogue = ranks["dialogue_word_freq"].get(w, 0)
        subtitle = ranks["subtlex"].get(w, 0)
        # 语料排名主导；输入法家族只提供较弱的人工收词证据。
        score = 1.2*written + 1.3*dialogue + 1.3*subtitle + .6*(w in simple) + .4*(w in tiger) + .4*(w in ice)
        groups = sum((written > 0, dialogue > 0, subtitle > 0, w in simple, w in tiger, w in ice))
        rows.append({"word":w,"code":codes[w],"score":score,"groups":groups,"written":written,
                     "dialogue":dialogue,"subtitle":subtitle,"simple":int(w in simple),
                     "tiger":int(w in tiger),"ice":int(w in ice)})
    rows.sort(key=lambda r: (-r["score"], -r["groups"], r["word"]))
    selected = rows[:LIMIT]
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(selected[0])
    with (OUT/"二字词_精选60000.tsv").open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=fields,delimiter="\t");wr.writeheader();wr.writerows(selected)
    (OUT/"二字词_精选60000.txt").write_text("\n".join(f"{r['word']}\t{r['code']}" for r in selected)+"\n",encoding="utf-8")

    slots=defaultdict(list)
    for rank,r in enumerate(selected,1): slots[r["code"]].append((rank,r))
    slotrows=[]
    for code,items in slots.items():
        # 候选位权重采用词条综合分之和；同时保留最强词和词数。
        slotrows.append({"code":code,"weight":sum(x[1]["score"] for x in items),"word_count":len(items),
                         "top_rank":min(x[0] for x in items),"words":" ".join(x[1]["word"] for x in items)})
    slotrows.sort(key=lambda r:(-r["weight"],r["code"]))
    with (OUT/"二字词_四码位.tsv").open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=["code","weight","word_count","top_rank","words"],delimiter="\t");wr.writeheader();wr.writerows(slotrows)
    report=["# 二字词整合报告","",f"- 可编码候选：{len(rows):,}",f"- 精选词条：{len(selected):,}",
            f"- 聚合四码位：{len(slotrows):,}",f"- 平均每码位：{len(selected)/len(slotrows):.2f} 词",
            f"- 最拥挤码位：{max(x['word_count'] for x in slotrows)} 词","","当前为权重透明的第一版，尚未接入退火。"]
    (OUT/"二字词整合报告.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print("\n".join(report));print("前100词："+" ".join(r["word"] for r in selected[:100]))

if __name__ == "__main__": main()
