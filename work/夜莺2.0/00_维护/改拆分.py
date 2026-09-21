# -*- coding: utf-8 -*-
"""改拆分：只改唯一原本（啾啾工具箱·拆分查询），其余副本由 export.py 的「拆分同步」一步带下去。
    python 改拆分.py 庸=广＋肀＋用 蓘=艹＋衣＋八＋厶     预演
    python 改拆分.py 庸=广＋肀＋用 --apply               写入（改前备份）
根之间用 ＋ + · 或空格分隔均可；每个根必须是现有字根。
预演会告诉你首末根变没变：变了，全码就要跟着改，打印出应有新码与现有候选，
那一步照老规矩走台账（apply_ledger.py），候选位按 出简让全／扩展字排末尾 定。
"""
import io, sys, os, re, json, shutil, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
SRC = W + '/65_群友离线工具包/夜莺啾啾工具箱.html'
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); assert m, name
    obj, n = json.JSONDecoder().raw_decode(s[m.end():]); return obj, m.end(), m.end() + n
def put(s, name, obj):
    _, a, b = get(s, name); return s[:a] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + s[b:]
args = [a for a in sys.argv[1:] if a != '--apply']; APPLY = '--apply' in sys.argv[1:]
if not args: sys.exit(__doc__)
page = open(SRC, encoding='utf-8-sig').read()
views, _, _ = get(page, 'views'); D, _, _ = get(views['query'], 'D')
META = {}
for c, r in D.items():
    for x in r['根']: META.setdefault(x['根'], x)
codes = collections.defaultdict(list); zi = collections.defaultdict(list)
for l in open(H + '/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); codes[t].append(c); zi[c].append(t)
todo = []
for a in args:
    if '=' not in a: sys.exit('格式应为 字=根＋根：%s' % a)
    ch, sp = a.split('=', 1)
    rs = [x for x in re.split(r'[＋+·\s]+', sp.strip()) if x]
    miss = [x for x in rs if x not in META]
    if ch not in D: sys.exit('%s 不在拆分原本里' % ch)
    if miss: sys.exit('%s：这些不是现有字根 %s' % (ch, miss))
    old = D[ch]['新拆']; new = ' ＋ '.join(rs)
    print('%s  %s\n    → %s' % (ch, old, new))
    if old == new: print('    （没有变化）'); continue
    o, n = old.split(' ＋ '), rs
    if (o[0], o[-1]) == (n[0], n[-1]):
        print('    首末根不变，编码不受影响。')
    else:
        full = [c for c in codes.get(ch, []) if len(c) == 4]
        for f in full:
            nc = f[:2] + META[n[0]]['键'] + META[n[-1]]['键']
            print('    首末根变了（%s…%s → %s…%s）：全码 %s → %s，新码位现有单字 %s'
                  % (o[0], o[-1], n[0], n[-1], f, nc, '、'.join(zi.get(nc, [])) or '空'))
        print('    → 需要走台账改码（单字表、字词表各一行）。三简只看首根，首根没变就不用动。')
    todo.append((ch, [dict(META[x]) for x in rs], new))
if not todo or not APPLY:
    print('\n%s' % ('没有要改的。' if not todo else '预演。加 --apply 写入原本，然后跑 export.py。')); sys.exit(0)
for ch, rs, new in todo: D[ch]['根'], D[ch]['新拆'] = rs, new
views['query'] = put(views['query'], 'D', D)
bk = H + '/备份/拆分原本/' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); os.makedirs(bk, exist_ok=True)
shutil.copy2(SRC, bk + '/' + os.path.basename(SRC))
open(SRC, 'w', encoding='utf-8-sig', newline='').write(put(page, 'views', views))
print('\n已写入原本 %d 字（备份 %s）。接下来跑 export.py，副本会自动同步。' % (len(todo), bk))
