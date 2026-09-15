# -*- coding: utf-8 -*-
"""三字词三码表（第 4 步·三字）。裁定（2026-09-15，路 A）：
候选池 = 鲸凉鹤三字简词（作者筛过）；码 = 我们的逐字首码（每个字优先取与鲸凉鹤原码该位一致的读音，否则取字典序最小）；
人工优先：三字词人工裁定（本目录，2026-09-15 用户授权代裁定）/ 三选保留配置 / 一简词转声母配置 / 码位人工指定 中的三码词；
每个三简位按手册 4.2 封顶：有单字最多 2 词、无单字最多 3 词；同码位按鲸凉鹤原序，且原本就在该码的词在前、从鲸凉鹤无理一简块并入的词（原码 ≠ 我们的码）在后（用户裁定 2026-09-15）。
含 8105 外字者无法取码，记录不收。产物为简词层，尚未入表。"""
import io, sys, os, json, collections, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
hits = {}
for line in open(B + '/08_词库与词频重建/综合词表_审计候选.jsonl', encoding='utf-8'):
    try: d = json.loads(line)
    except Exception: continue
    w = d.get('词')
    if w and len(w) == 3 and w not in hits: hits[w] = int(sum((d.get('各源原始词频') or {}).values()))
chars = collections.defaultdict(set); c3 = collections.defaultdict(list)
for line in open(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) < 2: continue
    chars[p[0]].add(p[1])
    if len(p[1]) == 3: c3[p[1]].append(p[0])
A = collections.defaultdict(set)
for w, cs in chars.items():
    for c in cs:
        if len(c) >= 4 and c not in TOL: A[w].add(c[0])
jlh = collections.OrderedDict()
for line in open(B + '/64_加入鲸凉鹤简词/弃用_含简词旧表/夜莺2.0含简词字词表_普通格式.txt', encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and len(p[0]) == 3 and 2 <= len(p[1]) <= 3 and p[1].isalpha(): jlh.setdefault(p[0], p[1])   # 含挂在鲸凉鹤无理一简上的二码三字词（的时候 do 等）
J = lambda f: json.load(open(B + '/64_加入鲸凉鹤简词/' + f, encoding='utf-8-sig'))
pri = collections.defaultdict(list); why = {}
def add(code, w, src):
    if len(code) == 3 and len(w) == 3 and w not in pri[code]: pri[code].append(w); why[(code, w)] = src
for code, ws in json.load(open(H + '/三字词人工裁定.json', encoding='utf-8')).items():   # 2026-09-15 代裁定，最高优先
    if code != '说明':
        for w in ws: add(code, w, '三字词人工裁定')
for code, ws in J('三选保留配置.json')['指定词保留'].items():
    for w in ws: add(code, w, '三选保留配置')
for w, codes in J('一简词转声母配置.json').items():
    for code in codes: add(code, w, '一简词转声母配置')
for code, ws in J('码位人工指定.json').items():
    for w in ws: add(code, w, '码位人工指定')

def code_of(w, orig):   # 逐字取码：鲸凉鹤原码该位字母在我们可选里就用它（多音字以作者选定读音为准），否则取字典序最小（2026-09-15 修，起因 重要性 vax→误成 iyx）
    if not all(ch in A for ch in w): return None
    return ''.join(o if o in A[ch] else sorted(A[ch])[0] for ch, o in zip(w, orig.ljust(3, '?')))

order0 = {w: i for i, w in enumerate(jlh)}
cand = collections.defaultdict(list); skipped = []
for w, orig in jlh.items():
    c = code_of(w, orig)
    if c is None: skipped.append(w); continue
    cand[c].append(w)
for k in cand: cand[k].sort(key=lambda w: (0 if jlh[w] == k else 1, order0[w]))   # 原码==本码者在前，并入者在后
rows = []; src = collections.Counter(); over = 0
for code in sorted(set(cand) | set(pri)):
    cap = 2 if c3.get(code) else 3
    lst = []
    for w in pri.get(code, []):
        if len(lst) < cap: lst.append((w, why[(code, w)])); src['人工'] += 1
    for w in cand.get(code, []):
        if len(lst) >= cap: over += 1; continue
        if w not in [x for x, _ in lst]:
            lst.append((w, '鲸凉鹤原序')); src['鲸凉鹤原序'] += 1
    for i, (w, s) in enumerate(lst): rows.append((code, i + 1, w, s))
out = '\r\n'.join('%s\t%s' % (w, code) for code, i, w, s in rows) + '\r\n'
open(H + '/夜莺2.0三字词三码表_普通格式.txt', 'wb').write(out.encode('utf-8-sig'))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '候选池': len(jlh), '含8105外字未收': skipped, '超出4.2上限未收': over,
           '条数': len(rows), '码位': len({c for c, *_ in rows}), '来源统计': dict(src),
           '明细': [{'码': c, '位': i, '词': w, '来由': s} for c, i, w, s in rows],
           'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()},
          open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('三字词三码 %d 条，占三简位 %d；来源 %s；超出上限未收 %d；含 8105 外字未收 %d' % (len(rows), len({c for c, *_ in rows}), dict(src), over, len(skipped)))
