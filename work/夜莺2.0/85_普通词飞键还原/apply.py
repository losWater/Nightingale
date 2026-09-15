# -*- coding: utf-8 -*-
"""普通词（四码词）字位飞键还原：一 e→y、也 a→y、要 a→y、都 o→d、时 o→u，以及 yi 音字首码 e→y（意/壹等）。
判定：词的实际码不可由单字表推导，且与最近合法码的差异全部落在上述字位替换上 → 改为该合法码。
处理：若目标码已有同词 → 仅删旧条；否则删旧条、在目标码块末尾追加。手心/搜狗重编序号。
A（AABB叠词）、B（s→u）、E（模糊音）、G（非8105字符）按用户裁定保留；D（特设短语）另行处理。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
KNOWN = {'一': ('e', 'y'), '也': ('a', 'y'), '要': ('a', 'y'), '都': ('o', 'd'), '时': ('o', 'u')}

codes = collections.defaultdict(set)
for line in open(B + '/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt', encoding='utf-8-sig'):
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

def is_yi(ch):
    return 'yi' in AB.get(ch, set()) and len(AB[ch]) == 1

plan = {}   # (词, 旧码) -> 新码
for w, cs in codes.items():
    if len(w) < 2: continue
    d = derive(w)
    if not d: continue
    for c in cs:
        if len(c) != 4 or c in d: continue
        h, x = min(((sum(a != b for a, b in zip(c, y)), y) for y in d))
        pm = posmap(w)
        diffs = [(i, c[i], x[i]) for i in range(4) if c[i] != x[i]]
        ok = True
        for i, a, b in diffs:
            ch, slot = pm[i]
            if ch in KNOWN and KNOWN[ch] == (a, b): continue
            if slot == 0 and (a, b) == ('e', 'y') and is_yi(ch): continue
            ok = False; break
        if ok: plan[(w, c)] = x
print('计划还原 %d 条' % len(plan))
by = collections.Counter()
for (w, c), x in plan.items():
    for i in range(4):
        if c[i] != x[i]: by[posmap(w)[i][0] if posmap(w)[i][0] in KNOWN else 'yi音首码e→y'] += 1
print('  按字位：', dict(by))

FILES = [('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt', 'utf-8-sig', 'plain'),
         ('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_码前格式.txt', 'utf-8-sig', 'code1st'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt', 'utf-8-sig', 'plain'),
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

res = []; applied_main = None
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict(); other = []
    for l in lines:
        c, w = parse(l, fmt)
        if c is None: other.append(l); continue
        blocks.setdefault(c, []).append(w)
    keys = list(blocks)
    assert keys == sorted(keys), ('文件码序非字典序', rel)
    removed = 0; moved = 0; dropped = 0
    for (w, c), x in plan.items():
        if c in blocks and w in blocks[c]:
            blocks[c].remove(w); removed += 1
            if not blocks[c]: del blocks[c]
            if w in blocks.get(x, []): dropped += 1
            else: blocks.setdefault(x, []).append(w); moved += 1
    out = other[:]  # 非条目行（应为空）
    for c in sorted(blocks):
        for i, w in enumerate(blocks[c]): out.append(emit(c, w, i + 1, fmt))
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    res.append({'文件': rel, '删旧条': removed, '迁入新码': moved, '目标已有同词而合并': dropped,
                '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 删%4d 迁%4d 合并%3d 行 %d→%d  %s' % (rel.split('/')[-1], removed, moved, dropped, len(lines), len(out), res[-1]['新sha256'][:16]))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '裁定': 'C 还原；A/B/E/G 保留；D 另行处理',
           '计划': [{'词': w, '旧码': c, '新码': x} for (w, c), x in sorted(plan.items())], '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
