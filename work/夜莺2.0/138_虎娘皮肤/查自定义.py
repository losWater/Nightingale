# -*- coding: utf-8 -*-
"""最后一个线索：「自定义」在 exe 与 dll 里各出现 3 次，看它指的是不是自定义主题。
若只是自定义字体／快捷键之类，那就可以定论：虎娘的主题是写死在二进制里的，不支持自制皮肤。
只读。"""
import io, sys, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'

def ctx(b, at, back=260, fwd=320):
    lo, hi = max(0, at - back), min(len(b), at + fwd)
    seg = b[lo:hi]; out = []; i = 0
    while i + 1 < len(seg):
        if seg[i + 1] == 0 and seg[i] == 0: i += 2; continue
        j = i; buf = []
        while j + 1 < len(seg):
            ch = seg[j] | (seg[j + 1] << 8)
            if ch == 0 or not (0x20 <= ch <= 0x7E or 0x2000 <= ch <= 0x9FFF or 0xFF00 <= ch <= 0xFFEF): break
            buf.append(chr(ch)); j += 2
        if len(buf) >= 2: out.append((lo + i, ''.join(buf))); i = j + 2
        else: i += 2
    return out

for fn in ('Tigirl.exe', 'Tigirl.dll'):
    b = open(os.path.join(V, fn), 'rb').read()
    w = '自定义'.encode('utf-16-le')
    print('═' * 70)
    print(fn)
    for m in re.finditer(re.escape(w), b):
        print('\n  --- 0x%X 附近 ---' % m.start())
        for o, s in ctx(b, m.start()):
            print('     %s%s' % (s[:50], '   ←' if o == m.start() else ''))
