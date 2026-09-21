# -*- coding: utf-8 -*-
"""按你定的拆法订正四条（2026-09-21）。默认预演，--apply 落盘。

  庸族  广＋折＋二＋冂＋举字底  →  广＋肀＋用      （本字与 慵墉镛鳙鄘 都走这条）
  庸族  广＋折＋二＋⺝＋丨      →  广＋肀＋用      （嘃嫞槦牅鷛 走的是另一种旧形式）
  卸左  𠂉＋正                →  卸左           （啣欫篽蓹衘，字形库确认同源）
  年族  𠂉＋一＋丨＋十         →  𠂉＋横＋竖＋横＋竖 （按年的登记规则）
  衮族  亠＋八＋厶＋𧘇         →  衣＋八＋厶      （按衮的拆法）

拆分在本工程有两条链共四处副本（码表概念与规则.md 四之三），四处都要改。
txt 的首末根两列按新拆分串重算；html 里根数组按根对象序列成对替换。
"""
import io, sys, os, re, json, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
U = W + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'; BK = H + '/备份'
APPLY = '--apply' in sys.argv[1:]
RULES = [
    (['广', '折', '二', '冂', '举字底'], ['广', '肀', '用'], '庸·旧形式甲'),
    (['广', '折', '二', '⺝', '丨'], ['广', '肀', '用'], '庸·旧形式乙'),
    (['𠂉', '正'], ['卸左'], '卸左'),
    (['𠂉', '一', '丨', '十'], ['𠂉', '横', '竖', '横', '竖'], '年'),
    (['亠', '八', '厶', '𧘇'], ['衣', '八', '厶'], '衮'),
]
FILES = [W + '/55_拆分继承核验/当前完整拆分表.txt',
         W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt',
         W + '/58_拆分查询/夜莺2.0拆分查询.html',
         O + '/拆分查询.html', O + '/部件反查.html',
         O + '/完整拆分表.html', O + '/完整拆分表.txt',
         U + '/夜莺2.0随身工具_单文件.html', U + '/夜莺啾啾工具箱.html']
q = open(O + '/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
META = {}
for c, d in D.items():
    for r in d.get('根', []): META.setdefault(r['根'], {'键': r['键'], '组': r['组']})
need = {x for o, n, _ in RULES for x in o + n}
miss = [x for x in need if x not in META]
if miss: sys.exit('这些根在现行 const D 里找不到：%s' % miss)
obj = lambda r: '{"根": "%s", "键": "%s", "组": "%s"}' % (r, META[r]['键'], META[r]['组'])
seq = lambda rs: ', '.join(obj(r) for r in rs)
esc = lambda s: s.replace('"', '\\"')
P = [{'why': w, 'sp_old': ' ＋ '.join(o), 'sp_new': ' ＋ '.join(n),
      'js_old': seq(o), 'js_new': seq(n)} for o, n, w in RULES]
for r in P: print('［%s］%s → %s' % (r['why'], r['sp_old'], r['sp_new']))
print()
def fix_cols(t):
    out = []
    for l in t.split('\n'):
        f = l.rstrip('\r').split('\t')
        if len(f) >= 4 and f[0] != '汉字' and f[1]:
            p = f[1].split(' ＋ '); f[2], f[3] = p[0], p[-1]
            l = '\t'.join(f) + ('\r' if l.endswith('\r') else '')
        out.append(l)
    return '\n'.join(out)
def fix_rows(t):
    return re.sub(r'\["([^"]+)", "([^"]+)", "[^"]*", "[^"]*"\]',
                  lambda m: '["%s", "%s", "%s", "%s"]' % (m.group(1), m.group(2),
                                                          m.group(2).split(' ＋ ')[0], m.group(2).split(' ＋ ')[-1]), t)
plan = []
for p in FILES:
    if not os.path.exists(p): print('  缺文件 %s' % p); continue
    s = open(p, encoding='utf-8-sig').read(); out = s; hit = collections.Counter()
    for r in P:
        for a, b, k in ((r['js_old'], r['js_new'], 'js'), (esc(r['js_old']), esc(r['js_new']), 'js转义'),
                        (r['sp_old'], r['sp_new'], '串')):
            n = out.count(a)
            if n: out = out.replace(a, b); hit[k] += n
    if p.endswith('.txt'): out = fix_cols(out)
    elif '完整拆分表' in p: out = fix_rows(out)
    rel = os.path.relpath(p, W).replace('\\', '/')
    left = sum(out.count(r['sp_old']) + out.count(r['js_old']) + out.count(esc(r['js_old'])) for r in P)
    print('  %-46s %-34s 残留 %d' % (rel, dict(hit) or '无命中', left))
    if left: sys.exit('  ！残留不为 0，停手')
    if out != s: plan.append((p, s, out, rel))
print('\n将改写 %d 个文件' % len(plan))
for p, s, out, rel in plan:
    if not rel.endswith('.html'): continue
    m = re.search(r'\bconst D\s*=\s*', out)
    if not m: continue
    try: d1 = json.JSONDecoder().raw_decode(out[m.end():])[0]
    except Exception: print('  %-28s 转义嵌套，跳过结构核对' % rel.split('/')[-1]); continue
    bad = [t for t in d1 if d1[t].get('新拆') != ' ＋ '.join(x['根'] for x in d1[t].get('根', []))]
    print('  %-28s const D %d 字，根与新拆一致 %s' % (rel.split('/')[-1], len(d1), '✓' if not bad else '✗ %s' % bad[:3]))
    if bad: sys.exit('结构核对不过')
for p, s, out, rel in plan:
    if not rel.endswith('.txt'): continue
    bad = [l.split('\t')[0] for l in out.split('\n')
           if len(l.rstrip('\r').split('\t')) >= 4 and not l.startswith('汉字') and l
           and (l.rstrip('\r').split('\t')[2] != l.rstrip('\r').split('\t')[1].split(' ＋ ')[0]
                or l.rstrip('\r').split('\t')[3] != l.rstrip('\r').split('\t')[1].split(' ＋ ')[-1])]
    print('  %-28s 首末根列一致 %s' % (rel.split('/')[-1], '✓' if not bad else '✗ %s' % bad[:5]))
    if bad: sys.exit('列核对不过')
if not APPLY:
    print('\n这是预演。确认后加 --apply 落盘。')
    sys.exit(0)
os.makedirs(BK, exist_ok=True)
stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
for p, s, out, rel in plan:
    shutil.copy2(p, '%s/%s_%s' % (BK, stamp, rel.replace('/', '_')))
    open(p, 'w', encoding='utf-8-sig', newline='').write(out)
    print('  已写入 %s' % rel)
print('\n完成。')
