# -*- coding: utf-8 -*-
"""二字简词表（第 4 步·二字）。裁定（2026-09-15）：
取码 = 首字首码 + 次字首码；来源 = 91 普通词表中的二字词，08 有记录；
优先序：二简人工裁定（102/二简人工裁定.json，2026-09-16）→ 三选保留配置 → 一简词转声母配置 → 简词人工裁定 → 码位人工指定（二码），之后按 08 排序指数降序；
每个二简位按手册 4.2 封顶：有单字则最多 2 词，无单字最多 3 词；词频下限 排序指数 ≥ 0.35（人工项不受下限约束）。
产物只是简词层，尚未入表（第 5 步）。"""
import io, sys, os, json, collections, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
FLOOR = 0.35
idx = {}; hits = {}; rk = {}
for line in open(B + '/08_词库与词频重建/综合词表_审计候选.jsonl', encoding='utf-8'):
    try: d = json.loads(line)
    except Exception: continue
    w = d.get('词')
    if w and w not in idx: idx[w] = d.get('排序指数', 0); hits[w] = sum((d.get('各源原始词频') or {}).values()); rk[w] = d.get('综合排名') or 10**9
c2 = collections.defaultdict(list)
for line in open(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and len(p[1]) == 2: c2[p[1]].append(p[0])
J = lambda f: json.load(open(B + '/64_加入鲸凉鹤简词/' + f, encoding='utf-8-sig'))
keep3 = J('三选保留配置.json'); conv = J('一简词转声母配置.json'); manual = J('简词人工裁定.json'); man = J('码位人工指定.json')
pri = collections.defaultdict(list); why = {}
def add(code, w, src):
    if len(code) == 2 and len(w) == 2 and w not in pri[code]:
        pri[code].append(w); why[(code, w)] = src
j2 = json.load(open(H + '/二简人工裁定.json', encoding='utf-8-sig'))   # 2026-09-16 三家投票裁定，最高优先
for code, ws in j2.items():
    if code != '说明':
        for w in ws: add(code, w, '二简人工裁定')
for code, ws in keep3['指定词保留'].items():
    for w in ws: add(code, w, '三选保留配置')
for w, codes in conv.items():
    for code in codes: add(code, w, '一简词转声母配置')
for code, ws in manual.items():
    for w in ws: add(code, w, '简词人工裁定')
for code, ws in man.items():
    for w in ws: add(code, w, '码位人工指定')
words = {}
for line in open(B + '/109_普通词共识筛选/夜莺2.0普通词表_普通格式.txt', encoding='utf-8-sig'):   # 2026-09-15 换源
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and len(p[0]) == 2 and len(p[1]) == 4 and p[1].isalpha(): words.setdefault(p[0], p[1][0] + p[1][2])
cand = collections.defaultdict(list)
for w, code in words.items():
    if hits.get(w, 0) > 0: cand[code].append(w)
for k in cand: cand[k] = sorted(set(cand[k]), key=lambda w: -idx.get(w, 0))
rows = []; src = collections.Counter(); notes = []
for code in sorted(set(cand) | set(pri)):
    cap = 2 if c2.get(code) else 3
    lst = []
    for w in pri.get(code, []):
        if len(lst) < cap: lst.append((w, why[(code, w)])); src['人工'] += 1
        else: notes.append('%s：人工项 %s 超出 4.2 上限未收' % (code, w))
    for w in cand.get(code, []):
        if len(lst) >= cap: break
        if w not in [x for x, _ in lst] and idx.get(w, 0) >= FLOOR: lst.append((w, '08词频 %.2f' % idx.get(w, 0))); src['词频'] += 1
    for i, (w, s) in enumerate(lst): rows.append((code, i + 1, w, s))
out = '\r\n'.join('%s\t%s' % (w, code) for code, i, w, s in rows) + '\r\n'
open(H + '/夜莺2.0二字简词表_普通格式.txt', 'wb').write(out.encode('utf-8-sig'))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '下限': FLOOR, '条数': len(rows), '码位': len({c for c, *_ in rows}),
           '来源统计': dict(src), '未收的人工项': notes,
           '明细': [{'码': c, '位': i, '词': w, '来由': s} for c, i, w, s in rows],
           'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()},
          open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('二字简词 %d 条，占用二简位 %d 个；来源：%s' % (len(rows), len({c for c, *_ in rows}), dict(src)))
if notes: print('人工项超出上限未收 %d 条：%s' % (len(notes), '；'.join(notes[:10])))
