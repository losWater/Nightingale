# -*- coding: utf-8 -*-
"""他用 ①②③ 这类占位符把某个词钉在固定的候选位上；夜莺单字插进来时，占位符和它后面的词会被往后推。
本脚本列出所有受影响的码位，供裁定。"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
SRC = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
CORE = W + '/106_全平台导出/夜莺2.0_字词表与输入法/手心/模块化挂接/01_核心单字.txt'
OUT = H + '/专属版/夜莺2.0_鲸凉鹤专属_手心挂接.txt'
L = re.compile(r'([a-z]+)=(\d+),(.+)')
def rd(p):
    d = collections.defaultdict(list)
    for l in open(p, encoding='utf-8-sig'):
        m = L.fullmatch(l.strip())
        if m: d[m.group(1)].append((int(m.group(2)), m.group(3)))
    for c in d: d[c].sort()
    return d
his, core, out = rd(SRC), rd(CORE), rd(OUT)
PH = set('①②③④⑤⑥⑦⑧⑨⑩')
moved = []
for c, items in his.items():
    ph = [(i, t) for i, t in items if t in PH]
    if not ph: continue
    now = {t: i for i, t in out[c]}
    shifted = [(t, i, now.get(t)) for i, t in ph if now.get(t) != i]
    if not shifted: continue
    tail = [(i, t) for i, t in items if i > min(x[1] for x in shifted) and t not in PH]
    moved.append({'码': c, '他的': ['%d=%s' % x for x in items], '专属版': ['%d=%s' % x for x in out[c]],
                  '占位符移位': ['%s %d→%s' % x for x in shifted],
                  '被推后的词': ['%s %d→%s' % (t, i, now.get(t)) for i, t in tail if now.get(t) != i]})
print('用了 ①②③ 类占位符的码位 %d 个；其中因夜莺单字插入而移位的 %d 个' % (sum(1 for c, v in his.items() if any(t in PH for _, t in v)), len(moved)))
for m in moved[:15]:
    print('\n  %-5s 他的   %s' % (m['码'], '、'.join(m['他的'])))
    print('        专属版 %s' % '、'.join(m['专属版']))
    print('        占位符 %s；被推后的词 %s' % ('、'.join(m['占位符移位']), '、'.join(m['被推后的词']) or '无'))
json.dump(moved, open(H + '/占位符移位清单.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n完整清单：131_鲸凉鹤专属版/占位符移位清单.json')
