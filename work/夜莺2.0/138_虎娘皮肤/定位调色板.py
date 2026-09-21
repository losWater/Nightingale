# -*- coding: utf-8 -*-
"""在已安装的 Tigirl 二进制里精确定位那张调色板（2026-09-20）。只读，不改任何文件。

结构（native/CandidateTheme.h）：
    struct CandidateTheme { uint32 foreground,background,border,selection;
                            double borderWidth; array<double,4> corners; };
  → 4×4 字节 + 8 字节对齐后的 double + 4×8 字节 = 56 字节一条，9 条共 504 字节。
拿「默认」那条的字节做锚点搜索：若能唯一命中，并且紧随其后的八条也能逐条解出来，
就证明这张表在文件里是连续、可定位、可改写的。
"""
import io, sys, os, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'
NAMES = ['默认', '通透', '一般通透', '迷雾', '星夜', '纸', '粉', '赛博朋克', '清晨']
EXPECT = [
    (0xff000000, 0xfff8f3 | 0xff000000, 0xff1a7b6b, 0x48000000, 1.25, (5, 5, 5, 5)),
]
def theme_bytes(fg, bg, bd, sel, bw, corners):
    b = struct.pack('<IIII', fg, bg, bd, sel) + struct.pack('<d', bw)
    for c in corners: b += struct.pack('<d', float(c))
    return b
anchor = theme_bytes(0xff000000, 0xfffff8f3, 0xff1a7b6b, 0x48000000, 1.25, (5, 5, 5, 5))
print('一条 %d 字节，九条 %d 字节' % (len(anchor), len(anchor) * 9))
for fn in ('Tigirl.dll', 'Tigirl.exe'):
    p = os.path.join(V, fn)
    b = open(p, 'rb').read()
    hits = []
    i = b.find(anchor)
    while i != -1:
        hits.append(i); i = b.find(anchor, i + 1)
    print('\n' + '═' * 66)
    print('%s  命中「默认」%d 处：%s' % (fn, len(hits), [hex(x) for x in hits]))
    for at in hits:
        print('  从 0x%X 起逐条解析：' % at)
        ok = True
        for k in range(9):
            off = at + 56 * k
            fg, bg, bd, sel = struct.unpack_from('<IIII', b, off)
            bw, = struct.unpack_from('<d', b, off + 16)
            cs = struct.unpack_from('<4d', b, off + 24)
            nm = NAMES[k] if k < len(NAMES) else '?'
            print('    %-8s 0x%08x 0x%08x 0x%08x 0x%08x  边 %-4g 角 %s'
                  % (nm, fg, bg, bd, sel, bw, ','.join('%g' % c for c in cs)))
            if not (0 <= bw <= 8) or any(not (0 <= c <= 64) for c in cs): ok = False
        print('    → %s' % ('九条全部解出，表是连续的 ✓' if ok else '有字段超出合理范围，可能不是这张表 ✗'))
