# -*- coding: utf-8 -*-
"""把「拆分」数据在工程里的所有副本找出来，看哪些已随订正更新、哪些还是旧的（2026-09-21）。

起因：改了 55 与 112 两个源并重跑 export 后，工具包里仍显示「由 ＋ 丨」。
查出 114/sync.py 对已有字是「拆分逐条不变」，只从 58 的页面继承——所以拆分不止两个源。
本脚本只读，逐个文件查这 6 个代表字的拆分，定位所有还没更新的副本。
"""
import io, sys, os, re, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
OLD, NEW = '由 ＋ 丨', '囗 ＋ 横 ＋ 丨 ＋ 丨'
OLD2, NEW2 = '由丨', '囗横丨丨'          # 无分隔符写法（虎娘 .拆分 用连写／间隔号）
PROBE = ['蛐', '澧', '農', '體']
FILES = []
for pat in ('55_拆分继承核验/*.txt', '112_扩展字继承/*.txt', '58_拆分查询/*.html',
            '65_群友离线工具包/**/*.txt', '65_群友离线工具包/**/*.html',
            '106_全平台导出/**/夜莺.拆分', '106_全平台导出/**/*拆分*',
            '123_虎娘导入/**/*.拆分', '137_虎娘单字版/**/*.拆分',
            '127_魔虎基座试验/**/*拆分*', '117_发布v2.0/**/*拆分*', '118_官网2.0/**/*拆分*'):
    FILES += glob.glob(W + '/' + pat, recursive=True)
FILES = sorted({os.path.normpath(f) for f in FILES if os.path.isfile(f)})
print('检查 %d 个文件\n' % len(FILES))
stale = []
for f in FILES:
    try: s = open(f, encoding='utf-8-sig', errors='replace').read()
    except Exception as e: print('  读不了 %s：%s' % (f, e)); continue
    n_old = s.count(OLD) + s.count(OLD2) + s.count('由·丨')
    n_new = s.count(NEW) + s.count(NEW2) + s.count('囗·横·丨·丨')
    if n_old == 0 and n_new == 0: continue
    rel = os.path.relpath(f, W).replace('\\', '/')
    tag = '旧 ✗' if n_old else '新 ✓'
    print('  %-4s 旧写法 %-4d 新写法 %-4d  %s' % (tag, n_old, n_new, rel))
    if n_old: stale.append(rel)
print('\n仍是旧写法的文件 %d 个：' % len(stale))
for r in stale: print('   ' + r)
if not stale: print('   （无）')
