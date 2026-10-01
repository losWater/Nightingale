"""稳健多来源字频（作者 2026-10-01 设想）：逐字判断各来源是否“离群”，离群来源降权。

来源（12 个）：2.0 五来源（新闻、文学、字幕、对话、微博）、自建 6 体裁（人民日报、维基、知乎、树洞、网文、名著）、形码盒子（笪骏）。
每来源先在 8105 字内归一化为每百万次数。
逐字：对数频率 → 中位数 m、MAD；来源 s 的稳健权重 w_s = 基础权重 × 1/(1+(d_s/(K·MAD))²)，d_s=|log f_s − m|。
样本可靠性：自建语料某字出现 < MIN_N 次时该来源不参与该字（避免小样本误判离群）；盒子只有前 6000 字。
最终频率 = Σ w_s f_s / Σ w_s（线性空间加权平均）。
"""
import json, math, re, collections, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W32 = Path('/private/tmp/claude-501/-Users-ice2447/1ee3833c-51ba-48d2-9510-f6f6b8889045/scratchpad/Nightingale/work/夜莺2.0')
K, MIN_N = 1.5, 30
HAN = re.compile(r'[一-鿿]')


def load_sources():
    t = json.load(open(next(W32.glob('32_*')) / '试验整字频率.json', encoding='utf-8-sig'))['字表']
    W0 = {'新闻': .2, '文学': .2, '字幕': .3, '对话': .2, '社交': .1}
    core = [r['字'] for r in t]
    src, n = {}, {}
    for s in W0:
        src['2.0' + s] = {r['字']: r['来源贡献'][s] / W0[s] for r in t}
        n['2.0' + s] = {c: 10 ** 9 for c in core}          # 大语料，视为可靠
    for g in 'news wiki zhihu forum webnovel classic'.split():
        cnt = collections.Counter()
        for l in open(ROOT / f'corpus/{g}.txt', encoding='utf-8'):
            cnt.update(HAN.findall(l))
        tot = sum(cnt[c] for c in core)
        src['自建' + g] = {c: 1e6 * cnt[c] / tot for c in core}
        n['自建' + g] = {c: cnt[c] for c in core}
    box = [l.rstrip('\n').split('\t') for l in open(ROOT / 'eval/box/默认字频.txt', encoding='utf-8') if '\t' in l][:6000]
    bt = sum(float(f) for w, f in box if w in set(core))
    bf = {w: 1e6 * float(f) / bt for w, f in box}
    src['盒子'] = {c: bf.get(c, 0.0) for c in core}
    n['盒子'] = {c: (10 ** 9 if c in bf else 0) for c in core}
    return core, src, n


