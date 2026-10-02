"""词组码位空间：音码（夜莺词码规则，小鹤双拼）vs 虎码（词库自带码），同一批词（虎码词库）。
夜莺词码：二字 AaAbBaBb（两字双拼）；三字 AaBaCa（三码）；四字以上 AaBaCaZa。拼音用 pypinyin 按词定音。
同码内按词频排序（不考虑简词、模型调序），排第 2 位及以后的词算“要选重”。
用法：.venv/bin/python release/word_space.py <输出json>
"""
import collections, json, math, sys
from pathlib import Path
import warnings; warnings.filterwarnings('ignore')
from pypinyin import lazy_pinyin
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

# ---- 词与虎码码：同词取权重最高的条目 ----
best = {}
for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 3 and not l.startswith('#') and p[1].isdigit() and len(p[0]) > 1 and p[2].isalpha():
        w, f, c = p[0], int(p[1]), p[2]
        if w not in best or f > best[w][0]:
            best[w] = (f, c)


def yin(word):
    py = lazy_pinyin(word, errors=lambda t: ['?'] * len(t))
    if len(py) != len(word) or '?' in py:
        return None
    try:
        sp = [encode(x, 'xiaohe') for x in py]
    except Exception:
        return None
    if len(sp) == 2: return sp[0] + sp[1]
    if len(sp) == 3: return sp[0][0] + sp[1][0] + sp[2][0]
    return sp[0][0] + sp[1][0] + sp[2][0] + sp[-1][0]


W = []                                   # (词, 频, 虎码, 音码)
for w, (f, c) in best.items():
    y = yin(w)
    if y: W.append((w, f, c, y))
W.sort(key=lambda x: -x[1])
rank = {x[0]: r for r, x in enumerate(W, 1)}
print('词数', len(W), '（虎码词库去重后', len(best), '）')

LEN = {'二字': lambda n: n == 2, '三字': lambda n: n == 3, '四字及以上': lambda n: n >= 4, '全部': lambda n: True}
BANDS = [('前1千', 1000), ('前1万', 10000), ('前3万', 30000), ('前6万', 60000), ('全部', 10 ** 9)]
SIZE = ['1', '2', '3', '4', '5–9', '10+']
size_lab = lambda n: str(n) if n <= 4 else '5–9' if n < 10 else '10+'


