# -*- coding: utf-8 -*-
"""把第一周实战反馈（清单.md 三条，均已裁定）生成台账行，交 apply_ledger.py 执行（2026-09-22）。
只追加「待处理」行，不碰主表。行的先后就是执行先后。
候选位口径同 apply_ledger：字词表里字和词一起数，单字表里只数字。
"""
import io, sys, os, re, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = W + '/00_维护/实战问题机器参数.tsv'
FIELDS = ['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词',
          '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']
ci = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); ci[c].append(t)
rows = []
def row(src, tab, op, oc='', ot='', nc='', nt='', pos='', note=''):
    rows.append([src, tab, op, oc, ot, nc, nt, str(pos), note])
# ── 一、词频（虎娘调频）──
S1 = '第一周实战·虎娘用户调频'
for c, w in [('jiqi', '机器'), ('lyg', '另一个'), ('fuke', '复刻'), ('jige', '几个'), ('jidi', '基地'),
             ('bdlu', '白鹭'), ('naui', '那是'), ('jiiu', '基础'), ('vryi', '转移'), ('yibo', '一波'),
             ('fz', '否则')]:
    row(S1, '字词表', '调序', c, w, pos=1, note='调到首位')
row(S1, '单字表', '调序', 'katq', '喀', pos=1, note='单字调到首位')
row(S1, '字词表', '调序', 'katq', '喀', pos=1, note='单字调到首位')
for c, w in [('wokc', '我靠'), ('yuyj', '寓言'), ('yudi', '玉帝'), ('fjjm', '凡间'), ('cdyz', '才有'), ('yeyk', '夜桜')]:
    row(S1, '字词表', '新增', nc=c, nt=w, note='加词，排码位末尾')
for c, w in [('qrui', '全是'), ('dhww', '档位'), ('jugz', '巨构'), ('zsm', '做什么')]:
    row(S1, '字词表', '新增', nc=c, nt=w, pos=1, note='加词并调到首位（巨构 jvgz 保留，两码都有）')
# ── 二、补二简词 ──
S2 = '第一周实战·补夜莺二简.txt'
row(S2, '字词表', '删除', 'yo', '有时', note='清单标删除')
row(S2, '字词表', '删除', 'yo', '一时', note='清单标删除')
lines = [l.strip() for l in open('D:/qqfile/补夜莺二简.txt', encoding='utf-8-sig') if l.strip()]
byc = collections.OrderedDict()
for l in lines:
    m = re.fullmatch(r'(\S+)\s+([a-z]+)\s*(（删除）)?', l)
    if not m.group(3): byc.setdefault(m.group(2), []).append(m.group(1))
for c, ws in byc.items():
    nchar = sum(1 for x in ci.get(c, []) if len(x) == 1)       # 单字仍在最前
    have = set(ci.get(c, []))
    for i, w in enumerate(ws, 1):
        pos = nchar + i
        if w in have: row(S2, '字词表', '调序', c, w, pos=pos, note='按清单顺序')
        else: row(S2, '字词表', '新增', nc=c, nt=w, pos=pos, note='按清单顺序；清单未提的原有简词接在后面')
# ── 三、字频 ──
S3 = '第一周实战·什的ufk改成伸'
for tab in ('单字表', '字词表'):
    row(S3, tab, '删除', 'ufk', '什', note='什退回全码 ufkc')
    row(S3, tab, '新增', nc='ufk', nt='伸', pos=1, note='伸占三简')
row(S3, '单字表', '调序', 'ufkp', '伸', pos=2, note='出简让全：伸有三简，全码位退到侁之后')
row(S3, '字词表', '调序', 'ufkp', '伸', pos=2, note='出简让全：伸有三简，全码位退到侁之后')
# 追加
old = list(csv.reader(open(P, encoding='utf-8-sig'), delimiter='\t'))
if old[0] != FIELDS: sys.exit('台账表头不符')
base = 'P0008'
if any(r and r[0].startswith(base) for r in old[1:]): sys.exit('%s 已存在，避免重复追加' % base)
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    for n, (src, tab, op, oc, ot, nc, nt, pos, note) in enumerate(rows, 1):
        w.writerow(['%s-%03d' % (base, n), src, '待处理', tab, op, oc, ot, nc, nt, pos, note, '', '', '', ''])
cnt = collections.Counter((r[0], r[2]) for r in rows)
print('已追加 %d 行：' % len(rows))
for (src, op), n in cnt.items(): print('  %-22s %s %d' % (src, op, n))
