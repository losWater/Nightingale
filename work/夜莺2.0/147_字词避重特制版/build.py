# -*- coding: utf-8 -*-
"""字词避重特制版综合表（2026-09-22，测试用，不进正式发布）。
规则：字频前 5000、且没有简码的字，它的每个四码全码位上的多字词全部删掉；简词（码长不足四码）不动。
「有简码」口径同 145：有一个码长 < 4 的码（容错码 TOL 不算）。
来源：发布目录的综合表，其余条目原样保留、顺序不变。
"""
import io, sys, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
sys.path.insert(0, W + '/00_维护'); from 版本 import VER, RELEASE_DIR
SRC = RELEASE_DIR + '/01_正式码表/夜莺%s综合表.txt' % VER
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
rank = {e['字']: e['字频'] for e in json.load(open(W + '/59_单字当量排行/单字当量排行.json', encoding='utf-8'))}
raw = open(SRC, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf'); nl = '\r\n' if b'\r\n' in raw else '\n'
rows = [l.split('\t') for l in raw.decode('utf-8-sig').splitlines()]
codes = collections.defaultdict(set)
for f in rows:
    if len(f) >= 2 and len(f[0]) == 1: codes[f[0]].add(f[1])
hasS = lambda w: any(len(c) < 4 and c not in TOL for c in codes[w])
guard = {}   # 四码位 → 守位的字
for w, cs in codes.items():
    if rank.get(w, 99999) <= 5000 and not hasS(w):
        for c in cs:
            if len(c) == 4: guard.setdefault(c, []).append(w)
out = []; dele = []
for f in rows:
    if len(f) >= 2 and f[1] in guard and len(f[0]) > 1: dele.append((f[1], f[0])); continue
    out.append('\t'.join([f[1], f[0]] + f[2:]))            # 码前：码在前、字词在后
name = '夜莺%s字词避重特制版综合表_码前.txt' % VER
open(H + '/' + name, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline=nl).write('\n'.join(out) + '\n')
by = collections.defaultdict(list)
for c, t in dele: by[c].append(t)
with open(H + '/删除清单.txt', 'w', encoding='utf-8-sig', newline='\r\n') as g:
    g.write('码\t守位的字\t删掉的词\n')
    for c in sorted(by): g.write('%s\t%s\t%s\n' % (c, '、'.join(guard[c]), '、'.join(by[c])))
nw = sum(1 for f in rows if len(f) >= 2 and len(f[0]) > 1)
print('守位字 %d 个，涉及四码位 %d 个；其中有词的码位 %d 个' % (
    sum(1 for w in codes if rank.get(w, 99999) <= 5000 and not hasS(w)), len(guard), len(by)))
print('删词 %d 条（原表多字词 %d 条，删去 %.1f%%）；综合表 %d → %d 条' % (len(dele), nw, len(dele) / nw * 100, len(rows), len(out)))
for c in list(sorted(by))[:8]: print('  %s  %s ← 删 %s' % (c, '、'.join(guard[c]), '、'.join(by[c])))
print('→ %s/%s\n→ %s/删除清单.txt' % (H, name, H))
