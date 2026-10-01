"""夜桜门禁检查（独立于引擎，读 code.txt + 输入目录的 elements/meta/run）。
用法：python build/gates.py <输入目录> <code.txt> [--baseline <基线 code.txt>]"""
import json, sys, collections, argparse
from pathlib import Path
import yaml

_L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


def setup(inp):
    global INP, E, meta, cfg, N
    INP = Path(inp)
    E = yaml.load(open(INP / 'elements.yaml', encoding='utf-8'), Loader=_L)
    meta = json.load(open(INP / 'meta.json', encoding='utf-8'))
    cfg = json.load(open(INP / 'run.json', encoding='utf-8'))
    N = sum(1 for e in E if e['拼音'] != 'reserved')
EQ = {}
for l in open(Path(__file__).resolve().parent.parent / 'data/inputs/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    try: EQ[p[0]] = float(p[1])
    except (IndexError, ValueError): pass


def read_codes(path):
    rows = [l.rstrip('\n').split('\t') for l in open(path, encoding='utf-8')]
    return [(r[1], int(r[2]), r[3], int(r[4])) for r in rows[:N]]


def sig(e):   # 键位无关签名：音节 + 首末根组
    s = e['元素序列']
    return (s[0]['element'], s[1]['element'], s[2]['element'], s[3]['element'])


def analyse(codes):
    by_code = collections.defaultdict(list)
    for i, (full, _, _, _) in enumerate(codes):
        by_code[full].append(i)
    exempt = lambda i: any(j != i and sig(E[j]) == sig(E[i]) for j in by_code[codes[i][0]])
    # 实际选重口径（作者 2026-10-01）：只看必须打全码的读音；有一二三简的读音在全码位让位，不参与
    ft = lambda i: not (0 < len(codes[i][2]) < len(codes[i][0]))
    def effective(idx):
        return [i for i in idx if ft(i) and any(j < i and ft(j) and sig(E[j]) != sig(E[i]) for j in by_code[codes[i][0]])]
    def non_exclusive(idx):
        bad, ex = [], []
        for i in idx:
            others = [j for j in by_code[codes[i][0]] if j != i]
            if others:
                (ex if all(sig(E[j]) == sig(E[i]) for j in others) else bad).append(i)
        return bad, ex
    T = {int(k): v for k, v in meta['tier_indices'].items()}
    b1500, e1500 = non_exclusive(T[1500])
    b3500, e3500 = non_exclusive(T[3500])
    three = sum(1 for i in T[6000] if 0 < len(codes[i][2]) <= 3 or len(codes[i][0]) <= 3)
    pairs = sum(len(v) * (len(v) - 1) // 2 for v in by_code.values())
    use = collections.Counter()
    eq34 = w = 0.0
    for i, (full, *_ ) in enumerate(codes):
        f = E[i]['频率']
        use[full[2]] += f; use[full[3]] += f
        eq34 += f * EQ.get(full[2:4], 1.3); w += f
    rank = sorted(use, key=lambda k: -use[k])
    idx = {(e['词'], e['拼音']): i for i, e in enumerate(E)}
    chong_niao_same = codes[idx[('虫', 'chong')]][0][2] == codes[idx[('鸟', 'niao')]][0][2]
    f1500, f3500 = effective(T[1500]), effective(T[3500])
    return dict(前1500有效重码=len(f1500), 前3500有效重码=len(f3500), 前3500有效重码字=[E[i]['词'] + E[i]['拼音'] for i in f3500],
                前1500非独占=len(b1500), 前1500豁免=len(e1500), 前1500违例=[E[i]['词'] + E[i]['拼音'] for i in b1500[:20]],
                前3500非独占=len(b3500), 前3500豁免=len(e3500), 前6000三码内=three, 全表重码对=pairs,
                p排名=rank.index('p') + 1, 三四码前五=[(k, round(use[k] / (2 * w), 4)) for k in rank[:5]],
                三四码当量=round(eq34 / w, 4), 虫鸟同键=chong_niao_same)


_BASE = {}


def check(code, baseline=None):
    r = analyse(read_codes(code))
    if baseline:
        if baseline not in _BASE:
            _BASE[baseline] = analyse(read_codes(baseline))
        b = _BASE[baseline]
        r['门禁'] = {'前1500有效无重': r['前1500有效重码'] == 0, '前3500有效重码个位数': r['前3500有效重码'] <= 9,
               '前6000三码损失≤100': b['前6000三码内'] - r['前6000三码内'] <= 100,
               '重码对增加≤20': r['全表重码对'] - b['全表重码对'] <= 20, 'p不进前20': r['p排名'] > 20,
               '虫鸟不同键': not r['虫鸟同键']}
    return r


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('code'); ap.add_argument('--baseline')
    a = ap.parse_args()
    setup(a.inp)
    print(json.dumps(check(a.code, a.baseline), ensure_ascii=False, indent=1))
