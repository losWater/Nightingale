# -*- coding: utf-8 -*-
"""练习例字补扩展字 + 例字两列（2026-09-16 你提出）：
① 字根练习"首末用根例字"（rootExamples）与根表"例字"（roots[].例字、字根总表第 4 列）原来只从 8105 字取，門/鳥/馬/長 等繁体根为空。
   现在把 112 的 7391 个扩展字接在 8105 之后作为候选（扩展字之间按语料次数降序、无记录按 112 表序），算法与 67/同步正根.py 完全相同，
   所以原来已够数的根例字逐条不变，只有不够的根才被扩展字补上。
② 练习页例字区改为两列（窄屏仍一列）。
练习题目/顺序/签名不动，本地进度不受影响。改前备份于本目录 实装前备份/。"""
import io, sys, os, re, json, shutil, hashlib, zipfile, datetime
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
# 候选字：8105（58 数据，按排名）+ 扩展字（112）
q = open(O + '/拆分查询.html', encoding='utf-8-sig').read(); D, _, _ = get(q, 'D')
base = [(c, [g['根'] for g in r['根']], r['新拆']) for c, r in sorted(((c, r) for c, r in D.items() if r['排名'] is not None), key=lambda t: t[1]['排名'])]
assert len(base) == 8105, len(base)
ext = []
for l in open(B + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt', encoding='utf-8-sig').read().splitlines()[1:]:
    c, sp, f, e = l.split('\t'); ext.append((c, sp.split(' ＋ '), sp))
assert len(ext) == 7391
cands = base + ext   # 112 表本身已按语料次数降序、无记录按 1.0 原序
def examples_for(name, old):
    """只补不改：原例字原样保留，不够的名额才从扩展字里补（补位仍按 首根/末根 交替的口径挑）。"""
    cs = []
    for c, rs, sp in ext:
        first = rs[0] == name; last = rs[-1] == name
        if first or last: cs.append({'字': c, '位置': '首末' if first and last else '首根' if first else '末根', '拆分': sp})
    out = {}
    for n in [1, 2, 4]:
        chosen = list(old[str(n)]); pattern = (['首根', '末根'] * (n // 2) if n > 1 else ['首根'])
        for pos in pattern[len(chosen):]:
            x = next((x for x in cs if x not in chosen and x['位置'] == pos), None)
            if x: chosen.append(x)
        for x in cs:
            if len(chosen) >= n: break
            if x not in chosen: chosen.append(x)
        out[str(n)] = chosen[:n]
    return out
def anywhere(name, k=5):
    return [c for c, rs, sp in cands if name in rs][:k]
main = U + '/夜莺2.0随身工具_单文件.html'; shell = open(main, encoding='utf-8-sig').read()
views, _, _ = get(shell, 'views'); frozen = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in views.items() if k not in ('practice', 'roots')}
pv = views['practice']; assert pv == open(O + '/字根练习.html', encoding='utf-8-sig').read()
roots, _, _ = get(pv, 'roots'); old_ex, _, _ = get(pv, 'rootExamples'); assert len(roots) == 404 and set(old_ex) == {r['根'] for r in roots}
new_ex = {}; changed_ex = []; changed_list = []
for r in roots:
    name = r['根']; o = old_ex[name]; e = examples_for(name, o)
    for n in ('1', '2', '4'):   # 原例字是新例字的前缀（只补不改）
        assert [x['字'] for x in o[n]] == [x['字'] for x in e[n]][:len(o[n])], (name, n)
    new_ex[name] = e
    if e != o: changed_ex.append((name, [x['字'] + '(' + x['位置'] + ')' for x in e['4']]))
    lst = [x for x in r['例字'].split('、') if x]
    if len(lst) < 5:
        add = [c for c in anywhere(name, 50) if c not in lst][:5 - len(lst)]
        if add: r['例字'] = '、'.join(lst + add); changed_list.append((name, r['例字']))
pv = put(pv, 'roots', roots); pv = put(pv, 'rootExamples', new_ex)
# 两列例字
two = '#example{display:grid;grid-template-columns:1fr 1fr;column-gap:0;align-items:start}#example .example-row:nth-child(odd){padding-right:18px}#example .example-row:nth-child(even){padding-left:18px;border-left:2px solid #9fb3a8}@media(max-width:600px){#example{grid-template-columns:1fr}#example .example-row:nth-child(odd){padding-right:0}#example .example-row:nth-child(even){padding-left:0;border-left:0}}'
if two not in pv:   # 放在样式表末尾（不能插在窄屏 @media 块里，2026-09-16 踩过）
    assert pv.count('</style>') == 1; pv = pv.replace('</style>', two + '\n</style>')
views['practice'] = pv; write(O + '/字根练习.html', pv)
# 字根总表第 4 列
rv = views['roots']; assert rv == open(O + '/字根总表.html', encoding='utf-8-sig').read()
def rootrow(m):
    cells = re.findall(r'<td>(.*?)</td>', m[0]); name = re.sub('<[^>]+>', '', cells[1]) if len(cells) == 4 else ''
    if name in new_ex: return m[0].replace('<td>' + cells[3] + '</td>', '<td>' + '、'.join(x['字'] for x in new_ex[name]['4']) + '</td>')
    return m[0]
rv2 = re.sub(r'<tr><td>.*?</tr>', rootrow, rv); views['roots'] = rv2; write(O + '/字根总表.html', rv2)
shell2 = put(shell, 'views', views); write(main, shell2); backup(U + '/夜莺啾啾工具箱.html'); shutil.copy2(main, U + '/夜莺啾啾工具箱.html')
write(U + '/记忆练习脚本.js', re.search(r'<script>([\s\S]*)</script>', pv)[1])
write(U + '/练习逐根例字.json', json.dumps(new_ex, ensure_ascii=False, indent=2))
up = O + '/使用说明.txt'; u = open(up, encoding='utf-8-sig').read()
line = '2026-09-16：字根练习的例字用扩展字补齐（門/鳥/馬/長 等繁体根有例字了），例字改为两列显示；题目与进度不变。'
if line not in u: write(up, u.rstrip('\r\n') + ('\r\n' if '\r\n' in u else '\n') + line + ('\r\n' if '\r\n' in u else '\n'), 'utf-8-sig')
# 复核
chk = open(main, encoding='utf-8-sig').read(); v2, _, _ = get(chk, 'views')
assert {k: hashlib.sha256(v.encode()).hexdigest() for k, v in v2.items() if k not in ('practice', 'roots')} == frozen
r2, _, _ = get(v2['practice'], 'roots'); assert [(r['根'], r['键']) for r in r2] == [(r['根'], r['键']) for r in roots]   # 签名所依赖的根序与键不变
e2, _, _ = get(v2['practice'], 'rootExamples'); assert e2 == new_ex
assert v2['practice'] == open(O + '/字根练习.html', encoding='utf-8-sig').read() and v2['roots'] == open(O + '/字根总表.html', encoding='utf-8-sig').read()
n = len(re.findall(r'</script', chk, re.I)); assert n == 1, n
zp = U + '/夜莺2.0离线工具包.zip'; backup(zp)
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(O)): z.write(O + '/' + fn, '夜莺2.0离线工具包/' + fn)
files = {fn: sha(O + '/' + fn) for fn in sorted(os.listdir(O))}
backup(U + '/文件核验.json'); json.dump(files, open(U + '/文件核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
bj = json.load(open(U + '/构建核验.json', encoding='utf-8')); backup(U + '/构建核验.json'); bj['文件'] = files
bj['练习例字'] = '2026-09-16 用 112 扩展字补齐首末用根例字与根表例字（只补不改）；例字两列。'
json.dump(bj, open(U + '/构建核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '例字有变的根': dict(changed_ex), '根表例字有变的根': dict(changed_list),
       '仍无例字的根': [k for k, v in new_ex.items() if not v['4']], '例字仍不足4的根': {k: len(v['4']) for k, v in new_ex.items() if 0 < len(v['4']) < 4},
       '单文件SHA256': sha(main), '啾啾SHA256': sha(U + '/夜莺啾啾工具箱.html'), '离线包zipSHA256': sha(zp)}
json.dump(rep, open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('例字有变的根 %d，根表例字有变 %d，仍无例字 %s，仍不足 4 个 %d' % (len(changed_ex), len(changed_list), rep['仍无例字的根'], len(rep['例字仍不足4的根'])))
for k, v in changed_ex: print('  ', k, '、'.join(v))
