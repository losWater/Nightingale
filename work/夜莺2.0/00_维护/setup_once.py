# -*- coding: utf-8 -*-
"""一次性收尾：78 audit 支持指定表路径；封存生成链重建脚本；建空台账；写维护说明。可重复运行。"""
import io, sys, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
p = W + '/78_纯单字表核验/audit.py'; s = open(p, encoding='utf-8').read()
old = "    for line in open(B+'/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt',encoding='utf-8-sig'):"; new = "    for line in open(sys.argv[1] if len(sys.argv)>1 else B+'/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt',encoding='utf-8-sig'):   # 2026-09-17 可指定表路径（主表体检用）"
if new not in s: assert s.count(old) == 1; open(p, 'w', encoding='utf-8').write(s.replace(old, new))
os.makedirs(H + '/封存', exist_ok=True)
for fn in ('rebuild.py', 'order_buyin.py', '重建记录.jsonl'):
    if os.path.exists(H + '/' + fn): shutil.move(H + '/' + fn, H + '/封存/' + fn)
g = H + '/封存/rebuild.py'; s = open(g, encoding='utf-8').read(); guard = "import sys\nif '--我知道已封存' not in sys.argv: sys.exit('生成链已于 2026-09-17 封存：主表冻结后不再从 83→113 重新生成。维护请用 apply_ledger.py，导出请用 export.py。')\n"
if guard not in s: open(g, 'w', encoding='utf-8').write(s.replace('import io, sys, os, re,', guard + 'import io, os, re,', 1))
L = H + '/实战问题机器参数.tsv'
if not os.path.exists(L): open(L, 'w', encoding='utf-8-sig', newline='').write('\t'.join(['问题ID', '原文摘录', '状态', '目标码表', '操作', '原编码', '原字词', '新编码', '新字词', '目标候选位', '备注', '处理时间', '处理结果', '修改前SHA256', '修改后SHA256']) + '\n')
open(H + '/README.md', 'w', encoding='utf-8').write('''# 夜莺 2.0 维护（2026-09-17 起）

默认两张主表已经没有问题。维护只往这两张表里改；生成各输入法格式是独立的第二步。两步互不依赖，风险隔离。

- `主表/夜莺2.0单字表.txt`：8105 字 + 7391 扩展字，`字\\t码`。
- `主表/夜莺2.0字词表.txt`：单字 + 词 + 简词，`字词\\t码`。同码的先后就是候选次序。

## 第一步：改主表

1. 你把问题用白话写进 `D:/nightingale/releases/v2.5/用户实战反馈.txt`（你手写的文件，脚本不碰）。
2. 每个问题翻译成 `实战问题机器参数.tsv` 里的几行原子操作（状态填"待处理"）：查询 / 新增 / 删除 / 改码 / 改词 / 调序。单字的改动两张表各写一行。
3. `python apply_ledger.py` 预演，看每行结果和体检；确认后 `python apply_ledger.py --apply` 落盘。自动备份到 `备份/时间戳/`，台账回填时间、结果、前后 SHA256。没被点名的行不变。

## 第二步：生成兼容格式（PowerShell）

`python export.py [--deploy] [--release]`。只读主表；结构体检不过即停；规则体检（78 的 14 项）只报告不拦。

## 已封存

`封存/rebuild.py` 是冻结前的生成链重建（83→113）。83、97、109、110、112、113 等目录只作历史来历，不再运行；里面的裁定批次、人工指定、补音表不再是真源。
''')
print('ok')
