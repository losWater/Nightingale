# -*- coding: utf-8 -*-
"""按字频档看：每档有多少字的全码"长得像二字词"（后两键是合法音节），其中多少有简码（会让位）、多少没有（字占首选）。"""
import io, sys, os, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
syls = {r['音码'] for r in J(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/字音基准.json')}
rank = {r['字']: r['新排名'] for r in J(W + '/32_多来源字频重建/试验整字频率.json')['字表']}
full = collections.defaultdict(list); short = collections.defaultdict(set)
for l in open(W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    q = l.rstrip('\r\n').split('\t')
    if len(q) < 2 or len(q[0]) != 1: continue
    (full[q[0]].append(q[1]) if len(q[1]) == 4 else short[q[0]].add(q[1]))
bands = [('1–500', 1, 500), ('501–1500', 501, 1500), ('1501–3000', 1501, 3000), ('3001–6000', 3001, 6000), ('6001–8105', 6001, 99999)]
rows = []; lines = ['# 按字频档：全码像二字词的字', '', '| 字频档 | 字数 | 全码像二字词 | 占比 | 有简码(让位) | 无简码(字占首选) | 无简码的字 |', '|---|---|---|---|---|---|---|']
for name, a, b in bands:
    cs = [c for c in full if a <= rank.get(c, 99999) <= b]
    like = [c for c in cs if any(k[:2] in syls and k[2:] in syls for k in full[c])]
    ys = [c for c in like if short.get(c)]; ns = sorted([c for c in like if not short.get(c)], key=lambda c: rank[c])
    rows.append({'档': name, '字数': len(cs), '像二字词': len(like), '有简码': len(ys), '无简码': len(ns), '无简码字': ns})
    lines.append('| %s | %d | %d | %.1f%% | %d | %d | %s |' % (name, len(cs), len(like), len(like) / len(cs) * 100, len(ys), len(ns), ''.join(ns[:60]) + ('…' if len(ns) > 60 else '')))
json.dump(rows, open(H + '/按字频档.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(H + '/按字频档.md', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
