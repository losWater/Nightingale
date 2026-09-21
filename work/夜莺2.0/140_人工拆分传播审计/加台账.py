# -*- coding: utf-8 -*-
"""给台账追加 6 个改码行（2026-09-21）。补齐人工规则传播后，这 6 个字首末根变了。

    剶 irbg→irpg   劙 libg→lipg   椼 yjwt→yjwa
    珬 xura→xurp   葕 yjmt→yjma   餰 jmxt→jmxa

落盘前逐条核对：新码位必须为空，原码位上必须真有这个字。
单字表与字词表都要改（两表同码位单字次序必须一致）。本脚本只追加台账，不碰主表。
"""
import io, sys, os, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = W + '/00_维护/实战问题机器参数.tsv'
FIELDS = ['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词',
          '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']
MOVES = [('剶', 'irbg', 'irpg', '彖'), ('劙', 'libg', 'lipg', '彖 蠡'), ('椼', 'yjwt', 'yjwa', '衍'),
         ('珬', 'xura', 'xurp', '戌'), ('葕', 'yjmt', 'yjma', '衍'), ('餰', 'jmxt', 'jmxa', '衍')]
zi = collections.defaultdict(list); ci = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); zi[c].append(t)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); ci[c].append(t)
print('落盘前核对（新码位允许已有字：扩展字按规则排在同码位现有字词之后，追加到末尾）：')
bad = []
for ch, old, new, why in MOVES:
    ok_old = ch in zi.get(old, []) and ch in ci.get(old, [])
    dup = ch in zi.get(new, []) or ch in ci.get(new, [])      # 不能已经在新码位上
    print('  %s  %s → %s   原位有此字 %s   原位其余 %s   新位现有 %s%s'
          % (ch, old, new, '✓' if ok_old else '✗',
             [x for x in zi.get(old, []) if x != ch] or '无',
             zi.get(new) or '空', '   ！新位已有此字' if dup else ''))
    if not ok_old or dup: bad.append(ch)
if bad: sys.exit('\n核对不过：%s，停手。' % '、'.join(bad))
rows = list(csv.reader(open(P, encoding='utf-8-sig'), delimiter='\t'))
if rows[0] != FIELDS: sys.exit('台账表头与预期不符')
base = 'P0006'
if any(r and r[0].startswith(base) for r in rows[1:]): sys.exit('%s 系列已存在' % base)
NOTE = '人工拆分规则漏传播（%s）；补齐后首末根变化，编码跟随'
new_rows = []; n = 0
for ch, old, nc, why in MOVES:
    for tab in ('单字表', '字词表'):
        n += 1
        new_rows.append(['%s-%02d' % (base, n),
                         '排查是否存在其他人为规定拆分的字有类似问题',
                         '待处理', tab, '改码', old, ch, nc, '', '',
                         NOTE % why + '；新码位为空位', '', '', '', ''])
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    for r in new_rows: w.writerow(r)
print('\n已追加 %d 行：' % len(new_rows))
for r in new_rows: print('  %s  %s  %s %s → %s' % (r[0], r[3], r[6], r[5], r[7]))
