# -*- coding: utf-8 -*-
"""F 类裁定实装（2026-09-14）：
(1) 词码还原：互换手误、误读/错码、方言旧读、零散 → 改为单字表可推导的最近合法码；目标码已有同词则仅删旧条，
    目标码已有其他候选则追加在末尾（词序属词词阶段）。
(2) 单字补标准读音：只加全码（双拼(新读音)+原形码），不给简码；新全码位若已有候选，新增条目排最后（让位）。
鲸凉鹤 o 前缀特设（oj/og 等）不在此处，归 D。"""
import io, sys, os, json, hashlib, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/实装前备份', exist_ok=True)
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
F = {o['词'] + '|' + o['实际码']: o for o in json.load(open(B + '/85_普通词飞键还原/F_归因.json', encoding='utf-8'))}

# —— (1) 词码还原清单（词|旧码）——
RESTORE = {
 '互换手误': ['弟媳|diix', '回府|hvuf', '画完|hxjw', '城防|ighf', '蛏子|igiz', '进气|jbiq', '进站|jbjv', '金樽|jbyz', '较弱|jnor', '巨胯|juxk', '假钱|jxmq', '战舞|vjuw', '阴气|ybiq'],
 '误读/错码': ['豆豉|dzgu', '讹谬|hxmq', '分袂|ffjt', '分袂|ffqt', '粳稻|ggdc', '豇豆|ghdz', '梼杌|izwu', '几阕|jikv', '联袂|lmqt', '尨茸|lsrs', '妹摄|mwnp', '摄生|npug', '女娲|nvgo', '锁血|xqxp', '耸立|ujli', '塑料|uoln', '骰子|udzi', '摇曳|ycvg', '租赁|zupk', '泥淖|nivo', '细说|xiyt', '女菀|nvyy', '楪祈|yeqi'],
 '方言旧读': ['夯货|bfho', '不被|bupi', '泽被|zepi', '孖份|maff', '孖女|manv', '孖拖|mato', '孖生|maug', '蕃王|fjwh', '吐蕃|tufj', '霰弹|sjdj', '呷西|gaxi'],
 '零散': ['且鳅|qpww', '欻拉|ixla', '老挝|lcvx', '抢跑|igpc'],
}
plan = {}
for kind, keys in RESTORE.items():
    for k in keys:
        o = F[k]; plan[(o['词'], o['实际码'])] = (o['最近合法码'], kind)

# —— (2) 单字补读音：字 -> 新读音拼音 ——
ADD = {'阏': 'e', '虾': 'ha', '伧': 'chen', '剿': 'chao', '喏': 're', '暴': 'pu', '邪': 'ye', '姥': 'mu', '唬': 'xia', '侧': 'zhai'}

