"""构造法（作者 2026-10-01 设想）：不退火，按首根/末根两阶段逐组放键。
权重：读音按音节分组，组内按字频排名做幂律衰减（1/k^S），再乘音节总字频（"先分组，再算组内字频"）。
阶段一（首根组）：常用字尽量各占一个三简（同音节、同首根键只有一个能拿三简；输的按权重罚 H，软但很重）；
                 键位偏好按「音码末键→首根键」当量。
阶段二（末根组）：常用字（前1521）有效重码硬约束；前3571 重码软约束；字词避重（6万词：常用4万+新码位2万）软约束；
                 三简得失与「首根键→末根键」当量照算。
每阶段按根组使用权重从高到低，一组一组挑代价最小的键。已有一二简的读音不参与三简竞争。
用法：python construct/build.py [输出名]
"""
import json, sys, collections
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
INP = ROOT / 'build/out/n30'
E = yaml.load(open(INP / 'elements.yaml', encoding='utf-8'), Loader=L)
META = json.load(open(INP / 'meta.json', encoding='utf-8')); G = sorted(META['groups'])
N = sum(1 for e in E if e['拼音'] != 'reserved')
C = json.load(open(ROOT / 'eval/box/combo.json'))
EQ = lambda a, b: C[a + b]['eq']
LAB = {r['组']: r['标注'] for r in json.load(open(ROOT / 'data/inputs/根组位置标注_前3500.json', encoding='utf-8'))}
WORDS = collections.Counter(w['码'] for w in json.load(open(ROOT / 'data/inputs/虎码词库_字词避重6万词.json', encoding='utf-8')))
T1521 = set(META['tier_indices']['1500']); T3571 = set(META['tier_indices']['3500'])
KEYS = 'abcdefghijklmnopqrstuvwxyz'
S, H, LAMBDA, W_DUP3, W_CLASH = 2.58, 10.0, 1.0, 3.0, 0.3
HARD = 1e6

R = []                                                     # (音码, 首根组, 末根组, 频率, 固定简码)
for e in E[:N]:
    s = e['元素序列']
    R.append((s[0]['element'][2:] + s[1]['element'][2:], s[2]['element'], s[3]['element'], e['频率'], bool(e.get('简码长度'))))
by_syl = collections.defaultdict(list)
for i, r in enumerate(R):
    by_syl[r[0]].append(i)
w = [0.0] * N
for syl, idx in by_syl.items():
    idx.sort(key=lambda i: -R[i][3])
    tot = sum(R[i][3] for i in idx)
    z = sum((k + 1) ** -S for k in range(len(idx)))
    for k, i in enumerate(idx):
        w[i] = tot * (k + 1) ** -S / z
W = sum(w); w = [x / W * 1e4 for x in w]               # 归一到总和 1 万
order = sorted(range(N), key=lambda i: -R[i][3]); pos = {i: k for k, i in enumerate(order)}


def evaluate(M, stage):
    """返回 (总代价, 明细)。只计已放好的根组涉及的读音。"""
    cost = 0.0; loss3 = 0.0; eq = 0.0; dup1 = dup3 = clash = 0
    short = set()
    for syl, idx in by_syl.items():
        best = {}
        for i in idx:
            if R[i][4]:
                short.add(i); continue
            k = M.get(R[i][1])
            if k is None:
                continue
            p = syl + k
            if p in best:
                loss3 += w[i]
            else:
                best[p] = i; short.add(i)
            eq += w[i] * EQ(syl[1], k)
    full = collections.defaultdict(list)
    for i in range(N):
        k1, k2 = M.get(R[i][1]), M.get(R[i][2])
        if k1 is None or k2 is None:
            continue
        eq += w[i] * EQ(k1, k2) * (0 if i in short else 1)
        if i not in short:
            code = R[i][0] + k1 + k2
            full[code].append(i)
            if stage == 2 and code in WORDS:
                clash += WORDS[code]
    if stage == 2:
        for code, idx in full.items():
            if len(idx) < 2:
                continue
            idx.sort(key=pos.get)
            for a in idx[1:]:
                if any(R[b][1:3] != R[a][1:3] for b in idx[:idx.index(a)]):
                    dup1 += a in T1521; dup3 += a in T3571
    cost = H * loss3 + LAMBDA * eq + HARD * dup1 + W_DUP3 * w_sum_dummy(dup3) + W_CLASH * clash
    return cost, {'三简损失': round(loss3, 1), '当量': round(eq, 1), '1521重': dup1, '3571重': dup3, '6万冲突': clash}


def w_sum_dummy(n):
    return n * 10.0


def place(M, groups, stage, mutex):
    for g in groups:
        best = None
        for k in KEYS:
            if g in mutex and M.get(mutex[g]) == k:
                continue
            M[g] = k
            c, d = evaluate(M, stage)
            if best is None or c < best[0]:
                best = (c, k, d)
        M[g] = best[1]
        print(f"阶段{stage} {g}{''.join(META['groups'][g][:2])} → {best[1]}  {best[2]}", flush=True)
    return M


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'c1'
    use1, use2 = collections.Counter(), collections.Counter()
    for i, r in enumerate(R):
        use1[r[1]] += w[i]; use2[r[2]] += w[i]
    g_bird = next(g for g in G if '鸟' in META['groups'][g]); g_bug = next(g for g in G if '虫' in META['groups'][g])
    mutex = {g_bird: g_bug, g_bug: g_bird}
    first = sorted((g for g in G if LAB[g] == '首根'), key=lambda g: -use1[g])
    rest = sorted((g for g in G if LAB[g] != '首根'), key=lambda g: -(use1[g] + use2[g]))
    M = place({}, first, 1, mutex)
    M = place(M, rest, 2, mutex)
    c, d = evaluate(M, 2)
    print('完成', d)
    json.dump(M, open(ROOT / f'construct/{name}.json', 'w'), ensure_ascii=False, indent=1)
