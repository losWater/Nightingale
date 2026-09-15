# -*- coding: utf-8 -*-
"""工具箱同步单字表（2026-09-15）：把 78 单字表的字码重算进工具箱单文件的 D['编码']（拆分查询、部件反查两个视图），
拆分/根/排名/练习/字根图/字根表/说明/本地进度一律不动。同步源页 58 与离线包同名页面、重打 zip。改前备份于本目录。"""
import io, sys, os, re, json, shutil, hashlib, zipfile, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); BK = H + '/实装前备份'
U = B + '/65_群友离线工具包'
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); assert m, name
    obj, n = json.JSONDecoder().raw_decode(s[m.end():]); return obj, m.end(), m.end() + n
def put(s, name, obj):
    _, a, b = get(s, name); return s[:a] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + s[b:]
def backup(p):
    q = BK + '/' + os.path.relpath(p, B); os.makedirs(os.path.dirname(q), exist_ok=True)
    if not os.path.exists(q): shutil.copy2(p, q)
def write(p, s):
    backup(p); open(p, 'w', encoding='utf-8').write(s)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
groups = collections.OrderedDict()
for line in open(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) >= 2: groups.setdefault(p[1], []).append(p[0])
def sync_D(D):
    old = {(c, e['码']) for c, r in D.items() for e in r['编码']}
    for r in D.values(): r['编码'] = []
    for k, chars in groups.items():
        for i, c in enumerate(chars, 1):
            assert c in D, c; D[c]['编码'].append({'码': k, '位': i, '同码': chars})
    for r in D.values(): r['编码'].sort(key=lambda e: (len(e['码']), e['码']))
    new = {(c, e['码']) for c, r in D.items() for e in r['编码']}
    return old, new
f58 = B + '/58_拆分查询/夜莺2.0拆分查询.html'; s = open(f58, encoding='utf-8-sig').read(); D, _, _ = get(s, 'D')
old, new = sync_D(D); write(f58, put(s, 'D', D))
main = U + '/夜莺2.0随身工具_单文件.html'; shell = open(main, encoding='utf-8-sig').read()
meta = {}
views, _, _ = get(shell, 'views'); frozen = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in views.items() if k not in ('query', 'components')}
for key, name in [('query', '拆分查询.html'), ('components', '部件反查.html')]:
    Dv, _, _ = get(views[key], 'D'); meta[key] = {c: (r['根'], r['新拆'], r['排名']) for c, r in Dv.items()}; o2, n2 = sync_D(Dv); assert n2 == new
    views[key] = put(views[key], 'D', Dv); write(U + '/夜莺2.0离线工具包/' + name, views[key])
shell2 = put(shell, 'views', views); write(main, shell2); backup(U + '/夜莺啾啾工具箱.html'); shutil.copy2(main, U + '/夜莺啾啾工具箱.html')
# 复核：重读单文件，D 与 78 完全一致、其他视图逐字节不变
chk = open(main, encoding='utf-8-sig').read(); v2, _, _ = get(chk, 'views')
assert {k: hashlib.sha256(v.encode()).hexdigest() for k, v in v2.items() if k not in ('query', 'components')} == frozen
for key in ('query', 'components'):
    Dc, _, _ = get(v2[key], 'D'); assert {(c, e['码']) for c, r in Dc.items() for e in r['编码']} == new
    gc = {}; [gc.setdefault(e['码'], e['同码']) for r in Dc.values() for e in r['编码']]; assert gc == dict(groups)
    assert {c: (r['根'], r['新拆'], r['排名']) for c, r in Dc.items()} == meta[key]   # 拆分/根/排名逐字未变
zp = U + '/夜莺2.0离线工具包.zip'; backup(zp)
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(U + '/夜莺2.0离线工具包')): z.write(U + '/夜莺2.0离线工具包/' + fn, '夜莺2.0离线工具包/' + fn)
files = {fn: sha(U + '/夜莺2.0离线工具包/' + fn) for fn in sorted(os.listdir(U + '/夜莺2.0离线工具包'))}
json.dump(files, open(U + '/文件核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
bj = json.load(open(U + '/构建核验.json', encoding='utf-8')); bj['单字基线'] = B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt'; bj['文件'] = files
bj['最新简码裁定'] = '2026-09-15 同步 78 单字表（第二十四批及全部让位/笔误/补读音裁定）；练习未变。'
json.dump(bj, open(U + '/构建核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '单字表': '78', '撤字码': sorted(old - new), '加字码': sorted(new - old),
       '单文件SHA256': sha(main), '啾啾SHA256': sha(U + '/夜莺啾啾工具箱.html'), '离线包zipSHA256': sha(zp), '未动视图': list(frozen)}
json.dump(rep, open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('撤 %d 加 %d；单文件 %s；两入口一致 %s；练习/字根图/字根表/说明视图逐字节未变' % (len(old - new), len(new - old), rep['单文件SHA256'][:16], rep['单文件SHA256'] == rep['啾啾SHA256']))

import re as _re
_t = open(main, encoding='utf-8-sig').read(); _n = len(_re.findall(r'</script', _t, _re.I)); assert _n == 1, ('字面 </script 数', _n)
print('硬检查：字面 </script 仅 1 个，嵌入页面不会截断外层脚本')
