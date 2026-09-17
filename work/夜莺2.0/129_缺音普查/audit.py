# -*- coding: utf-8 -*-
"""缺音普查（2026-09-17，你说"夜莺缺音有点严重"，例：裳 cháng、嬛 huán）。只列候选，收不收由你裁定。
做法：夜莺单字表里每个字现有的双拼音节集合，对照魔虎小鹤单字表（每个读音带字频）。魔虎有、夜莺没有、且该读音字频 > 0 的，列为候选。
例词取自魔虎基础词库里用到这个读音的词（按词频取前 4 个）。再用 pypinyin 标出该读音是否在其单字读音里（不在的多半是词库特设）。
输出：缺音候选.tsv / 缺音候选.html（按读音字频从高到低）。"""
import io, sys, os, re, json, collections, html
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pypinyin import pinyin, Style
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); U = W + '/127_魔虎基座试验/upstream/pkg'
ours = collections.defaultdict(set); full = collections.defaultdict(set)
for l in open(W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    t, c = l.rstrip('\r\n').split('\t')
    if len(c) >= 2: ours[t].add(c[:2])
    if len(c) == 4: full[t].add(c)
tol = set(json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))['容错码'])
cand = {}
for l in open(U + '/mohu_flypy.chars.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) != 3 or ';' not in f[1]: continue
    t, sp, w = f[0], f[1].split(';')[0], int(f[2] or 0)
    if t in ours and sp not in ours[t] and w > 0: cand[(t, sp)] = max(cand.get((t, sp), 0), w)
ex = collections.defaultdict(list)
need = collections.defaultdict(set)
for t, sp in cand: need[t].add(sp)
for fn in ('mohu_flypy.base.dict.yaml', 'mohu_flypy.words.dict.yaml'):
    for l in open(U + '/' + fn, encoding='utf-8'):
        f = l.rstrip('\n').split('\t')
        if len(f) < 2 or not (2 <= len(f[0]) <= 4): continue
        ss = f[1].split(' ')
        if len(ss) != len(f[0]): continue
        for ch, s in zip(f[0], ss):
            if ch in need and s[:2] in need[ch]: ex[(ch, s[:2])].append((int(f[2]) if len(f) > 2 and f[2].isdigit() else 0, f[0]))
FIN = None
def py_of(t):
    try: return ' '.join(pinyin(t, style=Style.TONE, heteronym=True)[0])
    except Exception: return ''
rows = []
for (t, sp), w in sorted(cand.items(), key=lambda x: -x[1]):
    words = [w_ for _, w_ in sorted(set(ex[(t, sp)]), reverse=True)[:4]]
    aux = sorted({c[2:] for c in full[t]})
    rows.append((t, sp, w, ' '.join(sorted(ours[t])), ' / '.join(sp + a for a in aux), '、'.join(words), py_of(t)))
open(H + '/缺音候选.tsv', 'w', encoding='utf-8').write('字\t缺的音节(小鹤)\t该读音字频\t夜莺现有音节\t若补则全码\t例词\t该字全部读音(pypinyin)\n' + ''.join('\t'.join(map(str, r)) + '\n' for r in rows))
hd = '<!doctype html><meta charset="utf-8"><title>夜莺缺音候选</title><style>body{font:15px/1.6 system-ui,"Microsoft YaHei";margin:24px;background:#fff;color:#222}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:3px 10px}th{background:#f3f3f3;position:sticky;top:0}td:first-child{font-size:22px}.n{color:#999}</style>'
body = '<h2>夜莺缺音候选 %d 条（涉及 %d 字）</h2><p>按该读音字频从高到低。有例词的更值得收；没例词的多半是生僻读音。只列候选，收不收由你定。</p><table><tr><th>字<th>缺的音节<th>读音字频<th>夜莺现有<th>若补则全码<th>例词<th>全部读音' % (len(rows), len({r[0] for r in rows}))
for r in rows: body += '<tr>' + ''.join('<td%s>%s' % (' class=n' if i == 6 else '', html.escape(str(x))) for i, x in enumerate(r))
open(H + '/缺音候选.html', 'w', encoding='utf-8').write(hd + body + '</table>')
withw = [r for r in rows if r[5]]
print('候选 %d 条，涉及 %d 字；其中有例词的 %d 条' % (len(rows), len({r[0] for r in rows}), len(withw)))
for r in withw[:60]: print('%s %s  频%d  现有[%s]  例:%s' % (r[0], r[1], r[2], r[3], r[5]))
