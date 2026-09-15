# -*- coding: utf-8 -*-
"""用户裁定（2026-09-14）：62 无简词表为唯一维护的词表，64 含简词表退役（成品表移入弃用目录，裁定记录保留）。
随后把 62 中残留的字位飞键（一/也/要/都/时 及 yi 音字首码 e→y）按 62 自身的表补还原（85 的计划按 64 生成，未覆盖 62 独有条目）。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
KNOWN = {'一': ('e', 'y'), '也': ('a', 'y'), '要': ('a', 'y'), '都': ('o', 'd'), '时': ('o', 'u')}

# —— 1. 64 退役 ——
R = B + '/64_加入鲸凉鹤简词/弃用_含简词旧表'
os.makedirs(R, exist_ok=True)
moved = []
for fn in ('夜莺2.0含简词字词表_普通格式.txt', '夜莺2.0含简词字词表_码前格式.txt'):
    src = B + '/64_加入鲸凉鹤简词/' + fn
    if os.path.exists(src):
        sha = hashlib.sha256(open(src, 'rb').read()).hexdigest()
        shutil.move(src, R + '/' + fn); moved.append({'文件': fn, 'sha256': sha})
open(R + '/README.txt', 'w', encoding='utf-8').write(
    '2026-09-14 用户裁定：62 无简词表为唯一维护的词表，本目录两张含简词成品表退役，仅作历史与简词阶段的输入参考。\n'
    '不要再向这两张表写入。64 目录内的 码位人工指定.json、简词人工裁定.json 等裁定记录继续有效。\n'
    + json.dumps(moved, ensure_ascii=False, indent=1))
print('64 成品表已移入 弃用_含简词旧表/：', [m['文件'] for m in moved])

# —— 2. 62 飞键补还原（计划按 62 自身表推导）——
P62 = B + '/62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt'
codes = collections.defaultdict(set)
for line in open(P62, encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and p[1].isalpha(): codes[p[0]].add(p[1])
AB = collections.defaultdict(set); A = collections.defaultdict(set)
for w, cs in codes.items():
    if len(w) != 1: continue
    for c in cs:
        if len(c) >= 4 and c not in TOL: AB[w].add(c[:2]); A[w].add(c[0])

def derive(word):
    n = len(word)
    if any(ch not in AB for ch in word): return None
    if n == 2: return {a + b for a in AB[word[0]] for b in AB[word[1]]}
    if n == 3: return {a + b + c for a in A[word[0]] for b in A[word[1]] for c in AB[word[2]]}
    return {a + b + c + d for a in A[word[0]] for b in A[word[1]] for c in A[word[2]] for d in A[word[-1]]}

def posmap(word):
    n = len(word)
    if n == 2: return {0: (word[0], 0), 1: (word[0], 1), 2: (word[1], 0), 3: (word[1], 1)}
    if n == 3: return {0: (word[0], 0), 1: (word[1], 0), 2: (word[2], 0), 3: (word[2], 1)}
    return {0: (word[0], 0), 1: (word[1], 0), 2: (word[2], 0), 3: (word[-1], 0)}

is_yi = lambda ch: AB.get(ch) == {'yi'}
plan = {}
for w, cs in codes.items():
    if len(w) < 2: continue
    d = derive(w)
    if not d: continue
    for c in cs:
        if len(c) != 4 or c in d: continue
        h, x = min(((sum(a != b for a, b in zip(c, y)), y) for y in d))
        pm = posmap(w); ok = True
        for i in [i for i in range(4) if c[i] != x[i]]:
            ch, slot = pm[i]; a, b = c[i], x[i]
            if ch in KNOWN and KNOWN[ch] == (a, b): continue
            if slot == 0 and (a, b) == ('e', 'y') and is_yi(ch): continue
            ok = False; break
        if ok: plan[(w, c)] = x
print('62 需补还原的飞键条目：%d' % len(plan))

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

res = []
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict()
    for l in lines:
        c, w = parse(l, fmt)
        if c is not None: blocks.setdefault(c, []).append(w)
    moved_n = merged = 0
    for (w, c), x in plan.items():
        if c in blocks and w in blocks[c]:
            blocks[c].remove(w)
            if not blocks[c]: del blocks[c]
            if w in blocks.get(x, []): merged += 1
            else: blocks.setdefault(x, []).append(w); moved_n += 1
    out = [emit(c, w, i + 1, fmt) for c in sorted(blocks) for i, w in enumerate(blocks[c])]
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    res.append({'文件': rel, '迁码': moved_n, '合并': merged, '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 迁%4d 合%4d 行 %d→%d  %s' % (rel.split('/')[-1], moved_n, merged, len(lines), len(out), res[-1]['新sha256'][:16]))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '裁定': '留 62 退 64', '64退役': moved,
           '62飞键补还原': [{'词': w, '旧码': c, '新码': x} for (w, c), x in sorted(plan.items())], '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
