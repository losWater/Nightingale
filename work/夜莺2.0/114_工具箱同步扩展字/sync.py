# -*- coding: utf-8 -*-
"""工具箱同步扩展字（2026-09-16 你裁定"全都同步"）：把 112 的 7391 个扩展字（拆分 + 113 最终表里的字码）加进工具箱的
拆分查询、部件反查、完整拆分表三个视图（源页 58、离线包同名页、单文件、啾啾），重打 zip。
扩展字排名为空（页面显示 —，部件反查按字频排在 8105 之后）；8105 字的拆分/根/排名/字码/候选位逐条不变；
练习/字根图/字根表视图逐字节不动。改前备份于本目录 实装前备份/。"""
import io, sys, os, re, json, shutil, hashlib, zipfile, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); BK = H + '/实装前备份'
U = B + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); assert m, name
    obj, n = json.JSONDecoder().raw_decode(s[m.end():]); return obj, m.end(), m.end() + n
def put(s, name, obj):
    _, a, b = get(s, name); return s[:a] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + s[b:]
def backup(p):
    q = BK + '/' + os.path.relpath(p, B); os.makedirs(os.path.dirname(q), exist_ok=True)
    if not os.path.exists(q): shutil.copy2(p, q)
def write(p, s, enc='utf-8'):
    backup(p); open(p, 'w', encoding=enc, newline='').write(s)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
