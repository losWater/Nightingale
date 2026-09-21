# -*- coding: utf-8 -*-
"""人工拆分规则的传播审计（2026-09-21 你要：查还有没有像「曲」那样的问题）。只读。

曲的问题本质：给一个部件定了规范拆法，但只落到本字，没传播到含它的字。
好在这类规则都登记在 重开工程/02_规范拆分/ 下，且每条都同时记了
「错的形式」与「对的形式」，所以可以反过来查——
**拿每条规则的「错的形式」去现行拆分表里搜，搜到就是漏传播。**

四份规则来源：
  传播式整字结构覆写_待验收.yaml   chai_sequence → canonical_sequence（交叉借笔类）
  正式字架规则.yaml                guarded_rewrites: expected_before → canonical_after
  正式历史结构裁决规则.yaml        guarded_rewrites: expected_before → canonical_after
  人工规范拆分_待验收.yaml         component_splits: 部件 → 规范根序列（无「错形式」，只核对本字）
现行拆分表 = 55（通用规范 8105）+ 112（扩展 7391）= 15496 字。

自测：先拿 139 的修复前备份跑一遍，必须能报出「曲」那 24 个字；报不出说明方法无效。
"""
import io, sys, os, csv, json, yaml, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
def _auth():
    """现行拆分以啾啾工具箱·拆分查询为准（55/112 已冻结，2026-09-21）"""
    import re as _re
    s = open(W + '/65_群友离线工具包/夜莺啾啾工具箱.html', encoding='utf-8-sig').read()
    v = json.JSONDecoder().raw_decode(s[_re.search(r'\b(?:const|let) views\s*=\s*', s).end():])[0]['query']
    D = json.JSONDecoder().raw_decode(v[_re.search(r'\bconst D\s*=\s*', v).end():])[0]
    return {c: r['新拆'].split(' ＋ ') for c, r in D.items()}
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); R = os.path.dirname(W) + '/重开工程/02_规范拆分'
SELFTEST = '--selftest' in sys.argv[1:]

def load_table(paths):
    t = {}
    for p in paths:
        if not os.path.exists(p): continue
        for r in csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'):
            t[r['汉字']] = r['完整拆分'].split(' ＋ ')
    return t

LIVE = [W + '/55_拆分继承核验/当前完整拆分表.txt', W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt']
BAK = [W + '/139_曲根拆分订正/备份/20260921195750_通用规范_当前完整拆分表.txt',
       W + '/139_曲根拆分订正/备份/20260921195750_扩展字_夜莺2.0扩展字拆分表.txt']
table = load_table(BAK) if SELFTEST else _auth()   # 现行拆分以啾啾工具箱为准（55/112 已冻结）
print('拆分表 %d 字%s\n' % (len(table), '（修复前备份，自测模式）' if SELFTEST else ''))

def rules():
    out = []
    p = R + '/传播式整字结构覆写_待验收.yaml'
    if os.path.exists(p):
        for ch, d in (yaml.safe_load(open(p, encoding='utf-8')).get('propagating_structural_overrides') or {}).items():
            if d.get('chai_sequence') and d.get('canonical_sequence'):
                out.append(('传播式覆写', ch, d['chai_sequence'], d['canonical_sequence'], d.get('expected_family_examples') or []))
    for fn, tag in (('正式字架规则.yaml', '字架规则'), ('正式历史结构裁决规则.yaml', '历史结构裁决')):
        p = R + '/' + fn
        if not os.path.exists(p): continue
        for ch, d in (yaml.safe_load(open(p, encoding='utf-8')).get('guarded_rewrites') or {}).items():
            if d.get('expected_before') and d.get('canonical_after'):
                out.append((tag, ch, d['expected_before'], d['canonical_after'], []))
    return out

def find_sub(seq, sub):
    n = len(sub)
    return [i for i in range(len(seq) - n + 1) if seq[i:i + n] == sub]

RS = rules()
print('载入规则 %d 条（带「错形式」的）\n' % len(RS))
print('═' * 78)
print('一、漏传播排查：现行表里还有哪些字用着规则明令撤销的旧形式')
print('═' * 78)
bad = []
for tag, ch, wrong, right, fam in RS:
    hits = [c for c, sp in table.items() if find_sub(sp, wrong)]
    if not hits: continue
    # 本字用对了吗
    own = ' ＋ '.join(table.get(ch, [])) if ch in table else '（不在表）'
    bad.append((tag, ch, wrong, right, hits, own))
    print('\n【%s · %s】' % (tag, ch))
    print('  应撤销的旧形式  %s' % ' ＋ '.join(wrong))
    print('  规范形式        %s' % ' ＋ '.join(right))
    print('  本字现在是      %s  %s' % (own, '✓' if find_sub(table.get(ch, []), right) else '✗ 本字也没改'))
    print('  仍在用旧形式的字 %d 个：%s' % (len(hits), '、'.join(hits[:30]) + ('…' if len(hits) > 30 else '')))
if not bad: print('\n  没有发现漏传播的规则 ✓')
print('\n' + '═' * 78)
print('二、部件规范拆分：本字是否与登记一致')
print('═' * 78)
p = R + '/人工规范拆分_待验收.yaml'
cs = (yaml.safe_load(open(p, encoding='utf-8')).get('component_splits') or {}) if os.path.exists(p) else {}
mism = []
for ch, seq in cs.items():
    cur = table.get(ch)
    if cur is None: print('  %-3s 登记 %-20s 不在拆分表' % (ch, ' ＋ '.join(seq))); continue
    ok = cur == list(seq)
    if not ok: mism.append((ch, seq, cur))
    print('  %-3s 登记 %-20s 现行 %-24s %s' % (ch, ' ＋ '.join(seq), ' ＋ '.join(cur), '✓' if ok else '✗'))
print('\n  共 %d 条，本字不一致 %d 条' % (len(cs), len(mism)))
json.dump({'模式': '自测' if SELFTEST else '现行', '规则数': len(RS),
           '漏传播': [{'来源': t, '字': c, '旧形式': w, '规范形式': r, '命中': h} for t, c, w, r, h, _ in bad],
           '部件本字不一致': [{'字': c, '登记': list(s), '现行': v} for c, s, v in mism]},
          open(H + ('/自测结果.json' if SELFTEST else '/审计结果.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s' % (H + ('/自测结果.json' if SELFTEST else '/审计结果.json')))
