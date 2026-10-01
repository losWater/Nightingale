"""夜莺 3.0 正式赛评分与排名（作者 2026-10-01 定）。
硬门禁淘汰后，各指标以 2.5 为 0 分、理想值为满分线性打分（上限 120%，下限 -50%），按权重求和（满分 100）。
第一轮：每大组取前 2 → 32 强；第二轮：实打三项改用 set1–set5 平均。
用法：python tournament/n30_rank.py round1
      python tournament/n30_rank.py round2
"""
import json, sys, statistics, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / 'runs/n30'
# 指标: (权重, 0 分锚点, 满分锚点)；值越小越好时 满分锚点 < 0 分锚点
SCORE = {
    '形码成本':  (25, 1.351, 1.330),
    'p占比':    (10, 0.073, 0.030),
    '撞码②':    (8, 3, 0),
    '撞码③':    (7, 5, 0),
    '三简':     (10, 3600, 3776),
    '换键根组':  (10, 50, 0),
    '小指干扰%': (10, 1.72, 1.40),
    '同指大跨排%': (10, 0.59, 0.45),
    '键均当量':  (10, 1.344, 1.335),
}


def metrics(ev, typing=None):
    t = typing or ev['实打']
    return {'形码成本': ev['形码成本'], 'p占比': ev['p占比'], '撞码②': ev['撞码'][1], '撞码③': ev['撞码'][2],
            '三简': ev['三简'], '换键根组': ev['换键根组'], '小指干扰%': t['小指干扰%'],
            '同指大跨排%': t['同指大跨排%'], '键均当量': t['键均当量']}


def score(m):
    total, parts = 0.0, {}
    for k, (w, zero, full) in SCORE.items():
        x = (m[k] - zero) / (full - zero)
        x = max(-0.5, min(1.2, x))
        parts[k] = round(100 * x, 1)
        total += w * x
    return total, parts


def round1():
    jobs = json.load(open(T / 'jobs.json', encoding='utf-8'))['jobs']
    rows = []
    for j in jobs:
        p = T / j['id'] / 'n30eval.json'
        if not p.exists():
            continue
        ev = json.load(open(p, encoding='utf-8'))
        if ev.get('failed'):
            rows.append({'id': j['id'], 'group': j['group'], 'ok': False, 'why': ['运行失败']}); continue
        fails = [k for k, v in ev['门禁'].items() if not v]
        s, parts = score(metrics(ev))
        rows.append({'id': j['id'], 'group': j['group'], 'ok': not fails, 'why': fails, '总分': s, '分项': parts,
                     '指标': metrics(ev)})
    by = collections.defaultdict(list)
    for r in rows:
        if r['ok']:
            by[r['group']].append(r)
    top = [x for g in sorted(by) for x in sorted(by[g], key=lambda r: -r['总分'])[:2]]
    json.dump({'已评': len(rows), '淘汰': sum(not r['ok'] for r in rows), '32强': [r['id'] for r in top], '明细': rows},
              open(T / 'round1.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sorted((r for r in rows if r['ok']), key=lambda r: -r['总分'])
    why = collections.Counter(w for r in rows if not r['ok'] for w in r['why'])
    print(f'已评 {len(rows)}，门禁淘汰 {sum(not r["ok"] for r in rows)} {dict(why)}')
    for r in ok[:10]:
        print(r['id'], round(r['总分'], 2), r['分项'])


def round2():
    sys.path.insert(0, str(ROOT / 'tournament'))
    import n30_eval as NE
    r1 = json.load(open(T / 'round1.json', encoding='utf-8'))
    rows = []
    for jid in r1['32强']:
        ev = json.load(open(T / jid / 'n30eval.json', encoding='utf-8'))
        ts = []
        for k in range(1, 6):
            t = NE.typing_only(jid, (k,))
            ts.append(t)
        avg = {k: statistics.mean(t[k] for t in ts) for k in ts[0]}
        s, parts = score(metrics(ev, avg))
        rows.append({'id': jid, '总分': s, '分项': parts, '实打五次平均': avg,
                     '实打键均当量标准差': statistics.pstdev(t['键均当量'] for t in ts)})
        print(jid, round(s, 2), flush=True)
    rows.sort(key=lambda r: -r['总分'])
    json.dump(rows, open(T / 'round2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('冠军', rows[0]['id'], round(rows[0]['总分'], 2))
    for r in rows[:5]:
        print(r['id'], round(r['总分'], 2), r['分项'])


if __name__ == '__main__':
    {'round1': round1, 'round2': round2}[sys.argv[1]]()