def robust(core, src, n, base=None):
    base = base or {s: 1.0 for s in src}
    out, wts = {}, {}
    for c in core:
        vals = [(s, src[s][c]) for s in src if n[s][c] >= MIN_N and src[s][c] > 0]
        if not vals:
            out[c] = 0.0; continue
        logs = [math.log(v) for _, v in vals]
        m = sorted(logs)[len(logs) // 2]
        mad = sorted(abs(x - m) for x in logs)[len(logs) // 2] or 0.1
        w = {s: base[s] / (1 + ((math.log(v) - m) / (K * mad)) ** 2) for s, v in vals}
        tw = sum(w.values())
        out[c] = sum(w[s] * v for s, v in vals) / tw
        wts[c] = {s: w[s] / tw for s in w}
    t = sum(out.values())
    return {c: 1e6 * v / t for c, v in out.items()}, wts


if __name__ == '__main__':
    core, src, n = load_sources()
    rob, wts = robust(core, src, n)
    W0 = {'新闻': .2, '文学': .2, '字幕': .3, '对话': .2, '社交': .1}
    cur = {c: sum(W0[s] * src['2.0' + s][c] for s in W0) for c in core}
    rk = lambda f: {c: i + 1 for i, (c, _) in enumerate(sorted(f.items(), key=lambda kv: -kv[1]))}
    r0, r1 = rk(cur), rk(rob)
    rb = rk({c: v for c, v in src['盒子'].items() if v > 0})
    print('| 字 | 2.0当前排名 | 稳健排名 | 盒子排名 | 被降权最多的来源 |'); print('|---|---|---|---|---|')
    for c in sys.argv[1] if len(sys.argv) > 1 else '的是我吗啊哈呢嘛嗯啥咋政济则形饭穿衣酒喝哥爸':
        w = wts.get(c, {})
        low = sorted(w, key=w.get)[:3]
        print(f'| {c} | {r0[c]} | {r1[c]} | {rb.get(c, "-")} | {"、".join(f"{s}{100 * w[s]:.0f}%" for s in low)} |')
    a = {c for c, r in r0.items() if r <= 500}; b = {c for c, r in r1.items() if r <= 500}
    print('前500 新进：', ''.join(sorted(b - a, key=r1.get)))
    print('前500 掉出：', ''.join(sorted(a - b, key=r0.get)))
    json.dump({'说明': __doc__, '频率': rob}, open(ROOT / 'data/inputs/稳健字频_试验.json', 'w', encoding='utf-8'), ensure_ascii=False)


CLUSTERS = {   # 两层：类内稳健、类间固定权重（作者 2026-10-01：口语类合计 ≤40%）
    '书面·正式': (0.30, ['2.0新闻', '自建news', '自建wiki', '盒子']),
    '书面·文学': (0.30, ['2.0文学', '自建classic', '自建webnovel']),
    '网络打字': (0.25, ['2.0社交', '自建forum', '自建zhihu']),
    '口语': (0.15, ['2.0字幕', '2.0对话']),
}


def two_level(core, src, n):
    clus = {}
    for name, (_, ss) in CLUSTERS.items():
        sub = {s: src[s] for s in ss}
        subn = {s: n[s] for s in ss}
        f, _ = robust(core, sub, subn)
        clus[name] = f                       # 每类内已归一化为每百万
    out = {}
    for c in core:
        num = den = 0.0
        for name, (w, _) in CLUSTERS.items():
            if clus[name].get(c, 0) > 0 or any(n[s][c] >= MIN_N for s in CLUSTERS[name][1]):
                num += w * clus[name].get(c, 0); den += w
        out[c] = num / den if den else 0.0
    t = sum(out.values())
    return {c: 1e6 * v / t for c, v in out.items()}, clus


def report_two_level(chars):
    core, src, n = load_sources()
    f2, clus = two_level(core, src, n)
    W0 = {'新闻': .2, '文学': .2, '字幕': .3, '对话': .2, '社交': .1}
    cur = {c: sum(W0[s] * src['2.0' + s][c] for s in W0) for c in core}
    rk = lambda f: {c: i + 1 for i, (c, _) in enumerate(sorted(f.items(), key=lambda kv: -kv[1]))}
    r0, r2 = rk(cur), rk(f2)
    rb = rk({c: v for c, v in src['盒子'].items() if v > 0})
    rc = {k: rk(v) for k, v in clus.items()}
    print('| 字 | 2.0当前 | 两层稳健 | 盒子 | ' + ' | '.join(CLUSTERS) + ' |'); print('|---|---|---|---|' + '---|' * len(CLUSTERS))
    for c in chars:
        print(f'| {c} | {r0[c]} | {r2[c]} | {rb.get(c, "-")} | ' + ' | '.join(str(rc[k][c]) for k in CLUSTERS) + ' |')
    a = {c for c, r in r0.items() if r <= 500}; b = {c for c, r in r2.items() if r <= 500}
    print('前500 新进：', ''.join(sorted(b - a, key=r2.get)))
    print('前500 掉出：', ''.join(sorted(a - b, key=r0.get)))
    for N in (500, 1500, 3500):
        A = {c for c, r in r0.items() if r <= N}; B = {c for c, r in r2.items() if r <= N}
        print(f'前{N} 与 2.0 当前重合 {len(A & B)}/{N}')
    json.dump({'说明': '两层稳健字频：' + json.dumps({k: v[0] for k, v in CLUSTERS.items()}, ensure_ascii=False), '频率': f2},
              open(ROOT / 'data/inputs/稳健字频_两层_试验.json', 'w', encoding='utf-8'), ensure_ascii=False)
