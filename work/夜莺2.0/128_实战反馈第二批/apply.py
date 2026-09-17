# -*- coding: utf-8 -*-
"""实战反馈第二批（2026-09-17）。可重复运行（已落的项跳过）。
单字（83 第二十七批）：裳 补读音 cháng → 全码 ihjs（照第二十三批先例：只给全码、不给简码、撞位排最后）。
词：补词 怨灵 yrlk，人工指定首选（原 圆领、沅陵 顺延）。
之后重跑：83 replay → 78 audit → 109 → 97 → 102 → 103 → 104 → 110 → 112 → 113 → 106 → 部署 → 114/115 → 123 → 125 → 117 → 118。"""
import io, sys, os, json, shutil, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); BK = H + '/实装前备份'
def backup(p):
    q = BK + '/' + os.path.relpath(p, B); os.makedirs(os.path.dirname(q), exist_ok=True)
    if not os.path.exists(q): shutil.copy2(p, q)
rj = lambda p: json.load(open(p, encoding='utf-8-sig'))
def wj(p, d): backup(p); json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ADD = [('裳', 'ihjs', '补标准读音 chang（霓裳、云裳）；仅全码不给简码；撞位排最后')]
WORDS = {'yrlk': ['怨灵']}                       # 补词
ORDER = {'yrlk': ['怨灵', '圆领', '沅陵']}       # 人工指定次序
# 1 裁定批次
batch = B + '/83_单字表重放/裁定/33_第二十七批_实战反馈第二批.json'
json.dump({'序号': 33, '批次': '第二十七批_实战反馈第二批', '状态': '生效', '日期': '2026-09-17', '说明': '你实打发现缺音：裳 cháng。照第二十三批先例只加全码。',
           '操作': [{'op': '加', '字': t, '码': c, '备注': n} for t, c, n in ADD]}, open(batch, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# 2 78 单字表
p78 = B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'; backup(p78)
rows = [l.rstrip('\r\n').split('\t') for l in open(p78, encoding='utf-8-sig') if l.strip()]
for t, c, _ in ADD:
    if [t, c] in rows: continue
    j = next((i for i, (_, k) in enumerate(rows) if k > c), len(rows)); rows.insert(j, [t, c])   # 同码排最后
assert [c for _, c in rows] == sorted(c for _, c in rows)
out = '\r\n'.join('%s\t%s' % (t, c) for t, c in rows) + '\r\n'; open(p78, 'wb').write(out.encode('utf-8-sig'))
p78r = B + '/78_纯单字表核验/夜莺2.0纯单字表_码前格式.txt'; backup(p78r)
outr = '\r\n'.join('%s\t%s' % (c, t) for t, c in rows) + '\r\n'; open(p78r, 'wb').write(outr.encode('utf-8-sig'))
exp = rj(B + '/78_纯单字表核验/导出说明.json'); exp['时间'] = datetime.datetime.now().isoformat(timespec='seconds'); exp['条目'] = len(rows)
if '第二十七批' not in exp.get('来源', ''): exp['来源'] = exp.get('来源', '') + '；2026-09-17 第二十七批 实战反馈第二批'
exp['文件'] = [{'文件': '夜莺2.0纯单字表_普通格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()},
              {'文件': '夜莺2.0纯单字表_码前格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(outr.encode('utf-8-sig')).hexdigest()}]
wj(B + '/78_纯单字表核验/导出说明.json', exp)
# 3 补词 + 人工指定
pb = B + '/109_普通词共识筛选/人工补词.json'; add = rj(pb); backup(pb)
for c, ws in WORDS.items():
    for w in ws:
        if w not in add['条目'].setdefault(c, []): add['条目'][c].append(w)
json.dump(add, open(pb, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
pm = B + '/64_加入鲸凉鹤简词/码位人工指定.json'; man = rj(pm)
for c, o in ORDER.items(): assert man.get(c) in (None, o), c; man[c] = o
wj(pm, man)
print('第二批已落：单字表 %d 条；补词 %s；人工指定现 %d 条' % (len(rows), WORDS, len(man)))
