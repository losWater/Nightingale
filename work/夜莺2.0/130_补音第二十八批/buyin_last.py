# -*- coding: utf-8 -*-
"""裁定 2026-09-17："补音字放在普通字的后面"（优先于出简让全·字对字）。落成代码规则：
① 00_维护/order_buyin.py：把单字表里登记码位上的补音字排到该码位普通字之后（幂等），rebuild.py 在 78 核验前调用；
② 78 audit：出简让全·字对字 检查时不看补音字（取代旧的逐码位 YIELD_EXC 手写豁免），新增检查"补音字排在普通字后"；
③ 规则文档 5b 改写。可重复运行。"""
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def patch(p, pairs):
    s = open(p, encoding='utf-8').read(); n = 0
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, (p, old[:50]); s = s.replace(old, new); n += 1
    open(p, 'w', encoding='utf-8').write(s); print(os.path.basename(p), '改', n, '处')
open(W + '/00_维护/order_buyin.py', 'w', encoding='utf-8').write('''# -*- coding: utf-8 -*-
"""单字表次序规则：登记在 83/补音表.json 的补音字，在所登记的全码位上排到普通字之后（裁定 2026-09-17）。幂等；有改动才写文件。"""
import io, sys, os, json, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = W + '/78_纯单字表核验/'
reg = json.load(open(W + '/83_单字表重放/补音表.json', encoding='utf-8'))['条目']
rows = [l.rstrip('\\r\\n').split('\\t') for l in open(D + '夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig') if l.strip()]; moved = []
for code, cs in reg.items():
    idx = [k for k, (_, c) in enumerate(rows) if c == code]; grp = [rows[k] for k in idx]; new = sorted(grp, key=lambda r: r[0] in cs)
    if new != grp:
        moved.append(code)
        for k, r in zip(idx, new): rows[k] = r
if moved:
    out = {}
    for fn, fmt in (('夜莺2.0纯单字表_普通格式.txt', '%s\\t%s'), ('夜莺2.0纯单字表_码前格式.txt', None)):
        data = ('\\r\\n'.join(('%s\\t%s' % (t, c)) if fmt else ('%s\\t%s' % (c, t)) for t, c in rows) + '\\r\\n').encode('utf-8-sig'); open(D + fn, 'wb').write(data); out[fn] = hashlib.sha256(data).hexdigest()
    e = json.load(open(D + '导出说明.json', encoding='utf-8-sig')); e['时间'] = datetime.datetime.now().isoformat(timespec='seconds')
    e['文件'] = [{'文件': fn, '条目': len(rows), 'sha256': h} for fn, h in out.items()]; json.dump(e, open(D + '导出说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('补音字后移 %d 个码位 %s' % (len(moved), moved))
''')
patch(W + '/78_纯单字表核验/audit.py', [
    ("YIELD_EXC = {'pubp': '暴', 'yeuy': '邪'}", "BUYIN = json.load(open(B+'/83_单字表重放/补音表.json',encoding='utf-8'))['条目']   # 补音字登记表：补音字排在普通字后，不参与出简让全·字对字（2026-09-17，取代逐码位手写豁免）\nYIELD_EXC = {}"),
    ("    for F,c in order.items():\n        if len(F)<4: continue\n        free=", "    for F,c in order.items():\n        if len(F)<4: continue\n        c=[w for w in c if w not in BUYIN.get(F,[])]\n        free="),
    ("    chk('出简让全·字对字',bad)\n", "    chk('出简让全·字对字',bad)\n    chk('补音字排在普通字后',[F for F,cs in BUYIN.items() if F in order and any(a in cs and b not in cs for a,b in zip(order[F],order[F][1:]))])\n")])
patch(W + '/00_维护/rebuild.py', [("step('78 核验',", "step('补音字次序', H + '/order_buyin.py')\nstep('78 核验',")])
p = W + '/码表概念与规则.md'; s = open(p, encoding='utf-8').read(); old = '字与字之间仍按单字表次序（含出简让全）。'
if old in s: s = s.replace(old, '**补音字也排在该码位全部普通字之后，优先于出简让全·字对字**（同日裁定"放在普通字的后面"；`00_维护/order_buyin.py` 维持单字表次序，78 核验有专项检查）。'); open(p, 'w', encoding='utf-8').write(s)
