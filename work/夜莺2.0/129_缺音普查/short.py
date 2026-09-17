# -*- coding: utf-8 -*-
"""缺音候选的三简位现状（二简位不可能空，不看）。三简 = 双拼 + 首根键。只列现状，给不给由你定。"""
import io, sys, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
tab = collections.defaultdict(list)
for l in open(W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    t, c = l.rstrip('\r\n').split('\t'); tab[c].append(t)
free, used = [], []
for l in list(open(H + '/缺音候选.tsv', encoding='utf-8'))[1:]:
    f = l.rstrip('\n').split('\t')
    for code in f[4].split(' / '):
        s = code[:3]; cur = tab.get(s, [])
        (used if cur else free).append('%s %s → %s  %s%s' % (f[0], code, s, ('现有: ' + ' '.join(cur[:4])) if cur else '空', '   例:' + f[5] if f[5] else ''))
out = ['【三简位空着】%d 条' % len(free)] + ['  ' + x for x in free] + ['【三简位已占】%d 条' % len(used)] + ['  ' + x for x in used]
open(H + '/缺音候选_三简位.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n'); print('\n'.join(out))
