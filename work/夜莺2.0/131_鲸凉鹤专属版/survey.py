# -*- coding: utf-8 -*-
"""鲸凉鹤专属版 · 摸底（2026-09-17 你的口径）：
  他的词库一个字节都不动——飞键、无理码、特设短语、词序、简词全部原样；
  只把他词库里的单字换成夜莺 2.0 的单字，并且单字要落在手心核心单字表指定的候选序号上（该表的序号空位本来就是留给挂接词库的）。
本脚本只统计，不产出码表。"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
SRC = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
CORE = W + '/106_全平台导出/夜莺2.0_字词表与输入法/手心/模块化挂接/01_核心单字.txt'
rd = lambda p: [m.groups() for m in (re.fullmatch(r'([a-z]+)=(\d+),(.+)', l.strip()) for l in open(p, encoding='utf-8-sig')) if m]
core = collections.defaultdict(dict)
for c, i, t in rd(CORE): core[c][int(i)] = t
print('夜莺核心单字表：%d 个码位、%d 条' % (len(core), sum(len(v) for v in core.values())))
his_w = collections.defaultdict(list); his_c = collections.defaultdict(list)
for c, i, t in rd(SRC): (his_c if len(t) == 1 else his_w)[c].append((int(i), t))
print('他的词库：词 %d 个码位、%d 条；单字 %d 个码位、%d 条（单字将被夜莺单字替换）' % (len(his_w), sum(len(v) for v in his_w.values()), len(his_c), sum(len(v) for v in his_c.values())))
# 空位统计：核心单字表里，序号不连续处即预留给词的位置
holes = 0; hole_codes = 0; filled = 0; short_fill = collections.Counter(); ex = []
for c, d in core.items():
    top = max(d); h = [i for i in range(1, top + 1) if i not in d]
    if h:
        hole_codes += 1; holes += len(h); n = len(his_w.get(c, []))
        if n >= len(h): filled += 1
        else: short_fill[len(h) - n] += 1
        if len(ex) < 8 and h: ex.append('%-5s 单字 %s ｜ 空位 %s ｜ 他的词 %d 个：%s' % (c, '、'.join('%d=%s' % (i, d[i]) for i in sorted(d)), h, n, '、'.join(t for _, t in sorted(his_w.get(c, [])))[:24]))
print('\n核心单字表有空位的码位 %d 个，空位共 %d 个；他的词填得满的 %d 个，填不满的 %d 个（缺口分布 %s）' % (hole_codes, holes, filled, sum(short_fill.values()), dict(sorted(short_fill.items())[:6])))
for e in ex: print('  ', e)
# 两边都有内容的码位
both = set(core) & set(his_w)
print('\n字词同码的码位 %d 个；只有字的 %d 个；只有词的 %d 个' % (len(both), len(set(core) - set(his_w)), len(set(his_w) - set(core))))
over = [(c, max(core[c]), len(his_w[c])) for c in both if max(core[c]) > 1 + len(his_w[c])]
print('单字最大序号 > 词数+1 的码位 %d 个（这些位置若不前移会留洞）' % len(over))
for c, m, n in sorted(over)[:6]: print('   %-5s 单字最大序号 %d，他只有 %d 个词' % (c, m, n))
json.dump({'核心单字码位': len(core), '核心单字条目': sum(len(v) for v in core.values()), '他的词码位': len(his_w), '他的词条目': sum(len(v) for v in his_w.values()),
           '他的单字条目': sum(len(v) for v in his_c.values()), '空位码位': hole_codes, '空位数': holes, '填不满': sum(short_fill.values())},
          open(H + '/摸底.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
