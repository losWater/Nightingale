# -*- coding: utf-8 -*-
"""把 6 条漏传播的人工规则补齐到全部拆分副本（2026-09-21）。默认预演，--apply 落盘。

6 条规则里有 4 条是包含关系（椽/掾/蠡 都被 彖 覆盖），最小去重后只需三条替换：
    折 ＋ 折 ＋ 豕            → 互中间 ＋ 豕            （彖 椽 掾 蠡）
    彳 ＋ 氵 ＋ 一 ＋ 丁       → 行 ＋ 氵               （衍）
    厂 ＋ 一 ＋ 折 ＋ 撇 ＋ 丶   → 戊 ＋ 横               （戌）

拆分在本工程有两条链共四处副本（见 码表概念与规则.md 四之三），四处都要改：
  ① 55_拆分继承核验/当前完整拆分表.txt
  ② 112_扩展字继承/夜莺2.0扩展字拆分表.txt
  ③ 58_拆分查询/夜莺2.0拆分查询.html 的 const D
  ④ 65_群友离线工具包/ 下六个产物各自的副本
txt 的首根末根两列按新拆分串重算；html 里根数组按「根对象序列」成对替换，
根对象的键与组名从现行 const D 里取，保证与全表写法一致。
"""
import io, sys, os, re, csv, json, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
U = W + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'; BK = H + '/备份'
APPLY = '--apply' in sys.argv[1:]
RULES = [
    (['折', '折', '豕'], ['互中间', '豕'], '彖 椽 掾 蠡'),
    (['彳', '氵', '一', '丁'], ['行', '氵'], '衍'),
    (['厂', '一', '折', '撇', '丶'], ['戊', '横'], '戌'),
]
FILES = [W + '/55_拆分继承核验/当前完整拆分表.txt',
         W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt',
         W + '/58_拆分查询/夜莺2.0拆分查询.html',
         O + '/拆分查询.html', O + '/部件反查.html',
         O + '/完整拆分表.html', O + '/完整拆分表.txt',
         U + '/夜莺2.0随身工具_单文件.html', U + '/夜莺啾啾工具箱.html']
