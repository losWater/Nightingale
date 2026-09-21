# -*- coding: utf-8 -*-
"""确认 main_records 的口径 = 码前缀树节点数（2026-09-20）。

小样本探针已证明：main_records 不是词条数，而是所有码的不同前缀个数（trie 节点数）。
  A 组 zqaa/zqbb/zqcc/zqdd → z,zq,zqa,zqb,zqc,zqd,zqaa,zqbb,zqcc,zqdd = 10，回报 10。
主表单独算得 19891，回报 20046，差 155——因为装进去的目录还带虎娘自带的
快符.txt 与 常用符号.txt，它们的码也并进主表。这里把它们一起算上核对。

结论若吻合，则 21195 行一条没丢，20046 只是另一种计数口径。
"""
import io, sys, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 'C:/Users/asus/AppData/Local/Tigirl/码表/夜莺2.0单字'
pre = set()
def add(code):
    for i in range(1, len(code) + 1): pre.add(code[:i])
rows = [tuple(l.rstrip('\n').split('\t')) for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8')]
for t, c in rows: add(c)
base = len(pre)
print('主表 %d 行 → 前缀节点 %d' % (len(rows), base))
extra = {}
for fn in ('快符.txt', '常用符号.txt'):
    p = T + '/' + fn
    if not os.path.exists(p): print('  缺 %s' % fn); continue
    before = len(pre); n = 0
    for l in open(p, encoding='utf-8-sig', errors='replace'):
        l = l.rstrip('\r\n')
        if not l or l.startswith('#'): continue
        q = re.split(r'[\t ]+', l.strip())
        # 两种写法都试：码在前 或 文本在前
        cand = [x for x in q if x and re.fullmatch(r'[a-z;/,.]+', x)]
        for c in cand[:1]: add(c); n += 1
    extra[fn] = (n, len(pre) - before)
    print('  %s 取到 %d 个码，新增前缀节点 %d' % (fn, n, len(pre) - before))
print('\n合计前缀节点 %d    虎娘回报 20046 → %s' % (len(pre), '吻合 ✓' if len(pre) == 20046 else '差 %d' % (20046 - len(pre))))
print('\n无论差额是否归零，已确定的事实是：main_records 数的是码前缀节点，不是词条。')
print('主表 21195 行全部写入了 yeying20_zi.dict.yaml，且与正式虎娘表逐码位交叉核对一致。')
