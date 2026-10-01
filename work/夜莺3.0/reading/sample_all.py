"""重做抽样（替代 pass1 的“单字成词”口径）：对全部多音字出现位置均匀蓄水池抽样。
每个样本记录：句、位置、pypinyin 整句读音（大陆词典）、jieba(无HMM) 是否单字成词。
上限：总频前 150 的多音字每体裁 200 处，其余 40 处。输出 out/<体裁>.sample.json（含各字总出现数）。"""
import json, random, sys, collections, logging, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import jieba
from pypinyin import lazy_pinyin

jieba.setLogLevel(logging.WARNING)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading'))
from annotate import READ, POLY, SENT, norm, BASE

tot = collections.Counter()
for r in BASE:
    tot[r['字']] += r['自然频率'] or 0
TOP = set(sorted(POLY, key=lambda c: -tot[c])[:150])


def run(genre):
    rng = random.Random(abs(hash(genre)) % 99991)
    n = collections.Counter()
    smp = collections.defaultdict(list)
    for line in open(ROOT / f'corpus/{genre}.txt', encoding='utf-8'):
        for s in SENT.findall(line):
            s = s.strip()
            if not (4 <= len(s) <= 120):
                continue
            idx = [i for i, c in enumerate(s) if c in POLY]
            if not idx:
                continue
            py = None
            singles = None
            for i in idx:
                c = s[i]
                n[c] += 1
                cap = 200 if c in TOP else 40
                if len(smp[c]) < cap:
                    slot = len(smp[c])
                    smp[c].append(None)
                else:
                    j = rng.randrange(n[c])
                    if j >= cap:
                        continue
                    slot = j
                if py is None:
                    py = lazy_pinyin(s, errors=lambda x: ['?'] * len(x))
                    singles, p = set(), 0
                    for w in jieba.lcut(s, HMM=False):
                        if len(w) == 1:
                            singles.add(p)
                        p += len(w)
                smp[c][slot] = [s, i, (norm(py[i]) if py[i] != '?' else None) if len(py) == len(s) else None, i in singles]
    json.dump({'n': n, 'sample': smp}, open(ROOT / f'reading/out/{genre}.sample.json', 'w', encoding='utf-8'),
              ensure_ascii=False)
    print(genre, '多音字出现', sum(n.values()), '样本', sum(len(v) for v in smp.values()), flush=True)


if __name__ == '__main__':
    run(sys.argv[1])