# 扩展字拆分（112）
ext = collections.OrderedDict()
for l in open(B + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt', encoding='utf-8-sig').read().splitlines()[1:]:
    c, sp, f, e = l.split('\t'); ext[c] = sp
assert len(ext) == 7391, len(ext)
# 字码：113 最终表里的单字行（8105 在前、扩展字在后，词不计入候选位——与 105 的口径一致）
groups = collections.OrderedDict(); codes_of = collections.defaultdict(list)
for line in open(B + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8-sig'):
    p = line.rstrip('\r\n').split('\t')
    if len(p) >= 2 and len(p[0]) == 1: groups.setdefault(p[1], []).append(p[0]); codes_of[p[0]].append(p[1])
g78 = collections.OrderedDict()
for line in open(B + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8-sig'):
    p = line.rstrip('\r\n').split('\t')
    if len(p) >= 2: g78.setdefault(p[1], []).append(p[0])
for k, chars in g78.items(): assert groups[k][:len(chars)] == chars, k   # 8105 字在每个码位的先后不变
assert set(codes_of) == set(g78 and {c for cs in g78.values() for c in cs}) | set(ext), '113 单字集合 = 8105 + 扩展字'
f58 = B + '/58_拆分查询/夜莺2.0拆分查询.html'; s58 = open(f58, encoding='utf-8-sig').read()
ROOTS, _, _ = get(s58, 'ROOTS'); rmap = {r['根']: r for r in ROOTS}
CHANGED = []   # 可重复运行：已有的字只更新字码（如 2026-09-16 莺 by、ykmg 换序）
def sync_D(D):
    assert len(D) in (8105, 8105 + 7391), len(D)
    old = {c: json.dumps(r, ensure_ascii=False, sort_keys=True) for c, r in D.items()}
    for c, sp in ext.items():
        if c in D: continue
        parts = sp.split(' ＋ '); D[c] = {'根': [dict(rmap[x]) for x in parts], '新拆': sp, '排名': None, '编码': []}
    for r in D.values(): r['编码'] = []
    for k, chars in groups.items():
        for i, c in enumerate(chars, 1): D[c]['编码'].append({'码': k, '位': i, '同码': chars})
    for r in D.values(): r['编码'].sort(key=lambda e: (len(e['码']), e['码']))
    for c in old:   # 已有字：拆分/根/排名逐条不变；字码/候选位若有变化列出（来自 78/113 的新裁定）
        a, b = json.loads(old[c]), D[c]
        assert (a['根'], a['新拆'], a['排名']) == (b['根'], b['新拆'], b['排名']), c
        if [(e['码'], e['位']) for e in a['编码']] != [(e['码'], e['位']) for e in b['编码']]:
            CHANGED.append((c, [(e['码'], e['位']) for e in a['编码']], [(e['码'], e['位']) for e in b['编码']]))
    return {(c, e['码']) for c, r in D.items() for e in r['编码']}
D58, _, _ = get(s58, 'D'); new = sync_D(D58); write(f58, put(s58, 'D', D58))
main = U + '/夜莺2.0随身工具_单文件.html'; shell = open(main, encoding='utf-8-sig').read()
views, _, _ = get(shell, 'views'); frozen = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in views.items() if k not in ('query', 'components', 'text')}
for key, name in [('query', '拆分查询.html'), ('components', '部件反查.html')]:
    if views[key] != open(O + '/' + name, encoding='utf-8-sig').read(): print('提示：单文件与离线页 %s 此前不一致，以单文件为基准重算' % name)
    Dv, _, _ = get(views[key], 'D'); assert sync_D(Dv) == new
    views[key] = put(views[key], 'D', Dv); write(O + '/' + name, views[key])
# 完整拆分表：html 里的 rows + txt
rows, _, _ = get(views['text'], 'rows'); assert len(rows) in (8105, 8105 + 7391) and rows[0][0] == '㑇', len(rows)
if len(rows) == 8105: rows += [[c, sp, sp.split(' ＋ ')[0], sp.split(' ＋ ')[-1]] for c, sp in ext.items()]
views['text'] = put(views['text'], 'rows', rows); write(O + '/完整拆分表.html', views['text'])
tp = O + '/完整拆分表.txt'; t = open(tp, encoding='utf-8-sig').read(); assert t.count('\n') in (8106, 8106 + 7391) and t.startswith('汉字\t完整拆分\t首根\t末根'), t.count('\n')
nl = '\r\n' if '\r\n' in t else '\n'
if t.count('\n') == 8106: write(tp, t + ''.join('%s\t%s\t%s\t%s%s' % (r[0], r[1], r[2], r[3], nl) for r in rows[8105:]), 'utf-8-sig')
shell2 = put(shell, 'views', views); write(main, shell2); backup(U + '/夜莺啾啾工具箱.html'); shutil.copy2(main, U + '/夜莺啾啾工具箱.html')
# 使用说明补一行
up = O + '/使用说明.txt'; u = open(up, encoding='utf-8-sig').read()
line = '2026-09-16：拆分查询、部件反查、完整拆分表加入 7391 个扩展字（新华字典比 8105 多出的字，含繁体旧字形），共 15496 字；扩展字无字频排名，显示为 —。练习与字根表未变。'
if line not in u: write(up, u.rstrip('\r\n') + ('\r\n' if '\r\n' in u else '\n') + line + ('\r\n' if '\r\n' in u else '\n'), 'utf-8-sig')
# 复核：重读单文件
chk = open(main, encoding='utf-8-sig').read(); v2, _, _ = get(chk, 'views')
assert {k: hashlib.sha256(v.encode()).hexdigest() for k, v in v2.items() if k not in ('query', 'components', 'text')} == frozen
for key in ('query', 'components'):
    Dc, _, _ = get(v2[key], 'D'); assert len(Dc) == 8105 + 7391 and {(c, e['码']) for c, r in Dc.items() for e in r['编码']} == new
    gc = {}; [gc.setdefault(e['码'], e['同码']) for r in Dc.values() for e in r['编码']]; assert gc == dict(groups)
    for c in ('兙', '亪', '诶'): assert Dc[c]['新拆'] == ext[c] and [e['码'] for e in Dc[c]['编码']] == sorted(codes_of[c], key=lambda k: (len(k), k)), c
r2, _, _ = get(v2['text'], 'rows'); assert len(r2) == 8105 + 7391
for name in ('拆分查询.html', '部件反查.html', '完整拆分表.html'): assert open(O + '/' + name, encoding='utf-8-sig').read() == v2[{'拆分查询.html': 'query', '部件反查.html': 'components', '完整拆分表.html': 'text'}[name]]
n = len(re.findall(r'</script', chk, re.I)); assert n == 1, ('字面 </script 数', n)
zp = U + '/夜莺2.0离线工具包.zip'; backup(zp)
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(O)): z.write(O + '/' + fn, '夜莺2.0离线工具包/' + fn)
files = {fn: sha(O + '/' + fn) for fn in sorted(os.listdir(O))}
backup(U + '/文件核验.json'); json.dump(files, open(U + '/文件核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
bj = json.load(open(U + '/构建核验.json', encoding='utf-8')); backup(U + '/构建核验.json')
bj['单字基线'] = B + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt（单字行：78 单字表 + 112 扩展字）'; bj['扩展字拆分'] = B + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt'; bj['文件'] = files
bj['最新简码裁定'] = '2026-09-16 同步 7391 个扩展字（拆分查询、部件反查、完整拆分表）；8105 字码与 78 一致；练习未变。'
json.dump(bj, open(U + '/构建核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '扩展字数': len(ext), '字总数': 8105 + len(ext), '扩展字码条数': sum(len(codes_of[c]) for c in ext),
       '单文件字节': os.path.getsize(main), '单文件SHA256': sha(main), '啾啾SHA256': sha(U + '/夜莺啾啾工具箱.html'), '离线包zipSHA256': sha(zp), '未动视图': list(frozen)}
json.dump(rep, open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
rep['字码有变'] = [{'字': c, '原': a, '现': b} for c, a, b in sorted(set((c, tuple(a), tuple(b)) for c, a, b in CHANGED))]
json.dump(rep, open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('字码有变:', rep['字码有变'])
print('扩展字 %d，字总数 %d，扩展字码 %d 条；单文件 %.1f MB %s；两入口一致 %s；练习/字根图/字根表逐字节未变；字面 </script 仅 1 个' % (
    len(ext), 8105 + len(ext), rep['扩展字码条数'], rep['单文件字节'] / 1048576, rep['单文件SHA256'][:16], rep['单文件SHA256'] == rep['啾啾SHA256']))
