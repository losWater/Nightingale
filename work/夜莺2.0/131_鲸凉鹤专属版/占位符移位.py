# -*- coding: utf-8 -*-
"""他用 ①②③ 这类占位符把叠词钉在固定的候选位上；夜莺单字插进来时，占位符和它后面的词会被往后推。
生成人能直接看的清单 专属版/占位符移位清单.txt（同时留一份 json 备查）。"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
SRC = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
OUT = H + '/专属版/夜莺2.0_鲸凉鹤专属_手心挂接.txt'
L = re.compile(r'([a-z]+)=(\d+),(.+)')
PH = set('①②③④⑤⑥⑦⑧⑨⑩')
def rd(p):
    d = collections.defaultdict(list)
    for l in open(p, encoding='utf-8-sig'):
        m = L.fullmatch(l.strip())
        if m: d[m.group(1)].append((int(m.group(2)), m.group(3)))
    for c in d: d[c].sort()
    return d
his, out = rd(SRC), rd(OUT)
used = [c for c, v in his.items() if any(t in PH for _, t in v)]
rows = []
for c in sorted(used):
    now = {t: i for i, t in out[c]}
    shifted = [(t, i, now.get(t)) for i, t in his[c] if t in PH and now.get(t) != i]
    if not shifted: continue
    first = min(i for _, i, _ in shifted)
    tail = [(t, i, now.get(t)) for i, t in his[c] if t not in PH and i > first and now.get(t) != i]
    need = max((b - a for _, a, b in shifted + tail if b), default=0)
    rows.append({'码': c, '原': his[c], '新': out[c], '占位符': shifted, '被推后': tail, '移位量': need})
fmt = lambda items: '  '.join('%d=%s' % x for x in items)
txt = ['占位符移位清单', '=' * 60, '',
       '你用 ①②③ 这类占位符把叠词钉在固定的候选位上（例如 csmh=4,匆匆忙忙 是按 4 键上屏）。',
       '夜莺单字插进来时，如果那个码位夜莺也有字，占位符和它后面的词会被整体往后推。',
       '下面这些码位受影响，你可以自己调（一般删掉几个占位符，后面的词就回到原位了）。', '',
       '用了占位符的码位共 %d 个，其中 %d 个受影响。' % (len(used), len(rows)), '']
for r in rows:
    txt += ['-' * 60, r['码'],
            '  你原来  ' + fmt(r['原']),
            '  现在    ' + fmt(r['新']),
            '  占位符  ' + '  '.join('%s %d→%s' % x for x in r['占位符'])]
    if r['被推后']: txt.append('  被推后  ' + '  '.join('%s %d→%s' % x for x in r['被推后']))
    if r['移位量']: txt.append('  想还原  在这个码位删掉 %d 个占位符即可' % r['移位量'])
    txt.append('')
open(H + '/专属版/占位符移位清单.txt', 'wb').write(('\r\n'.join(txt) + '\r\n').encode('utf-8-sig'))
json.dump(rows, open(H + '/占位符移位清单.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print('用占位符的码位 %d 个，受影响 %d 个 → 专属版/占位符移位清单.txt' % (len(used), len(rows)))
