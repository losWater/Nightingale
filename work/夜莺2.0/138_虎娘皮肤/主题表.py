# -*- coding: utf-8 -*-
"""抓出虎娘内置主题的完整列表（2026-09-20）。

线索：用户 config.txt 里写着「主题 = 赛博朋克」，而这个名字在 Tigirl.exe 与 Tigirl.dll
各出现一次。主题名多半是连成一片的 UTF-16 字串表，把那一段前后都打出来就是整张表。
顺带看看每个名字旁边有没有颜色常量，能不能反推出配色是怎么定义的。
只读。
"""
import io, sys, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'

def strings_around(b, center, back=900, fwd=1400):
    lo, hi = max(0, center - back), min(len(b), center + fwd)
    seg = b[lo:hi]
    out = []
    i = 0
    while i + 1 < len(seg):
        if seg[i + 1] == 0 and seg[i] == 0: i += 2; continue
        j = i; buf = []
        while j + 1 < len(seg):
            ch = seg[j] | (seg[j + 1] << 8)
            if ch == 0: break
            if not (0x20 <= ch <= 0x7E or 0x2000 <= ch <= 0x9FFF or 0xFF00 <= ch <= 0xFFEF): break
            buf.append(chr(ch)); j += 2
        if len(buf) >= 2: out.append((lo + i, ''.join(buf))); i = j + 2
        else: i += 2
    return out

for fn, at in (('Tigirl.exe', 0x1F84A0), ('Tigirl.dll', 0x2DAAE8)):
    b = open(os.path.join(V, fn), 'rb').read()
    print('═' * 72)
    print('%s @ 0x%X 附近的字串' % (fn, at))
    for o, s in strings_around(b, at):
        mark = '   ← 赛博朋克' if o == at else ''
        print('  %08X  %s%s' % (o, s[:52], mark))
