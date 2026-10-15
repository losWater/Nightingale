"""测评站口径汇总：前1500（1-300/301-500/501-1500）最短码 3码/4码字数、全码重（区间字的全码与前 hi 字中另一字相同）、形部大跨排/小指干扰（扣掉 1→2）。"""
import collections, json, os, sys
ROOT = os.path.expanduser('~/Yozakura')
M = json.load(open(ROOT + '/eval/box/combo.json'))
fr = [p[0] for p in (l.rstrip('\n').split('\t') for l in open(ROOT + '/eval/box/默认字频.txt', encoding='utf-8-sig')) if len(p) >= 2]
fin = {}
for row in ('qwert', 'asdfg', 'zxcvb'):
    for i, k in enumerate(row): fin[k] = ('L', [0, 1, 2, 3, 3][i])
for row in ('yuiop', 'hjkl;', 'nm,./'):
    for i, k in enumerate(row): fin[k] = ('R', [3, 3, 2, 1, 0][i])
PD = lambda a, b: fin[a][0] == fin[b][0] and {fin[a][1], fin[b][1]} == {0, 1}
def stats(path):
    codes = collections.defaultdict(list)
    for l in open(path, encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2 and len(p[0]) == 1: codes[p[0]].append(p[1])
    S = {c: min(v, key=len) for c, v in codes.items()}; L = {c: max(v, key=len) for c, v in codes.items()}
    o = collections.defaultdict(list)
    for lo, hi in ((0, 300), (300, 500), (500, 1500)):
        cnt = collections.Counter(L[x] for x in fr[:hi]); c = collections.Counter()
        for ch in fr[lo:hi]:
            s = S[ch]; c['3码'] += len(s) == 3; c['4码'] += len(s) == 4; c['全码重'] += cnt[L[ch]] > 1
            for i in range(1, len(s) - 1):
                c['形部大跨'] += bool(M[s[i:i + 2]]['ms']); c['形部小指'] += PD(s[i], s[i + 1])
            for i in range(len(s) - 1):
                c['大跨(全)'] += bool(M[s[i:i + 2]]['ms']); c['小指(全)'] += PD(s[i], s[i + 1])
        for k in ('3码', '4码', '全码重', '形部大跨', '形部小指', '大跨(全)', '小指(全)'): o[k].append(c[k])
    return o
H = os.path.expanduser('~/Downloads/')
T = [('夜莺3.1', ROOT + '/release/tables/普通单字表.txt'), ('精修16组', H + '夜桜_精修16组_普通单字表.txt')] + [tuple(x.split('=')) for x in sys.argv[1:]]
K = ('3码', '4码', '全码重', '形部大跨', '形部小指', '大跨(全)', '小指(全)')
print('方案       | ' + ' | '.join(K))
for n, p in T:
    o = stats(p); print(f'{n:10s} | ' + ' | '.join('/'.join(map(str, o[k])) + f'={sum(o[k])}' for k in K))
