# -*- coding: utf-8 -*-
"""继续追 1149 行的差额。上一版假设（折掉本字全码前缀的简码）已被否掉：那是 5248 行。
本版换几个角度：注释覆盖、Unicode 面、以及「同码同字不同来源」的可能。
"""
import io, sys, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 'C:/Users/asus/AppData/Local/Tigirl/码表/夜莺2.0单字'
rows = [tuple(l.rstrip('\n').split('\t')) for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8')]
chars = {t for t, c in rows}
GAP = 21195 - 20046
print('要解释的差额：%d 行\n' % GAP)

def firstcol(path):
    s = set()
    for l in open(path, encoding='utf-8-sig', errors='replace'):
        l = l.rstrip('\r\n')
        if l: s.add(l.split('\t')[0])
    return s
py = firstcol(T + '/1拼音.注释')
uni = firstcol(T + '/unicode.注释')
sp = firstcol(T + '/夜莺.拆分')
for name, s in (('1拼音.注释', py), ('unicode.注释', uni), ('夜莺.拆分', sp)):
    miss = [t for t in chars if t not in s]
    mr = sum(1 for t, c in rows if t not in s)
    print('  %-12s 收 %6d 项   主表有 %5d 字不在其中 → %5d 行%s'
          % (name, len(s), len(miss), mr, '   ★ 正好等于差额' if mr == GAP else ''))
# Unicode 面分布
plane = collections.Counter()
for t, c in rows: plane['BMP' if ord(t) <= 0xFFFF else 'SIP(扩B+)'] += 1
print('\n  Unicode 面：%s' % dict(plane))
ext = sum(1 for t, c in rows if 0x3400 <= ord(t) <= 0x4DBF)          # 扩展A
print('  扩展A(3400-4DBF) 行数 %d%s' % (ext, '   ★ 正好等于差额' if ext == GAP else ''))
cjk = sum(1 for t, c in rows if 0x4E00 <= ord(t) <= 0x9FFF)
print('  基本区(4E00-9FFF) 行数 %d' % cjk)
rest = len(rows) - ext - cjk
print('  其余（扩B以上等）行数 %d' % rest)
print('  扩展A + 扩B以上 = %d%s' % (ext + rest, '   ★ 正好等于差额' if ext + rest == GAP else ''))
