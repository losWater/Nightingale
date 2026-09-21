# -*- coding: utf-8 -*-
"""9 月 17 日的夜莺 2.0 综合表 vs 现在的 2.5 综合表，逐条分类，生成更新日志（2026-09-22）。
分类（按你给的顺序）：
  一 错码修复   同一个字的全码从一个码换到另一个码（旧码删、新码加，双拼相同）
  二 调整频     同码同条目两边都有，但在码位里的先后变了（分 字 / 词 / 简词）
  三 新增       新出现的条目（分 字 / 词 / 简词），已归入一的不重复计
  四 删除       消失的条目（分 字 / 词 / 简词），已归入一的不重复计
  五 其它调整   单字简码换人（一个码位上字的简码让给另一个字）、符号与快符
口径：条目 = (文字, 码)。字 = 单个汉字；简词 = 多字且码长 < 4；词 = 多字且码长 ≥ 4；其余（标点、假名等）归符号。
"""
import io, sys, os, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
OLD = 'D:/qqfile/夜莺2.0综合表.txt'
NEW = 'D:/nightingale/releases/v2.5/01_正式码表/夜莺2.5综合表.txt'
CJK = lambda s: all('\u3400' <= ch <= '\u9fff' or '\U00020000' <= ch <= '\U0003134f' or ch == '〇' for ch in s)
def load(p):
    rows = []
    for l in open(p, encoding='utf-8-sig'):
        f = l.rstrip('\r\n').split('\t')
        if len(f) >= 2 and f[0] and f[1]: rows.append((f[0], f[1]))
    return rows
old, new = load(OLD), load(NEW)
def slots(rows):
    d = collections.defaultdict(list)
    for t, c in rows: d[c].append(t)
    return d
so, sn = slots(old), slots(new)
def kind(t, c):
    if not CJK(t): return '符号'
    if len(t) == 1: return '字'
    return '简词' if len(c) < 4 else '词'
po, pn = set(old), set(new)
added, removed = pn - po, po - pn
# 一 错码修复：单字，旧全码删、新全码加，双拼相同
fix = []
for t in sorted({t for t, c in removed if kind(t, c) == '字' and len(c) == 4}):
    olds = [c for tt, c in removed if tt == t and len(c) == 4]
    news = [c for tt, c in added if tt == t and len(c) == 4]
    for oc in olds:
        m = [nc for nc in news if nc[:2] == oc[:2]]
        if m: fix.append((t, oc, m[0])); news.remove(m[0])
fixset = {(t, a) for t, a, b in fix} | {(t, b) for t, a, b in fix}
# 五 其它：单字简码换人（同一简码位上，旧字删、新字加）
jm = []
for c in sorted({c for t, c in removed if kind(t, c) == '字' and len(c) < 4}):
    a = [t for t, cc in removed if cc == c and kind(t, cc) == '字']
    b = [t for t, cc in added if cc == c and kind(t, cc) == '字']
    if a and b: jm.append((c, a, b))
jmset = {(t, c) for c, a, b in jm for t in a + b}
# 二 调整频
freq = collections.defaultdict(list)
for c in set(so) & set(sn):
    common = [t for t in so[c] if t in sn[c]]
    o = [t for t in so[c] if t in common]; n = [t for t in sn[c] if t in common]
    if o != n:
        k = kind(n[0], c) if n else '词'
        # 按码位主体归类：谁被提上来了
        moved = [t for i, t in enumerate(n) if o.index(t) > i]
        k = kind(moved[0], c) if moved else k
        freq[k].append((c, so[c], sn[c]))
add_by = collections.defaultdict(list); del_by = collections.defaultdict(list)
for t, c in sorted(added, key=lambda x: (x[1], x[0])):
    if (t, c) in fixset or (t, c) in jmset: continue
    add_by[kind(t, c)].append((t, c))
for t, c in sorted(removed, key=lambda x: (x[1], x[0])):
    if (t, c) in fixset or (t, c) in jmset: continue
    del_by[kind(t, c)].append((t, c))
print('旧 %d 条，新 %d 条' % (len(old), len(new)))
print('一 错码修复 %d' % len(fix))
print('二 调整频 ' + '，'.join('%s %d' % (k, len(v)) for k, v in freq.items()))
print('三 新增 ' + '，'.join('%s %d' % (k, len(v)) for k, v in add_by.items()))
print('四 删除 ' + '，'.join('%s %d' % (k, len(v)) for k, v in del_by.items()))
print('五 简码换人 %d' % len(jm))
import pickle
pickle.dump(dict(old=len(old), new=len(new), fix=fix, freq=dict(freq), add=dict(add_by), dele=dict(del_by), jm=jm),
            open(H + '/对比结果.pkl', 'wb'))
print('\n错码修复样例：', fix[:12])
print('简码换人：', jm)
print('删除·字：', del_by.get('字', [])[:20])
print('新增·字：', add_by.get('字', [])[:20])
