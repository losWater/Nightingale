"""给定字根布局，精确求一简/二简/三简的最优分配（最小化按字频加权的打字当量）。

模型（读音即字，8105 字全部读音，夜桜字音基准频率）：
- 成本：一简 c1␣；二简 c1c2␣；三简 c1c2c3␣；全码 c1c2c3c4（同码非首选加选重键）。按键对当量求和。
- 二码位每位至多 1 字；2.5 留给词的二码位（含 嗯 en）不给单字。
- 每个音节独立：枚举二简归属；其余读音按 前缀（音节+首根键）分组，每组取“三简收益 f×(全码成本−三简成本)”最大者拿三简；
  其余打全码，同全码者按频率排候选。
- 一简：每个字母在前 K 个候选中枚举，联动重算其音节。
用法：python eval/opt_short.py [布局: 2.5 | <运行目录>]
"""
import json, sys, collections
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode
C = json.load(open(ROOT / 'eval/box/combo.json'))
EQ = lambda s: sum(C[s[i:i + 2]]['eq'] for i in range(len(s) - 1))
SEL = " ;'456789"
K1 = 40


def load_readings():
    B = json.load(open(ROOT / 'data/inputs/夜桜字音基准.json', encoding='utf-8'))
    return [(r['字'], r['拼音'], r['自然频率']) for r in B if r['自然频率'] > 0 or True]


def layout_keys(which):
    sp = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
    if which == '2.5':
        rk = json.load(open(ROOT / 'data/baseline/root_key.json', encoding='utf-8'))
        return lambda ch: rk[sp[ch][0][0]] + rk[sp[ch][-1][0]]
    meta = json.load(open(ROOT / 'build/out/formal/meta.json', encoding='utf-8'))
    g_of = {r: g for g, rs in meta['groups'].items() for r in rs}
    out = sorted(Path(which).glob('output-*'))[0]
    m = yaml.load(open(out / 'config.yaml', encoding='utf-8'), Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))['form']['mapping']
    return lambda ch: m[g_of[sp[ch][0][0]]] + m[g_of[sp[ch][-1][0]]]


def reserved_two():
    N25 = Path.home() / 'Nightingale/夜莺2.5/产物'
    single2 = {l.split('\t')[1].strip() for l in open(N25 / '普通单字表.txt', encoding='utf-8-sig')
               if '\t' in l and len(l.split('\t')[0]) == 1 and len(l.split('\t')[1].strip()) == 2}
    res = set()
    for l in open(N25 / '综合字词表.txt', encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) == 2 and len(p[1]) == 2 and len(p[0]) >= 2 and p[1] not in single2:
            res.add(p[1])
    res.add('en')
    return res


class Model:
    def __init__(self, which='2.5', scheme='xiaohe'):
        tail = layout_keys(which)
        self.R = []                      # (字, 拼音, 频率, 音节码, 全码)
        for ch, py, f in load_readings():
            sy = encode(py, scheme)
            self.R.append((ch, py, f, sy, sy + tail(ch)))
        self.by_syl = collections.defaultdict(list)
        for i, r in enumerate(self.R):
            self.by_syl[r[3]].append(i)
        self.reserved = reserved_two()
        self.cost_full_base = {i: EQ(r[4]) for i, r in enumerate(self.R)}

    def syllable_cost(self, syl, excluded=frozenset(), two=None):
        """给定音节、已排除（拿了一简）的读音、二简归属，返回 (成本和, 分配{读音: 码})"""
        idx = [i for i in self.by_syl[syl] if i not in excluded]
        cost, assign = 0.0, {}
        if two is not None:
            cost += self.R[two][2] * EQ(syl + ' ')
            assign[two] = syl
            idx = [i for i in idx if i != two]
        groups = collections.defaultdict(list)
        for i in idx:
            groups[self.R[i][4][:3]].append(i)
        rest = []
        for p, g in groups.items():
            best = max(g, key=lambda i: self.R[i][2] * (self.cost_full_base[i] - EQ(p + ' ')))
            cost += self.R[best][2] * EQ(p + ' ')
            assign[best] = p
            rest += [i for i in g if i != best]
        full = collections.defaultdict(list)
        for i in rest:
            full[self.R[i][4]].append(i)
        for code, g in full.items():
            g.sort(key=lambda i: -self.R[i][2])
            for k, i in enumerate(g):
                typed = code + (SEL[min(k, 8)] if k > 0 else '')
                cost += self.R[i][2] * EQ(typed)
                assign[i] = typed
        return cost, assign

    def best_syllable(self, syl, excluded=frozenset()):
        cands = [None]
        if syl not in self.reserved:
            cands += [i for i in self.by_syl[syl] if i not in excluded]
        best = None
        for two in cands:
            c, a = self.syllable_cost(syl, excluded, two)
            if best is None or c < best[0]:
                best = (c, a, two)
        return best

    def solve(self, fixed_one=None, fixed_two=None):
        """fixed_one: {字母: 读音序号}，fixed_two: {音节: 读音序号}；为 None 时优化。返回 (总成本, 一简, 二简, 分配)"""
        letters = sorted({s[0] for s in self.by_syl})
        base = {s: self.best_syllable(s) for s in self.by_syl} if fixed_two is None else None
        one, total, assign_all, two_map = {}, 0.0, {}, {}
        used_syl = {}
        for L in letters:
            syls = [s for s in self.by_syl if s[0] == L]
            if fixed_one is not None:
                cands = [fixed_one.get(L)]
            else:
                pool = sorted((i for s in syls for i in self.by_syl[s]), key=lambda i: -self.R[i][2])[:K1]
                cands = [None] + pool
            best = None
            for x in cands:
                c = 0.0 if x is None else self.R[x][2] * EQ(L + ' ')
                parts = {}
                for s in syls:
                    exc = frozenset([x]) if x is not None and self.R[x][3] == s else frozenset()
                    if fixed_two is not None:
                        t = fixed_two.get(s)
                        if t is not None and t in exc:
                            t = None
                        r = (*self.syllable_cost(s, exc, t), t)
                    elif exc:
                        r = self.best_syllable(s, exc)
                    else:
                        r = base[s]
                    c += r[0]
                    parts[s] = r
                if best is None or c < best[0]:
                    best = (c, x, parts)
            c, x, parts = best
            total += c
            if x is not None:
                one[L] = x
                assign_all[x] = L
            for s, (sc, a, t) in parts.items():
                assign_all.update(a)
                if t is not None:
                    two_map[s] = t
        return total, one, two_map, assign_all


def current_25(model):
    fixed = json.load(open(ROOT / 'data/inputs/2.5一二简固定.json', encoding='utf-8'))['fixed']
    idx = {(r[0], r[1]): i for i, r in enumerate(model.R)}
    one, two = {}, {}
    for ch, py, n in fixed:
        i = idx[(ch, py)]
        if n == 1:
            one[model.R[i][3][0]] = i
        else:
            two[model.R[i][3]] = i
    return one, two
