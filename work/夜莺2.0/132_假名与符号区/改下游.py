# -*- coding: utf-8 -*-
"""符号进两张主表后，给下游加"只认汉字"的过滤（2026-09-17 你定：Rime 不能被符号污染整句）。
  106/build.py  辅助码、Rime 整句词典/原生词表/反查 三处只收汉字，符号仍进固定码表与各平台码表。
  114/sync.py   工具箱的字码与断言只看汉字。
改前各自备份到 132_假名与符号区/改下游前备份/。可重复运行。"""
import io, sys, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); BK = H + '/改下游前备份'
HAN_SRC = ("HAN=lambda t:len(t)==1 and ('\\u3400'<=t<='\\u9fff' or '\\uf900'<=t<='\\ufaff' or '\\U00020000'<=t<='\\U0003134f')"
           "   # 2026-09-17 o 区符号也在单字表里，这里只认汉字\n")
def patch(rel, pairs):
    p = W + '/' + rel; s = open(p, encoding='utf-8').read(); n = 0
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, (rel, old[:60], s.count(old)); s = s.replace(old, new); n += 1
    if n:
        q = BK + '/' + rel; os.makedirs(os.path.dirname(q), exist_ok=True)
        if not os.path.exists(q): shutil.copy2(p, q)
        open(p, 'w', encoding='utf-8').write(s)
    print('%-28s 改 %d 处' % (rel, n))
patch('106_全平台导出/build.py', [
    ("aux=defaultdict(list)\nfor t,c in single:\n if len(c)==4 and c[2:] not in aux[t]:aux[t].append(c[2:])",
     HAN_SRC + "aux=defaultdict(list)\nfor t,c in single:\n if len(c)==4 and HAN(t) and c[2:] not in aux[t]:aux[t].append(c[2:])"),
    ("full=defaultdict(list)\nfor t,c in single:\n if len(c)==4:full[t,c[:2]].append(c)",
     "full=defaultdict(list)\nfor t,c in single:\n if len(c)==4 and HAN(t):full[t,c[:2]].append(c)   # 符号不进整句词典与反查")])
patch('114_工具箱同步扩展字/sync.py', [
    ("    if len(p) >= 2 and len(p[0]) == 1: groups.setdefault(p[1], []).append(p[0]); codes_of[p[0]].append(p[1])",
     "    if len(p) >= 2 and HAN(p[0]): groups.setdefault(p[1], []).append(p[0]); codes_of[p[0]].append(p[1])"),
    ("    if len(p) >= 2: g78.setdefault(p[1], []).append(p[0])",
     "    if len(p) >= 2 and HAN(p[0]): g78.setdefault(p[1], []).append(p[0])"),
    ("groups = collections.OrderedDict(); codes_of = collections.defaultdict(list)",
     HAN_SRC.rstrip('\n').replace('HAN=', 'HAN = ') + '\ngroups = collections.OrderedDict(); codes_of = collections.defaultdict(list)')])
