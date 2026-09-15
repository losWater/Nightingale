# -*- coding: utf-8 -*-
"""扩展字继承试算四：在试算三之上，把 2.0 新增整根按 55 的"新根还原"反向合并（散序列 → 整根），先回归 8105，再套扩展字；
然后草拟扩展字全码：声码取 1.0 扩展字表的前两位（1.0 也是小鹤双拼），首根/末根 → 根组 → 键（键从 58 数据学）。只算不改表。"""
import io, sys, os, json, csv, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
SRC = 'D:/nightingale/work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv'
read = lambda p: json.load(open(p, encoding='utf-8-sig'))
I = read(W + '/04_逐根删除评估/input.json'); norm = dict(I['norm']); inv = {x['id']: x['display'] for x in I['inventory']}
for x in I['inventory']: norm.setdefault(x['display'], x['id'])
audit = read(W + '/54_补删鹿旁保留羊南心四起点试跑/输入核验.json'); rep = {'利': ['禾', '刂'], **audit['替换']}
ptr = read(W + '/54_补删鹿旁保留羊南心四起点试跑/二简人工复核/当前裁定基线.json'); roots = read(ptr['根表'])['根组']
rid = set(); grp = {}
for g in roots:
    for t, v in zip(g['根形ID'], g['根形']): inv[t] = v; rid.add(t); norm.setdefault(v, t); grp[v] = g['根组']
ZH = norm.get('正', '正')
R55 = read(W + '/55_拆分继承核验/局部替换规则.json'); rules = R55['删根展开']; newroot = R55['新根还原']
learned = {'享字头': ['亠', '口'], '肄左': ['匕', '矢'], '贤字头': ['丨', '丨', '又'], '览字头': ['丨', '丨', '𠂉', '丶']}
def nid(t): return norm.get(t, t)
def expand(t, depth=0):
    if t in rid or depth > 8: return [t]
    if t in rep: return [x for y in rep[t] for x in expand(y, depth + 1)]
    d = inv.get(t, t)
    if d in learned: return [x for y in learned[d] for x in expand(nid(y), depth + 1)]
    if d in rules: return [x for y in rules[d] if y != '' for x in expand(nid(y), depth + 1)]
    return [t]
# 新根合并表：新根 display → 其 1.0 序列（展开到 2.0 根 ID），长序列优先
merges = []
for nr, seq in newroot.items():
    if not nr or nr not in norm: continue
    ids = [x for y in seq if y != '' for x in expand(nid(y))]
    if ids: merges.append((ids, nid(nr)))
merges.append(([nid('一'), nid('止')], ZH))
merges.sort(key=lambda x: -len(x[0]))
def merge(ts):
    out = []; i = 0
    while i < len(ts):
        for seq, r in merges:
            if ts[i:i + len(seq)] == seq: out.append(r); i += len(seq); break
        else: out.append(ts[i]); i += 1
    return out
def convert(text): return merge([x for t in text.split('＋') if t.strip() for x in expand(nid(t.strip()))])
show = lambda ts: ' ＋ '.join(inv.get(t, t) for t in ts)
cur = {r['汉字']: r['完整拆分'] for r in csv.DictReader(open(W + '/55_拆分继承核验/当前完整拆分表.txt', encoding='utf-8-sig'), delimiter='\t')}
old = {r['汉字']: r['最终规范拆分'] for r in csv.DictReader(open('E:/夜莺2.0/releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt', encoding='utf-8-sig'), delimiter='\t')}
manual = set(read(W + '/04_逐根删除评估/active-baseline.json')['manual'])
hit = 0; diffs = []
for ch, v in old.items():
    got = show(convert(v))
    if got == cur.get(ch): hit += 1
    else: diffs.append((ch, got, cur.get(ch), '人工' if ch in manual else ''))
nonman = [d for d in diffs if not d[3]]
print('回归：8105 复现 %d/%d，不同 %d（人工覆写 %d，非人工 %d）' % (hit, len(old), len(diffs), len(diffs) - len(nonman), len(nonman)))
print('非人工不同样例:', nonman[:15])
# 首末根是否一致（编码只看首末根）
s = open(W + '/58_拆分查询/夜莺2.0拆分查询.html', encoding='utf-8-sig').read(); m = re.search(r'\bconst D\s*=\s*', s); D = json.JSONDecoder().raw_decode(s[m.end():])[0]
rk = {}
for r in D.values():
    for g in r['根']: rk.setdefault(g['组'], g['键'])
keyof = lambda disp: rk.get(grp.get(disp))
fe_ok = sum(1 for ch, got, c, _ in diffs if c and got.split(' ＋ ')[0] == c.split(' ＋ ')[0] and got.split(' ＋ ')[-1] == c.split(' ＋ ')[-1])
print('不同的 %d 个里首末根仍一致（编码不受影响）的: %d' % (len(diffs), fe_ok))
# 扩展字
rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig'), delimiter='\t'))
ext10 = collections.defaultdict(list)
for l in open('E:/夜莺2.0/releases/v1.0/01_正式码表/夜莺码v1.0扩展字表.tsv', encoding='utf-8-sig').read().splitlines()[1:]:
    p = l.split('\t')
    if len(p) >= 2: ext10[p[0]].append(p[1])
ok = {}; bad = {}; codes = {}; nokey = collections.Counter(); same10 = 0; tot10 = 0
for r in rows:
    ch = r['汉字']; ts = convert(r['最终规范拆分'])
    if any(t not in rid for t in ts): bad[ch] = show(ts); continue
    disp = [inv[t] for t in ts]; ok[ch] = ' ＋ '.join(disp)
    k1, k2 = keyof(disp[0]), keyof(disp[-1])
    if not k1 or not k2: nokey[disp[0] if not k1 else disp[-1]] += 1; continue
    cs = []
    for c10 in ext10.get(ch, []):
        c = c10[:2] + k1 + k2; cs.append(c); tot10 += 1; same10 += (c == c10)
    codes[ch] = sorted(set(cs))
print('扩展字 %d：拆分可继承 %d，对不上 %d；首末根无键 %d %s；拟码 %d 字（与 1.0 码相同 %d/%d，不同是键位/根集变化所致）' % (len(rows), len(ok), len(bad), sum(nokey.values()), nokey.most_common(5), len(codes), same10, tot10))
print('拟码样例:', list(codes.items())[:10])
# 与 8105 撞码
ours = collections.defaultdict(list)
for l in open(W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    p = l.strip().split('\t')
    if len(p) >= 2 and len(p[1]) == 4: ours[p[1]].append(p[0])
allc = collections.Counter(c for cs in codes.values() for c in cs)
print('扩展字全码 %d 个码位；与 8105 全码撞 %d 个码位；扩展字之间重码 %d 个码位（最多 %d 字）' % (len(allc), sum(1 for c in allc if c in ours), sum(1 for c, n in allc.items() if n > 1), max(allc.values())))
json.dump({'回归不同': diffs, '拆分': ok, '对不上': bad, '拟码': codes}, open(H + '/继承试算4.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
