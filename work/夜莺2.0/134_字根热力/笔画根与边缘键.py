# -*- coding: utf-8 -*-
"""验群友补充的两条学说（2026-09-17）：
  甲「夜莺字根多，拆笔画的情况没那么多，所以笔画根到 p 并没有问题」——群友江畔寻花2012
  乙「总体上来看，边缘按键的使用率还是少的」——群友 二阶堂希罗的鲸
  丙「字根数量也是一个重要的环节，要看字根多造成了多大的影响」——群主

测法：
  1 笔画根用量占字根总量多少？分严格（十个纯笔画形）与宽口径（加准笔画）。
  2 多少字的码里出现了笔画根？——这才是「拆笔画的情况」有多少。
  3 p 的 6.81% 字根量里，笔画根贡献几成？如果只占小头，那甲说得对：p 的重不是笔画造成的。
  4 边缘键（小指列 q a z p）在键位热力口径与字根口径下的合计用量对照。
  5 字根多的直接后果：平均每个字用几个根位、单根覆盖率。
"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
freq = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq.append((p[0], int(p[1])))
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
skip = {(t, c) for grp in ('容错码', '特殊简码') for c, t in irr[grp].items()}
codes = collections.defaultdict(list); full = {}
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if (t, c) in skip: continue
    codes[t].append(c)
    if len(c) == 4 and t not in full: full[t] = c
best = {t: min(cs, key=lambda c: (len(c), cs.index(c))) for t, cs in codes.items()}
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}
for c, d in D.items():
    for r in d.get('根', []): KEY[r['根']] = r['键']
STRICT = set('一丨丿丶乙横竖撇点折')                      # 纯笔画形
LOOSE = STRICT | set('二三㐅乂丷冫彡丩') | {'𠂇', '𠂆', '𠂉', '⺈', '⺊'}   # 准笔画（两三笔的纯笔形组合）
KEYS = 'abcdefghijklmnopqrstuvwxyz'
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
OUT = {}
for name, n in BANDS:
    press = collections.Counter()            # 键位热力：所有码位
    root = collections.Counter()             # 字根量：第 3、4 位
    st_w = 0; lo_w = 0; tot_r = 0            # 笔画根加权用量
    st_chars = 0; st_cw = 0; tot_c = 0; tot_cw = 0
    p_st = 0; p_lo = 0; p_all = 0
    slots = 0                                # 实际敲到的根位数（加权）
    rootuse = collections.Counter()
    for t, f in freq[:n]:
        c = best.get(t)
        if not c: continue
        tot_c += 1; tot_cw += f
        for ch in c: press[ch] += f
        rs = D.get(t, {}).get('根')
        if len(c) < 3 or not rs: continue
        use = [rs[0]['根']] + ([rs[-1]['根']] if len(c) == 4 else [])
        hit = False
        for i, r in enumerate(use):
            k = KEY.get(r, c[2 + i])
            root[k] += f; tot_r += f; slots += f; rootuse[r] += f
            if r in STRICT: st_w += f; hit = True
            if r in LOOSE: lo_w += f
            if k == 'p':
                p_all += f
                if r in STRICT: p_st += f
                if r in LOOSE: p_lo += f
        if hit: st_chars += 1; st_cw += f
    tp = sum(press.values())
    edge = 'qazp'
    OUT[name] = {
        '笔画根占字根量_严格%': st_w / tot_r * 100, '笔画根占字根量_宽%': lo_w / tot_r * 100,
        '含笔画根的字数%': st_chars / tot_c * 100, '含笔画根的字频%': st_cw / tot_cw * 100,
        'p的字根量%': p_all / tot_r * 100, 'p里笔画根占比_严格%': p_st / p_all * 100 if p_all else 0,
        'p里笔画根占比_宽%': p_lo / p_all * 100 if p_all else 0,
        '边缘键qazp_键位热力%': sum(press[k] for k in edge) / tp * 100,
        '边缘键qazp_字根量%': sum(root[k] for k in edge) / tot_r * 100,
        '平均每字根位': slots / tot_cw, '不同根形数': len(rootuse),
        '键位热力': {k: press[k] / tp * 100 for k in KEYS},
        '字根量': {k: root[k] / tot_r * 100 for k in KEYS},
    }
    print('\n' + '═' * 72)
    print('══════ %s 字 ══════' % name)
    o = OUT[name]
    print('\n【甲：字根多 → 拆笔画少？】')
    print('  笔画根占字根总用量   严格 %.2f%%   宽口径 %.2f%%' % (o['笔画根占字根量_严格%'], o['笔画根占字根量_宽%']))
    print('  码里出现笔画根的字   %.2f%%（按字频 %.2f%%）' % (o['含笔画根的字数%'], o['含笔画根的字频%']))
    print('  实际用到的不同根形   %d 个' % o['不同根形数'])
    print('\n【丙：那 p 的重是笔画造成的吗？】')
    print('  p 的字根量 %.2f%%，其中笔画根 严格 %.1f%%  宽 %.1f%%'
          % (o['p的字根量%'], o['p里笔画根占比_严格%'], o['p里笔画根占比_宽%']))
    print('\n【乙：边缘键（q a z p）整体用量】')
    print('  键位热力口径 %.2f%%      字根口径 %.2f%%  ← 差 %.1f 倍'
          % (o['边缘键qazp_键位热力%'], o['边缘键qazp_字根量%'],
             o['边缘键qazp_字根量%'] / o['边缘键qazp_键位热力%']))
# 笔画根各自的量与所在键
print('\n\n' + '═' * 72)
print('══════ 各笔画根的用量与所在键（前 1500）══════')
n = 1500
cnt = collections.Counter()
tot = 0
for t, f in freq[:n]:
    c = best.get(t); rs = D.get(t, {}).get('根')
    if not c or len(c) < 3 or not rs: continue
    for r in [rs[0]['根']] + ([rs[-1]['根']] if len(c) == 4 else []):
        cnt[r] += f; tot += f
print('根    键   占字根总量')
for r in sorted(LOOSE, key=lambda x: -cnt[x]):
    if cnt[r]: print('  %-4s %s    %5.2f%%%s' % (r, KEY.get(r, '?'), cnt[r] / tot * 100, '   ← 严格笔画' if r in STRICT else ''))
json.dump(OUT, open(H + '/笔画根与边缘键.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/笔画根与边缘键.json' % H)
