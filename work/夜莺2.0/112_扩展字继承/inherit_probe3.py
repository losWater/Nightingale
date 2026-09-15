# -*- coding: utf-8 -*-
"""扩展字继承试算三：试算一的做法（别名归一到根 ID + 54 替换）再叠 55 的删根展开与四个学来的映射（享字头→亠口、肄左→匕矢、贤字头→丨丨又、览字头→丨丨𠂉丶），
一＋止→正。同规则先在 8105 上回归（1.0 拆分 → 规则 → 应等于 2.0 现行拆分），再套到 18770 扩展字。只算不改表。"""
import io, sys, os, json, csv, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
SRC = 'D:/nightingale/work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv'
read = lambda p: json.load(open(p, encoding='utf-8-sig'))
I = read(W + '/04_逐根删除评估/input.json'); norm = dict(I['norm']); inv = {x['id']: x['display'] for x in I['inventory']}
for x in I['inventory']: norm.setdefault(x['display'], x['id'])
audit = read(W + '/54_补删鹿旁保留羊南心四起点试跑/输入核验.json'); rep = {'利': ['禾', '刂'], **audit['替换']}
ptr = read(W + '/54_补删鹿旁保留羊南心四起点试跑/二简人工复核/当前裁定基线.json'); roots = read(ptr['根表'])['根组']
rid = set()
for g in roots:
    for t, v in zip(g['根形ID'], g['根形']): inv[t] = v; rid.add(t); norm.setdefault(v, t)
ZH = norm.get('正', '正'); print('正 的根 ID:', repr(ZH), ' 在根表:', ZH in rid)
rules = read(W + '/55_拆分继承核验/局部替换规则.json')['删根展开']
learned = {'享字头': ['亠', '口'], '肄左': ['匕', '矢'], '贤字头': ['丨', '丨', '又'], '览字头': ['丨', '丨', '𠂉', '丶']}
def nid(t): return norm.get(t, t)
def expand(t, depth=0):
    if t in rid or depth > 8: return [t]
    if t in rep: return [x for y in rep[t] for x in expand(y, depth + 1)]
    d = inv.get(t, t)
    if d in learned: return [x for y in learned[d] for x in expand(nid(y), depth + 1)]
    if d in rules: return [x for y in rules[d] if y != '' for x in expand(nid(y), depth + 1)]
    return [t]
def convert(text):
    ts = [x for t in text.split('＋') if t.strip() for x in expand(nid(t.strip()))]
    mm = []; i = 0
    while i < len(ts):
        if i + 1 < len(ts) and inv.get(ts[i], ts[i]) == '一' and inv.get(ts[i + 1], ts[i + 1]) == '止': mm.append(ZH); i += 2
        else: mm.append(ts[i]); i += 1
    return mm
show = lambda ts: ' ＋ '.join(inv.get(t, t) for t in ts)
cur = {r['汉字']: r['完整拆分'] for r in csv.DictReader(open(W + '/55_拆分继承核验/当前完整拆分表.txt', encoding='utf-8-sig'), delimiter='\t')}
old = {r['汉字']: r['最终规范拆分'] for r in csv.DictReader(open('E:/夜莺2.0/releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt', encoding='utf-8-sig'), delimiter='\t')}
manual = set(read(W + '/04_逐根删除评估/active-baseline.json')['manual'])
hit = 0; diffs = []
for ch, v in old.items():
    got = show(convert(v))
    if got == cur.get(ch): hit += 1
    else: diffs.append((ch, got, cur.get(ch), '人工' if ch in manual else ''))
print('回归：8105 复现 %d/%d，不同 %d（其中人工覆写 %d）；非人工不同样例:' % (hit, len(old), len(diffs), sum(1 for d in diffs if d[3])), [d for d in diffs if not d[3]][:10])
rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig'), delimiter='\t'))
ok = {}; bad = collections.Counter(); badchars = {}
for r in rows:
    ch = r['汉字']; ts = convert(r['最终规范拆分'])
    miss = [t for t in ts if t not in rid]
    if miss:
        for t in miss: bad[inv.get(t, t)] += 1
        badchars[ch] = show(ts)
    else: ok[ch] = show(ts)
print('扩展字 %d：可继承 %d，对不上 %d；对不上的根:' % (len(rows), len(ok), len(badchars)), bad.most_common(30))
print('对不上样例:', list(badchars.items())[:12])
json.dump({'可继承': ok, '对不上': badchars, '对不上的根': dict(bad), '回归不同': diffs}, open(H + '/继承试算3.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
