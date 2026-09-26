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
import io, sys, os, csv, json, hashlib, shutil, datetime, collections, argparse, re
from pathlib import Path
from context import load as load_context, table_paths, atomic, json_bytes
from semantics import evolve
FIELDS = ['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词', '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']
sha = lambda b: hashlib.sha256(b).hexdigest()
def load(p): return [tuple(l.split('\t')) for l in Path(p).read_text(encoding='utf-8').split('\n') if l]
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
    for field in ('原字词','新字词'):
        value=r[field]
        if value and (value!=value.strip() or any(ord(c)<32 or ord(c)==127 or c in '\u2028\u2029' for c in value)):
            raise ValueError(field+'含首尾空白或控制分隔字符')
    for field in ('原编码','新编码'):
        if r[field] and not re.fullmatch('[a-z]+',r[field]): raise ValueError(field+'必须为小写英文字母')
    op = r['操作'].strip(); oc, ot, nc, nt = r['原编码'].strip(), r['原字词'].strip(), r['新编码'].strip(), r['新字词'].strip()
    rank = int(r['目标候选位']) if r['目标候选位'].strip() else None
    if op == '查询':
        c = oc or nc; return '%s：%s' % (c, '、'.join(t for t, x in rows if x == c) or '空')
    if op == '新增':
        if not nt or not nc: raise ValueError('新增需要新字词和新编码')
        if (nt, nc) in rows: raise ValueError('已存在：%s %s' % (nt, nc))
        k = insert(rows, nt, nc, rank); return '新增 %s,%d=%s → %s' % (nc, k, nt, '、'.join(t for t, x in rows if x == nc))
    if (ot, oc) not in rows: raise ValueError('找不到：%s %s' % (ot, oc))
    before = '、'.join(t for t, x in rows if x == oc)
    if op == '删除': rows.remove((ot, oc)); return '删除 %s=%s；%s：%s → %s' % (oc, ot, oc, before, '、'.join(t for t, x in rows if x == oc) or '空')
    if op == '改词':
        if not nt: raise ValueError('改词需要新字词')
        if (nt, oc) in rows: raise ValueError('已存在：%s %s' % (nt, oc))
        rows[rows.index((ot, oc))] = (nt, oc); return '改词 %s：%s → %s' % (oc, ot, nt)
    if op == '改码':
        if not nc: raise ValueError('改码需要新编码')
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
        e = [r for r in rows if len(r) != 2 or not r[0] or not re.fullmatch('[a-z]+',r[1])
             or any(ord(c)<32 or ord(c)==127 or c in '\u2028\u2029' for c in r[0])
             or (n=='单字表' and len(r[0])!=1)]
        if e: bad.append('%s 非法字段或编码：%s' % (n, e[:5]))
    if bad: return bad
    a = collections.defaultdict(list); b = collections.defaultdict(list)
    for t, c in tabs['单字表']: a[c].append(t)
    for t, c in tabs['字词表']:
        if len(t) == 1: b[c].append(t)
    diff = [c for c in set(a) | set(b) if a.get(c) != b.get(c)]
    if diff: bad.append('两表单字不一致 %d 个码位：%s' % (len(diff), ['%s 单字表[%s] 字词表[%s]' % (c, ''.join(a.get(c, [])), ''.join(b.get(c, []))) for c in sorted(diff)[:8]]))
    return bad
