# -*- coding: utf-8 -*-
"""把 E:/夜莺2.0/work/夜莺2.0 按 rules.py 的规则镜像到 D:/nightingale/work/夜莺2.0（GitHub 仓库 losWater/Nightingale 的工作树）。
- 镜像：源里入库的文件复制过去（大小+修改时间相同则跳过），目标里多出的文件删除（只动 work/夜莺2.0 这一棵）。
- 附带：00_工作区/（E 盘根的 README/AGENTS/迁移校验清单）、排除清单.json（每个被排除的目录/文件及原因）、.gitignore（同一套规则）。
- 不做 git 提交；提交由调用方决定。用法：python sync.py [--dry]"""
import io, sys, os, json, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import walk_included, gitignore_text
SRC = 'E:/夜莺2.0/work/夜莺2.0'; DST = 'D:/nightingale/work/夜莺2.0'; EROOT = 'E:/夜莺2.0'
dry = '--dry' in sys.argv
MB = lambda b: '%.1f' % (b / 1048576)
inc, exc = walk_included(SRC)
plan = {p: SRC + '/' + p for p, s in inc}
for n in ['README.md', 'AGENTS.md', '迁移校验清单.json']:
    if os.path.exists(EROOT + '/' + n): plan['00_工作区/' + n] = EROOT + '/' + n
copied = 0; skipped = 0; removed = 0; bytes_copied = 0
for rel, src in sorted(plan.items()):
    dst = DST + '/' + rel; st = os.stat(src)
    if os.path.exists(dst):
        dt = os.stat(dst)
        if dt.st_size == st.st_size and int(dt.st_mtime) == int(st.st_mtime): skipped += 1; continue
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
    copied += 1; bytes_copied += st.st_size
# 删除目标里多出的
want = set(plan) | {'排除清单.json', '.gitignore'}
if os.path.isdir(DST):
    for dp, dn, fn in os.walk(DST, topdown=False):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), DST).replace('\\', '/')
            if rel not in want:
                if not dry: os.remove(os.path.join(dp, f))
                removed += 1
        if not dry:
            for d in dn:
                q = os.path.join(dp, d)
                if os.path.isdir(q) and not os.listdir(q): os.rmdir(q)
why = collections.Counter(); whys = collections.Counter()
for p, s, w in exc: why[w] += 1; whys[w] += s
manifest = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '源': SRC, '规则': '116_仓库同步/rules.py',
            '入库': {'文件数': len(plan), '字节': sum(os.path.getsize(v) for v in plan.values())},
            '排除': {'条目数': len(exc), '字节': sum(s for p, s, w in exc), '按原因': {w: {'条目': why[w], 'MB': float(MB(whys[w]))} for w in why}},
            '排除明细': [{'路径': p, 'MB': float(MB(s)), '原因': w} for p, s, w in sorted(exc)]}
if not dry:
    os.makedirs(DST, exist_ok=True)
    json.dump(manifest, open(DST + '/排除清单.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(DST + '/.gitignore', 'w', encoding='utf-8', newline='\n').write(gitignore_text())
    json.dump(manifest, open(os.path.dirname(os.path.abspath(__file__)) + '/上次同步.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('%s入库 %d 文件 %s MB；本次复制 %d（%s MB）、未变跳过 %d、目标多余删除 %d；排除 %d 条 %s MB' % (
    '[试运行] ' if dry else '', len(plan), MB(manifest['入库']['字节']), copied, MB(bytes_copied), skipped, removed, len(exc), MB(manifest['排除']['字节'])))
