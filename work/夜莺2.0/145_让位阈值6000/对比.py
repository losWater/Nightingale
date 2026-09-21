# -*- coding: utf-8 -*-
"""字词让位阈值 5000 → 6000 的影响（2026-09-22，大佬提议）。只读。
规则（码表概念与规则.md 第五节第 5 条，97/build.py 第 33 行）：四码位上首个是二字词、且该码位所有单字都
「有简码 或 字频排名 > 阈值」时，词排第一、字全部让到后面。阈值改 6000，排名 5001–6000、又没有简码的字就不再
让位；一个码位只要有一个这样的字，整组字都回到词前面。
按现行主表模拟：找现在「二字词在首位、字在后」的码位，看哪些会因阈值变成 6000 而回退。
人工指定码位、第 5 条第 7 款的逐条裁定码位、补音字（第 5b 条永远让位）都不动。
"""
import io, sys, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else H; W = os.path.dirname(H)
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
EXC = {'xmic', 'xime', 'vatk', 'xkyb', 'bcpg', 'jiyt'}
man = set(json.load(open(W + '/64_加入鲸凉鹤简词/码位人工指定.json', encoding='utf-8-sig')))
rank = {e['字']: e['字频'] for e in json.load(open(W + '/59_单字当量排行/单字当量排行.json', encoding='utf-8'))}
buyin = json.load(open(W + '/83_单字表重放/补音表.json', encoding='utf-8'))['条目']
buyin_pairs = {(t, c) for c, ts in buyin.items() for t in (ts if isinstance(ts, list) else [ts])}
slot = collections.defaultdict(list); codes = collections.defaultdict(set)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); slot[c].append(t)
    if len(t) == 1: codes[t].add(c)
hasS = lambda w: any(len(c) < 4 and c not in TOL for c in codes[w])
back = []
for c, v in slot.items():
    if len(c) != 4 or c in man or c in EXC or len(v[0]) != 2: continue
    ch = [w for w in v if len(w) == 1 and (w, c) not in buyin_pairs]
    if not ch: continue
    blockers = [w for w in ch if not hasS(w) and 5000 < rank.get(w, 99999) <= 6000]
    if blockers: back.append((c, v, blockers))
print('阈值 5000 → 6000：会回到词前面的码位 %d 个\n' % len(back))
for c, v, b in sorted(back, key=lambda x: rank.get(x[2][0], 0)):
    ch = [w for w in v if len(w) == 1]; wd = [w for w in v if len(w) > 1]
    print('  %s  现 %-20s → %-20s  回来的字：%s' % (c, '、'.join(v), '、'.join(ch + wd),
          '、'.join('%s(第%d名)' % (w, rank.get(w, 0)) for w in b)))
json.dump([{'码': c, '现序': v, '回来的字': b, '排名': [rank.get(w) for w in b]} for c, v, b in back],
          open(H + '/对比结果.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
