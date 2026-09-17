# -*- coding: utf-8 -*-
"""单字表次序规则：登记在 83/补音表.json 的补音字，在所登记的全码位上排到普通字之后（裁定 2026-09-17）。幂等；有改动才写文件。"""
import io, sys, os, json, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = W + '/78_纯单字表核验/'
reg = json.load(open(W + '/83_单字表重放/补音表.json', encoding='utf-8'))['条目']
rows = [l.rstrip('\r\n').split('\t') for l in open(D + '夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig') if l.strip()]; moved = []
for code, cs in reg.items():
    idx = [k for k, (_, c) in enumerate(rows) if c == code]; grp = [rows[k] for k in idx]; new = sorted(grp, key=lambda r: r[0] in cs)
    if new != grp:
        moved.append(code)
        for k, r in zip(idx, new): rows[k] = r
if moved:
    out = {}
    for fn, fmt in (('夜莺2.0纯单字表_普通格式.txt', '%s\t%s'), ('夜莺2.0纯单字表_码前格式.txt', None)):
        data = ('\r\n'.join(('%s\t%s' % (t, c)) if fmt else ('%s\t%s' % (c, t)) for t, c in rows) + '\r\n').encode('utf-8-sig'); open(D + fn, 'wb').write(data); out[fn] = hashlib.sha256(data).hexdigest()
    e = json.load(open(D + '导出说明.json', encoding='utf-8-sig')); e['时间'] = datetime.datetime.now().isoformat(timespec='seconds')
    e['文件'] = [{'文件': fn, '条目': len(rows), 'sha256': h} for fn, h in out.items()]; json.dump(e, open(D + '导出说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('补音字后移 %d 个码位 %s' % (len(moved), moved))
