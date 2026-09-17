# -*- coding: utf-8 -*-
"""Rime 主力版引擎关卡：全新独立目录部署 → 抽 3000 码位核对前 5 候选与码表一致 + 反查 + 整句样例。任何一项不过即返回非零。"""
import io, sys, os, shutil, subprocess, random, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); PKG = H + '/夜莺魔虎试验版'; T = 'E:/ymt'
if os.path.isdir(T): shutil.rmtree(T)          # 本脚本自己的测试目录
for root, _, fs in os.walk(PKG):
    d = os.path.join(T, os.path.relpath(root, PKG)); os.makedirs(d, exist_ok=True)
    for fn in fs:
        if fn != '生成清单.json': shutil.copy2(os.path.join(root, fn), os.path.join(d, fn))
os.link(H + '/upstream/model/mohu-sentence-ngram-v5.bin', T + '/mohu/model/mohu-sentence-ngram-v5.bin'); shutil.copy2(H + '/upstream/pkg/default.yaml', T + '/default.yaml')
g = collections.defaultdict(list)
for l in open(PKG + '/mohu_flypy_fixed.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) == 2 and f[1].isalpha() and len(f[1]) <= 4: g[f[1]].append(f[0])
rnd = random.Random(127); codes = [c for c in g if len(c) <= 2] + rnd.sample([c for c in g if len(c) == 3], 1000) + rnd.sample([c for c in g if len(c) == 4], 2000)
extra = ['`vg', '~zheng', 'woxihrni', 'wobuvidc']
p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', T, 'mohu_flypy', 'maintenance'], input=('\n'.join(codes + extra) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3000)
assert p.returncode == 0, p.stderr[-600:]
res = {l.split('\t')[0]: l.rstrip('\n').split('\t')[3:] for l in p.stdout.decode('utf-8').splitlines()}
bad = [c for c in codes if res.get(c, [])[:min(5, len(g[c]))] != g[c][:5]]
ok = not bad and '正' in res['`vg'] and '正' in res['~zheng'] and res['woxihrni'][:1] == ['我喜欢你'] and res['wobuvidc'][:1] == ['我不知道']
print('码位抽检 %d，不一致 %d %s；反查 %s；整句 %s / %s' % (len(codes), len(bad), bad[:5], '通过' if '正' in res['`vg'] else '失败', res['woxihrni'][:1], res['wobuvidc'][:1]))
print('main PASS' if ok else 'main FAIL'); sys.exit(0 if ok else 1)
