# -*- coding: utf-8 -*-
"""曲部件拆分不一致的诊断（2026-09-21 群友反馈）。

现象：曲 本身拆成「囗 ＋ 横 ＋ 丨 ＋ 丨」，但所有含曲的字都拆成「由 ＋ 丨」。
由 的竖是出头的，曲 的两竖不出头，两者不是一回事，由＋丨 是错拆。

本脚本只做诊断，不改任何文件：
  1 这 24 个字分别在哪份拆分源里；
  2 订正后首根／末根会不会变——夜莺只取首末两根，中间怎么拆不影响编码；
  3 真会变码的那几个字，现在主表里的码是什么，改了会不会和主表冲突。
"""
import io, sys, os, re, json, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
SRC = {
    '通用规范': W + '/55_拆分继承核验/当前完整拆分表.txt',
    '扩展字': W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt',
}
tables = {}
for name, p in SRC.items():
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'))
    tables[name] = {r['汉字']: r['完整拆分'] for r in rows}
    print('%s：%d 字（%s）' % (name, len(rows), os.path.basename(p)))
# 字根 → 键
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}
for c, d in D.items():
    for r in d.get('根', []): KEY[r['根']] = r['键']
# 主表
codes = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    codes[t].append(c)
freq = {}
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1])

QU_OLD = '由 ＋ 丨'
QU_NEW = '囗 ＋ 横 ＋ 丨 ＋ 丨'      # 与「曲」本字保持一致
print('\n' + '═' * 78)
print('受影响的字：把「%s」换成「%s」' % (QU_OLD, QU_NEW))
print('═' * 78)
print('%-3s %-6s %-8s %-30s %-30s %s' % ('字', '来源', '字频', '现拆分', '订正后', '首/末根变化'))
rows = []
for name, tab in tables.items():
    for t, s in tab.items():
        if QU_OLD not in s: continue
        ns = s.replace(QU_OLD, QU_NEW)
        a = s.split(' ＋ '); b = ns.split(' ＋ ')
        chg = (a[0] != b[0]) or (a[-1] != b[-1])
        rows.append((t, name, s, ns, a, b, chg))
rows.sort(key=lambda r: (-freq.get(r[0], 0), r[0]))
for t, name, s, ns, a, b, chg in rows:
    mark = '首根 %s→%s' % (a[0], b[0]) if a[0] != b[0] else ''
    if a[-1] != b[-1]: mark += ('，' if mark else '') + '末根 %s→%s' % (a[-1], b[-1])
    print('%-3s %-6s %-8s %-30s %-30s %s'
          % (t, name, freq.get(t, '—'), s[:28], ns[:28], mark or '不变'))
print('\n共 %d 字。其中首末根会变的：' % len(rows))
chg = [r for r in rows if r[6]]
if not chg: print('  无——中间怎么拆都不影响编码。')
for t, name, s, ns, a, b, _ in chg:
    ok = KEY.get(a[0], '?'), KEY.get(b[0], '?')
    print('  %s（%s，字频 %s）：首根 %s(%s) → %s(%s)，主表现有码 %s'
          % (t, name, freq.get(t, '—'), a[0], ok[0], b[0], ok[1], codes.get(t, ['（不在主表）'])))
json.dump({'受影响': [{'字': t, '来源': n, '现': s, '订正': ns, '变码': c} for t, n, s, ns, _, _, c in rows]},
          open(H + '/诊断.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/诊断.json' % H)
