# -*- coding: utf-8 -*-
"""接着找主题列表：UTF-16 里只有一个「默认」，说明主题名不是以 UTF-16 存的。
本脚本扫 UTF-8 编码的中文串，并找颜色值（0xRRGGBB 常量、rgb()、#hex）与 json/ini 片段。
只读。"""
import io, sys, os, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'
H = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(rb'(?:[\xe2-\xe9][\x80-\xbf]{2}|[\x20-\x7e]){3,80}')
for fn in ('Tigirl.dll', 'Tigirl.exe'):
    b = open(os.path.join(V, fn), 'rb').read()
    out = []
    for m in PAT.finditer(b):
        try: s = m.group().decode('utf-8')
        except UnicodeDecodeError: continue
        if any('\u4e00' <= ch <= '\u9fff' for ch in s): out.append((m.start(), s))
    print('═' * 72)
    print('%s：UTF-8 中文串 %d 条' % (fn, len(out)))
    open(H + '/utf8_%s.txt' % fn.replace('.', '_'), 'w', encoding='utf-8').write(
        '\n'.join('%08X\t%s' % (o, s) for o, s in out))
    kw = [s for o, s in out if re.search(r'主题|皮肤|配色|深色|浅色|暗|亮|经典|简约|夜|白|黑', s)]
    print('  含主题相关词的 %d 条：' % len(kw))
    for s in kw[:40]: print('    ', s[:70])
    # 颜色常量：找形如 0x00RRGGBB 的密集区
    cols = collections.Counter()
    for m in re.finditer(rb'#[0-9A-Fa-f]{6}\b', b):
        cols[m.group().decode()] += 1
    print('  #RRGGBB 形式的串 %d 种：%s' % (len(cols), list(cols)[:16]))
print('\n全部 UTF-8 中文串已存到 utf8_*.txt')
