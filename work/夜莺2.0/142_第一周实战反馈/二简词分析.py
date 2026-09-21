# -*- coding: utf-8 -*-
"""分析 D:/qqfile/补夜莺二简.txt 要加的二简词（2026-09-22）。只读。
每行「词 码」，同码按文件顺序；标（删除）的是要删。
对照主表字词表：该码位现在有什么（字在前、简词在后），词是否已存在，是否合二字简词规则（两字双拼首码）。
"""
import io, sys, os, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
lines = [l.strip() for l in open('D:/qqfile/补夜莺二简.txt', encoding='utf-8-sig') if l.strip()]
add = []; dele = []
for l in lines:
    m = re.fullmatch(r'(\S+)\s+([a-z]+)\s*(（删除）)?', l)
    if not m: print('看不懂的行：', l); continue
    (dele if m.group(3) else add).append((m.group(1), m.group(2)))
ci = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); ci[c].append(t)
# 单字全码 → 取双拼首码（字的前两码里的第一码就是声母键）
sp = collections.defaultdict(set)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(c) == 4: sp[t].add(c[0])
print('要加 %d 条，要删 %d 条，涉及二码位 %d 个\n' % (len(add), len(dele), len({c for _, c in add})))
print('要删：')
for w, c in dele:
    print('  %s %s   现在该码位：%s   %s' % (w, c, '、'.join(ci.get(c, [])) or '空', '存在' if w in ci.get(c, []) else '！主表里本来就没有'))
exist = [(w, c) for w, c in add if w in ci.get(c, [])]
print('\n已经在该码位上的（不用加，但顺序可能要按文件调）：%d 条：%s' % (len(exist), ' '.join('%s%s' % x for x in exist)))
norule = [(w, c) for w, c in add if len(w) != 2 or not (c[0] in sp.get(w[0], set()) and c[1] in sp.get(w[1], set()))]
print('\n不合「两字双拼首码」规则的：%d 条：%s' % (len(norule), ' '.join('%s %s' % x for x in norule)))
# 每个码位：现状 vs 加完后
print('\n各码位现状（单字/简词混排的现序）与这次要加的：')
byc = collections.OrderedDict()
for w, c in add: byc.setdefault(c, []).append(w)
for c, ws in byc.items():
    cur = ci.get(c, [])
    chars = [x for x in cur if len(x) == 1]; words = [x for x in cur if len(x) > 1]
    print('  %-3s 现：字[%s] 词[%s]   加：%s' % (c, ''.join(chars), '、'.join(words), '、'.join(ws)))
