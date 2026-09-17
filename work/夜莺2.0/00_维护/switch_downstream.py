# -*- coding: utf-8 -*-
"""一次性：把导出端脚本的输入从生成链产物（78、113）改到两张主表。改前各自备份到 00_维护/备份/切换前/。可重复运行。"""
import io, sys, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
S = '00_维护/主表/夜莺2.0单字表.txt'; Z = '00_维护/主表/夜莺2.0字词表.txt'
JOBS = {
 '106_全平台导出/build.py': [
  ("SRC=W/'113_扩展字入表/夜莺2.0最终表_普通格式.txt'", "SRC=W/'%s'" % Z),
  ("pointer={'单字表':'78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt','字词表':'113_扩展字入表/夜莺2.0最终表_普通格式.txt（110 投票序 + 112 扩展字）'}", "pointer={'单字表':'%s','字词表':'%s'}   # 2026-09-17 主表冻结" % (S, Z)),
  ("single=[tuple(x.rsplit('\\t',1)) for x in (baseline/'夜莺2.0纯单字表_普通格式.txt').read_text(encoding='utf-8-sig').splitlines() if x]+[tuple(x.rsplit('\\t',1)) for x in (W/'112_扩展字继承/夜莺2.0扩展字表_普通格式.txt').read_text(encoding='utf-8-sig').splitlines() if x]",
   "single=[tuple(x.rsplit('\\t',1)) for x in (W/'%s').read_text(encoding='utf-8-sig').splitlines() if x]" % S)],
 '106_全平台导出/verify.py': [("P.parent/'113_扩展字入表/夜莺2.0最终表_普通格式.txt'", "P.parent/'%s'" % Z)],
 '114_工具箱同步扩展字/sync.py': [("open(B + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):\n    p = line", "open(B + '/%s', encoding='utf-8-sig'):\n    p = line" % Z),
  ("open(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):", "open(B + '/%s', encoding='utf-8-sig'):" % S)],
 '117_发布v2.0/build_release.py': [("W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt'", "W + '/%s'" % Z), ("W + '/113_扩展字入表/夜莺2.0最终表_码前格式.txt'", "W + '/00_维护/派生/夜莺2.0字词表_码前.txt'"),
  ("W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'", "W + '/%s'" % S)],
 '118_官网2.0/compute_performance.py': [("open(W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt'", "open(W + '/%s'" % Z)],
}
for rel, pairs in JOBS.items():
    p = W + '/' + rel; s = open(p, encoding='utf-8').read(); n = 0
    for old, new in pairs:
        if old in s:
            assert s.count(old) == 1, (rel, old[:40]); s = s.replace(old, new); n += 1
        else: assert new in s, (rel, '找不到锚点', old[:60])
    if n:
        bk = H + '/备份/切换前/' + rel; os.makedirs(os.path.dirname(bk), exist_ok=True)
        if not os.path.exists(bk): shutil.copy2(p, bk)
        open(p, 'w', encoding='utf-8').write(s)
    print(rel, '改', n, '处')
