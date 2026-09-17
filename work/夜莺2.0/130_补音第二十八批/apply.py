# -*- coding: utf-8 -*-
"""补音（2026-09-17）。你的裁定："俗读和少数读音全收"；"如果简码是空着的，可以加简码"。
来源：129_缺音普查/缺音候选.tsv 全部 74 条（72 字）→ 各补全码，同码排最后；其中三简位完全空着的 13 条另给三简。
三简位上只有三字词的 8 条（嗯忒陂聒饨解屯镐）不给三简。蕃 fān 原判不补，本次改判收入。可重复运行。"""
import io, sys, os, json, shutil, hashlib, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); BK = H + '/实装前备份'
def backup(p):
    q = BK + '/' + os.path.relpath(p, B); os.makedirs(os.path.dirname(q), exist_ok=True)
    if not os.path.exists(q): shutil.copy2(p, q)
rj = lambda p: json.load(open(p, encoding='utf-8-sig'))
lst = H + '/补音清单.json'
if os.path.exists(lst): items = rj(lst)
else:
    tab = collections.defaultdict(list)
    for l in open(B + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
        t, c = l.rstrip('\r\n').split('\t'); tab[c].append(t)
    items = []
    for l in list(open(B + '/129_缺音普查/缺音候选.tsv', encoding='utf-8'))[1:]:
        f = l.rstrip('\n').split('\t')
        for code in f[4].split(' / '):
            items.append({'字': f[0], '全码': code, '三简': code[:3] if not tab.get(code[:3]) else None, '例词': f[5]})
    short = [i['三简'] for i in items if i['三简']]; assert len(short) == len(set(short)), '两个字抢同一个空三简'
    json.dump(items, open(lst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ADD = []
for i in items:
    if i['三简']: ADD.append((i['字'], i['三简'], '补读音并给三简（三简位原为空）；例：' + i['例词']))
    ADD.append((i['字'], i['全码'], '补读音全码，同码排最后；例：' + i['例词']))
batch = B + '/83_单字表重放/裁定/34_第二十八批_补音.json'
json.dump({'序号': 34, '批次': '第二十八批_补音', '状态': '生效', '日期': '2026-09-17', '说明': '缺音普查 74 条全收（含俗读与少数读音）；三简位完全空着的 13 条给三简。',
           '操作': [{'op': '加', '字': t, '码': c, '备注': n} for t, c, n in ADD]}, open(batch, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
p78 = B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'; backup(p78)
rows = [l.rstrip('\r\n').split('\t') for l in open(p78, encoding='utf-8-sig') if l.strip()]
for t, c, _ in ADD:
    if [t, c] in rows: continue
    j = next((k for k, (_, x) in enumerate(rows) if x > c), len(rows)); rows.insert(j, [t, c])
# 出简让全·字对字（规则五）：同一全码里，自己有"该全码前缀简码"的字排到没有的字后面（稳定排序，只动本批涉及的码位）
shorts = collections.defaultdict(set)
for t, c in rows:
    if len(c) < 4: shorts[t].add(c)
for code in {c for _, c, _ in ADD if len(c) == 4}:
    idx = [k for k, (_, x) in enumerate(rows) if x == code]; grp = [rows[k] for k in idx]
    grp.sort(key=lambda r: any(code.startswith(s) for s in shorts[r[0]]))
    for k, r in zip(idx, grp): rows[k] = r
assert [c for _, c in rows] == sorted(c for _, c in rows)
out = '\r\n'.join('%s\t%s' % (t, c) for t, c in rows) + '\r\n'; open(p78, 'wb').write(out.encode('utf-8-sig'))
p78r = B + '/78_纯单字表核验/夜莺2.0纯单字表_码前格式.txt'; backup(p78r)
outr = '\r\n'.join('%s\t%s' % (c, t) for t, c in rows) + '\r\n'; open(p78r, 'wb').write(outr.encode('utf-8-sig'))
pe = B + '/78_纯单字表核验/导出说明.json'; exp = rj(pe); backup(pe); exp['时间'] = datetime.datetime.now().isoformat(timespec='seconds'); exp['条目'] = len(rows)
if '第二十八批' not in exp.get('来源', ''): exp['来源'] = exp.get('来源', '') + '；2026-09-17 第二十八批 补音'
exp['文件'] = [{'文件': '夜莺2.0纯单字表_普通格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()},
              {'文件': '夜莺2.0纯单字表_码前格式.txt', '条目': len(rows), 'sha256': hashlib.sha256(outr.encode('utf-8-sig')).hexdigest()}]
json.dump(exp, open(pe, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('补音 %d 条读音（三简 %d），单字表现 %d 条' % (len(items), sum(1 for i in items if i['三简']), len(rows)))
