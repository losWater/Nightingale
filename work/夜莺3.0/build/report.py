"""夜桜候选性能报告：从 code.txt + metric.json 汇总多项指标，与基线并列。
用法：python build/report.py 名称=运行目录 [名称=运行目录 ...]
运行目录内需有 elements.yaml、meta.json、output-*/code.txt 与 metric.json。"""
import glob, json, sys, collections
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
M = json.load(open(ROOT / 'data/frozen54/matrix.json', encoding='utf-8'))
LEFT, RIGHT = set('qwertasdfgzxcv'), set('yuiophjklbnm')
PINKY = set('qazp')
SEL = " ;'456789"
TIERS = ('300', '1500', '3500', '6000')


def load(run):
    run = Path(run)
    out = sorted(run.glob('output-*'))[-1]
    E = yaml.safe_load(open(run / 'elements.yaml', encoding='utf-8'))
    meta = json.load(open(run / 'meta.json', encoding='utf-8'))
    n = sum(1 for e in E if e['拼音'] != 'reserved')
    rows = [l.rstrip('\n').split('\t') for l in open(out / 'code.txt', encoding='utf-8')][:n]
    metric = json.load(open(out / 'metric.json', encoding='utf-8'))
    return E[:n], meta, rows, metric


def typed(r):
    full, fr, short, sr = r[1], int(r[2]), r[3], int(r[4])
    code, rank = (short, sr) if short and len(short) < len(full) or (short and sr < fr) else (full, fr)
    if len(code) < 4 or rank > 0:
        code += SEL[min(rank, len(SEL) - 1)]
    return code


def eq(code):
    ps = [M.get(code[i:i + 2], 1.3) for i in range(len(code) - 1)]
    return sum(ps) / len(ps) if ps else 0


def stats(run):
    E, meta, rows, metric = load(run)
    f = [e['频率'] for e in E]
    res = {}
    for t in TIERS:
        idx = meta['tier_indices'][t]
        w = sum(f[i] for i in idx)
        le3 = [i for i in idx if len(typed(rows[i]).rstrip(SEL)) <= 3]
        res[f'前{t}三码率'] = round(len(le3) / len(idx), 4)
        res[f'前{t}三码字频覆盖'] = round(sum(f[i] for i in le3) / w, 4)
    W = sum(f)
    tc = [typed(r) for r in rows]
    res['平均码长(含选重)'] = round(sum(fi * len(c) for fi, c in zip(f, tc)) / W, 4)
    res['打字当量'] = round(sum(fi * eq(c) for fi, c in zip(f, tc)) / W, 4)
    res['全码当量'] = round(sum(fi * eq(r[1]) for fi, r in zip(f, rows)) / W, 4)
    res['二三码当量'] = round(sum(fi * M.get(r[1][1:3], 1.3) for fi, r in zip(f, rows)) / W, 4)
    res['三四码当量'] = round(sum(fi * M.get(r[1][2:4], 1.3) for fi, r in zip(f, rows)) / W, 4)
    keys = collections.Counter()
    for fi, c in zip(f, tc):
        for k in c:
            keys[k] += fi
    kt = sum(v for k, v in keys.items() if k.isalpha())
    res['左手'] = round(sum(keys[k] for k in LEFT) / kt, 4)
    res['小指(qazp)'] = round(sum(keys[k] for k in PINKY) / kt, 4)
    res['最忙键'] = max((k for k in keys if k.isalpha()), key=keys.get) + f"{keys[max((k for k in keys if k.isalpha()), key=keys.get)] / kt:.1%}"
    cs = metric['metric'].get('characters_short') or {}
    for tier in cs.get('tiers') or []:
        if tier['top'] in (len(meta['tier_indices']['1500']),):
            wf = tier.get('weighted_fingering') or []
            if wf:
                res['前1521简码同手率'] = round(wf[0], 4)
                res['前1521简码同指大跨排'] = round(wf[1], 4)
                res['前1521简码同指小跨排'] = round(wf[2], 4)
                res['前1521简码小指干扰'] = round(wf[3], 4)
    cw = metric['metric'].get('character_word_collision') or {}
    res['字词避重(软)'] = round(cw.get('soft', 0), 3)
    return res


if __name__ == '__main__':
    runs = [a.split('=', 1) for a in sys.argv[1:]]
    table = {name: stats(path) for name, path in runs}
    keys = list(next(iter(table.values())))
    names = [n for n, _ in runs]
    print('| 指标 | ' + ' | '.join(names) + ' |')
    print('|---|' + '---|' * len(names))
    for k in keys:
        print(f'| {k} | ' + ' | '.join(str(table[n].get(k, '')) for n in names) + ' |')
