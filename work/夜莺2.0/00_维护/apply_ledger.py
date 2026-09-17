# -*- coding: utf-8 -*-
"""第一步：按台账改两张主表（仿 0.9/1.0 的 apply_v085_practice_issues.py）。默认预演，--apply 才落盘。
    python apply_ledger.py            # 预演：列出每行会做什么、体检结果，不写任何文件
    python apply_ledger.py --apply    # 落盘：先备份两张主表与台账，再写表，回填台账（状态/时间/结果/前后 SHA256）
台账 实战问题机器参数.tsv 字段：问题ID 原文摘录 状态 目标码表 操作 原编码 原字词 新编码 新字词 目标候选位 备注 处理时间 处理结果 修改前SHA256 修改后SHA256
  状态：待处理 / 已修复 / 忽略（只处理"待处理"）；目标码表：单字表 / 字词表 / 符号表
  操作：查询；新增（新编码 新字词 [目标候选位，缺省排最后；占位则原有的顺延]）；删除（原编码 原字词）；
        改码（原编码 原字词 → 新编码 [目标候选位]）；改词（原编码 原字词 → 新字词）；调序（原编码 原字词 → 目标候选位，其余顺延）
  候选位 = 该表里同码的第几个（字词表里字和词一起数；单字表里只数字）。
只许动两张主表；没被点名的行一个字节都不变。落盘前对结果做结构体检（不过则拒绝落盘）：
  ① 无重复行 ② 单字表每一行都在字词表里，反之字词表的单字行都在单字表里 ③ 每个码位上，单字在两表里的先后一致。"""
import io, sys, os, csv, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); M = H + '/主表'; LEDGER = H + '/实战问题机器参数.tsv'
TABLES = {'单字表': M + '/夜莺2.0单字表.txt', '字词表': M + '/夜莺2.0字词表.txt', '符号表': M + '/夜莺2.0符号表.txt'}
FIELDS = ['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词', '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']
sha = lambda b: hashlib.sha256(b).hexdigest()
def load(p): return [tuple(l.split('\t')) for l in open(p, encoding='utf-8').read().split('\n') if l]
def render(rows): return ('\n'.join('%s\t%s' % r for r in rows) + '\n').encode('utf-8')
def slot(rows, code):
    idx = [i for i, r in enumerate(rows) if r[1] == code]; return idx
def insert(rows, text, code, rank):
    idx = slot(rows, code)
    if idx:
        k = len(idx) if rank is None else rank - 1
        if not 0 <= k <= len(idx): raise ValueError('目标候选位 %s 超出范围（%s 现有 %d 个）' % (rank, code, len(idx)))
        pos = idx[k] if k < len(idx) else idx[-1] + 1
    else:
        if rank not in (None, 1): raise ValueError('%s 是空码位，候选位只能是 1' % code)
        pos = next((i for i, r in enumerate(rows) if r[1] > code), len(rows))      # 新码位按编码顺序落位
    rows.insert(pos, (text, code)); return len(idx) + 1 if rank is None else rank
def apply_row(rows, r):
    op = r['操作'].strip(); oc, ot, nc, nt = r['原编码'].strip(), r['原字词'].strip(), r['新编码'].strip(), r['新字词'].strip()
    rank = int(r['目标候选位']) if r['目标候选位'].strip() else None
    if op == '查询':
        c = oc or nc; return '%s：%s' % (c, '、'.join(t for t, x in rows if x == c) or '空')
    if op == '新增':
        if (nt, nc) in rows: raise ValueError('已存在：%s %s' % (nt, nc))
        k = insert(rows, nt, nc, rank); return '新增 %s,%d=%s → %s' % (nc, k, nt, '、'.join(t for t, x in rows if x == nc))
    if (ot, oc) not in rows: raise ValueError('找不到：%s %s' % (ot, oc))
    before = '、'.join(t for t, x in rows if x == oc)
    if op == '删除': rows.remove((ot, oc)); return '删除 %s=%s；%s：%s → %s' % (oc, ot, oc, before, '、'.join(t for t, x in rows if x == oc) or '空')
    if op == '改词':
        if (nt, oc) in rows: raise ValueError('已存在：%s %s' % (nt, oc))
        rows[rows.index((ot, oc))] = (nt, oc); return '改词 %s：%s → %s' % (oc, ot, nt)
    if op == '改码':
        if (ot, nc) in rows: raise ValueError('已存在：%s %s' % (ot, nc))
        rows.remove((ot, oc)); k = insert(rows, ot, nc, rank); return '改码 %s：%s → %s,%d；%s：%s' % (ot, oc, nc, k, nc, '、'.join(t for t, x in rows if x == nc))
    if op == '调序':
        if rank is None: raise ValueError('调序必须填目标候选位')
        rows.remove((ot, oc)); insert(rows, ot, oc, rank); return '调序 %s：%s → %s' % (oc, before, '、'.join(t for t, x in rows if x == oc))
    raise ValueError('未知操作：' + op)