# 根对象写法从现行 const D 取
q = open(O + '/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
META = {}
for c, d in D.items():
    for r in d.get('根', []): META.setdefault(r['根'], {'键': r['键'], '组': r['组']})
missing = [x for _, new, _ in RULES for x in new if x not in META] + [x for old, _, _ in RULES for x in old if x not in META]
if missing: sys.exit('这些根在现行 const D 里找不到：%s' % sorted(set(missing)))
obj = lambda r: '{"根": "%s", "键": "%s", "组": "%s"}' % (r, META[r]['键'], META[r]['组'])
seq = lambda rs: ', '.join(obj(r) for r in rs)
esc = lambda s: s.replace('"', '\\"')
PAIRS = []
for old, new, why in RULES:
    PAIRS.append({'why': why,
                  'sp_old': ' ＋ '.join(old), 'sp_new': ' ＋ '.join(new),
                  'js_old': seq(old), 'js_new': seq(new)})
    print('规则［%s］  %s  →  %s' % (why, ' ＋ '.join(old), ' ＋ '.join(new)))
print()
def fix_cols(text):
    """完整拆分表 txt：按拆分串重算首根末根两列。"""
    out = []
    for l in text.split('\n'):
        f = l.rstrip('\r').split('\t')
        if len(f) >= 4 and f[0] != '汉字' and f[1]:
            p = f[1].split(' ＋ '); f[2], f[3] = p[0], p[-1]
            l = '\t'.join(f) + ('\r' if l.endswith('\r') else '')
        out.append(l)
    return '\n'.join(out)
def fix_rows(text):
    """html 里 rows 形式：["字", "拆分", "首根", "末根"]，含转义变体。"""
    def rep(m):
        ch, sp = m.group(2), m.group(3); p = sp.split(' ＋ ')
        return '%s%s", "%s", "%s", "%s"' % (m.group(1), ch, sp, p[0], p[-1]) if m.group(1) == '["' else m.group(0)
    text = re.sub(r'(\["|\[\\")([^"\\\]]+)(?:"|\\")\s*,\s*(?:"|\\")([^"\\]+?)(?:"|\\")\s*,\s*(?:"|\\")[^"\\]*(?:"|\\")\s*,\s*(?:"|\\")[^"\\]*(?:"|\\")\]',
                  lambda m: '["%s", "%s", "%s", "%s"]' % (m.group(2), m.group(3), m.group(3).split(' ＋ ')[0], m.group(3).split(' ＋ ')[-1])
                  if m.group(1) == '["' else m.group(0), text)
    return text
plan = []
for p in FILES:
    if not os.path.exists(p): print('  缺文件 %s' % p); continue
    s = open(p, encoding='utf-8-sig').read(); out = s; hits = collections.Counter()
    for r in PAIRS:
        for a, b, k in ((r['js_old'], r['js_new'], 'js'), (esc(r['js_old']), esc(r['js_new']), 'js转义'),
                        (r['sp_old'], r['sp_new'], '拆分串')):
            n = out.count(a)
            if n: out = out.replace(a, b); hits[k] += n
    if p.endswith('.txt'): out = fix_cols(out)
    elif 'rows' in out[:4000] or '完整拆分表' in p: out = fix_rows(out)
    rel = os.path.relpath(p, W).replace('\\', '/')
    left = sum(out.count(r['sp_old']) + out.count(r['js_old']) + out.count(esc(r['js_old'])) for r in PAIRS)
    print('  %-48s %s  残留 %d' % (rel, dict(hits) or '无命中', left))
    if left: sys.exit('  ！%s 仍有残留，停手' % rel)
    if out != s: plan.append((p, s, out, rel))
print('\n将改写 %d 个文件' % len(plan))
# 结构核对
for p, s, out, rel in plan:
    if not rel.endswith('.html'): continue
    m = re.search(r'\bconst D\s*=\s*', out)
    if not m: continue
    try: d1 = json.JSONDecoder().raw_decode(out[m.end():])[0]
    except Exception:
        print('  %-30s const D 转义嵌套，跳过（残留已为 0）' % rel.split('/')[-1]); continue
    bad = [t for t in d1 if d1[t].get('新拆') != ' ＋ '.join(x['根'] for x in d1[t].get('根', []))]
    print('  %-30s const D %d 字，根与新拆一致 %s' % (rel.split('/')[-1], len(d1), '✓' if not bad else '✗ %s' % bad[:3]))
    if bad: sys.exit('  结构核对不过，停手')
for p, s, out, rel in plan:
    if not rel.endswith('完整拆分表.txt') and not rel.endswith('当前完整拆分表.txt') and not rel.endswith('扩展字拆分表.txt'): continue
    bad = []
    for l in out.split('\n'):
        f = l.rstrip('\r').split('\t')
        if len(f) >= 4 and f[0] != '汉字' and f[1]:
            pp = f[1].split(' ＋ ')
            if f[2] != pp[0] or f[3] != pp[-1]: bad.append(f[0])
    print('  %-30s 首末根列一致 %s' % (rel.split('/')[-1], '✓' if not bad else '✗ %s' % bad[:5]))
    if bad: sys.exit('  列核对不过，停手')
if not APPLY:
    print('\n这是预演。确认后加 --apply 落盘。')
    sys.exit(0)
os.makedirs(BK, exist_ok=True)
stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
for p, s, out, rel in plan:
    shutil.copy2(p, '%s/%s_%s' % (BK, stamp, rel.replace('/', '_')))
    open(p, 'w', encoding='utf-8-sig', newline='').write(out)
    print('  已写入 %s' % rel)
print('\n完成。下一步：台账改 6 个码，再跑 export.py。')
