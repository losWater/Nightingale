# -*- coding: utf-8 -*-
"""实验（2026-09-16 你提议）：把小鹤双拼所有实际存在的音节两两组合成"假想二字词"（码 = 音码1+音码2），
看这些四码里有多少撞上夜莺单字的全码；撞到的字有没有简码（有简码 → 字让位、词首选；无简码 → 字占首选）。
音节来自 54/frozen/字音基准（8105 字的实际音码）；单字表用 78（8105 字）+ 可选扩展字（113）。"""
import io, sys, os, json, re, collections, itertools
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
pron = J(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/字音基准.json')
syl = {}   # 音码 -> 拼音集合
for r in pron: syl.setdefault(r['音码'], set()).add(re.sub(r'[1-5]$', '', r['拼音']))
codes = sorted(syl)
rank = {r['字']: r['新排名'] for r in J(W + '/32_多来源字频重建/试验整字频率.json')['字表']}
def load(p):
    full = collections.defaultdict(list); short = collections.defaultdict(set)
    for l in open(p, encoding='utf-8-sig'):
        q = l.rstrip('\r\n').split('\t')
        if len(q) < 2 or len(q[0]) != 1: continue
        (full[q[1]].append(q[0]) if len(q[1]) == 4 else short[q[0]].add(q[1]))
    return full, short
res = {}
for label, p in [('8105 字', W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'), ('含扩展字 15496', W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt')]:
    full, short = load(p)
    total = len(codes) ** 2; hit = 0; yield_all = 0; char_first = 0; multi = 0
    by_char = collections.Counter(); examples = []
    for a, b in itertools.product(codes, repeat=2):
        k = a + b
        if k in full:
            hit += 1; chars = full[k]
            if len(chars) > 1: multi += 1
            for c in chars: by_char[c] += 1
            if all(short.get(c) for c in chars): yield_all += 1
            else: char_first += 1
            if len(examples) < 12 and any(rank.get(c, 99999) <= 1500 and not short.get(c) for c in chars): examples.append((k, chars, sorted(syl[a])[:2], sorted(syl[b])[:2]))
    top = sorted(((c, n) for c, n in by_char.items() if not short.get(c)), key=lambda t: (rank.get(t[0], 99999)))[:30]
    res[label] = {'音节数': len(codes), '假想二字词': total, '撞单字全码': hit, '占比%': round(hit / total * 100, 2), '其中撞到多于一字': multi,
                  '撞到的字都有简码(词可首选)': yield_all, '有字无简码(字占首选)': char_first,
                  '被撞的单字数': len(by_char), '其中无简码的字数': sum(1 for c in by_char if not short.get(c)),
                  '无简码且字频靠前的被撞字(排名)': [(c, rank.get(c, 99999), n) for c, n in top],
                  '样例(码,字,前音,后音)': examples}
json.dump(res, open(H + '/结果.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for label, r in res.items():
    print('==', label)
    for k, v in r.items(): print('  ', k, ':', v if not isinstance(v, list) else v[:12])
