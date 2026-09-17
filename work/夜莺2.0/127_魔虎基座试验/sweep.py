# -*- coding: utf-8 -*-
"""随机抽 3000 个码位（各码长都有），核对试验版前 5 个候选与夜莺固定码表次序一致。"""
import io, sys, os, random, subprocess, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); g = collections.defaultdict(list)
for l in open(H + '/夜莺魔虎试验版/mohu_flypy_fixed.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) == 2 and f[1].isalpha() and len(f[1]) <= 4: g[f[1]].append(f[0])
rnd = random.Random(127); codes = [c for c in g if len(c) <= 2] + rnd.sample([c for c in g if len(c) == 3], 1000) + rnd.sample([c for c in g if len(c) == 4], 3000 - 1000)
p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', 'E:/ymt', 'mohu_flypy'], input=('\n'.join(codes) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3000)
assert p.returncode == 0, p.stderr[-400:]
bad = []; n = collections.Counter()
for l in p.stdout.decode('utf-8').splitlines():
    f = l.split('\t'); c = f[0]; exp = g[c][:5]; n[len(c)] += 1
    if f[3:3 + len(exp)] != exp: bad.append('%s  引擎 %s | 码表 %s' % (c, ' '.join(f[3:8]), ' '.join(exp)))
print('抽检', dict(n), '不一致', len(bad)); open(H + '/码位抽检不一致.txt', 'w', encoding='utf-8').write('\n'.join(bad) + '\n'); print('\n'.join(bad[:25]))
