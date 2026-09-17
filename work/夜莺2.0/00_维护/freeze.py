# -*- coding: utf-8 -*-
"""一次性：把 2.0 冻结成两张主表（2026-09-17 你裁定：默认单字表和字词表已经没有问题，以后维护只改这两张表；
生成兼容格式是独立的第二步，风险隔离）。主表已存在则拒绝覆盖。
  主表/夜莺2.0单字表.txt = 78 纯单字表（8105 字）+ 112 扩展字表（7391 字），字\\t码
  主表/夜莺2.0字词表.txt = 113 最终表，字词\\t码
格式：UTF-8 无 BOM、LF。同码的先后 = 候选次序。"""
import io, sys, os, json, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); M = H + '/主表'; os.makedirs(M, exist_ok=True)
rd = lambda p: [l.rstrip('\r\n') for l in open(p, encoding='utf-8-sig') if l.strip()]
src = {'夜莺2.0单字表.txt': [W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', W + '/112_扩展字继承/夜莺2.0扩展字表_普通格式.txt'], '夜莺2.0字词表.txt': [W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt']}
info = {'冻结时间': datetime.datetime.now().isoformat(timespec='seconds'), '说明': '冻结后生成链（83→113）封存不再运行；维护只经 apply_ledger.py 改这两张表。', '文件': {}}
for fn, ps in src.items():
    assert not os.path.exists(M + '/' + fn), '主表已存在，拒绝覆盖：' + fn
    rows = [l for p in ps for l in rd(p)]; data = ('\n'.join(rows) + '\n').encode('utf-8'); open(M + '/' + fn, 'wb').write(data)
    info['文件'][fn] = {'条目': len(rows), 'sha256': hashlib.sha256(data).hexdigest(), '来源': [p[len(W) + 1:] for p in ps]}; print(fn, len(rows))
json.dump(info, open(M + '/冻结说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
