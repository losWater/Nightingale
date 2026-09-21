# -*- coding: utf-8 -*-
"""变体：阈值 6000，但有简码的字照样让位，只让没简码、排名 5001–6000 的字回到词前面（2026-09-22）。只读。"""
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
src = open(H + '/对比.py', encoding='utf-8').read().split('back = []')[0].replace("sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')", '')
exec(compile(src, H + '/对比.py', 'exec'))
n = 0; kept = []
for c, v in slot.items():
    if len(c) != 4 or c in man or c in EXC or len(v[0]) != 2: continue
    ch = [w for w in v if len(w) == 1 and (w, c) not in buyin_pairs]
    if not ch: continue
    blk = [w for w in ch if not hasS(w) and 5000 < rank.get(w, 99999) <= 6000]
    if not blk: continue
    n += 1
    stay = [w for w in ch if w not in blk]
    wd = [w for w in v if len(w) > 1]
    if stay: kept.append((c, v, blk + wd[:1] + stay + wd[1:], stay))
print('会变的码位仍是 %d 个' % n)
print('其中原本会被连带拖回、现在留在词后面的：%d 个码位' % len(kept))
for c, v, new, s in kept:
    print('  %s  %s → %s   留在后面：%s' % (c, '、'.join(v), '、'.join(new), '、'.join(s)))
