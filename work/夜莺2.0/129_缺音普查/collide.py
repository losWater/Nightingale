# -*- coding: utf-8 -*-
"""缺音候选若补入（只给全码、排该码位单字最后），各码位现状：空位 / 只有词 / 已有字。"""
import io, sys, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
tab = collections.defaultdict(list)
for l in open(W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    t, c = l.rstrip('\r\n').split('\t'); tab[c].append(t)
std = set(open(W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig').read())
kinds = collections.defaultdict(list)
for l in list(open(H + '/缺音候选.tsv', encoding='utf-8'))[1:]:
    f = l.rstrip('\n').split('\t')
    for code in f[4].split(' / '):
        cur = tab.get(code, []); chars = [x for x in cur if len(x) == 1 and x in std]; ext = [x for x in cur if len(x) == 1 and x not in std]; words = [x for x in cur if len(x) > 1]
        k = '空位' if not cur else '只有扩展字' if not chars and not words else '只有词' if not chars else '已有常用字'
        kinds[k].append('%s %s  现有: %s' % (f[0], code, ' '.join(cur[:5]) or '—'))
out = []
for k in ('空位', '只有扩展字', '只有词', '已有常用字'):
    out.append('【%s】%d 条' % (k, len(kinds[k]))); out += ['  ' + x for x in kinds[k]]
open(H + '/缺音候选_重码情况.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n'); print('\n'.join(out))
