# -*- coding: utf-8 -*-
"""数一数新华字典多出的 7391 字在 BCC 四语料 + SUBTLEX 里各出现多少次（只统计，不改表）。"""
import io, sys, os, json, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
X = json.load(open(H + '/候选字_初筛.json', encoding='utf-8'))
extra = set(X['多出']); trad = set(X['其中繁体旧字形'])
cnt = collections.defaultdict(collections.Counter)
for src in ['bcc_balanced', 'bcc_dialogue', 'bcc_news', 'bcc_literature']:
    for row in csv.reader(open(B + '/08_词库与词频重建/来源快照/%s.csv' % src, encoding='utf-8')):
        if len(row) < 2 or not row[1].isdigit(): continue
        n = int(row[1])
        for ch in set(row[0]):
            if ch in extra: cnt[ch][src] += n
j = json.load(open(B + '/08_词库与词频重建/来源快照/subtlex.json', encoding='utf-8'))
hi = j['headers']; iw = hi.index('Word'); ic = hi.index('WCount')
for r in j['data']:
    try: n = int(float(r[ic]))
    except Exception: continue
    for ch in set(r[iw]):
        if ch in extra: cnt[ch]['subtlex'] += n
tot = {ch: sum(c.values()) for ch, c in cnt.items()}
nont = {ch: n for ch, n in tot.items() if ch not in trad}
print('多出 %d 字：五源语料出现过 %d（非繁体 %d）' % (len(extra), len(tot), len(nont)))
bands = {'≥10000': (10000, 10**12), '1000-9999': (1000, 10000), '100-999': (100, 1000), '10-99': (10, 100), '1-9': (1, 10)}
print('非繁体按总次数:', {k: sum(1 for n in nont.values() if lo <= n < hi) for k, (lo, hi) in bands.items()})
print('繁体/旧字形按总次数:', {k: sum(1 for ch, n in tot.items() if ch in trad and lo <= n < hi) for k, (lo, hi) in bands.items()})
top = sorted(nont.items(), key=lambda x: -x[1])
print('非繁体出现最多的 80:', ' '.join('%s%d' % (c, n) for c, n in top[:80]))
print('1000-9999 段样例:', ''.join(c for c, n in top if 1000 <= n < 10000)[:150])
print('100-999 段样例:', ''.join(c for c, n in top if 100 <= n < 1000)[:150])
trtop = sorted(((c, n) for c, n in tot.items() if c in trad), key=lambda x: -x[1])[:30]
print('繁体出现最多的 30:', ' '.join('%s%d' % (c, n) for c, n in trtop))
json.dump({'口径': 'BCC 四语料（含该字的 token 计数之和）+ SUBTLEX WCount；只统计新华字典多出的 7391 字',
           '按字': {ch: {'总': tot[ch], '繁体旧字形': ch in trad, **dict(cnt[ch])} for ch in tot}},
          open(H + '/多出字_语料出现次数.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