def main():
    parser = argparse.ArgumentParser(description='默认只预演；--apply 才改表。历史状态不会重复执行。')
    parser.add_argument('--root')
    parser.add_argument('--version', help='目录名，仅允许对当前未封存目录落盘')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    _, directory, _ = load_context(args.root, args.version, writable=args.apply)
    H = str(directory); LEDGER = str(directory/'记录/修改台账.tsv')
    TABLES = {n: str(p) for n, p in table_paths(directory).items()}
    ledger_original=Path(LEDGER).read_bytes()
    meta_path=directory/'配置/编码类型.json'
    meta_original=meta_path.read_bytes() if meta_path.exists() else None
    with io.StringIO(ledger_original.decode('utf-8-sig'), newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        assert reader.fieldnames == FIELDS, '台账字段不符'
        rows_l = list(reader)
    assert all(None not in r and None not in r.values() for r in rows_l), '台账列数不符'
    ids = [r['问题ID'] for r in rows_l]
    assert all(ids) and len(ids) == len(set(ids)), '台账问题ID为空或重复'
    pending = [r for r in rows_l if r['状态'].strip() == '待处理']
    tabs = {n: load(p) for n, p in TABLES.items()}; before = {n: render(tabs[n]) for n in tabs}
    before_tabs={n:list(rows) for n,rows in tabs.items()}
    for n, p in TABLES.items(): assert before[n] == Path(p).read_bytes(), n + ' 读写不往返，拒绝处理'
    base_bad = checkup(tabs)
    if base_bad: raise ValueError('原始主表体检失败：' + str(base_bad))
    if not pending: print('没有待处理的行。主表体检：通过'); return
    results = []
    for r in pending:
        n = r['目标码表'].strip(); assert n in TABLES, '目标码表只能是 单字表/字词表：%s' % r['问题ID']
        try: res = apply_row(tabs[n], r)
        except ValueError as e: print('✗ %s [%s] %s' % (r['问题ID'], n, e)); sys.exit(1)
        results.append(res); print('  %s [%s] %s' % (r['问题ID'], n, res))
    bad = checkup(tabs); after = {n: render(tabs[n]) for n in tabs}
    for n in tabs: print('%s：%d → %d 行  %s → %s' % (n, before[n].count(b'\n'), after[n].count(b'\n'), sha(before[n])[:12], sha(after[n])[:12]))
    if bad: print('✗ 体检不过，拒绝落盘：\n  ' + '\n  '.join(bad)); sys.exit(1)
    meta,warnings=evolve(directory,pending,before_tabs,tabs)
    meta_after=json_bytes(meta)
    for warning in warnings: print('影响提示：'+warning)
    print('体检通过。')
    if not args.apply: print('（预演，未写任何文件；确认后加 --apply）'); return
    now = datetime.datetime.now().astimezone(); bk = H + '/备份/' + now.strftime('%Y%m%d_%H%M%S_%f'); os.makedirs(bk)
    for n, p in TABLES.items(): shutil.copy2(p, bk)
    shutil.copy2(LEDGER, bk)
    if meta_original is not None: shutil.copy2(meta_path,bk)
    for r, res in zip(pending, results):
        n = r['目标码表'].strip(); r.update({'状态': '已修复' if r['操作'].strip() != '查询' else '已查询', '处理时间': now.isoformat(timespec='seconds'), '处理结果': res, '修改前SHA256': sha(before[n]), '修改后SHA256': sha(after[n])})
        r['处理结果'] += '；编码类型SHA256='+sha(meta_after)
        if warnings: r['处理结果'] += '；影响提示：'+'；'.join(warnings)
    output = io.StringIO(newline='')
    w = csv.DictWriter(output, fieldnames=FIELDS, delimiter='\t', lineterminator='\n'); w.writeheader(); w.writerows(rows_l)
    # Abort on concurrent edits; retain backups and roll back ordinary write failures.
    originals = {Path(p): before[n] for n, p in TABLES.items()}
    originals[Path(LEDGER)] = ledger_original
    originals[meta_path] = meta_original
    if any((p.read_bytes() if p.exists() else None) != data for p, data in originals.items()):
        raise ValueError('预演期间文件发生变化，拒绝覆盖')
    try:
        for n, p in TABLES.items():
            if after[n] != before[n]: atomic(p, after[n])
        atomic(meta_path,meta_after)
        atomic(LEDGER, output.getvalue().encode('utf-8'))
    except Exception:
        for p, data in originals.items():
            if data is None: p.unlink(missing_ok=True)
            else: atomic(p, data)
        raise
    print('已落盘 %d 行；备份在 %s' % (len(pending), bk))
if __name__ == '__main__': main()
