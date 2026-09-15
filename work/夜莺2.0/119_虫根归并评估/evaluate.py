# -*- coding: utf-8 -*-
"""群友提议（2026-09-16）：把 虫 从 鸟／虫 组挪走（并入 禸/禺字底 组，或并入 口 组），让 萤(艹冖虫) 与 莺(艹冖鸟) 分开。
按《评估规则》算完整重码：同音（去声调音节）+ 首根同组 + 末根同组 才计一对；新增与消除分列，加权取字对读音已分配频次的较小值。
另列三简容量影响：虫为首根的字换组后，在各音节里与目标组首根字的新竞争。范围 8105 字（字音基准 + 32 字频）。"""
import io, sys, os, json, re, collections, itertools
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; O = W + '/65_群友离线工具包/夜莺2.0离线工具包'; H = os.path.dirname(os.path.abspath(__file__))
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); return json.JSONDecoder().raw_decode(s[m.end():])[0]
D = get(open(O + '/拆分查询.html', encoding='utf-8-sig').read(), 'D')
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
pron = collections.defaultdict(list)
for r in J(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/字音基准.json'):
    syl = re.sub(r'[1-5]$', '', r['拼音']); pron[r['字']].append((syl, r.get('自然频率', r['频率']) or 0))
wt = {r['字']: r['每百万核心字预计次数'] for r in J(W + '/32_多来源字频重建/试验整字频率.json')['字表']}
chars = [c for c in D if D[c]['排名'] is not None and c in pron]
def groups(move):   # move: {根名: 新组名}
    g = {}
    for c in chars:
        rs = D[c]['根']; f, l = rs[0], rs[-1]
        g[c] = (move.get(f['根'], f['组']), move.get(l['根'], l['组']))
    return g
def conflicts(g):
    """返回 {(音节, 字a, 字b): 加权} 完整重码对（同一无序字对同音节只算一次）"""
    out = {}
    by = collections.defaultdict(list)
    for c in chars:
        for syl, fq in pron[c]: by[(syl, g[c][0], g[c][1])].append((c, fq))
    for (syl, _, _), lst in by.items():
        for (a, fa), (b, fb) in itertools.combinations(sorted(set(lst)), 2):
            if a == b: continue
            k = (syl, min(a, b), max(a, b))
            out[k] = max(out.get(k, 0), min(fa or wt.get(a, 0), fb or wt.get(b, 0)))
    return out
base = conflicts(groups({}))
def first_groups(g):
    by = collections.defaultdict(set)
    for c in chars:
        for syl, fq in pron[c]: by[(syl, g[c][0])].add(c)
    return by
rep = {'基线完整重码对': len(base)}
lines = ['# 虫根归并评估（2026-09-16）', '', '规则：同音（去声调）+ 首根同组 + 末根同组 = 完整重码；新增/消除分列，加权 = 字对读音频次较小值。范围 8105 字。', '', '基线完整重码对：%d' % len(base), '']
ROOTS = get(open(O + '/拆分查询.html', encoding='utf-8-sig').read(), 'ROOTS'); grp = {r['根']: r['组'] for r in ROOTS}
members = collections.defaultdict(list)
for r in ROOTS: members[r['组']].append(r['根'])
BIRDS = [x for x in members[grp['鸟']] if x != '虫' and x != '𠀐']   # 鸟、鸟省、乌、鳥
lines += ['鸟／虫 组成员：' + '、'.join(members[grp['鸟']]) + '；鸟系 = ' + '、'.join(BIRDS), '']
scen = [('虫 → 禸组（与 禺字底 同组）', {'虫': grp['禺字底']}), ('虫 → 口组', {'虫': grp['口']}), ('虫 + 𠀐 → 禸组', {'虫': grp['禺字底'], '𠀐': grp['禺字底']})]
for label, tgt in [('兔象', '兔'), ('牛马', '牛'), ('龙', '龙'), ('羊', '羊')]:
    if tgt in grp: scen.append(('鸟系 → %s组（%s）' % (label, grp[tgt]), {b: grp[tgt] for b in BIRDS}))
    else: lines.append('（找不到根 %s）' % tgt)
for name, move in scen:
    g = groups(move); after = conflicts(g)
    new = {k: v for k, v in after.items() if k not in base}; gone = {k: v for k, v in base.items() if k not in after}
    fg0, fg1 = first_groups(groups({})), first_groups(g)
    # 三简竞争：虫为首根的字，换组后同音节新遇到的首根同组字数
    comp_new, comp_gone = [], []
    for c in chars:
        if D[c]['根'][0]['根'] in move:
            for syl, fq in pron[c]:
                before = fg0[(syl, groups({})[c][0])] - {c}; now = fg1[(syl, g[c][0])] - {c}
                if now - before: comp_new.append((c, syl, ''.join(sorted(now - before))))
                if before - now: comp_gone.append((c, syl, ''.join(sorted(before - now))))
    rep[name] = {'新增完整重码': len(new), '新增加权': round(sum(new.values()), 1), '消除完整重码': len(gone), '消除加权': round(sum(gone.values()), 1),
                 '新增明细': sorted([(k[0], k[1], k[2], round(v, 1)) for k, v in new.items()], key=lambda t: -t[3]),
                 '消除明细': sorted([(k[0], k[1], k[2], round(v, 1)) for k, v in gone.items()], key=lambda t: -t[3]),
                 '三简新竞争': comp_new, '三简解除竞争': comp_gone}
    lines += ['## %s' % name, '', '- 新增完整重码 %d 对（加权 %.1f）；消除 %d 对（加权 %.1f）' % (len(new), sum(new.values()), len(gone), sum(gone.values())),
              '- 新增：' + ('、'.join('%s/%s(%s,%.0f)' % (a, b, s, v) for s, a, b, v in rep[name]['新增明细'][:30]) or '无'),
              '- 消除：' + ('、'.join('%s/%s(%s,%.0f)' % (a, b, s, v) for s, a, b, v in rep[name]['消除明细'][:30]) or '无'),
              '- 三简新竞争（虫首根字 → 同音节新遇到的同组首根字）%d 处：' % len(comp_new) + ('；'.join('%s(%s)↔%s' % t for t in comp_new[:40]) or '无'),
              '- 三简解除竞争 %d 处：' % len(comp_gone) + ('；'.join('%s(%s)↔%s' % t for t in comp_gone[:40]) or '无'), '']
# ===== 键位层复核（你指出：土 与 禸 同在 q，虫→禸组后 萤 ykmq 撞 茔）：同音 + 首键同 + 末键同 = 实际全码重码
KEY = {r['根']: r['键'] for r in ROOTS}
def keys_of(move_key):   # move_key: {根名: 新键}
    g = {}
    for c in chars:
        rs = D[c]['根']; f, l = rs[0]['根'], rs[-1]['根']
        g[c] = (move_key.get(f, KEY[f]), move_key.get(l, KEY[l]))
    return g
kbase = conflicts(keys_of({}))
lines += ['', '# 键位层复核（同音 + 首键同 + 末键同，反映实际全码重码）', '', '基线实际全码重码对：%d' % len(kbase), '']
kscen = [('虫 → q（禸组键）', {'虫': KEY['禺字底']}), ('虫 → t（口组键）', {'虫': KEY['口']})]
for label, tgt in [('兔象', '兔'), ('牛马', '牛'), ('龙', '龙'), ('羊', '羊')]:
    kscen.append(('鸟系 → %s（%s组键）' % (KEY[tgt], label), {b: KEY[tgt] for b in BIRDS}))
rep['键位层'] = {'基线': len(kbase)}
for name, mk in kscen:
    after = conflicts(keys_of(mk)); new = {k: v for k, v in after.items() if k not in kbase}; gone = {k: v for k, v in kbase.items() if k not in after}
    rep['键位层'][name] = {'新增': len(new), '新增加权': round(sum(new.values()), 1), '消除': len(gone), '消除加权': round(sum(gone.values()), 1),
                        '新增明细': sorted([(k[0], k[1], k[2], round(v, 1)) for k, v in new.items()], key=lambda t: -t[3]), '消除明细': sorted([(k[0], k[1], k[2], round(v, 1)) for k, v in gone.items()], key=lambda t: -t[3])}
    lines += ['## %s' % name, '', '- 新增 %d 对（加权 %.1f）；消除 %d 对（加权 %.1f）' % (len(new), sum(new.values()), len(gone), sum(gone.values())),
              '- 新增：' + ('、'.join('%s/%s(%s,%.0f)' % (a, b, s_, v) for s_, a, b, v in rep['键位层'][name]['新增明细'][:30]) or '无'),
              '- 消除：' + ('、'.join('%s/%s(%s,%.0f)' % (a, b, s_, v) for s_, a, b, v in rep['键位层'][name]['消除明细'][:30]) or '无'), '']
json.dump(rep, open(H + '/评估结果.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(H + '/评估结果.md', 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
