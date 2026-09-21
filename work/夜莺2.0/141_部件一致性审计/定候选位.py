# -*- coding: utf-8 -*-
"""给 12 个改码字定全码位的候选位（2026-09-21）。只读，出结论供落台账。

依据 码表概念与规则.md 第四节【全码位字对字让位】：
    有简码（同读音前缀）的字在全码位退到无简码的字之后，仍在候选中。
    容错码不算简码，不触发让位。
所以对每个落点，先看落点上已有的字有没有简码、搬过去的字有没有简码：
    搬来的有简码、原住民没有  → 排在原住民之后
    搬来的没有、原住民有      → 排在原住民之前
    都有或都无               → 按常用程度（字频）排
字词表里还混着词，候选位要按「字和词一起数」的口径算，所以两表的位置可能不同。
"""
import io, sys, os, csv, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
MOVES = [('庸', 'yscr', 'yscz'), ('慵', 'ysvr', 'ysvz'), ('镛', 'ysur', 'ysuz'),
         ('墉', 'ysqr', 'ysqz'), ('鳙', 'ysdr', 'ysdz'), ('嘃', 'istl', 'istz'),
         ('嫞', 'yssl', 'yssz'), ('槦', 'yswl', 'yswz'), ('欫', 'qikx', 'qivx'),
         ('牅', 'ysnl', 'ysnz'), ('脌', 'nbzc', 'nbzl'), ('蓘', 'gyms', 'gymh')]
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
TOLER = {(t, c) for c, t in irr['容错码'].items()}
zi_rows = [tuple(l.rstrip('\n').split('\t')) for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8')]
ci_rows = [tuple(l.rstrip('\n').split('\t')) for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8')]
zi = collections.defaultdict(list); ci = collections.defaultdict(list)
codes = collections.defaultdict(list)
for t, c in zi_rows: zi[c].append(t); codes[t].append(c)
for t, c in ci_rows: ci[c].append(t)
freq = {}
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1])
def has_short(t):
    """有没有非容错的简码（码长 < 4）"""
    return any(len(c) < 4 and (t, c) not in TOLER for c in codes.get(t, []))
print('落点分析（出简让全：有简码的退到无简码的之后）\n')
out = []
for ch, old, new in MOVES:
    occ_z = [x for x in zi.get(new, [])]
    occ_c = [x for x in ci.get(new, [])]
    me = has_short(ch)
    print('%s  %s → %s   %s简码' % (ch, old, new, '有' if me else '无'))
    if not occ_z and not occ_c:
        print('   落点为空 → 候选位 1（两表同）'); out.append((ch, old, new, 1, 1, '空位')); continue
    print('   单字表落点现有：%s' % ('、'.join('%s(%s简码,字频%s)' % (x, '有' if has_short(x) else '无', freq.get(x, '—')) for x in occ_z) or '空'))
    print('   字词表落点现有：%s' % ('、'.join(occ_c) or '空'))
    # 单字表位置：只数字
    pos_z = 1
    for i, x in enumerate(occ_z, 1):
        xs = has_short(x)
        if me and not xs: pos_z = i + 1                      # 我有简码、它没有 → 我退到它后面
        elif me == xs and freq.get(x, 0) >= freq.get(ch, 0): pos_z = i + 1   # 同类按常用度
    # 字词表位置：字和词一起数，把同样的相对次序放到字词表里
    #   规则：保持与单字表里「相对于其他单字」的先后一致，插到该单字之后的第一个位置
    if pos_z == 1:
        pos_c = 1
    else:
        anchor = occ_z[pos_z - 2]                            # 我要排在这个字之后
        pos_c = occ_c.index(anchor) + 2 if anchor in occ_c else len(occ_c) + 1
    why = ('我有简码、落点上有无简码的字 → 退后' if me and any(not has_short(x) for x in occ_z)
           else '按常用程度排')
    print('   → 单字表候选位 %d，字词表候选位 %d（%s）' % (pos_z, pos_c, why))
    out.append((ch, old, new, pos_z, pos_c, why))
print('\n汇总：')
for ch, old, new, pz, pc, why in out:
    print('  %-3s %s → %s   单字表位 %d   字词表位 %d' % (ch, old, new, pz, pc))
json.dump([{'字': c, '原码': o, '新码': n, '单字表位': pz, '字词表位': pc, '理由': w} for c, o, n, pz, pc, w in out],
          open(H + '/候选位.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/候选位.json' % H)
