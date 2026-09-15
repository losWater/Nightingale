# -*- coding: utf-8 -*-
"""扩展字继承试算（只算不改表）：把 1.0 扩展字规范拆分（18770 字，1.0 根名）按 55 的同一套规则（别名归一、删根展开、新根还原、54 替换）
和 67 的 一＋止→正 转到 2.0 根表，统计多少字的根全部落在 2.0 根表里、哪些根对不上。"""
import io, sys, os, json, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
SRC = 'D:/nightingale/work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv'
read = lambda p: json.load(open(p, encoding='utf-8-sig'))
I = read(W + '/04_逐根删除评估/input.json'); norm = dict(I['norm']); inv = {x['id']: x['display'] for x in I['inventory']}
for x in I['inventory']: norm.setdefault(x['display'], x['id'])
audit = read(W + '/54_补删鹿旁保留羊南心四起点试跑/输入核验.json'); rep = {'利': ['禾', '刂'], **audit['替换']}
def expand(t): return [x for y in rep[t] for x in expand(y)] if t in rep else [t]
roots = read(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当前完整根表.json')['根组']
rid = {}; key = {}
for g in roots:
    for t, v in zip(g['根形ID'], g['根形']): inv[t] = v; rid[t] = g.get('键') or g.get('键位'); key[v] = g.get('键') or g.get('键位')
print('2.0 根表根组', len(roots), '根形', len(rid), ' 根组字段:', list(roots[0].keys()))
# 67 的正根：2.0 现行根表若已含 正 则直接用；否则把 一＋止 合成 正
cur = {}
for r in csv.DictReader(open(W + '/55_拆分继承核验/当前完整拆分表.txt', encoding='utf-8-sig'), delimiter='\t'): cur[r['汉字']] = r['完整拆分']
has_zheng = any('正' in v.split(' ＋ ') for v in cur.values()); print('2.0 现行拆分含 正 根:', has_zheng, ' 例 政:', cur.get('政'), ' 焉:', cur.get('焉'))
rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig'), delimiter='\t'))
ok = 0; bad = collections.Counter(); badchars = {}; out = {}
for r in rows:
    ch = r['汉字']; ts = [norm.get(t.strip(), t.strip()) for t in r['最终规范拆分'].split('＋') if t.strip()]
    ts = [x for t in ts for x in expand(t)]
    # 一＋止 → 正（与 67 同规则：相邻的 一 与 止 合并）
    m = []; i = 0
    while i < len(ts):
        if has_zheng and i + 1 < len(ts) and inv.get(ts[i], ts[i]) == '一' and inv.get(ts[i + 1], ts[i + 1]) == '止': m.append(norm.get('正', '正')); i += 2
        else: m.append(ts[i]); i += 1
    ts = m
    miss = [t for t in ts if t not in rid]
    if miss:
        for t in miss: bad[inv.get(t, t)] += 1
        badchars[ch] = [inv.get(t, t) for t in ts]
    else: ok += 1; out[ch] = [inv.get(t, t) for t in ts]
print('扩展字 %d：根全部落在 2.0 根表 %d，对不上 %d' % (len(rows), ok, len(badchars)))
print('对不上的根（前 40）:', bad.most_common(40))
print('对不上的字样例:', list(badchars.items())[:12])
json.dump({'来源': SRC, '可继承': out, '对不上': badchars, '对不上的根统计': dict(bad)}, open(H + '/继承试算.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
