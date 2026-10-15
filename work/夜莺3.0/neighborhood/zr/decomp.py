import json, collections, os
M = json.load(open('eval/box/combo.json'))
fr = []
for l in open('eval/box/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2: fr.append((p[0], float(p[1])))
def book(path):
    pos = collections.Counter(); best = {}
    for l in open(path, encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) < 2 or len(p[0]) != 1: continue
        k = pos[p[1]]; pos[p[1]] += 1
        if p[0] not in best or (len(p[1]), k) < (len(best[p[0]][0]), best[p[0]][1]): best[p[0]] = (p[1], k)
    return best
H = os.path.expanduser('~/Downloads/')
T = [('小鹤NB46', 'runs/zr_probe/n30/table/夜桜_小鹤_n30_普通单字表.txt'), ('小鹤3.1正式', 'release/tables/普通单字表.txt'),
     ('自然码原样', H + '夜桜_NB46自然码_普通单字表.txt'), ('精修16组', H + '夜桜_精修16组_普通单字表.txt')]
SEL = " ;'456789"
R = {}
for name, path in T:
    b = book(path); out = {}
    for rng, lo, hi in (('1-300', 0, 300), ('301-500', 300, 500), ('501-1500', 500, 1500), ('1-1500', 0, 1500)):
        st = collections.defaultdict(float); W = 0
        for ch, f in fr[lo:hi]:
            c, k = b[ch]; t = c + (SEL[min(k, 8)] if (len(c) < 4 or k) else '')
            W += f
            for i in range(len(t) - 1):
                kind = '→空格' if i == len(t) - 2 and len(t) > len(c) else ['1→2', '2→3', '3→4'][i]
                d = M[t[i:i + 2]]
                st[kind, 'eq'] += f * d['eq']; st[kind, 'n'] += f; st[kind, 'ms'] += f * d['ms']; st[kind, 'pd'] += f * d['pd']
        out[rng] = {k: v / W for k, v in st.items()}
    R[name] = out
json.dump({n: {r: {f'{a}|{b}': v for (a, b), v in d.items()} for r, d in o.items()} for n, o in R.items()},
          open('/private/tmp/claude-501/-Users-ice2447/cacdc25d-6532-4fe0-8bff-3d8b12941232/scratchpad/decomp.json', 'w'), ensure_ascii=False)
for rng in ('1-300', '301-500', '501-1500', '1-1500'):
    print('==', rng)
    print('  方案        字均当量 | 各段当量贡献（每字）：1→2  2→3  3→4  →空格 | 大跨排(每千字)：1→2 2→3 3→4 空格 | 小指干扰(每千字)：同')
    for name, _ in T:
        o = R[name][rng]; K = ['1→2', '2→3', '3→4', '→空格']
        tot = sum(o.get((k, 'eq'), 0) for k in K)
        print(f"  {name:8s} {tot:.4f} | " + ' '.join(f"{o.get((k,'eq'),0):.4f}" for k in K)
              + ' | ' + ' '.join(f"{1000*o.get((k,'ms'),0):5.1f}" for k in K) + ' | ' + ' '.join(f"{1000*o.get((k,'pd'),0):5.1f}" for k in K))
