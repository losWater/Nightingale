# -*- coding: utf-8 -*-
"""第五.7 口径逐条裁定（2026-09-14）：字仅靠其他读音的简码被判可让位、但本读音有实际使用的 12 处，
用户逐条裁定：纤 xmic / 茜 xime / 咋 vatk / 省 xkyb / 剥 bcpg / 奇 jiyt 改回字优先；其余 6 处维持词优先。
实现：这 6 个码位单字整组在前（保持原字序），词随后（保持原词序）。"""
import io, sys, os, json, hashlib, shutil, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
TARGET = {'xmic': '纤', 'xime': '茜', 'vatk': '咋', 'xkyb': '省', 'bcpg': '剥', 'jiyt': '奇'}
KEEP = {'jktp': '劲', 'binv': '秘', 'tctg': '叨', 'somf': '莎', 'xpgv': '解', 'uikc': '什'}
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

res = []; changes = {}
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    out = []; i = 0; done = set()
    while i < len(lines):
        c, w = parse(lines[i], fmt)
        if c in TARGET and c not in done:
            j = i; blk = []
            while j < len(lines):
                c2, w2 = parse(lines[j], fmt)
                if c2 != c: break
                blk.append(w2); j += 1
            ch = [x for x in blk if len(x) == 1]; wd = [x for x in blk if len(x) > 1]
            assert TARGET[c] in ch, ('目标字不在码位', rel, c, blk)
            new = ch + wd
            if blk != new: changes.setdefault(c, (blk, new))
            out.extend(emit(c, x, k + 1, fmt) if new != blk else lines[i + k] for k, x in enumerate(new))
            done.add(c); i = j; continue
        out.append(lines[i]); i += 1
    assert done == set(TARGET), ('未全部命中', rel, sorted(set(TARGET) - done))
    assert len(out) == len(lines)
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    res.append({'文件': rel, '行数': len(lines), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s OK  %s' % (rel.split('/')[-1], res[-1]['新sha256'][:16]))
for c, (a, b) in changes.items():
    print('   %-5s [%s] → [%s]' % (c, '、'.join(a), '、'.join(b)))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'),
           '口径': '第五.7 逐条裁定：字仅靠其他读音简码被判可让位、本读音有实际使用者，由用户逐条决定',
           '改回字优先': TARGET, '维持词优先': KEEP,
           '改动': {c: {'前': a, '后': b} for c, (a, b) in changes.items()}, '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
