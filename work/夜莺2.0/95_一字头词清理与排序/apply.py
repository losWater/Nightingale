# -*- coding: utf-8 -*-
"""用户裁定（2026-09-14）：一 开头的词走路 A——留在 y 音节；六源零出现的 一 词删除；
凡含 一 词的码位，词与词之间按 08 词频重排（无记录者排最后、保持原相对序）。单字位置随后由 89 按字词规则复修。
对象：62（第 2 步输入）；随后重建 91。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
hits = {}; idx = {}
for line in open(B + '/08_词库与词频重建/综合词表_审计候选.jsonl', encoding='utf-8'):
    try: d = json.loads(line)
    except Exception: continue
    w = d.get('词')
    if w and w not in hits:
        hits[w] = sum((d.get('各源原始词频') or {}).values()); idx[w] = d.get('排序指数', 0)
key = lambda w: (0 if hits.get(w, 0) > 0 else 1, -idx.get(w, 0))

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
    blocks = collections.OrderedDict(); deleted = []
    for l in lines:
        c, w = parse(l, fmt)
        if c is None: continue
        if len(w) > 1 and w[0] == '一' and c.isalpha() and len(c) >= 4 and hits.get(w, 0) == 0:
            deleted.append((w, c)); continue
        blocks.setdefault(c, []).append(w)
    reordered = {}
    for c, ws in blocks.items():
        if len(c) != 4 or not any(len(w) > 1 and w[0] == '一' for w in ws): continue
        ch = [w for w in ws if len(w) == 1]; wd = [w for w in ws if len(w) > 1]
        # 稳定排序：有记录者按排序指数降序，无记录者保持原相对序排后
        wd2 = sorted(wd, key=key)
        if wd2 != wd:
            reordered[c] = (ws, ch + wd2); blocks[c] = ch + wd2   # 单字先放前，89 再按字词规则定
    out = [emit(c, w, i + 1, fmt) for c, ws in blocks.items() for i, w in enumerate(ws)]
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    if log is None: log = {'删除': deleted, '重排': reordered}
    res.append({'文件': rel, '删除': len(deleted), '重排码位': len(reordered), '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 删 %d  重排 %d 码位  行 %s  %s' % (rel.split('/')[-1], len(deleted), len(reordered), res[-1]['行数'], res[-1]['新sha256'][:16]))
print('\n重排样例：')
for c, (a, b) in list(log['重排'].items())[:8]:
    print('   %-5s [%s] → [%s]' % (c, '、'.join(a[:5]), '、'.join(b[:5])))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '裁定': '一 词留 y；零出现删；含一词码位按08词频排',
           '删除': [{'词': w, '码': c} for w, c in log['删除']],
           '重排': {c: {'前': a, '后': b} for c, (a, b) in log['重排'].items()}, '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
