"""第一遍：pypinyin 词典分词全量统计。
- 多音字在多字词内：读音由词典决定，直接计入 inword。
- 多音字单字成词：计总次数，并按(体裁,字)蓄水池抽样至多 CAP 处，留给 g2pW 消歧。
- 另对词内出现抽样 VCAP 处，供 g2pW 对照、估计词典路准确率。"""
import json, random, re, sys, collections
from pathlib import Path
from pypinyin import lazy_pinyin
from pypinyin.seg.mmseg import seg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading'))
from annotate import READ, POLY, SENT, norm

CAP, VCAP = 400, 30


def run(genre):
    rng = random.Random(hash(genre) & 0xffff)
    inword = collections.defaultdict(collections.Counter)
    single_n = collections.Counter()
    single_s = collections.defaultdict(list)
    vword_n = collections.Counter()
    vword_s = collections.defaultdict(list)
    poly_total = collections.Counter()

    def reservoir(store, n, key, item, cap):
        if len(store[key]) < cap:
            store[key].append(item)
        else:
            j = rng.randrange(n)
            if j < cap:
                store[key][j] = item

    for line in open(ROOT / f'corpus/{genre}.txt', encoding='utf-8'):
        for s in SENT.findall(line):
            s = s.strip()
            if not (4 <= len(s) <= 120) or not any(c in POLY for c in s):
                continue
            pos = 0
            for w in seg.cut(s):
                if len(w) == 1:
                    if w in POLY:
                        poly_total[w] += 1
                        single_n[w] += 1
                        reservoir(single_s, single_n[w], w, (s, pos), CAP)
                else:
                    pys = lazy_pinyin(w)
                    if len(pys) == len(w):
                        for i, c in enumerate(w):
                            if c in POLY:
                                poly_total[c] += 1
                                syl = norm(pys[i])
                                inword[c][syl if syl in READ[c] else '?' + str(syl)] += 1
                                vword_n[c] += 1
                                reservoir(vword_s, vword_n[c], c, (s, pos + i, syl), VCAP)
                pos += len(w)
    out = ROOT / 'reading/out'
    out.mkdir(parents=True, exist_ok=True)
    json.dump({'inword': inword, 'single_n': single_n, 'single_sample': single_s,
               'vword_n': vword_n, 'vword_sample': vword_s, 'poly_total': poly_total},
              open(out / f'{genre}.pass1.json', 'w', encoding='utf-8'), ensure_ascii=False)
    q1 = sum(len(v) for v in single_s.values()); q2 = sum(len(v) for v in vword_s.values())
    print(genre, '多音字出现', sum(poly_total.values()), '单字成词', sum(single_n.values()),
          '待g2pW：单字样本', q1, '词内对照样本', q2, flush=True)


if __name__ == '__main__':
    run(sys.argv[1])
