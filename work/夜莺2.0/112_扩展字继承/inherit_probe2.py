# -*- coding: utf-8 -*-
"""扩展字继承试算二：根表改用当前裁定基线的 当前完整根表.json（含 67 的 正）；1.0 根名对不上的按 55 的删根展开 + 从 8105 现行拆分学到的映射
（享字头→亠口、肄左→匕矢、贤字头→丨丨又、览字头→丨丨𠂉丶）；根→键 用 58 拆分查询数据。只算不改表。"""
import io, sys, os, json, csv, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
SRC = 'D:/nightingale/work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv'
read = lambda p: json.load(open(p, encoding='utf-8-sig'))
ptr = read(W + '/54_补删鹿旁保留羊南心四起点试跑/二简人工复核/当前裁定基线.json'); print('基线:', ptr['目录'].split('\\')[-1])
roots = read(ptr['根表'])['根组']; names = {v for g in roots for v in g['根形']}
print('根表 根组 %d 根形 %d，含 正: %s' % (len(roots), len(names), '正' in names))
# 根→键：从 58 的 D 学（每个字的 根 列表带 键）
s = open(W + '/58_拆分查询/夜莺2.0拆分查询.html', encoding='utf-8-sig').read(); m = re.search(r'\bconst D\s*=\s*', s); D = json.JSONDecoder().raw_decode(s[m.end():])[0]
rk = {}
for r in D.values():
    for g in r['根']: rk.setdefault(g['根'], g['键'])
print('根→键 学到 %d 个根；与根表比：根表有而无键 %s' % (len(rk), sorted(names - set(rk))[:20]))
rules = read(W + '/55_拆分继承核验/局部替换规则.json')['删根展开']
learned = {'享字头': ['亠', '口'], '肄左': ['匕', '矢'], '贤字头': ['丨', '丨', '又'], '览字头': ['丨', '丨', '𠂉', '丶'], '正': ['正']}
def expand(t):
    if t in names: return [t]
    if t in learned: return [x for y in learned[t] for x in expand(y)]
    if t in rules: return [x for y in rules[t] for x in expand(y) if y != '']
    return [t]
cur = {r['汉字']: r['完整拆分'] for r in csv.DictReader(open(W + '/55_拆分继承核验/当前完整拆分表.txt', encoding='utf-8-sig'), delimiter='\t')}
rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig'), delimiter='\t'))
ok = {}; bad = collections.Counter(); badchars = {}
for r in rows:
    ch = r['汉字']; ts = [x for t in r['最终规范拆分'].split('＋') if t.strip() for x in expand(t.strip())]
    mm = []; i = 0
    while i < len(ts):
        if i + 1 < len(ts) and ts[i] == '一' and ts[i + 1] == '止': mm.append('正'); i += 2
        else: mm.append(ts[i]); i += 1
    ts = mm
    miss = [t for t in ts if t not in names]
    if miss:
        for t in miss: bad[t] += 1
        badchars[ch] = ts
    else: ok[ch] = ts
print('扩展字 %d：可继承 %d，对不上 %d；对不上的根:' % (len(rows), len(ok), len(badchars)), bad.most_common(30))
print('对不上样例:', list(badchars.items())[:10])
# 8105 里用同一套规则回归验证：1.0 拆分 → 规则 → 是否等于 2.0 现行拆分（人工覆写的字除外，看命中率）
old = {r['汉字']: r['最终规范拆分'] for r in csv.DictReader(open('E:/夜莺2.0/releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt', encoding='utf-8-sig'), delimiter='\t')}
hit = tot = 0; diffs = []
for ch, v in old.items():
    ts = [x for t in v.split('＋') if t.strip() for x in expand(t.strip())]
    mm = []; i = 0
    while i < len(ts):
        if i + 1 < len(ts) and ts[i] == '一' and ts[i + 1] == '止': mm.append('正'); i += 2
        else: mm.append(ts[i]); i += 1
    tot += 1; got = ' ＋ '.join(mm)
    if got == cur.get(ch): hit += 1
    else: diffs.append((ch, got, cur.get(ch)))
print('回归验证：8105 里同规则复现 2.0 现行拆分 %d/%d，不同 %d（多为人工覆写）；样例:' % (hit, tot, len(diffs)), diffs[:8])
json.dump({'可继承': ok, '对不上': badchars, '对不上的根': dict(bad), '回归不同': diffs}, open(H + '/继承试算2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
