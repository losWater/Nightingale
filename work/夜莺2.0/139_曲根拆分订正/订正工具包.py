# -*- coding: utf-8 -*-
"""订正工具包里各产物自带的拆分副本（2026-09-21）。默认预演，--apply 落盘。

为什么要逐个改：114/sync.py 是一次性迁移脚本，第 52 行明确断言
「已有字的拆分/根/排名逐条不变」，它只补新扩展字、只刷新字码，
不会把 58 的拆分改动带下去。每个产物各自带一份拆分副本，所以得逐个订正。

三类替换：
  ① 根数组成对模式（原样与转义两种形式）——必须成对匹配，
     因为单独的「由」根对象在含由的字里到处都是（拆分查询.html 里就有 112 处）。
  ② 新拆串 由 ＋ 丨 → 囗 ＋ 横 ＋ 丨 ＋ 丨。
  ③ 首根列：只有 農、鄷 的曲在字首，首根由 由 变 囗，
     完整拆分表的 .txt 与 .html rows 里那一列要跟着改。
备份目录（*前备份/）是历史快照，不动。
"""
import io, sys, os, re, shutil, datetime, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
U = W + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'
BK = H + '/备份'
APPLY = '--apply' in sys.argv[1:]
PAIR_OLD = '{"根": "由", "键": "p", "组": "田／里／果"}, {"根": "丨", "键": "l", "组": "竖"}'
PAIR_NEW = ('{"根": "囗", "键": "j", "组": "囗"}, {"根": "横", "键": "p", "组": "横"}, '
            '{"根": "丨", "键": "l", "组": "竖"}, {"根": "丨", "键": "l", "组": "竖"}')
esc = lambda s: s.replace('"', '\\"')
SPLIT_OLD, SPLIT_NEW = '由 ＋ 丨', '囗 ＋ 横 ＋ 丨 ＋ 丨'
HEAD_FIX = ['農', '鄷']        # 首根 由 → 囗 的两个字
FILES = [
    O + '/拆分查询.html', O + '/部件反查.html',
    O + '/完整拆分表.html', O + '/完整拆分表.txt',
    U + '/夜莺2.0随身工具_单文件.html', U + '/夜莺啾啾工具箱.html',
]
print('订正 %d 个产物（备份目录不动）\n' % len(FILES))
plan = []
for p in FILES:
    if not os.path.exists(p): print('  缺文件：%s' % p); continue
    s = open(p, encoding='utf-8-sig').read()
    n_raw, n_esc, n_sp = s.count(PAIR_OLD), s.count(esc(PAIR_OLD)), s.count(SPLIT_OLD)
    out = s.replace(PAIR_OLD, PAIR_NEW).replace(esc(PAIR_OLD), esc(PAIR_NEW)).replace(SPLIT_OLD, SPLIT_NEW)
    # 首根列：农/鄷 在 .txt 是制表符分隔，在 html rows 里是 "字","拆分","首根","末根"
    n_head = 0
    for ch in HEAD_FIX:
        pats = [
            # 完整拆分表.txt：汉字 \t 拆分 \t 首根 \t 末根
            (r'(%s\t%s[^\t\n]*\t)由(\t)' % (re.escape(ch), re.escape(SPLIT_NEW)), r'\1囗\2'),
            # 完整拆分表.html 的 rows：["農", "囗 ＋ …", "由", "辰"]（逗号后有空格）
            (r'("%s",\s*"%s[^"]*",\s*)"由"' % (re.escape(ch), re.escape(SPLIT_NEW)), r'\1"囗"'),
            # 单文件里 rows 被转义成 \"農\", \"…\", \"由\"
            (r'(\\"%s\\",\s*\\"%s[^\\"]*\\",\s*)\\"由\\"' % (re.escape(ch), re.escape(SPLIT_NEW)), r'\1\\"囗\\"'),
        ]
        for a, b in pats:
            out, k = re.subn(a, b, out); n_head += k
    rel = os.path.relpath(p, W).replace('\\', '/')
    print('  %-44s 成对(原样/转义) %3d/%3d   新拆串 %3d   首根列 %d' % (rel, n_raw, n_esc, n_sp, n_head))
    left = out.count(PAIR_OLD) + out.count(esc(PAIR_OLD)) + out.count(SPLIT_OLD)
    if left: print('       ！替换后仍残留 %d 处' % left)
    plan.append((p, s, out, rel))
print()
# 结构核对：能解析的 JSON 结构要仍然合法、字数不变
for p, s, out, rel in plan:
    if not rel.endswith('.html'): continue
    m = re.search(r'\bconst D\s*=\s*', out)
    if not m: continue
    try:
        d0 = json.JSONDecoder().raw_decode(s[re.search(r'\bconst D\s*=\s*', s).end():])[0]
        d1 = json.JSONDecoder().raw_decode(out[m.end():])[0]
    except Exception:
        # 单文件/啾啾里各视图是被转义后套在 views 里的，const D 不能直接解析；
        # 这两个文件靠上面的「替换后残留为 0」来保证，跳过结构核对。
        print('  %-30s const D 为转义嵌套，跳过结构核对（残留已为 0）' % rel.split('/')[-1])
        continue
    bad = [t for t in d1 if d1[t].get('新拆') != ' ＋ '.join(r['根'] for r in d1[t].get('根', []))]
    print('  %-30s const D %d → %d 字，根与新拆一致性 %s'
          % (rel.split('/')[-1], len(d0), len(d1), '✓' if not bad else '✗ %s' % bad[:3]))
    if len(d0) != len(d1) or bad: sys.exit('  结构核对不过，停手。')
# 完整拆分表.txt 的列核对
for p, s, out, rel in plan:
    if not rel.endswith('完整拆分表.txt'): continue
    bad = []
    for l in out.split('\n'):
        if not l or l.startswith('汉字'): continue
        f = l.rstrip('\r').split('\t')
        if len(f) < 4: continue
        parts = f[1].split(' ＋ ')
        if f[2] != parts[0] or f[3] != parts[-1]: bad.append(f[0])
    print('  完整拆分表.txt 首末根列与拆分串一致性：%s' % ('全部一致 ✓' if not bad else '✗ %d 个 %s' % (len(bad), bad[:5])))
    if bad: sys.exit('  列核对不过，停手。')
if not APPLY:
    print('\n这是预演。确认后加 --apply 落盘。')
    sys.exit(0)
os.makedirs(BK, exist_ok=True)
stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
for p, s, out, rel in plan:
    bak = '%s/%s_%s' % (BK, stamp, rel.replace('/', '_'))
    shutil.copy2(p, bak)
    open(p, 'w', encoding='utf-8-sig', newline='').write(out)
    print('  已写入 %s' % rel)
print('\n完成。下一步重跑 export.py，让 123/137 虎娘从新的完整拆分表取数。')
