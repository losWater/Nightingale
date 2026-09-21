# -*- coding: utf-8 -*-
"""拆分的唯一原本 = 啾啾工具箱里的「拆分查询」页（2026-09-21 你定）。
工具箱自己的其余页面由它同步，不再手改：
    （55、112 两份拆分表冻结不动；106 的 Bime/Rime 拆分直接读原本）
    58_拆分查询/夜莺2.0拆分查询.html          （114 的源页）
    65/夜莺2.0离线工具包/拆分查询.html、部件反查.html、完整拆分表.html、完整拆分表.txt
    65/夜莺2.0随身工具_单文件.html            （啾啾工具箱是它的同内容副本）
只同步每个字的「根」与「新拆」两项；排名、字码由各自原有流程维护，不碰。
txt 只改 完整拆分/首根/末根 三列，行的归属与次序不变。
    python sync_chaifen.py            预演：列出每处与原本不一致的字数
    python sync_chaifen.py --apply    写入（改前备份到 备份/拆分同步/）
由 export.py 在 106 之前调用。55/112 两份拆分表冻结，不在同步范围。
"""
import io, sys, os, re, json, shutil, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
U = W + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'
SRC = U + '/夜莺啾啾工具箱.html'
APPLY = '--apply' in sys.argv[1:]
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); assert m, name
    obj, n = json.JSONDecoder().raw_decode(s[m.end():]); return obj, m.end(), m.end() + n
def put(s, name, obj):
    _, a, b = get(s, name); return s[:a] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + s[b:]
rd = lambda p: open(p, encoding='utf-8-sig').read()
views, _, _ = get(rd(SRC), 'views')
AUTH = {c: (r['根'], r['新拆']) for c, r in get(views['query'], 'D')[0].items()}
bad = [c for c, (rs, sp) in AUTH.items() if ' ＋ '.join(x['根'] for x in rs) != sp]
if bad: sys.exit('原本自身不自洽（根与新拆对不上）：%s' % bad[:10])
print('原本：啾啾工具箱·拆分查询，%d 字，根与新拆全部自洽' % len(AUTH))
changes = []
def fix_D(s):
    """page 里 const D 的 根/新拆 对齐原本；返回 (新文本, 不一致字数)"""
    D, _, _ = get(s, 'D'); n = 0
    for c, r in D.items():
        if c in AUTH and (r['根'], r['新拆']) != AUTH[c]:
            r['根'], r['新拆'] = [dict(x) for x in AUTH[c][0]], AUTH[c][1]; n += 1
    miss = set(AUTH) - set(D)
    if miss: sys.exit('副本缺字：%s' % list(miss)[:5])
    return (put(s, 'D', D) if n else s), n
def fix_rows(s):
    rows, _, _ = get(s, 'rows'); n = 0
    for r in rows:
        if r[0] in AUTH:
            sp = AUTH[r[0]][1]; p = sp.split(' ＋ ')
            if r[1:4] != [sp, p[0], p[-1]]: r[1:4] = [sp, p[0], p[-1]]; n += 1
    return (put(s, 'rows', rows) if n else s), n
def fix_txt(s):
    out = []; n = 0
    for l in s.split('\n'):
        f = l.rstrip('\r').split('\t')
        if len(f) >= 4 and f[0] in AUTH:
            sp = AUTH[f[0]][1]; p = sp.split(' ＋ ')
            if f[1:4] != [sp, p[0], p[-1]]:
                f[1:4] = [sp, p[0], p[-1]]; n += 1
                l = '\t'.join(f) + ('\r' if l.endswith('\r') else '')
        out.append(l)
    return '\n'.join(out), n
# 55/112 两份拆分表冻结不动（你定：只在加新字时从拆分重新导出），不在同步范围内；106 直接读原本。
for p, kind in ((W + '/58_拆分查询/夜莺2.0拆分查询.html', 'D'),
                (O + '/拆分查询.html', 'D'), (O + '/部件反查.html', 'D'),
                (O + '/完整拆分表.html', 'rows'), (O + '/完整拆分表.txt', 'txt'),
                (U + '/夜莺2.0随身工具_单文件.html', 'views')):
    s = rd(p)
    if kind == 'txt': ns, n = fix_txt(s)
    elif kind == 'D': ns, n = fix_D(s)
    elif kind == 'rows': ns, n = fix_rows(s)
    else:
        v, _, _ = get(s, 'views'); n = 0
        for k, f in (('query', fix_D), ('components', fix_D), ('text', fix_rows)):
            v[k], m = f(v[k]); n += m
        ns = put(s, 'views', v) if n else s
    print('  %-44s 与原本不一致 %d 字' % (os.path.relpath(p, W).replace('\\', '/'), n))
    if n: changes.append((p, ns))
# 啾啾自身的另两个视图也要与 query 一致
vn = 0
for k, f in (('components', fix_D), ('text', fix_rows)):
    views[k], m = f(views[k]); vn += m
print('  %-44s 与原本不一致 %d 字' % ('啾啾工具箱 自身的部件反查/完整拆分表视图', vn))
if vn: changes.append((SRC, put(rd(SRC), 'views', views)))
if not changes: print('\n全部一致，无需写入。'); sys.exit(0)
if not APPLY: print('\n预演：%d 个文件需要同步。加 --apply 写入。' % len(changes)); sys.exit(0)
bk = H + '/备份/拆分同步/' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); os.makedirs(bk, exist_ok=True)
for p, ns in changes:
    shutil.copy2(p, bk + '/' + os.path.basename(p))
    open(p, 'w', encoding='utf-8-sig', newline='').write(ns)
print('\n已同步 %d 个文件（备份 %s）' % (len(changes), bk))
