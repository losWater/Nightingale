# -*- coding: utf-8 -*-
"""用户裁定（2026-09-14）：AABB 叠词不再挂在 AB 词的第 4 位（我们无四重），改为规则码（前三字首码+末字首码）；
凡叠词落入的码位，最多保留两个叠词（按 08 词频取高者），非叠词一律不动。改 62（第 2 步输入），随后重建 91。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
freq = {}
for line in open(B + '/08_词库与词频重建/综合词表_审计候选.jsonl', encoding='utf-8'):
    try: d = json.loads(line)
    except Exception: continue
    if d.get('词') and '排序指数' in d: freq.setdefault(d['词'], d['排序指数'])
reg = json.load(open(B + '/91_普通词表/非规则词登记表.json', encoding='utf-8'))['登记']['叠词写法(字1AB+字3AB)']
P62 = B + '/62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt'
chars = collections.defaultdict(set)
for line in open(P62, encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and len(p[0]) == 1 and p[1].isalpha(): chars[p[0]].add(p[1])
A = collections.defaultdict(set)
for w, cs in chars.items():
    for c in cs:
        if len(c) >= 4 and c not in TOL: A[w].add(c[0])
# 叠词 -> 规则码（多音字取字典序最小的一种；全部可推导）
rule = {}
for r in reg:
    w = r['词']
    tg = sorted({a + b + c + d for a in A[w[0]] for b in A[w[1]] for c in A[w[2]] for d in A[w[-1]]})
    rule[(w, r['码'])] = tg[0]
affected = {x for x in rule.values()}
aabb_set = {w for (w, c) in rule}
key = lambda w: (0 if w in freq else 1, -freq.get(w, 0))

FILES = [('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt', 'utf-8-sig', 'plain'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_码前格式.txt', 'utf-8-sig', 'code1st'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_手心格式.txt', 'utf-8-sig', 'shouxin'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_搜狗.txt', 'utf-16', 'sogou')]

def parse(l, f):
    if f == 'plain':
        p = l.split('\t'); return (p[1], p[0]) if len(p) >= 2 else (None, None)
    if f == 'code1st':
        p = l.split('\t'); return (p[0], p[1]) if len(p) >= 2 else (None, None)
    if f == 'shouxin':
        if '=' in l and ',' in l:
            c, r = l.split('=', 1); n, w = r.split(',', 1); return (c, w)
    if f == 'sogou':
        if '=' in l and ',' in l:
            le, w = l.split('=', 1); c, n = le.rsplit(',', 1); return (c, w)
    return (None, None)

def emit(c, w, i, f):
    return {'plain': w + '\t' + c, 'code1st': c + '\t' + w, 'shouxin': c + '=' + str(i) + ',' + w, 'sogou': c + ',' + str(i) + '=' + w}[f]

res = []; log = None
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict()
    for l in lines:
        c, w = parse(l, fmt)
        if c is not None: blocks.setdefault(c, []).append(w)
    alias_removed = 0
    for (w, c), t in rule.items():
        if c in blocks and w in blocks[c]:
            blocks[c].remove(w); alias_removed += 1
            if not blocks[c]: del blocks[c]
            if w not in blocks.get(t, []): blocks.setdefault(t, []).append(w)
    dropped = []; kept_detail = {}
    for t in sorted(affected):
        if t not in blocks: continue
        ch = [w for w in blocks[t] if len(w) == 1]; wd = [w for w in blocks[t] if len(w) > 1]
        others = [w for w in wd if w not in aabb_set]; ab = sorted([w for w in wd if w in aabb_set], key=key)
        keep, cut = ab[:2], ab[2:]                      # 上限只管叠词：每码最多两个叠词，非叠词一律不动
        if cut: dropped.extend((t, w) for w in cut)
        blocks[t] = ch + others + keep
        kept_detail[t] = keep
    out = [emit(c, w, i + 1, fmt) for c in sorted(blocks) for i, w in enumerate(blocks[c])]
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    if log is None: log = {'删别名': alias_removed, '影响码位': len(kept_detail), '删除词': dropped, '保留': kept_detail}
    res.append({'文件': rel, '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 行 %s  %s' % (rel.split('/')[-1], res[-1]['行数'], res[-1]['新sha256'][:16]))
aabb = {w for (w, c) in rule}
d_aabb = sum(1 for t, w in log['删除词'] if w in aabb); d_other = len(log['删除词']) - d_aabb
print('\n删叠词别名 %d；影响码位 %d；删除 %d 个词（其中叠词 %d、其他词 %d）' % (log['删别名'], log['影响码位'], len(log['删除词']), d_aabb, d_other))
print('被删的非叠词样例：', '、'.join('%s(%s)' % (w, t) for t, w in log['删除词'] if w not in aabb)[:400])
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '裁定': '叠词改规则码；叠词所落码位最多保留两个词，按08词频',
           '叠词改码': {'%s|%s' % k: v for k, v in rule.items()}, '结果': {'删别名': log['删别名'], '影响码位': log['影响码位'],
           '删除词': [{'码': t, '词': w, '词频': freq.get(w)} for t, w in log['删除词']], '保留': log['保留']}, '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