codes = collections.defaultdict(set); order = collections.defaultdict(list)
for line in open(B + '/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt', encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2 and p[1].isalpha(): codes[p[0]].add(p[1]); order[p[1]].append(p[0])
# 拼音 -> 小鹤双拼：用单读音字学习
import csv
readings = collections.defaultdict(set)
with open(B + '/03_字音频率审计/分读音字频_审计版.tsv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'): readings[r['汉字']].add(r['拼音'])
d59 = json.load(open(B + '/59_单字当量排行/单字当量排行.json', encoding='utf-8'))
py2sp = collections.defaultdict(collections.Counter)
for e in d59:
    if len(readings.get(e['字'], ())) == 1:
        for c in e['所有编码']:
            if len(c['码']) >= 4: py2sp[e['读音']][c['码'][:2]] += 1
py2sp = {k: v.most_common(1)[0][0] for k, v in py2sp.items()}
newfull = {}
for ch, py in ADD.items():
    assert py in py2sp, ('无法确定双拼', ch, py)
    shape = sorted({c[2:4] for c in codes[ch] if len(c) >= 4 and c not in TOL})
    assert len(shape) == 1, ('形码不唯一', ch, shape)
    nf = py2sp[py] + shape[0]
    assert nf not in codes[ch], ('已存在', ch, nf)
    newfull[ch] = (nf, py)
print('补读音全码：', '、'.join('%s=%s(%s)' % (ch, nf, py) for ch, (nf, py) in newfull.items()))

FILES = [('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt', 'utf-8-sig', 'plain'),
         ('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_码前格式.txt', 'utf-8-sig', 'code1st'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt', 'utf-8-sig', 'plain'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_码前格式.txt', 'utf-8-sig', 'code1st'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_手心格式.txt', 'utf-8-sig', 'shouxin'),
         ('62_无简词字词表导出/夜莺2.0无简词字词表_搜狗.txt', 'utf-16', 'sogou')]

def parse(l, f):
    if f == 'plain':
        p = l.split('\t'); return (p[1], p[0]) if len(p) >= 2 else (None, None)
    if f == 'code1st':
        p = l.split('\t'); return (p[0], p[1]) if len(p) >= 2 else (None, None)
    if f == 'shouxin':
        if '=' in l and ',' in l:
            c, r = l.split('=', 1); n, w = r.split(',', 1); return (c, w)
    if f == 'sogou':
        if '=' in l and ',' in l:
            le, w = l.split('=', 1); c, n = le.rsplit(',', 1); return (c, w)
    return (None, None)

def emit(c, w, i, f):
    return {'plain': w + '\t' + c, 'code1st': c + '\t' + w, 'shouxin': c + '=' + str(i) + ',' + w, 'sogou': c + ',' + str(i) + '=' + w}[f]

res = []; log = None
for rel, enc, fmt in FILES:
    src = B + '/' + rel
    shutil.copy2(src, H + '/实装前备份/' + rel.replace('/', '__'))
    txt = open(src, 'rb').read().decode(enc); nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl); tail = lines.pop() if lines and lines[-1] == '' else None
    blocks = collections.OrderedDict()
    for l in lines:
        c, w = parse(l, fmt)
        if c is not None: blocks.setdefault(c, []).append(w)
    moved = merged = 0; miss = []
    for (w, c), (x, kind) in plan.items():
        if c in blocks and w in blocks[c]:
            blocks[c].remove(w)
            if not blocks[c]: del blocks[c]
            if w in blocks.get(x, []): merged += 1
            else: blocks.setdefault(x, []).append(w); moved += 1
        else: miss.append(w + '|' + c)
    added = []
    for ch, (nf, py) in newfull.items():
        if ch in blocks.get(nf, []): continue
        blocks.setdefault(nf, []).append(ch); added.append((ch, nf, len(blocks[nf])))
    out = [emit(c, w, i + 1, fmt) for c in sorted(blocks) for i, w in enumerate(blocks[c])]
    data = nl.join(out + ([tail] if tail is not None else [])).encode(enc)
    open(src, 'wb').write(data)
    if log is None: log = {'迁码': moved, '合并': merged, '未命中': miss, '补读音': added}
    res.append({'文件': rel, '迁码': moved, '合并': merged, '未命中': len(miss), '补读音': len(added), '行数': '%d→%d' % (len(lines), len(out)), '新sha256': hashlib.sha256(data).hexdigest()})
    print('%-46s 迁%3d 合%3d 缺%2d 补%2d 行 %d→%d  %s' % (rel.split('/')[-1], moved, merged, len(miss), len(added), len(lines), len(out), res[-1]['新sha256'][:16]))
print('\n补读音落位（字, 新全码, 候选位）：', '、'.join('%s %s 第%d位' % a for a in log['补读音']))
if log['未命中']: print('未命中（62 无此词属正常）：', log['未命中'])
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'),
           '词码还原': [{'词': w, '旧码': c, '新码': x, '类别': k} for (w, c), (x, k) in sorted(plan.items())],
           '补读音': {ch: {'新全码': nf, '读音': py} for ch, (nf, py) in newfull.items()}, '落位': log['补读音'], '文件': res},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
