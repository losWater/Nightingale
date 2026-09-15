# -*- coding: utf-8 -*-
"""2026-09-16 你裁定（彩蛋，仿小鹤系 eh=鹤）：
① by = 莺（特殊简码，二简位；by 原无字，简词 表演/不要/必要 按 4.2 有字最多 2 词由 102 重算）；
② yeby = 夜莺（词的无理码）；yeyk 人工指定改回 野营 首选、夜莺 次选；
③ ykmg 萤 首选、莺 次选（莺有简码后按规则四让位，同时是你的明示裁定）。
落点：83 裁定第二十五批 + 无理码表/词无理码表；78 单字表（加行 + ykmg 换序）；78 audit 的特殊简码表；64 人工指定；109 词表脚本注入词无理码。
之后重跑：83 replay → 78 audit → 109 → 97 → 102 → 104 → 110 → 112 → 113 → 106 → 部署 → 114 → 117 → 118。"""
import io, sys, os, json, shutil, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); BK = H + '/实装前备份'
def backup(p):
    q = BK + '/' + os.path.relpath(p, B); os.makedirs(os.path.dirname(q), exist_ok=True)
    if not os.path.exists(q): shutil.copy2(p, q)
def rj(p): return json.load(open(p, encoding='utf-8-sig'))
def wj(p, d): backup(p); json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# ① 83 裁定批次
batch = B + '/83_单字表重放/裁定/31_第二十五批_by给莺.json'
assert not os.path.exists(batch)
json.dump({'序号': 31, '批次': '第二十五批_by给莺', '状态': '生效', '日期': '2026-09-16',
           '说明': '彩蛋：仿小鹤系 eh=鹤，by 给 莺（夜莺）。by 二简位原无字。同时 ykmg 改为 萤 首选、莺 次选（莺有简码后按规则四让位，亦为用户明示裁定；单字表内以行序表达）。词层：yeby=夜莺 登记为词无理码，yeyk 人工指定改回 野营 首选。',
           '操作': [{'op': '加', '字': '莺', '码': 'by', '备注': '特殊简码，登记于 无理码表.json 特殊简码'}]},
          open(batch, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
irr = rj(B + '/83_单字表重放/无理码表.json'); irr['特殊简码']['by'] = '莺'
irr['来源']['特殊简码'] = '57 历史盘点：小鹤系传统 eh=鹤，用户裁决；2026-09-16 第二十五批 by=莺（夜莺彩蛋）'
wj(B + '/83_单字表重放/无理码表.json', irr)
wirr = rj(B + '/83_单字表重放/词无理码表.json'); wirr['条目']['yeby'] = '夜莺'
wirr['来源'] += '；2026-09-16 用户裁定 yeby=夜莺（彩蛋，yeyk 规则码仍在、野营首选）'; wirr['时间'] = datetime.datetime.now().isoformat(timespec='seconds')
wj(B + '/83_单字表重放/词无理码表.json', wirr)
# ② 78 单字表：加 莺 by（按码序插入）；ykmg 萤 前、莺 后
p78 = B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'; backup(p78)
rows = [l.rstrip('\r\n').split('\t') for l in open(p78, encoding='utf-8-sig') if l.strip()]
assert ['莺', 'by'] not in rows
j = next(i for i, (t, c) in enumerate(rows) if c > 'by'); rows.insert(j, ['莺', 'by'])
yk = [i for i, (t, c) in enumerate(rows) if c == 'ykmg']; assert [rows[i][0] for i in yk] == ['莺', '萤'], [rows[i] for i in yk]
rows[yk[0]], rows[yk[1]] = rows[yk[1]], rows[yk[0]]
out = '\r\n'.join('%s\t%s' % (t, c) for t, c in rows) + '\r\n'; open(p78, 'wb').write(out.encode('utf-8-sig'))
p78r = B + '/78_纯单字表核验/夜莺2.0纯单字表_码前格式.txt'; backup(p78r)
outr = '\r\n'.join('%s\t%s' % (c, t) for t, c in rows) + '\r\n'; open(p78r, 'wb').write(outr.encode('utf-8-sig'))
exp = rj(B + '/78_纯单字表核验/导出说明.json'); exp['时间'] = datetime.datetime.now().isoformat(timespec='seconds'); exp['条目'] = len(rows)
exp['来源'] = '62 无简词表抽取单字；2026-09-16 第二十五批 by=莺、ykmg 萤/莺 换序（83 可重放）'
exp['文件'] = [{'文件': '夜莺2.0纯单字表_普通格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()},
              {'文件': '夜莺2.0纯单字表_码前格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(outr.encode('utf-8-sig')).hexdigest()}]
wj(B + '/78_纯单字表核验/导出说明.json', exp)
# 78 audit 的特殊简码表
pa = B + '/78_纯单字表核验/audit.py'; backup(pa); s = open(pa, encoding='utf-8').read()
assert "SPEC={'eh':'鹤'}" in s; s = s.replace("SPEC={'eh':'鹤'}", "SPEC={'eh':'鹤','by':'莺'}"); open(pa, 'w', encoding='utf-8').write(s)
# ③ 人工指定 yeyk
pm = B + '/64_加入鲸凉鹤简词/码位人工指定.json'; man = rj(pm); assert man['yeyk'] == ['夜莺', '野营']; man['yeyk'] = ['野营', '夜莺']; wj(pm, man)
# ④ 109 注入词无理码
p109 = B + '/109_普通词共识筛选/build.py'; backup(p109); s = open(p109, encoding='utf-8').read()
anchor = "out = '\\r\\n'.join('%s\\t%s' % (w, c) for c in sorted(blocks) for w in blocks[c]) + '\\r\\n'\n"
assert s.count(anchor) == 1 and '词无理码表' not in s
inject = """# 2026-09-16 词无理码表（83）里的特设入口若不在表中则补入码位末尾（如 yeby=夜莺）
for _c, _w in json.load(open(B + '/83_单字表重放/词无理码表.json', encoding='utf-8-sig'))['条目'].items():
    if _w not in blocks.get(_c, []): blocks.setdefault(_c, []).append(_w)
"""
open(p109, 'w', encoding='utf-8').write(s.replace(anchor, inject + anchor))
print('裁定已落：83 第二十五批、无理码表 by=莺、词无理码表 yeby=夜莺、78 加行+ykmg 换序（%d 条）、audit SPEC、人工指定 yeyk=野营/夜莺、109 注入词无理码' % len(rows))
