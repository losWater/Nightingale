# -*- coding: utf-8 -*-
"""给台账追加 農、鄷 的改码行（2026-09-21）。

曲部件拆分订正后，这两个字的首根由 由(p) 变成 囗(j)，编码要跟着改，
否则拆分提示与实际编码对不上。单字表与字词表都要改，两表同码位单字次序必须一致。
    農  nspz → nsjz
    鄷  fgpy → fgjy
两个新码位都是空的（已核对），旧码位 nspz 上另有「燶」，它的首根是火不受影响，留在原处。
本脚本只往台账追加「待处理」行，不碰主表；改表由 apply_ledger.py 负责。
"""
import io, sys, os, csv, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = W + '/00_维护/实战问题机器参数.tsv'
FIELDS = ['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词',
          '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']
rows = list(csv.reader(open(P, encoding='utf-8-sig'), delimiter='\t'))
head = rows[0]
if head != FIELDS: sys.exit('台账表头与预期不符：%s' % head)
ids = {r[0] for r in rows[1:] if r}
base = 'P0005'
if any(i.startswith(base) for i in ids): sys.exit('%s 系列已存在，避免重复追加' % base)
NOTE = '群友反馈含曲的字错拆成由+丨；曲部件统一改为囗+横+丨+丨（与曲本字一致），首根 由(p)→囗(j)'
new = []
n = 0
for ch, old, nc in (('農', 'nspz', 'nsjz'), ('鄷', 'fgpy', 'fgjy')):
    for tab in ('单字表', '字词表'):
        n += 1
        new.append([
            '%s-%02d' % (base, n),
            '仍有一些错拆字，比如含曲的字，仍然被错误的拆成了由和竖',
            '待处理', tab, '改码', old, ch, nc, '', '',
            NOTE + '；新码位为空位', '', '', '', ''])
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    for r in new: w.writerow(r)
print('已追加 %d 行到台账：' % len(new))
for r in new: print('  %s  %s  %s  %s %s → %s' % (r[0], r[3], r[4], r[6], r[5], r[7]))
print('\n接着跑：python 00_维护/apply_ledger.py      （预演）')
print('        python 00_维护/apply_ledger.py --apply（落盘）')
