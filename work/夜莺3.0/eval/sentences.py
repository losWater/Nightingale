"""抽取实打测评句子：6 套 × 1 万句（第一轮 set0，第二轮 set1–set5），彼此不重叠。
条件：去掉标点后 10–20 个汉字；全部汉字属于 8105 核心字（夜桜字音基准）；不含拉丁字母与数字；6 体裁各占 1/6。
输出 eval/sentences/set{k}.json：[{"g": 体裁, "s": 原句}]"""
import json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
G = 'news wiki zhihu forum webnovel classic'.split()
CHARS = {r['字'] for r in json.load(open(ROOT / 'data/inputs/夜桜字音基准.json', encoding='utf-8'))}
SENT = re.compile(r'[^。！？；…\n]+[。！？；…]*')
HAN = re.compile(r'[一-鿿]')
BAD = re.compile(r'[A-Za-z0-9０-９Ａ-Ｚａ-ｚ]')
PER_SET, SETS = 10000, 6


def pool(genre):
    out = []
    for line in open(ROOT / f'corpus/{genre}.txt', encoding='utf-8'):
        for s in SENT.findall(line):
            s = s.strip()
            han = HAN.findall(s)
            if 10 <= len(han) <= 20 and not BAD.search(s) and all(c in CHARS for c in han):
                out.append(s)
    return out


if __name__ == '__main__':
    rng = random.Random(20260930)
    per_genre = PER_SET // len(G)
    extra = PER_SET - per_genre * len(G)
    sets = [[] for _ in range(SETS)]
    for gi, g in enumerate(G):
        p = sorted(set(pool(g)))
        rng.shuffle(p)
        need = per_genre + (1 if gi < extra else 0)
        assert len(p) >= need * SETS, (g, len(p))
        for k in range(SETS):
            sets[k] += [{'g': g, 's': s} for s in p[k * need:(k + 1) * need]]
        print(g, '候选句', len(p))
    d = ROOT / 'eval/sentences'
    d.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(sets):
        rng.shuffle(s)
        json.dump(s, open(d / f'set{k}.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'set{k}', len(s), '句', sum(len(HAN.findall(x["s"])) for x in s), '字')
