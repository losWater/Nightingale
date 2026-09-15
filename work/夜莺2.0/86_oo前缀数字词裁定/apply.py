# -*- coding: utf-8 -*-
"""用户裁定：鲸凉鹤 `oo` 前缀四码词只保留数字词，其余去掉。
注意：本方案单字 o=哦、oo=噢 是我们自己的一简/二简，与此无关，不动；只处理四码多字词。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
NUM = set('零〇一二三四五六七八九十百千万亿两廿卅')
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

def target(c, w):
    return len(w) > 1 and len(c) == 4 and c.startswith('oo')

res = []; kept = None; removed = None
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict(); rm = []; kp = []
    for l in lines:
        c, w = parse(l, fmt)
        if c is None: continue
        if target(c, w):
            if all(ch in NUM for ch in w): kp.append((c, w))
            else: rm.append((c, w)); continue
        blocks.setdefault(c, []).append(w)
    out = []
    for c, ws in blocks.items():
        for i, w in enumerate(ws): out.append(emit(c, w, i + 1, fmt))
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    if kept is None: kept, removed = kp, rm
    res.append({'文件': rel, '删除': len(rm), '保留数字词': len(kp), '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 删 %3d  留数字词 %3d  行 %d→%d  %s' % (rel.split('/')[-1], len(rm), len(kp), len(lines), len(out), res[-1]['新sha256'][:16]))
print('\n保留的数字词（64）：', '、'.join('%s=%s' % x for x in kept))
print('\n删除的（64）：', '、'.join('%s=%s' % x for x in removed))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '裁定': 'oo 前缀四码词只保留数字词；单字 o=哦/oo=噢 不动',
           '保留': kept, '删除': removed, '文件': res}, open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
