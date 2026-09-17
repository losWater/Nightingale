# -*- coding: utf-8 -*-
"""实战反馈第一批（2026-09-17 你逐条确认）。来源：releases/v2.0/用户实战反馈.txt 10 条 + 虎娘 user.tcu 4 条。
单字（83 第二十六批）：
  简码换位：待 拿二简 dd、带 只留三简 ddm；喂 拿三简 wwt、味 退到全码 wwtl。
  容错码：金 jbx、承 igpf、载 zde、哉 zdt、栽 zdw、兜 dzp（豆让出三简 dzp，只留全码 dzpp）。
词：人工指定 yruf 原神、uivj 实战、jiyi 记忆、hdzd 还在、jihv 机会、uiji 实际 为首选；三字词 uql 说起来 首选；补词 没来 mwld。
之后重跑：83 replay → 78 audit → 109 → 97 → 102 → 103 → 104 → 110 → 112 → 113 → 106 → 部署 → 114/115 → 123 → 125 → 117 → 118。"""
import io, sys, os, json, shutil, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); BK = H + '/实装前备份'
def backup(p):
    q = BK + '/' + os.path.relpath(p, B); os.makedirs(os.path.dirname(q), exist_ok=True)
    if not os.path.exists(q): shutil.copy2(p, q)
rj = lambda p: json.load(open(p, encoding='utf-8-sig'))
def wj(p, d): backup(p); json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
REMOVE = [('带', 'dd'), ('味', 'wwt'), ('豆', 'dzp')]
ADD = [('待', 'dd'), ('喂', 'wwt')]
TOL = [('金', 'jbx'), ('承', 'igpf'), ('载', 'zde'), ('哉', 'zdt'), ('栽', 'zdw'), ('兜', 'dzp')]
# 1 裁定批次
batch = B + '/83_单字表重放/裁定/32_第二十六批_实战反馈第一批.json'; assert not os.path.exists(batch)
ops = [{'op': '删', '字': t, '码': c, '备注': '简码换位/让出'} for t, c in REMOVE] + [{'op': '加', '字': t, '码': c, '备注': '简码换位'} for t, c in ADD] + [{'op': '加', '字': t, '码': c, '备注': '容错码，登记 无理码表.json'} for t, c in TOL]
json.dump({'序号': 32, '批次': '第二十六批_实战反馈第一批', '状态': '生效', '日期': '2026-09-17',
           '说明': '你实打后逐条裁定：待 dd（带留 ddm）；喂 wwt（味 退 wwtl，喂多单用、wwtl 手感尚可）；容错 金 jbx、承 igpf、载 zde、哉 zdt、栽 zdw、兜 dzp（豆让出 dzp 只留 dzpp，你确认）。', '操作': ops},
          open(batch, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
irr = rj(B + '/83_单字表重放/无理码表.json')
for t, c in TOL: assert c not in irr['容错码']; irr['容错码'][c] = t
irr['来源']['容错码'] += '；2026-09-17 第二十六批 实战反馈：jbx 金、igpf 承、zde 载、zdt 哉、zdw 栽、dzp 兜'
wj(B + '/83_单字表重放/无理码表.json', irr)
# 2 78 单字表
p78 = B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'; backup(p78)
rows = [l.rstrip('\r\n').split('\t') for l in open(p78, encoding='utf-8-sig') if l.strip()]
for t, c in REMOVE: rows.remove([t, c])
for t, c in ADD + TOL:
    assert [t, c] not in rows
    j = next((i for i, (_, k) in enumerate(rows) if k > c), len(rows)); rows.insert(j, [t, c])
assert [c for _, c in rows] == sorted(c for _, c in rows)
out = '\r\n'.join('%s\t%s' % (t, c) for t, c in rows) + '\r\n'; open(p78, 'wb').write(out.encode('utf-8-sig'))
p78r = B + '/78_纯单字表核验/夜莺2.0纯单字表_码前格式.txt'; backup(p78r)
outr = '\r\n'.join('%s\t%s' % (c, t) for t, c in rows) + '\r\n'; open(p78r, 'wb').write(outr.encode('utf-8-sig'))
exp = rj(B + '/78_纯单字表核验/导出说明.json'); exp['时间'] = datetime.datetime.now().isoformat(timespec='seconds'); exp['条目'] = len(rows)
exp['来源'] = exp.get('来源', '') + '；2026-09-17 第二十六批 实战反馈第一批'
exp['文件'] = [{'文件': '夜莺2.0纯单字表_普通格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()},
              {'文件': '夜莺2.0纯单字表_码前格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(outr.encode('utf-8-sig')).hexdigest()}]
wj(B + '/78_纯单字表核验/导出说明.json', exp)
pa = B + '/78_纯单字表核验/audit.py'; backup(pa); s = open(pa, encoding='utf-8').read()
old = "'yvl':'欲','yvz':'予','yvc':'郁','yvo':'羽'}"; assert s.count(old) == 1
s = s.replace(old, "'yvl':'欲','yvz':'予','yvc':'郁','yvo':'羽',\n     'jbx':'金','igpf':'承','zde':'载','zdt':'哉','zdw':'栽','dzp':'兜'}   # 2026-09-17 第二十六批"); open(pa, 'w', encoding='utf-8').write(s)
# 3 人工指定
pm = B + '/64_加入鲸凉鹤简词/码位人工指定.json'; man = rj(pm)
for code, order in {'yruf': ['原神', '元神'], 'uivj': ['实战', '施展'], 'jiyi': ['记忆', '几亿', '技艺'], 'hdzd': ['还在', '昏倒在地'], 'jihv': ['机会', '几回', '忌讳', '集会'], 'uiji': ['实际', '十几', '时机', '世纪']}.items():
    assert code not in man, code; man[code] = order
wj(pm, man)
# 4 三字词人工裁定
p3 = B + '/103_三字词三码/三字词人工裁定.json'; d3 = rj(p3); assert 'uql' not in d3; d3['uql'] = ['说起来']
d3['说明'] += ' 2026-09-17 实战反馈：uql 说起来 首选。'; wj(p3, d3)
# 5 人工补词（109 注入）
pb = B + '/109_普通词共识筛选/人工补词.json'
add = rj(pb) if os.path.exists(pb) else {'说明': '用户实打后要求补入的规则词（码可由单字表推导）；109/build.py 注入到码位末尾，由人工指定决定是否提前。', '条目': {}}
add['条目'].setdefault('mwld', [])
if '没来' not in add['条目']['mwld']: add['条目']['mwld'].append('没来')
json.dump(add, open(pb, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
p109 = B + '/109_普通词共识筛选/build.py'; backup(p109); s = open(p109, encoding='utf-8').read()
if '人工补词.json' not in s:
    anchor = "# 2026-09-16 词无理码表（83）里的特设入口若不在表中则补入码位末尾（如 yeby=夜莺）\n"; assert s.count(anchor) == 1
    s = s.replace(anchor, "# 2026-09-17 人工补词（用户实打反馈，规则码）：不在表中则补入码位末尾\nfor _c, _ws in json.load(open(H + '/人工补词.json', encoding='utf-8'))['条目'].items():\n    for _w in _ws:\n        if _w not in blocks.get(_c, []): blocks.setdefault(_c, []).append(_w)\n" + anchor)
    open(p109, 'w', encoding='utf-8').write(s)
print('第二十六批已落：单字表 %d 条；人工指定 +6（现 %d 条）；三字词裁定 uql；补词 没来 mwld；容错码 +6（现 %d 个）' % (len(rows), len(man), len(irr['容错码'])))
