# -*- coding: utf-8 -*-
"""迁词/增词/增字之后，按既定字词让位规则（第五节 1–5a）重排受影响码位。对象：62（第 2 步输入）。可重复运行。"""
import io, sys, os, json, collections, hashlib, shutil, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
EXC = {'xmic', 'xime', 'vatk', 'xkyb', 'bcpg', 'jiyt'}   # 84 逐条裁定：字优先
rank = {e['字']: e['字频'] for e in json.load(open(B + '/59_单字当量排行/单字当量排行.json', encoding='utf-8'))}
man = json.load(open(B + '/64_加入鲸凉鹤简词/码位人工指定.json', encoding='utf-8-sig'))
codes = collections.defaultdict(set)
for line in open(B + '/62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt', encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and p[1].isalpha() and len(p[0]) == 1: codes[p[0]].add(p[1])
hasS = lambda w: any(c not in TOL and len(c) < 4 for c in codes[w])

def target(F, blk):
    ch = [w for w in blk if len(w) == 1]; wd = [w for w in blk if len(w) > 1]
    if not ch or not wd or len(F) != 4 or F in man or F in EXC: return blk
    ok = len(wd[0]) == 2 and all(hasS(w) or rank.get(w, 99999) > 5000 for w in ch)
    return (wd[:1] + ch + wd[1:]) if ok else ch + wd

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

stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
os.makedirs(H + '/实装前备份_' + stamp, exist_ok=True)
res = []; chg0 = None
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份_' + stamp + '/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict()
    for l in lines:
        c, w = parse(l, fmt)
        if c is not None: blocks.setdefault(c, []).append(w)
    chg = {}
    for c in blocks:
        t = target(c, blocks[c])
        if t != blocks[c]: chg[c] = (blocks[c], t); blocks[c] = t
    out = [emit(c, w, i + 1, fmt) for c, ws in blocks.items() for i, w in enumerate(ws)]
    open(src, 'wb').write(nl.join(out + ([tail] if tail is not None else [])).encode(enc))
    if chg0 is None: chg0 = chg
    res.append({'文件': rel, '调整码位': len(chg), '新sha256': hashlib.sha256(open(src, 'rb').read()).hexdigest()})
    print('%-46s 调整 %d 码位  %s' % (rel.split('/')[-1], len(chg), res[-1]['新sha256'][:16]))
for c, (a, b) in list(chg0.items())[:10]: print('   %-5s [%s] → [%s]' % (c, '、'.join(a), '、'.join(b)))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '改动': {c: {'前': a, '后': b} for c, (a, b) in chg0.items()}, '文件': res},
          open(H + '/实装报告_' + stamp + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