def checkup(tabs):
    bad = []
    for n, rows in tabs.items():
        d = [r for r, c in collections.Counter(rows).items() if c > 1]
        if d: bad.append('%s 重复行：%s' % (n, d[:5]))
        e = [r for r in rows if len(r) != 2 or not r[0] or not r[1]]
        if e: bad.append('%s 空字段：%s' % (n, e[:5]))
    a = collections.defaultdict(list); b = collections.defaultdict(list)
    for t, c in tabs['单字表']: a[c].append(t)
    for t, c in tabs['字词表']:
        if len(t) == 1: b[c].append(t)
    diff = [c for c in set(a) | set(b) if a.get(c) != b.get(c)]
    if diff: bad.append('两表单字不一致 %d 个码位：%s' % (len(diff), ['%s 单字表[%s] 字词表[%s]' % (c, ''.join(a.get(c, [])), ''.join(b.get(c, []))) for c in sorted(diff)[:8]]))
    return bad
def main():
    rows_l = list(csv.DictReader(open(LEDGER, encoding='utf-8-sig', newline=''), delimiter='\t'))
    assert not rows_l or list(rows_l[0].keys()) == FIELDS, '台账字段不符'
    pending = [r for r in rows_l if r['状态'].strip() == '待处理']
    tabs = {n: load(p) for n, p in TABLES.items()}; before = {n: render(tabs[n]) for n in tabs}
    for n, p in TABLES.items(): assert before[n] == open(p, 'rb').read(), n + ' 读写不往返，拒绝处理'
    base_bad = checkup(tabs)
    if not pending: print('没有待处理的行。主表体检：%s' % (base_bad or '通过')); return
    results = []
    for r in pending:
        n = r['目标码表'].strip(); assert n in TABLES, '目标码表只能是 单字表/字词表：%s' % r['问题ID']
        try: res = apply_row(tabs[n], r)
        except ValueError as e: print('✗ %s [%s] %s' % (r['问题ID'], n, e)); sys.exit(1)
        results.append(res); print('  %s [%s] %s' % (r['问题ID'], n, res))
    bad = checkup(tabs); after = {n: render(tabs[n]) for n in tabs}
    for n in tabs: print('%s：%d → %d 行  %s → %s' % (n, before[n].count(b'\n'), after[n].count(b'\n'), sha(before[n])[:12], sha(after[n])[:12]))
    if bad: print('✗ 体检不过，拒绝落盘：\n  ' + '\n  '.join(bad)); sys.exit(1)
    print('体检通过。')
    if '--apply' not in sys.argv: print('（预演，未写任何文件；确认后加 --apply）'); return
    now = datetime.datetime.now(); bk = H + '/备份/' + now.strftime('%Y%m%d_%H%M%S'); os.makedirs(bk)
    for n, p in TABLES.items(): shutil.copy2(p, bk)
    shutil.copy2(LEDGER, bk)
    for n, p in TABLES.items():
        if after[n] != before[n]: open(p + '.tmp', 'wb').write(after[n]); os.replace(p + '.tmp', p)
    for r, res in zip(pending, results):
        n = r['目标码表'].strip(); r.update({'状态': '已修复' if r['操作'].strip() != '查询' else '已查询', '处理时间': now.isoformat(timespec='seconds'), '处理结果': res, '修改前SHA256': sha(before[n]), '修改后SHA256': sha(after[n])})
    w = csv.DictWriter(open(LEDGER, 'w', encoding='utf-8-sig', newline=''), fieldnames=FIELDS, delimiter='\t', lineterminator='\n'); w.writeheader(); w.writerows(rows_l)
    print('已落盘 %d 行；备份在 %s' % (len(pending), bk))
main()
