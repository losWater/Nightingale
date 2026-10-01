"""用 g2pW（上下文消歧）与 pypinyin（词典分词）两路标注语料中的多音字，按“字+去调音节”计数。
只处理含多音字（字音基准中读音数>1）的句子；单音字读音唯一，无需标注。
输出 reading/out/<体裁>.counts.json：{字: {音节: {"g2pw": n, "pypinyin": n, "agree": n}}}，另记 g2pW 给出库外读音的样例。"""
import json, re, sys, time, collections
from pathlib import Path
from pypinyin import lazy_pinyin, Style
from g2pw import G2PWConverter

ROOT = Path(__file__).resolve().parent.parent
BASE = json.load(open(ROOT / 'data/inputs/字音基准.json', encoding='utf-8-sig'))
READ = collections.defaultdict(set)
for r in BASE:
    READ[r['字']].add(r['拼音'])
POLY = {c for c, s in READ.items() if len(s) > 1}
SENT = re.compile(r'[^。！？；…\n]+[。！？；…]*')


def norm(py):
    if not py:
        return None
    return py.rstrip('012345').replace('ü', 'v').replace('u:', 'v')


def sentences(path, limit_chars):
    used = 0
    for line in open(path, encoding='utf-8'):
        for s in SENT.findall(line):
            s = s.strip()
            if 4 <= len(s) <= 120 and any(c in POLY for c in s):
                yield s
                used += len(s)
                if used >= limit_chars:
                    return


def main(genre, limit_chars=10**12, batch=64):
    conv = G2PWConverter(model_dir=str(ROOT / 'models/G2PWModel/'), style='pinyin',
                         enable_non_tradional_chinese=True, num_workers=0, batch_size=batch)
    counts = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter()))
    outside = collections.Counter()
    buf, n_sent, t0 = [], 0, time.time()

    def flush():
        nonlocal n_sent
        for s, g in zip(buf, conv(buf)):
            p = lazy_pinyin(s, style=Style.NORMAL, errors=lambda x: [None] * len(x), v_to_u=False)
            for i, c in enumerate(s):
                if c not in POLY:
                    continue
                gs = norm(g[i]) if i < len(g) else None
                ps = norm(p[i]) if i < len(p) else None
                if gs in READ[c]:
                    counts[c][gs]['g2pw'] += 1
                elif gs:
                    outside[(c, gs)] += 1
                if ps in READ[c]:
                    counts[c][ps]['pypinyin'] += 1
                if gs and gs == ps and gs in READ[c]:
                    counts[c][gs]['agree'] += 1
        n_sent += len(buf)
        buf.clear()

    for s in sentences(ROOT / f'corpus/{genre}.txt', limit_chars):
        buf.append(s)
        if len(buf) >= 2048:
            flush()
            print(genre, n_sent, f'{n_sent / (time.time() - t0):.0f} 句/秒', flush=True)
    if buf:
        flush()
    out = ROOT / 'reading/out'
    out.mkdir(parents=True, exist_ok=True)
    json.dump({'句数': n_sent,
               'counts': {c: {k: dict(v) for k, v in d.items()} for c, d in counts.items()},
               '库外读音': {f'{c}\t{s}': n for (c, s), n in outside.most_common()}},
              open(out / f'{genre}.counts.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(genre, '完成', n_sent, '句', f'{time.time() - t0:.0f} 秒', flush=True)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10**12)
