# -*- coding: utf-8 -*-
"""抽出虎娘 config.txt 的完整可用键，以及内置主题列表（2026-09-20）。

dll 里 0x2DA700–0x2DAB00 是一整片连着的配置键名与取值，
把它完整打出来，就知道 config.txt 到底能写哪些行。
只读。"""
import io, sys, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'
b = open(os.path.join(V, 'Tigirl.dll'), 'rb').read()
lo, hi = 0x2DA600, 0x2DAB00
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
THEMES = {'默认', '通透', '一般通透', '迷雾', '星夜', '赛博朋克', '清晨'}
print('虎娘 config.txt 可用键与取值（dll 0x%X–0x%X 连续区）\n' % (lo, hi))
for o, s in out:
    if not any('\u4e00' <= ch <= '\u9fff' for ch in s) and not re.fullmatch(r'[\w+ /\[\]]+', s): continue
    tag = '  ← 主题名' if s in THEMES else ''
    print('  %08X  %s%s' % (o, s, tag))
print('\n内置主题共 %d 个：%s' % (len(THEMES), '、'.join(['默认', '清晨', '迷雾', '星夜', '通透', '一般通透', '赛博朋克'])))
print('没有主题文件、没有颜色键、没有主题目录 → 配色写死在 dll 里，不支持自制皮肤。')
