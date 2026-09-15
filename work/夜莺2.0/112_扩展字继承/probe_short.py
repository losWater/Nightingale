# -*- coding: utf-8 -*-
"""扩展字简码试算：对全部扩展字重数语料次数（BCC 四语料 + SUBTLEX），看语料出现过、且二简/三简位空着（110 最终表里该码位无任何字词）的有多少。只算不改表。"""
import io, sys, os, json, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
codes = json.load(open(H + '/继承试算5.json', encoding='utf-8'))['拟码']
ext = set(codes)
cnt = collections.Counter()
for src in ['bcc_balanced', 'bcc_dialogue', 'bcc_news', 'bcc_literature']:
    for row in csv.reader(open(W + '/08_词库与词频重建/来源快照/%s.csv' % src, encoding='utf-8')):
        if len(row) < 2 or not row[1].isdigit(): continue
        for ch in set(row[0]):
            if ch in ext: cnt[ch] += int(row[1])
j = json.load(open(W + '/08_词库与词频重建/来源快照/subtlex.json', encoding='utf-8')); hi = j['headers']; iw = hi.index('Word'); ic = hi.index('WCount')
for r in j['data']:
    try: n = int(float(r[ic]))
    except Exception: continue
    for ch in set(r[iw]):
        if ch in ext: cnt[ch] += n
json.dump(dict(cnt), open(H + '/扩展字_语料次数.json', 'w', encoding='utf-8'), ensure_ascii=False)
occ = set()
for l in open(W + '/110_词序三家投票/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) >= 2: occ.add(p[1])
seen = {ch: n for ch, n in cnt.items() if n > 0}
print('扩展字 %d：语料出现过 %d（≥100 次 %d，≥10 次 %d）' % (len(ext), len(seen), sum(1 for n in seen.values() if n >= 100), sum(1 for n in seen.values() if n >= 10)))
get2 = {}; get3 = {}
for ch, n in seen.items():
    for c in codes[ch]:
        if c[:2] not in occ: get2.setdefault(ch, []).append(c[:2])
        elif c[:3] not in occ: get3.setdefault(ch, []).append(c[:3])
print('二简位空着的: %d 字；三简位空着的（二简已占）: %d 字' % (len(get2), len(get3)))
top = sorted(seen.items(), key=lambda x: -x[1])
print('语料前 40 及其可得简码:', ' '.join('%s%d%s' % (ch, n, ('/二' + '|'.join(get2[ch])) if ch in get2 else ('/三' + '|'.join(get3[ch])) if ch in get3 else '') for ch, n in top[:40]))
print('拿到二简的样例:', list(get2.items())[:15])
json.dump({'二简': get2, '三简': get3}, open(H + '/扩展字_可得简码.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