def analyse(idx):
    """idx: 0=虎码 2=… 实际传 2 或 3（列号）。返回该方案在各词长下的统计。"""
    out = {}
    for ln, ok in LEN.items():
        ws = [x for x in W if ok(len(x[0]))]
        buckets = collections.defaultdict(list)
        for x in ws:
            buckets[x[idx]].append(x)
        pos = {}
        for c, b in buckets.items():
            b.sort(key=lambda x: -x[1])
            for k, x in enumerate(b):
                pos[x[0]] = (k, len(b), c)
        tot_f = sum(x[1] for x in ws)
        r = {'词数': len(ws), '码位数': len(buckets), '词每码位': len(ws) / max(1, len(buckets))}
        r['独占码位的词'] = sum(1 for x in ws if pos[x[0]][1] == 1) / len(ws)
        r['要选重的词'] = sum(1 for x in ws if pos[x[0]][0] > 0) / len(ws)
        r['选重率_按词频'] = sum(x[1] for x in ws if pos[x[0]][0] > 0) / tot_f
        r['平均候选位_按词频'] = sum(x[1] * (pos[x[0]][0] + 1) for x in ws) / tot_f
        # 码位大小分布：落在 n 词码位里的词占比
        sz = collections.Counter(size_lab(pos[x[0]][1]) for x in ws)
        r['码位大小分布'] = {s: sz[s] / len(ws) for s in SIZE}
        # 候选位分布（按词数、按词频）
        cp = collections.Counter(min(pos[x[0]][0], 4) for x in ws)
        cpf = collections.Counter(); [cpf.update({min(pos[x[0]][0], 4): x[1]}) for x in ws]
        r['候选位分布'] = {str(k + 1) if k < 4 else '5+': cp[k] / len(ws) for k in range(5)}
        r['候选位分布_按词频'] = {str(k + 1) if k < 4 else '5+': cpf[k] / tot_f for k in range(5)}
        # 分词频档：该档内的词有多少要选重（档内按全局词频序）
        bands = {}
        for bn, lim in BANDS:
            bw = [x for x in ws if rank[x[0]] <= lim]
            if not bw: continue
            bf = sum(x[1] for x in bw)
            bands[bn] = {'词数': len(bw), '要选重': sum(1 for x in bw if pos[x[0]][0] > 0),
                         '要选重比例': sum(1 for x in bw if pos[x[0]][0] > 0) / len(bw),
                         '选重率_按词频': sum(x[1] for x in bw if pos[x[0]][0] > 0) / bf,
                         '第3选及以后': sum(1 for x in bw if pos[x[0]][0] > 1)}
        r['分词频'] = bands
        # 区间档（不累计）
        iv, lo = {}, 0
        for bn, lim in BANDS:
            bw = [x for x in ws if lo < rank[x[0]] <= lim]
            if bw:
                iv[f'{lo + 1}–{min(lim, len(W))}'] = {'词数': len(bw), '要选重比例': sum(1 for x in bw if pos[x[0]][0] > 0) / len(bw)}
            lo = lim
        r['分词频区间'] = iv
        # 集中度：词最多的前 1% / 10% 码位装了多少词；基尼系数
        sizes = sorted((len(b) for b in buckets.values()), reverse=True)
        n = len(sizes)
        r['前1%码位装词'] = sum(sizes[:max(1, n // 100)]) / len(ws)
        r['前10%码位装词'] = sum(sizes[:max(1, n // 10)]) / len(ws)
        asc = sizes[::-1]; cum = sum((i + 1) * s for i, s in enumerate(asc))
        r['基尼'] = (2 * cum) / (n * sum(asc)) - (n + 1) / n
        r['洛伦兹'] = [[k / 50, sum(sizes[:max(0, round(n * k / 50))]) / len(ws)] for k in range(51)]
        # 最挤的码位
        r['最挤码位'] = [[c, len(b), [x[0] for x in b[:8]]] for c, b in sorted(buckets.items(), key=lambda kv: -len(kv[1]))[:15]]
        # 代价最大的选重：高频词排在第 2 位及以后
        cost = sorted((x for x in ws if pos[x[0]][0] > 0), key=lambda x: -x[1])[:25]
        r['最常用却要选重'] = [[x[0], rank[x[0]], x[idx], pos[x[0]][0] + 1, buckets[x[idx]][0][0]] for x in cost]
        # 码位空间热力（前两码 26×26 的词数；只二字词有意义）
        if ln == '二字':
            hm = [[0] * 26 for _ in range(26)]
            for x in ws:
                c = x[idx]; hm[ord(c[0]) - 97][ord(c[1]) - 97] += 1
            r['前两码热力'] = hm
            r['可用码位'] = 26 ** 4 if idx == 2 else None
        out[ln] = r
    return out


res = {'词数': len(W), '虎码': analyse(2), '音码': analyse(3)}
# 音码二字词的理论码位：音节对数
syl = set()
for x in W:
    if len(x[0]) == 2: syl.add(x[3][:2]); syl.add(x[3][2:])
res['音码']['二字']['可用码位'] = len(syl) ** 2
res['音码']['二字']['音节数'] = len(syl)
json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False)
for s in ('虎码', '音码'):
    for ln in LEN:
        r = res[s][ln]
        print(s, ln, '词', r['词数'], '码位', r['码位数'], f"词/码位 {r['词每码位']:.2f}", f"要选重 {r['要选重的词']:.1%}",
              f"选重率(按频) {r['选重率_按词频']:.1%}", f"基尼 {r['基尼']:.3f}")
