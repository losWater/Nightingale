"""实打测评（只打单字）：按句子逐字、按读音取码，模拟真实击键流。
取码规则与形码盒子一致：该读音所有码中取最短，其次候选位靠前；码长 <4 或非首选须加选重键（首选为空格）。
一个连续汉字段内，字与字之间的衔接也计入当量与手感；标点、符号断开击键流。

指标：字均键数、键均当量、字均当量、选重率、互击/同指大跨排/同指小跨排/小指干扰/错手（按键对）、三连击、
按键热力（各键份额）、最忙键份额、小指份额、左手份额、与形码盒子理想负荷的偏差（L1）。"""
import json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = ROOT / 'eval/box'
COMBO = json.load(open(BOX / 'combo.json', encoding='utf-8'))
FL = json.load(open(BOX / 'finger_load.json', encoding='utf-8'))
_t = sum(FL.values())
IDEAL = {k: v / _t for k, v in FL.items()}
SEL = " ;'456789"
FLAGS = ('dh', 'ms', 'ss', 'pd', 'lfd')
LEFT = set('qwertasdfgzxcvb12345')
PINKY = set("qaz1p;/'0-=[]")


def code_book(items):
    """items: [(code, rank, idx, ch, py)] 已按表序排列 → {(字,读音): 实打键串}"""
    pos, book = collections.Counter(), {}
    placed = []
    for code, _, i, ch, py in items:
        placed.append((code, pos[code], ch, py))
        pos[code] += 1
    best = {}
    for code, p, ch, py in placed:
        key = (ch, py)
        cand = (len(code), p, code)
        if key not in best or cand < best[key]:
            best[key] = cand
    for key, (L, p, code) in best.items():
        book[key] = code + (SEL[min(p, len(SEL) - 1)] if (L < 4 or p > 0) else '')
    return book


def simulate(book, sentences, readings):
    chars = keys = sel = trible = 0
    pairs = 0
    eq = 0.0
    flag = collections.Counter()
    use = collections.Counter()
    for x, rd in zip(sentences, readings):
        stream = ''
        for c, r in zip(x['s'], rd):
            if r is None:
                if stream:
                    yield_stream = stream
                    stream = ''
                    pairs, eq = _acc(yield_stream, pairs, eq, flag)
                    trible += _trible(yield_stream)
                continue
            k = book.get((c, r))
            if k is None:
                continue
            chars += 1
            keys += len(k)
            sel += (k[-1] in SEL[1:])
            for ch in k:
                use[ch] += 1
            stream += k
        if stream:
            pairs, eq = _acc(stream, pairs, eq, flag)
            trible += _trible(stream)
    tot = sum(use.values())
    letters = {k: v for k, v in use.items() if k.isalpha()}
    lt = sum(letters.values())
    share = {k: v / tot for k, v in use.items()}
    dev = sum(abs(share.get(k, 0) - IDEAL.get(k, 0)) for k in set(IDEAL) | set(share))
    busiest = max(letters, key=letters.get)
    return {
        '字数': chars, '字均键数': keys / chars, '键均当量': eq / pairs, '字均当量': eq / chars,
        '选重率': sel / chars, '三连击率': trible / chars,
        **{f'{f}率': flag[f] / pairs for f in FLAGS},
        '最忙键': busiest, '最忙键份额': letters[busiest] / lt,
        '小指份额': sum(v for k, v in use.items() if k in PINKY) / tot,
        '左手份额': sum(v for k, v in letters.items() if k in LEFT) / lt,
        '负荷偏差L1': dev,
        '热力': {k: round(v / tot, 5) for k, v in sorted(use.items(), key=lambda kv: -kv[1])},
    }


def _acc(stream, pairs, eq, flag):
    for a, b in zip(stream, stream[1:]):
        d = COMBO.get(a + b)
        if d is None:
            continue
        pairs += 1
        eq += d['eq']
        for f in FLAGS:
            flag[f] += d[f]
    return pairs, eq


def _trible(stream):
    return sum(1 for a, b, c in zip(stream, stream[1:], stream[2:]) if a == b == c)


def run(elements, code_txt, set_k):
    import sys
    sys.path.insert(0, str(ROOT / 'eval'))
    from make_table import build
    items = build(elements, code_txt)
    S = json.load(open(ROOT / f'eval/sentences/set{set_k}.json', encoding='utf-8'))
    R = json.load(open(ROOT / f'eval/sentences/set{set_k}.readings.json', encoding='utf-8'))
    return simulate(code_book(items), S, R)


if __name__ == '__main__':
    import sys
    r = run(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    r.pop('热力')
    print(json.dumps(r, ensure_ascii=False, indent=1))
