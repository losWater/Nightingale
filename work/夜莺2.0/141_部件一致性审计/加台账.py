# -*- coding: utf-8 -*-
"""12 个改码字落台账（2026-09-21）。

候选位按两套规则分开定：
  通用规范字（庸慵镛墉鳙，都有简码）
      对无简码单字：第四节「出简让全」→ 退到它之后
      对四码词：    第五节第 1 条 字有简码 + 四码词 → 字让位 → 退到词之后
      合起来就是排在该码位末尾（单字表里只数字，字词表里字词一起数）
  扩展字（嘃嫞槦欫牅脌蓘）
      113 的既定口径「扩展字全码排在同码位现有字词之后」→ 一律追加末尾
两表同码位的单字先后必须一致，落盘前 apply_ledger 会体检。
"""
import io, sys, os, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = W + '/00_维护/实战问题机器参数.tsv'
FIELDS = ['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词',
          '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']
COMMON = {'庸', '慵', '镛', '墉', '鳙'}
MOVES = [('庸', 'yscr', 'yscz', '庸'), ('慵', 'ysvr', 'ysvz', '庸'), ('镛', 'ysur', 'ysuz', '庸'),
         ('墉', 'ysqr', 'ysqz', '庸'), ('鳙', 'ysdr', 'ysdz', '庸'), ('嘃', 'istl', 'istz', '庸'),
         ('嫞', 'yssl', 'yssz', '庸'), ('槦', 'yswl', 'yswz', '庸'), ('牅', 'ysnl', 'ysnz', '庸'),
         ('欫', 'qikx', 'qivx', '卸左'), ('脌', 'nbzc', 'nbzl', '年'), ('蓘', 'gyms', 'gymh', '衮')]
zi = collections.defaultdict(list); ci = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); zi[c].append(t)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); ci[c].append(t)
print('候选位（两类规则都指向「排在该码位末尾」）：\n')
plan = []
bad = []
for ch, old, new, why in MOVES:
    if ch not in zi.get(old, []) or ch not in ci.get(old, []): bad.append('%s 不在原码位 %s' % (ch, old)); continue
    if ch in zi.get(new, []) or ch in ci.get(new, []): bad.append('%s 已在新码位 %s' % (ch, new)); continue
    pz = len(zi.get(new, [])) + 1
    pc = len(ci.get(new, [])) + 1
    kind = '通用规范' if ch in COMMON else '扩展字'
    print('  %-3s[%s] %s → %s   单字表位 %d（现有 %s）   字词表位 %d（现有 %s）'
          % (ch, kind, old, new, pz, '、'.join(zi.get(new, [])) or '空', pc, '、'.join(ci.get(new, [])) or '空'))
    plan.append((ch, old, new, pz, pc, why, kind))
if bad: sys.exit('\n核对不过：%s' % '；'.join(bad))
rows = list(csv.reader(open(P, encoding='utf-8-sig'), delimiter='\t'))
if rows[0] != FIELDS: sys.exit('台账表头不符')
base = 'P0007'
if any(r and r[0].startswith(base) for r in rows[1:]): sys.exit('%s 已存在' % base)
new_rows = []; n = 0
for ch, old, nc, pz, pc, why, kind in plan:
    for tab, pos in (('单字表', pz), ('字词表', pc)):
        n += 1
        note = ('部件一致性审计：%s 族拆分订正后首末根变化。%s，按%s排在码位末尾'
                % (why, kind, '出简让全＋字词让位' if kind == '通用规范' else '扩展字既定口径'))
        new_rows.append(['%s-%02d' % (base, n), '含曲错拆之后的全面排查（141 部件一致性审计）',
                         '待处理', tab, '改码', old, ch, nc, '', str(pos), note, '', '', '', ''])
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    for r in new_rows: w.writerow(r)
print('\n已追加 %d 行台账' % len(new_rows))
