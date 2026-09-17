# -*- coding: utf-8 -*-
"""把试验版部署到独立目录 E:/ymt（不碰 D:/rime_data），用小狼毫 0.17.4 引擎实跑，对照夜莺固定码表。"""
import io, sys, os, shutil, subprocess, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); PKG = H + '/夜莺魔虎试验版'; T = 'E:/ymt'
fresh = '--fresh' in sys.argv
if fresh and os.path.isdir(T): shutil.rmtree(T)
for root, dirs, files in os.walk(PKG):
    rel = os.path.relpath(root, PKG); d = os.path.join(T, rel); os.makedirs(d, exist_ok=True)
    for fn in files:
        if fn == '生成清单.json': continue
        shutil.copy2(os.path.join(root, fn), os.path.join(d, fn))
m = T + '/mohu/model/mohu-sentence-ngram-v5.bin'
if not os.path.exists(m): os.link(H + '/upstream/model/mohu-sentence-ngram-v5.bin', m)
# default.yaml：独立目录里没有小狼毫自带的，用上游的
shutil.copy2(H + '/upstream/pkg/default.yaml', T + '/default.yaml')
g = collections.defaultdict(list)
for l in open(PKG + '/mohu_flypy_fixed.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) == 2: g[f[1]].append(f[0])
cases = [a for a in sys.argv[1:] if not a.startswith('--')] or ['a', 'q', 'no', 'by', 'dd', 'ddm', 'wwt', 'wwts', 'yeby', 'yeyk', 'ykmg', 'yruf', 'uivj', 'jihv', 'uql', 'mwld', 'vgss', 'qtxb', 'nihc', 'bb', 'jvb',
         'woxihrni', 'wobuvidc', 'jbtmtmqibucoxdcwigqusjbu', 'nikeyibhvegewfjmfagzwoma', 'yeykuuruwaiguvdeyigeuurufa']
out = open(H + '/engine.tsv', 'wb'); err = open(H + '/engine.log', 'wb')
p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', T, 'mohu_flypy', 'maintenance'], input=('\n'.join(cases) + '\n').encode(), stdout=out, stderr=err, timeout=900)
out.close(); err.close(); print('退出码', p.returncode)
bad = 0
for l in open(H + '/engine.tsv', encoding='utf-8'):
    f = l.rstrip('\n').split('\t'); c, cands = f[0], f[3:]
    exp = g.get(c, [])[:5]; ok = cands[:len(exp)] == exp
    if exp and not ok: bad += 1
    print('%s %s  引擎: %s%s  [%sms]' % ('✓' if ok else '✗', c, ' '.join(cands[:7]), '' if ok else '   码表: ' + ' '.join(exp), f[1][:6]))
print('不一致', bad)
print(open(H + '/engine.log', encoding='utf-8', errors='replace').read()[-1500:])
