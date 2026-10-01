"""给实打句子逐字定读音（读音即字）：pypinyin 整句读音 + jieba 单字判断，多音字位置用 g2pW，
按 build_basis.final_reading 同一规则校正（台湾读音改大陆、文白异读仅单字成词取白读）。
输出 eval/sentences/set{k}.readings.json：与句子对齐的读音列表（非汉字为 null）。
用法：G2PW_THREADS=2 python eval/label_sentences.py 0 1 2 3 4 5"""
import json, os, sys, time, logging, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import jieba
from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading'))
jieba.setLogLevel(logging.WARNING)
from annotate import READ, POLY, norm
import build_basis as bb
import label_samples as ls      # 复用 g2pW 会话与 label()（按 G2PW_THREADS 设置线程）

cache = dict(ls.cache)
for l in open(ROOT / 'reading/out/labels.jsonl', encoding='utf-8'):
    j = json.loads(l)
    cache[(j['s'], j['i'])] = (j['g2pw'], j['conf'])

main_reading = {}
for r in json.load(open(ROOT / 'data/inputs/夜桜字音基准.json', encoding='utf-8')):
    if r['字'] not in main_reading or r['自然频率'] > main_reading[r['字']][1]:
        main_reading[r['字']] = (r['拼音'], r['自然频率'])


def label_set(k):
    src = ROOT / f'eval/sentences/set{k}.json'
    dst = ROOT / f'eval/sentences/set{k}.readings.json'
    if dst.exists():
        print(f'set{k} 已有', flush=True)
        return
    S = json.load(open(src, encoding='utf-8'))
    out, t0, q = [], time.time(), 0
    for n, x in enumerate(S, 1):
        s = x['s']
        py = lazy_pinyin(s, errors=lambda t: ['?'] * len(t))
        py = py if len(py) == len(s) else ['?'] * len(s)
        singles, p = set(), 0
        for w in jieba.lcut(s, HMM=False):
            if len(w) == 1:
                singles.add(p)
            p += len(w)
        rd = []
        for i, c in enumerate(s):
            if c not in READ:
                rd.append(None)
                continue
            p_i = norm(py[i]) if py[i] != '?' else None
            if c not in POLY:
                rd.append(next(iter(READ[c])))
                continue
            key = (s, i)
            if key not in cache:
                cache[key] = ls.label(s, i)
                q += 1
            g, _ = cache[key]
            r, _ = bb.final_reading({'c': c, 'g2pw': g, 'py': p_i, 'single': i in singles})
            rd.append(r if r in READ[c] else main_reading[c][0])
        out.append(rd)
        if n % 1000 == 0:
            print(f'set{k}', n, '句', f'g2pW 新标 {q}', f'{time.time() - t0:.0f}秒', flush=True)
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'set{k} 完成', flush=True)


if __name__ == '__main__':
    for k in sys.argv[1:]:
        label_set(int(k))
