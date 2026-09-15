# -*- coding: utf-8 -*-
"""用户裁定（2026-09-14）：按简单鹤"强规范打词规则"清理普通词表中由语法功能字拼出的二字词。
- 动词+助词类（末字 了着过呢吗吧啊的）全部保留（语料分词会切开它们，词频不可信；且它们是真词）
- 其余含功能字的二字词：六源语料零出现者删除，出现过者保留
对象：62（第 2 步输入）；随后重建 91。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
FUNC = set('的地得所了着过呢吗吧啊' '你我他她它这那哪此谁咱' '都也就还又才很太最不没别只仅全总再已正要曾刚将仍常能必' '个只' '〇零一二三四五六七八九十百千万亿两')
PART = set('了着过呢吗吧啊的')
hits = {}
for line in open(B + '/08_词库与词频重建/综合词表_审计候选.jsonl', encoding='utf-8'):
    try: d = json.loads(line)
    except Exception: continue
    w = d.get('词')
    if w and w not in hits: hits[w] = sum((d.get('各源原始词频') or {}).values())

def to_delete(w, c):
    if len(w) != 2 or len(c) != 4 or not c.isalpha(): return False
    if not any(ch in FUNC for ch in w): return False
    if w[1] in PART: return False
    return hits.get(w, 0) == 0

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

res = []; deleted = None
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict(); dl = []
    for l in lines:
        c, w = parse(l, fmt)
        if c is None: continue
        if to_delete(w, c): dl.append((w, c)); continue
        blocks.setdefault(c, []).append(w)
    out = [emit(c, w, i + 1, fmt) for c, ws in blocks.items() for i, w in enumerate(ws)]
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    if deleted is None: deleted = dl
    res.append({'文件': rel, '删除': len(dl), '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 删 %d  行 %s  %s' % (rel.split('/')[-1], len(dl), res[-1]['行数'], res[-1]['新sha256'][:16]))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'),
           '裁定': '功能字二字词：动词+助词全留；其余六源零出现者删',
           '功能字集合': ''.join(sorted(FUNC)), '删除': [{'词': w, '码': c} for w, c in deleted], '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('删除清单已写入 实装报告.json（%d 条）' % len(deleted))
