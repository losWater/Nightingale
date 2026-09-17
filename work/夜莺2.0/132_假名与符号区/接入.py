# -*- coding: utf-8 -*-
"""把符号表接进流程（2026-09-17 你定的三表架构）。改前备份到 132_假名与符号区/接入前备份/。可重复运行。
  106/build.py      读符号表并进 groups（符号排在同码位原有条目之后）；新增产出 综合表 与 普通单字表；
                    手心加 05_符号 模块。single 不含符号，所以辅助码、Rime 整句词典与反查天然干净。
  00_维护/export.py  体检三张表，运行前后校验三张表都没被改动。
  00_维护/apply_ledger.py  目标码表增加「符号表」。"""
import io, sys, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); BK = H + '/接入前备份'
def patch(rel, pairs):
    p = W + '/' + rel; s = open(p, encoding='utf-8').read(); n = 0
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, (rel, old[:70], s.count(old)); s = s.replace(old, new); n += 1
    if n:
        q = BK + '/' + rel; os.makedirs(os.path.dirname(q), exist_ok=True)
        if not os.path.exists(q): shutil.copy2(p, q)
        open(p, 'w', encoding='utf-8').write(s)
    print('%-28s 改 %d 处' % (rel, n))
patch('106_全平台导出/build.py', [
    # 1 读符号表
    ("groups=defaultdict(list)\nfor t,c in rows:groups[c].append(t)",
     "symbols=[tuple(x.rsplit('\\t',1)) for x in (W/'00_维护/主表/夜莺2.0符号表.txt').read_text(encoding='utf-8-sig').splitlines() if x]   # 2026-09-17 第三张主表\n"
     "pointer['符号表']='00_维护/主表/夜莺2.0符号表.txt'\n"
     "groups=defaultdict(list)\nfor t,c in rows:groups[c].append(t)\n"
     "for t,c in symbols:groups[c].append(t)   # 符号排在同码位原有条目之后"),
    # 2 综合表与普通单字表两份发布物
    ("groups=defaultdict(list)\nfor t,c in rows:groups[c].append(t)\nfor t,c in symbols:groups[c].append(t)   # 符号排在同码位原有条目之后",
     "groups=defaultdict(list)\nfor t,c in rows:groups[c].append(t)\nfor t,c in symbols:groups[c].append(t)   # 符号排在同码位原有条目之后\n"
     "# 发布用的两份：综合表＝字词表＋符号（＋快符，下面并入）；普通单字表＝单字表＋符号（含多字符的符号），给只打单字的人\n"
     "plain_single=[(t,c) for t,c in single]+[(t,c) for t,c in symbols]\n"
     "plain_single.sort(key=lambda r:(r[1],))\n"
     "for reverse in [False,True]:\n"
     " write(OUT/'普通字词表'/f'夜莺2.0_普通单字表_{\"码前\" if reverse else \"普通\"}.txt',''.join(f'{c}\\t{t}\\r\\n' if reverse else f'{t}\\t{c}\\r\\n' for t,c in plain_single))"),
    # 3 手心加 05_符号
    (" if (t,c) in quickset:k='04_快符'\n elif len(t)==1:k='01_核心单字'",
     " if (t,c) in quickset:k='04_快符'\n elif (t,c) in symbolset:k='05_符号'\n elif len(t)==1:k='01_核心单字'"),
    ("quickset={(t,c) for t,c,n in quick}", "quickset={(t,c) for t,c,n in quick}\nsymbolset={(t,c) for t,c in symbols}"),
    # 4 报告
    ("report['Rime固定条数']=len(allrows)", "report['符号表条数']=len(symbols);report['综合表条数']=len(allrows);report['普通单字表条数']=len(plain_single)\nreport['Rime固定条数']=len(allrows)")])
patch('00_维护/export.py', [
    ("M = {'单字表': H + '/主表/夜莺2.0单字表.txt', '字词表': H + '/主表/夜莺2.0字词表.txt'}",
     "M = {'单字表': H + '/主表/夜莺2.0单字表.txt', '字词表': H + '/主表/夜莺2.0字词表.txt', '符号表': H + '/主表/夜莺2.0符号表.txt'}"),
    ("bad = checkup(rows); print('%s 主表结构体检  单字表 %d 行，字词表 %d 行  %s' % ('✗' if bad else '✓', len(rows['单字表']), len(rows['字词表']), '；'.join(bad)))",
     "bad = checkup(rows); print('%s 主表结构体检  单字表 %d 行，字词表 %d 行，符号表 %d 行  %s' % ('✗' if bad else '✓', len(rows['单字表']), len(rows['字词表']), len(rows['符号表']), '；'.join(bad)))")])
patch('00_维护/apply_ledger.py', [
    ("TABLES = {'单字表': M + '/夜莺2.0单字表.txt', '字词表': M + '/夜莺2.0字词表.txt'}",
     "TABLES = {'单字表': M + '/夜莺2.0单字表.txt', '字词表': M + '/夜莺2.0字词表.txt', '符号表': M + '/夜莺2.0符号表.txt'}"),
    ("  状态：待处理 / 已修复 / 忽略（只处理\"待处理\"）；目标码表：单字表 / 字词表",
     "  状态：待处理 / 已修复 / 忽略（只处理\"待处理\"）；目标码表：单字表 / 字词表 / 符号表")])
