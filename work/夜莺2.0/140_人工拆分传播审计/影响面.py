# -*- coding: utf-8 -*-
"""漏传播的 6 条规则：逐字算影响面（2026-09-21）。只读。

audit.py 查出 6 条人工规则「本字改对了、族里没跟上」。
这里逐字给出：现拆分 → 订正后拆分、首末根是否变、变则现行码与应有码、字频。
口径与 139 处理「曲」时一致：夜莺只取首末两根，部件在字中间则编码不受影响。
顺带核对第二类（部件本字与登记不符）到底是真错还是根名别名。
"""
import io, sys, os, csv, json, yaml, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); R = os.path.dirname(W) + '/重开工程/02_规范拆分'
SRC = {'通用规范': W + '/55_拆分继承核验/当前完整拆分表.txt', '扩展字': W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt'}
table = {}; origin = {}
for n, p in SRC.items():
    for r in csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'):
        table[r['汉字']] = r['完整拆分'].split(' ＋ '); origin[r['汉字']] = n
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}; GRP = {}
for c, d in D.items():
    for r in d.get('根', []): KEY[r['根']] = r['键']; GRP[r['根']] = r['组']
codes = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); codes[t].append(c)
freq = {}
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1])
RULES = []
for fn, tag in (('正式字架规则.yaml', '字架规则'), ('正式历史结构裁决规则.yaml', '历史结构裁决')):
    for ch, d in (yaml.safe_load(open(R + '/' + fn, encoding='utf-8')).get('guarded_rewrites') or {}).items():
        if d.get('expected_before') and d.get('canonical_after'):
            RULES.append((tag, ch, list(d['expected_before']), list(d['canonical_after'])))
def sub(seq, s):
    n = len(s); return [i for i in range(len(seq) - n + 1) if seq[i:i + n] == s]
fix = {}
for tag, ch, wrong, right in RULES:
    for c, sp in table.items():
        at = sub(sp, wrong)
        if not at: continue
        ns = list(sp)
        for i in reversed(at): ns[i:i + len(wrong)] = right
        prev = fix.get(c, (sp, None))[0]
        fix[c] = (prev, ns, fix.get(c, (None, None, []))[2] + [ch] if len(fix.get(c, ())) > 2 else [ch])
        table[c] = ns     # 允许多条规则叠加命中同一个字
print('═' * 80)
print('漏传播的字：逐字影响面（共 %d 个）' % len(fix))
print('═' * 80)
print('%-3s %-6s %-7s %-34s %-34s %s' % ('字', '来源', '字频', '现拆分', '订正后', '编码'))
chg = []
for c in sorted(fix, key=lambda x: (-freq.get(x, 0), x)):
    old, new, rules = fix[c][0], table[c], fix[c][2] if len(fix[c]) > 2 else []
    a0, a1, b0, b1 = old[0], old[-1], new[0], new[-1]
    if (a0, a1) == (b0, b1):
        mark = '不变'
    else:
        cur = codes.get(c, [])
        full = [x for x in cur if len(x) == 4]
        exp = (full[0][:2] + KEY.get(b0, '?') + KEY.get(b1, '?')) if full else '?'
        mark = '%s → %s' % (','.join(cur) or '（不在主表）', exp)
        chg.append((c, cur, exp, a0, b0, a1, b1))
    print('%-3s %-6s %-7s %-34s %-34s %s'
          % (c, origin.get(c, '?'), freq.get(c, '—'), ' ＋ '.join(old)[:32], ' ＋ '.join(new)[:32], mark))
print('\n首末根有变、需要改码的：%d 个' % len(chg))
for c, cur, exp, a0, b0, a1, b1 in chg:
    print('  %s  首根 %s(%s)→%s(%s)  末根 %s(%s)→%s(%s)  %s → %s'
          % (c, a0, KEY.get(a0, '?'), b0, KEY.get(b0, '?'), a1, KEY.get(a1, '?'), b1, KEY.get(b1, '?'), ','.join(cur), exp))
if not chg: print('  无——全部部件都在字中间，编码不受影响。')
# 第二类：部件本字不符，看是不是同组别名
print('\n' + '═' * 80)
print('第二类核对：部件本字与登记不符的 4 条，是真错还是同组别名')
print('═' * 80)
cs = yaml.safe_load(open(R + '/人工规范拆分_待验收.yaml', encoding='utf-8')).get('component_splits') or {}
for ch in ('万', '每', '虍', '武'):
    if ch not in cs or ch not in table: continue
    reg, cur = list(cs[ch]), table[ch]
    print('\n  %s  登记 %s' % (ch, ' ＋ '.join(reg)))
    print('     现行 %s' % ' ＋ '.join(cur))
    if len(reg) != len(cur):
        print('     根数不同（%d vs %d）——登记可能已被根集变动作废' % (len(reg), len(cur)))
        for x in set(reg) | set(cur):
            print('       %-4s 键 %-2s 组 %s' % (x, KEY.get(x, '—'), GRP.get(x, '—')))
        continue
    for a, b in zip(reg, cur):
        if a == b: continue
        same = GRP.get(a) == GRP.get(b) and GRP.get(a) is not None
        print('     %s(键%s 组%s)  vs  %s(键%s 组%s)  → %s'
              % (a, KEY.get(a, '—'), GRP.get(a, '—'), b, KEY.get(b, '—'), GRP.get(b, '—'),
                 '同组，仅根名差异，不影响编码' if same else '不同组，影响编码'))
json.dump({'漏传播': {c: {'现': fix[c][0], '订正': table[c]} for c in fix},
           '需改码': [{'字': c, '现码': cur, '应有码': exp} for c, cur, exp, *_ in chg]},
          open(H + '/影响面.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/影响面.json' % H)
