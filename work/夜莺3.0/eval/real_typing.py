"""用 6 套测试句（约 88 万字，逐字定好读音）实打任意普通单字表，统计击键数据。
取码：该字该读音的码 = 表中以该读音音节码（对应双拼）为前缀的码里最短者、再按候选位；码长<4 或非首选加选重键。
另统计：键对中碰到形码（第3、4码）的比例。"""
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode
C = json.load(open(ROOT / 'eval/box/combo.json'))
SEL = " ;'456789"
READ = collections.defaultdict(set)
for r in json.load(open(ROOT / 'data/inputs/夜桜字音基准.json', encoding='utf-8')):
    READ[r['字']].add(r['拼音'])

ONE = {(c, py) for c, py, k in json.load(open(ROOT / 'data/inputs/2.5一二简固定.json', encoding='utf-8'))['fixed'] if k == 1}


def book(table, scheme):
    pos = collections.Counter(); best = {}
    for l in open(table, encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) < 2 or len(p[0]) != 1: continue
        ch, code = p; k = pos[code]; pos[code] += 1
        for py in READ.get(ch, ()):
            sy = encode(py, scheme)
            if len(code) == 1:
                if (ch, py) not in ONE: continue        # 一简只归属其固定读音（读音即字）
            elif code[:2] != sy:
                continue
            if True:
                key = (ch, py)
                if key not in best or (len(code), k) < (len(best[key][0]), best[key][1]):
                    best[key] = (code, k)
    return {k: (c, c + (SEL[min(i, 8)] if (len(c) < 4 or i > 0) else '')) for k, (c, i) in best.items()}

def run(table, scheme, sets=range(6)):
    B = book(table, scheme)
    st = collections.Counter(); miss = 0
    for k in sets:
        S = json.load(open(ROOT / f'eval/sentences/set{k}.json', encoding='utf-8'))
        R = json.load(open(ROOT / f'eval/sentences/set{k}.readings.json', encoding='utf-8'))
        for x, rd in zip(S, R):
            stream, shape = '', []
            def flush():
                for i in range(len(stream) - 1):
                    d = C[stream[i:i + 2]]
                    st['pairs'] += 1; st['eq'] += d['eq']
                    for f in ('ms', 'ss', 'pd', 'lfd', 'dh'): st[f] += d[f]
                    st['shape'] += shape[i] or shape[i + 1]
            for ch, r in zip(x['s'], rd):
                if r is None or (ch, r) not in B:
                    if r is not None: miss += 1
                    flush(); stream, shape = '', []; continue
                code, typed = B[(ch, r)]
                st['chars'] += 1; st['keys'] += len(typed); st['sel'] += typed[-1] in SEL[1:]
                st[f'len{len(code)}'] += 1
                stream += typed; shape += [i >= 2 for i in range(len(code))] + [False] * (len(typed) - len(code))
            flush()
    n, p = st['chars'], st['pairs']
    return {'字数': n, '缺码': miss, '一简%': 100 * st['len1'] / n, '二简%': 100 * st['len2'] / n, '三码%': 100 * st['len3'] / n,
            '四码%': 100 * st['len4'] / n, '字均键数': st['keys'] / n, '键均当量': st['eq'] / p, '字均当量': st['eq'] / n,
            '选重%': 100 * st['sel'] / n, '互击%': 100 * st['dh'] / p, '同指大跨排%': 100 * st['ms'] / p,
            '同指小跨排%': 100 * st['ss'] / p, '小指干扰%': 100 * st['pd'] / p, '错手%': 100 * st['lfd'] / p,
            '碰到形码的键对%': 100 * st['shape'] / p}

if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=1))
