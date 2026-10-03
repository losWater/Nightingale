"""整句准确率离线评测：同一五元模型、同一解码规则，比较虎码与夜莺各版码表。
小句 = 测试句里连续的汉字段（≥2 字）；用户为每个字打该读音的本码；首选与原文按编辑距离算逐字准确率。
用法：python tool/sentence/eval_sentence.py <输出目录> [套号,...] [每套最多句数]
"""
import collections, json, multiprocessing as mp, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lib'))
from tsent import FiveGram, Lexical, Lexicon, Decoder, read_codes, read_ranks
from shuangpin import encode

ROOT = Path(__file__).resolve().parents[2]
TP = Path.home() / 'Downloads/虎整句-Rime-20261001-D89-r3-四档纠错瓢虫版'
NB46 = ROOT / 'release/tables/夜莺3.0_NB46_普通单字表.txt'
NOYJ = Path.home() / 'Downloads/夜莺3.0_NB46_无一简试验版_普通单字表.txt'

G = {}


def build():
    ranks = read_ranks(TP / 'tiger_sentence.char_ranks.txt')
    wl = set(''.join(l.strip() for l in open(TP / 'tiger_sentence.full_code_whitelist.txt', encoding='utf-8') if not l.startswith('#')))
    tiger = read_codes(TP / 'tiger_sentence.codes.txt')
    nb, noyj = read_codes(NB46), read_codes(NOYJ)
    # 前 1500（按虎整句字频排名）里的多音字：码表里有不同双拼前缀的字
    pre = collections.defaultdict(set)
    for w, c in noyj:
        if len(w) == 1 and len(c) >= 2: pre[w].add(c[:2])
    poly = {w for w, s in pre.items() if len(s) > 1 and ranks.get(w, 10 ** 9) <= 1500}
    S = {
        '虎码': (Lexicon(tiger, ranks, 1500, wl), 'char'),
        '夜莺现行': (Lexicon(nb, ranks, 1500, ()), 'yy'),
        '夜莺C_原样': (Lexicon(noyj, ranks, 1500, ()), 'yy'),
        '夜莺C_白名单': (Lexicon(noyj, ranks, 1500, poly), 'yy'),
        '夜莺C_按读音': (Lexicon(noyj, ranks, 1500, (), primary_by='reading'), 'yy'),
    }
    typing = {'yy': Lexicon(noyj, ranks, 1500, (), primary_by='reading'),
              'yynow': Lexicon(nb, ranks, 1500, (), primary_by='reading')}
    return ranks, S, typing, poly


def init():
    lm = FiveGram(TP / 'models/sentence-fivegram-mobile.bin')
    lex = Lexical(TP / 'models/tiger_sentence.lexical.bin')
    ranks, S, typing, _ = build()
    G.update(lm=lm, lex=lex, ranks=ranks, S=S, typing=typing,
             D={k: Decoder(lm, lex, L, ranks) for k, (L, _) in S.items()})


def typed(name, chars, sys_):
    if G['S'][name][1] == 'char':
        L = G['S'][name][0]; codes = [L.typed(ch) for ch, _ in chars]
    else:
        T = G['typing']['yynow' if name == '夜莺现行' else 'yy']
        codes = [T.typed(ch, sy) for ch, sy in chars]
    return None if any(c is None for c in codes) else ''.join(codes)


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def work(job):
    genre, chars = job
    text = ''.join(ch for ch, _ in chars)
    raws = {k: typed(k, chars, None) for k in G['S']}
    if any(v is None for v in raws.values()):
        return None
    out = {}
    for k, raw in raws.items():
        r = G['D'][k].decode(raw)
        top = r[0]['text'] if r else ''
        out[k] = (top, lev(top, text), raw)
    return genre, text, out


def clauses(sets, per_set, seed=1):
    jobs = []
    for k in sets:
        S = json.load(open(ROOT / f'eval/sentences/set{k}.json', encoding='utf-8'))
        R = json.load(open(ROOT / f'eval/sentences/set{k}.readings.json', encoding='utf-8'))
        idx = list(range(len(S)))
        random.Random(seed + k).shuffle(idx)
        for i in idx[:per_set]:
            s, rd = S[i]['s'], R[i]
            run = []
            for ch, py in list(zip(s, rd)) + [(None, None)]:
                if py:
                    try: run.append((ch, encode(py, 'xiaohe')))
                    except Exception: run = []; continue
                else:
                    if len(run) >= 2: jobs.append((S[i]['g'], run))
                    run = []
    return jobs


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    sets = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '0').split(',')]
    per = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    _, _, _, poly = build()
    print('前1500多音字白名单', len(poly), ''.join(sorted(poly))[:200])
    jobs = clauses(sets, per)
    print('小句', len(jobs), '字', sum(len(c) for _, c in jobs)); t = time.time()
    res = []
    with mp.Pool(8, initializer=init) as pool:
        for i, r in enumerate(pool.imap_unordered(work, jobs, chunksize=20)):
            if r: res.append(r)
            if i % 2000 == 0: print(i, f'{time.time() - t:.0f}s', flush=True)
    json.dump(res, open(out / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False)
    names = list(res[0][2])
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])      # 字数, 错字, 小句, 小句全对
    for g, text, o in res:
        for k in names:
            for key in (g, '全部'):
                a = agg[(k, key)]; a[0] += len(text); a[1] += o[k][1]; a[2] += 1; a[3] += o[k][1] == 0
    genres = sorted({g for g, _, _ in res}) + ['全部']
    print('\n逐字准确率（小句全对率）')
    print('\t'.join(['方案'] + genres))
    for k in names:
        print('\t'.join([k] + [f"{100 * (1 - agg[(k, g)][1] / agg[(k, g)][0]):.2f}%（{100 * agg[(k, g)][3] / agg[(k, g)][2]:.1f}%）" for g in genres]))
    print('有效小句', len(res), '字', sum(len(t) for _, t, _ in res))
