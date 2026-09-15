# -*- coding: utf-8 -*-
"""为历史批次（≤第二十一批）中已生效的反转操作补标 覆盖:true 与备注。
第二十二批（本日）不补标，由 replay 真实检查。只改本目录裁定 JSON。"""
import io, sys, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(H + '/裁定/*.json'))
batches = [(f, json.load(open(f, encoding='utf-8'))) for f in files]
active = sorted([(f, b) for f, b in batches if b.get('状态') == '生效'], key=lambda x: x[1]['序号'])
LAST_HIST = 27   # 第二十一批的序号
history = {}
marked = 0
for f, b in active:
    n, name = b['序号'], b['批次']
    changed = False
    for o in b['操作']:
        key = (o['字'], o['码'])
        prior = history.get(key)
        if prior and prior[1] != o['op'] and not o.get('覆盖') and n <= LAST_HIST:
            o['覆盖'] = True
            o['备注'] = '反转 %s 的“%s”；历史上已生效，2026-09-14 重放核验时补标' % (prior[0], prior[1])
            marked += 1
            changed = True
        history[key] = (name, o['op'])
    if changed:
        json.dump(b, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('补标 %-30s' % name)
print('共补标 %d 条历史反转' % marked)
