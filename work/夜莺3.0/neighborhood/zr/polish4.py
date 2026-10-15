"""第四轮精修（2026-10-13）：按实际最短码压形部大跨排/小指干扰（测评站口径，扣掉 1→2），目标 ≤ 夜莺3.1 的 25/15。
每步先实际出表，取测评站字表（形码盒子默认字频）前1500 字的最短码长度与音节，扫描候选时按新布局重算 2→3（与四码字的 3→4）。
另加：测评站字表前1500 键位相关全码重 ×5、换键组数 ×1（鼓励撤回不必要的换键）。其余同第三轮。
用法：../../.venv/bin/python polish4.py <起点 json> <起点步> <最多步数> <输出名>"""
import collections, glob, json, os, subprocess, sys
import polish3 as P
import common as C
KEYS = P.KEYS; ROOT = C.ROOT; INP = C.E.INP
fr = [p[0] for p in (l.rstrip('\n').split('\t') for l in open(ROOT / 'eval/box/默认字频.txt', encoding='utf-8-sig')) if len(p) >= 2][:1500]
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
g_of = {r: g for g, rs in C.E.META['groups'].items() for r in rs}
ROOTS = {c: (g_of[splits[c][0][0]], g_of[splits[c][-1][0]]) for c in fr if c in splits}
MS0, PD0 = 25, 15


def build_table(lay, d):
    d = Path(d); subprocess.run(['rm', '-rf', str(d)]); d.mkdir(parents=True)
    cfg = json.load(open(INP / 'run.json', encoding='utf-8')); cfg['form'] = json.loads(json.dumps(C.NB46)); cfg['form']['mapping'].update(lay)
    json.dump(cfg, open(d / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.run([str(C.E.ENGINE), 'encode', 'run.json', '-e', str(INP / 'elements.yaml'), '-k', str(INP / 'distribution.txt'),
                    '-p', str(INP / 'equivalence.txt')], cwd=d, env=C.E.ENV, capture_output=True, check=True)
    env = dict(os.environ, YZ_INP=INP.name, YZ_FIX=str(ROOT / 'data/inputs/一二简.json'))
    subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'build/make_plain_table.py'), str(d), str(d / 'table'), 'ziranma'],
                   env=env, check=True, capture_output=True)
    return glob.glob(str(d / 'table/*.txt'))[0]


from pathlib import Path


def site_basis(table):
    """测评站字表前1500 字：最短码 (音节2码, 码长)、最长码音节；只保留能按根组重算的字。"""
    codes = collections.defaultdict(list)
    for l in open(table, encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2 and len(p[0]) == 1: codes[p[0]].append(p[1])
    B = []
    for c in fr:
        if c not in ROOTS or c not in codes: continue
        s = min(codes[c], key=len); L = max(codes[c], key=len)
        B.append((c, s[:2], len(s), L[:2]))
    return B


def site_feel(lay, B):
    ms = pd = 0; full = collections.defaultdict(set)
    for c, sy, n, lsy in B:
        g3, g4 = ROOTS[c]; k3, k4 = lay[g3], lay[g4]
        if n >= 3:
            ms += P.MS[sy[1] + k3]; pd += P.PD[sy[1] + k3]
        if n == 4:
            ms += P.MS[k3 + k4]; pd += P.PD[k3 + k4]
        full[lsy + k3 + k4].add((lsy, g3, g4))
    dup = sum(len(v) - 1 for v in full.values() if len(v) > 1)
    return ms, pd, dup


def evaluate(w, lay, B):
    r = P.evaluate(w, lay); r['sms'], r['spd'], r['sdup'] = site_feel(lay, B); return r


def F(r):
    return (P.F(r) - 5 * max(0, r['ms'] - P.MS0) - 5 * max(0, r['pd'] - P.PD0) - 0.3 * (r['ms'] + r['pd'])   # 换掉第三轮的全码代理手感
            + 5 * max(0, r['sms'] - MS0) + 5 * max(0, r['spd'] - PD0) + 0.5 * (r['sms'] + r['spd'])
            + 5 * r['sdup'] + 1.0 * r['nb_moved'])


def line(r):
    return P.line(r) + f" 站形部大跨{r['sms']} 站形部小指{r['spd']} 站全码重(键位){r['sdup']}"


if __name__ == '__main__':
    src, st, MAXSTEP, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    cur = dict({c['step']: c for c in json.load(open(src, encoding='utf-8'))}[st]['layout'])
    w = C.Worker()
    B = site_basis(build_table(cur, f'pts/{OUT}_work')); r = evaluate(w, cur, B); f = F(r)
    log = open(f'{OUT}.log', 'w')
    def say(*a):
        print(*a, flush=True); print(*a, file=log, flush=True)
    say('起点', f'F={f:.2f}', line(r))
    curve = [{'step': 0, 'F': f, 'layout': dict(cur), 'line': line(r)}]
    for step in range(1, MAXSTEP + 1):
        cands = []
        for g in C.G:
            for k in KEYS:
                if k != cur[g]:
                    lay = dict(cur); lay[g] = k
                    cands.append((F(evaluate(w, lay, B)) - f, g, k))
        cands.sort()
        mv = None
        for d, g, k in cands[:30]:          # 候选按当前最短码估算；出表复核后取第一个真改进的
            if d >= -0.3: break
            lay = dict(cur); lay[g] = k
            B2 = site_basis(build_table(lay, f'pts/{OUT}_work')); r2 = evaluate(w, lay, B2)
            if F(r2) < f - 0.3:
                mv, B, r, f = (g, k), B2, r2, F(r2); break
        if mv is None:
            say('无复核通过的改进，结束'); break
        before = cur[mv[0]]; cur[mv[0]] = mv[1]
        say(f"步{step} {C.NAME[mv[0]]} {before}→{mv[1]} F={f:.2f} " + line(r))
        curve.append({'step': step, 'F': f, 'layout': dict(cur), 'line': line(r), 'moves': [mv]})
        json.dump(curve, open(f'{OUT}.json', 'w', encoding='utf-8'), ensure_ascii=False)
