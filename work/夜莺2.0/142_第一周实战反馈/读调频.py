# -*- coding: utf-8 -*-
"""读虎娘「夜莺2.0」方案的用户调频记录，对照现行主表（2026-09-22）。只读。
格式沿用 123/read_user_tcu.py 摸出来的：文件头 TIGERU01，之后每条 [size u32][h u32][body]，
body = kind u32, 码长 u32, 字长 u32, 码(UTF-16), 字(UTF-16)。
每条列出：码 → 你调到前面的字词，以及这个码在主表里现在的候选顺序。
"""
import io, sys, os, struct, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = os.environ['LOCALAPPDATA'] + '/Tigirl/schemas/夜莺2.0/user.tcu'
b = open(P, 'rb').read()
assert b[:8] == b'TIGERU01', b[:8]
recs = []; i = 8
while i < len(b):
    size, h = struct.unpack_from('<II', b, i); body = b[i + 8:i + 8 + size]
    kind, clen, tlen = struct.unpack_from('<III', body, 0)
    code = body[12:12 + clen * 2].decode('utf-16le')
    text = body[12 + clen * 2:12 + (clen + tlen) * 2].decode('utf-16le')
    recs.append((code, text, kind, h)); i += 8 + size
tab = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); tab[c].append(t)
print('用户记录 %d 条，kind 取值 %s，h 取值 %s\n' % (len(recs), sorted({k for _, _, k, _ in recs}),
                                                sorted({x for _, _, _, x in recs})[:8]))
for code, text, kind, h in recs:
    cur = tab.get(code, [])
    pos = cur.index(text) + 1 if text in cur else None
    print('  %-6s → %-8s  kind=%d h=%-10d  主表现序：%s%s'
          % (code, text, kind, h, '、'.join(cur[:8]) or '（主表无此码）',
             '' if pos else '   ←主表里这个码没有这一项'))
