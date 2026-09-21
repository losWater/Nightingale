# -*- coding: utf-8 -*-
"""摸清虎娘的皮肤／配色机制（2026-09-20）。

已知：设置界面里有「候选主题」「候选外观」「候选字体」「字号」等项，
但安装目录和用户目录里都没有皮肤文件，所以配色多半是 config.txt 里的若干键。
这里把 Tigirl.exe 的 UTF-16 字串按偏移顺序抽出来（对齐到偶数位，避免错位乱码），
再打印「主题/外观/颜色」这些词前后的邻居——资源表里相关字串通常挨在一起，
邻居就是同一组设置项的键名和可选值。
只读，不改任何东西。
"""
import io, sys, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'
OUT = os.path.dirname(os.path.abspath(__file__))

def utf16_strings(b, minlen=2):
    """按偶数偏移扫 UTF-16LE 串，返回 [(offset, text)]，只要含中文或像设置键的串。"""
    res = []
    i = 0; n = len(b)
    while i + 1 < n:
        if b[i + 1] == 0 and b[i] == 0: i += 2; continue
        j = i; buf = []
        while j + 1 < n:
            lo, hi = b[j], b[j + 1]
            if lo == 0 and hi == 0: break
            ch = lo | (hi << 8)
            if ch == 0xFFFE or ch == 0xFEFF: break
            if not (0x20 <= ch <= 0x7E or 0x2000 <= ch <= 0x9FFF or 0xFF00 <= ch <= 0xFFEF): break
            buf.append(chr(ch)); j += 2
        if len(buf) >= minlen:
            res.append((i, ''.join(buf))); i = j + 2
        else: i += 2
    return res

for fn in ('Tigirl.exe', 'Tigirl.dll'):
    b = open(os.path.join(V, fn), 'rb').read()
    ss = utf16_strings(b)
    print('═' * 74)
    print('%s：抽到 %d 条 UTF-16 字串' % (fn, len(ss)))
    anchors = [i for i, (o, s) in enumerate(ss) if re.search(r'主题|外观|候选字体|字号|颜色', s)]
    seen = set()
    for a in anchors:
        lo, hi = max(0, a - 6), min(len(ss), a + 10)
        key = (lo, hi)
        if key in seen: continue
        seen.add(key)
        print('\n--- 锚点「%s」@0x%X 的上下文 ---' % (ss[a][1], ss[a][0]))
        for o, s in ss[lo:hi]:
            mark = ' ←' if (o, s) == ss[a] else ''
            print('    %-40s%s' % (s[:40], mark))
    open(OUT + '/字串_%s.txt' % fn.replace('.', '_'), 'w', encoding='utf-8').write(
        '\n'.join('%08X\t%s' % (o, s) for o, s in ss))
print('\n全部字串已存到 138_虎娘皮肤/字串_*.txt，可自行检索。')
