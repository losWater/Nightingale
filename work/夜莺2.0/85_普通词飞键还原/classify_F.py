# -*- coding: utf-8 -*-
"""F 类逐条自动归因：互换 / 邻键手误 / 03承认的读音 / 字典有此读音(方言旧读) / 无此读音(误读或错码)。"""
import io, sys, os, json, collections, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(H + '/F_混合待看清单.json', encoding='utf-8'))
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
try:
    from pypinyin import pinyin, Style
    def dict_readings(ch):
        return {p for p in pinyin(ch, style=Style.NORMAL, heteronym=True)[0]}
    HAS_DICT = True
except Exception:
    HAS_DICT = False
    def dict_readings(ch): return set()

# 小鹤双拼 AB -> 拼音：用单读音字学习
d59 = json.load(open(B + '/59_单字当量排行/单字当量排行.json', encoding='utf-8'))
readings03 = collections.defaultdict(set)
with open(B + '/03_字音频率审计/分读音字频_审计版.tsv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        readings03[r['汉字']].add(r['拼音'])
sp2py = collections.defaultdict(collections.Counter)
for e in d59:
    if len(readings03.get(e['字'], ())) == 1:
        for c in e['所有编码']:
            if len(c['码']) >= 4: sp2py[c['码'][:2]][e['读音']] += 1
sp2py = {k: v.most_common(1)[0][0] for k, v in sp2py.items()}
ADJ = {'q': 'wa', 'w': 'qeas', 'e': 'wrsd', 'r': 'etdf', 't': 'ryfg', 'y': 'tugh', 'u': 'yihj', 'i': 'uojk', 'o': 'ipkl', 'p': 'ol',
       'a': 'qwsz', 's': 'awedxz', 'd': 'serfcx', 'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'j': 'huikmn', 'k': 'jiolm', 'l': 'kop',
       'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'}

def posmap(w):
    n = len(w)
    if n == 2: return {0: (w[0], 0), 1: (w[0], 1), 2: (w[1], 0), 3: (w[1], 1)}
    if n == 3: return {0: (w[0], 0), 1: (w[1], 0), 2: (w[2], 0), 3: (w[2], 1)}
    return {0: (w[0], 0), 1: (w[1], 0), 2: (w[2], 0), 3: (w[-1], 0)}

out = []
for r in F:
    w, c, x = r['词'], r['实际码'], r['最近合法码']
    pm = posmap(w)
    diffs = [i for i in range(4) if c[i] != x[i]]
    chars = {pm[i][0] for i in diffs}
    tag = None; note = ''
    # 互换：同一字的两位对调
    if len(diffs) == 2 and pm[diffs[0]][0] == pm[diffs[1]][0] and c[diffs[0]] == x[diffs[1]] and c[diffs[1]] == x[diffs[0]]:
        tag = '互换手误'
    elif len(chars) == 1:
        ch = next(iter(chars))
        # 该字在实际码中的 AB
        idx = [i for i in range(4) if pm[i][0] == ch]
        if len(idx) == 2:
            ab = c[idx[0]] + c[idx[1]]
            py = sp2py.get(ab)
            if py is None:
                tag = '非法音节'; note = ab
            elif py in readings03.get(ch, ()):
                tag = '03承认的读音（单字表缺）'; note = py
            elif HAS_DICT and py in dict_readings(ch):
                tag = '字典有此读音（方言/旧读/多音）'; note = py
            else:
                near = all(c[i] in ADJ.get(x[i], '') for i in diffs)
                tag = '邻键手误' if near else '无此读音（误读或错码）'; note = py
        else:
            near = all(c[i] in ADJ.get(x[i], '') for i in diffs)
            tag = '邻键手误' if near else '首码错（误读或错码）'
    else:
        tag = '多字同时不同'
    out.append({**r, '归因': tag, '备注': note})
cnt = collections.Counter(o['归因'] for o in out)
print('pypinyin 可用：%s\n' % HAS_DICT)
for k, n in cnt.most_common():
    print('%4d  %s' % (n, k))
json.dump(out, open(H + '/F_归因.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n按归因列出：')
for k, _ in cnt.most_common():
    print('\n【%s】' % k)
    for o in out:
        if o['归因'] == k:
            print('   %-8s %s → %s  %s' % (o['词'], o['实际码'], o['最近合法码'], ('(' + o['备注'] + ')') if o['备注'] else ''))
