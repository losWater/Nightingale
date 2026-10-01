"""第一轮排名：读各方案 eval.json，按口径（typed 实际打法 / full 只用全码）打分、门禁淘汰、每大组取前 2。

尺子：用试跑方案（固定一二简的 b3–b7 与基线）在同一口径下校准并冻结（eval/calib/scale_<口径>.json）。
门禁（淘汰）：前1500有效无重、前3500有效重码个位数、前6000三码损失≤100、重码对增加≤20、虫鸟不同键。
（p 排名门禁已由作者撤销，不参与淘汰。）

用法：python tournament/rank.py calibrate              # 两口径各校准一次
      python tournament/rank.py rank [typed|full|mix]   # 输出排名与 64 强（正式采用 mix：两口径五五开）
"""
import glob, json, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval')); sys.path.insert(0, str(ROOT / 'tournament'))
import score as SC

T = ROOT / 'runs/formal'
GATES = ['前1500有效无重', '前3500有效重码个位数', '前6000三码损失≤100', '重码对增加≤20', '虫鸟不同键']


def flatten(ev, mode):
    flat = {f'box.{i}.{k}': v for i, s in enumerate(ev[mode]['box']) for k, v in s.items() if isinstance(v, (int, float))}
    flat['cross'] = ev['cross']
    flat.update({f'type.{k}': v for k, v in ev[mode]['type'].items() if isinstance(v, (int, float))})
    return flat


def trial_eval(run_dir):
    """对试跑目录按与正式赛相同的方法算两口径原始指标（不含门禁）。"""
    import evaluate as EV
    from make_table import build
    import type_sim
    d = Path(run_dir)
    out = sorted(d.glob('output-*'))[0]
    items = build(str(d / 'elements.yaml'), str(out / 'code.txt'))
    res = {}
    for name, its in (('typed', items), ('full', EV.full_only(items, out / 'code.txt'))):
        res[name] = {'box': EV.box(its)['sections'], 'type': type_sim.simulate(type_sim.code_book(its), EV.S0, EV.R0)}
    res['cross'] = json.load(open(out / 'metric.json', encoding='utf-8'))['metric']['character_word_collision']['soft']
    return res


def calibrate():
    runs = ['build/out/fixtest'] + [str(Path(d).relative_to(ROOT)) for d in sorted(glob.glob(str(ROOT / 'runs/b[3-7]/*')))
                                    if list(Path(d).glob('output-*')) and (Path(d) / 'elements.yaml').exists()]
    evs = {r: trial_eval(ROOT / r) for r in runs}
    for mode in ('typed', 'full'):
        rows = {r: flatten(e, mode) for r, e in evs.items()}
        scale = {}
        for k in next(iter(rows.values())):
            vs = [rows[r][k] for r in rows]
            lo, hi = min(vs), max(vs)
            pad = (hi - lo) * SC.MARGIN
            lo, hi = lo - pad, hi + pad
            name = k.split('.')[-1]
            if name in SC.FLOOR:
                kind, x = SC.FLOOR[name]
                need = x * abs((lo + hi) / 2) if kind == 'rel' else x
                if hi - lo < need:
                    mid = (lo + hi) / 2
                    lo, hi = mid - need / 2, mid + need / 2
            scale[k] = [lo, hi]
        json.dump({'校准方案': runs, '尺子': scale, '原始值': rows},
                  open(ROOT / f'eval/calib/scale_{mode}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        base = SC.score(rows['build/out/fixtest'], scale)
        print(mode, '校准方案', len(rows), '基线总分', round(base['总分'], 2))


MIX = {'typed': 0.5, 'full': 0.5}      # 作者 2026-09-30：两口径五五开


def mixed_score(ev):
    """混合口径：各口径总分按 MIX 加权；理论分、实打分同样加权以便查看。"""
    out = {'总分': 0.0, '理论分': 0.0, '实打分': 0.0, '分口径': {}}
    for m, w in MIX.items():
        sc = json.load(open(ROOT / f'eval/calib/scale_{m}.json', encoding='utf-8'))['尺子']
        s = SC.score(flatten(ev, m), sc)
        out['分口径'][m] = s
        for k in ('总分', '理论分', '实打分'):
            out[k] += w * s[k]
    out['理论分项'] = out['分口径']['typed']['理论分项']
    out['实打分项'] = out['分口径']['typed']['实打分项']
    return out


def rank(mode):
    if mode == 'mix':
        cal = {m: json.load(open(ROOT / f'eval/calib/scale_{m}.json', encoding='utf-8')) for m in MIX}
        base = {'总分': sum(w * SC.score(cal[m]['原始值']['build/out/fixtest'], cal[m]['尺子'])['总分'] for m, w in MIX.items())}
    else:
        scale = json.load(open(ROOT / f'eval/calib/scale_{mode}.json', encoding='utf-8'))['尺子']
        base = SC.score(json.load(open(ROOT / f'eval/calib/scale_{mode}.json', encoding='utf-8'))['原始值']['build/out/fixtest'], scale)
    jobs = json.load(open(T / 'jobs.json', encoding='utf-8'))['jobs']
    rows = []
    for j in jobs:
        p = T / j['id'] / 'eval.json'
        if not p.exists():
            continue
        ev = json.load(open(p, encoding='utf-8'))
        if ev.get('failed'):
            rows.append({**j, 'ok': False, 'why': '运行失败'})
            continue
        fails = [g for g in GATES if not ev['gates']['门禁'][g]]
        s = mixed_score(ev) if mode == 'mix' else SC.score(flatten(ev, mode), scale)
        rows.append({'id': j['id'], 'group': j['group'], 'kind': j['kind'], 'ok': not fails, 'why': fails,
                     '总分': s['总分'], '理论分': s['理论分'], '实打分': s['实打分'],
                     '理论分项': s['理论分项'], '实打分项': s['实打分项'], 'cross': ev['cross']})
    by = collections.defaultdict(list)
    for r in rows:
        if r['ok']:
            by[r['group']].append(r)
    top = []
    for g in sorted(by):
        top += sorted(by[g], key=lambda r: -r['总分'])[:2]
    out = {'口径': mode, '基线总分': base['总分'], '已评': len(rows), '淘汰': sum(not r['ok'] for r in rows),
           '64强': [r['id'] for r in top], '明细': rows}
    json.dump(out, open(T / f'round1_{mode}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sorted((r for r in rows if r['ok']), key=lambda r: -r['总分'])
    kinds = collections.Counter(r['kind'] for r in top)
    print(f'口径 {mode}：已评 {len(rows)}，门禁淘汰 {out["淘汰"]}，基线总分 {base["总分"]:.2f}')
    print('第一轮全体前 10：', [(r['id'], r['kind'], round(r['总分'], 2)) for r in ok[:10]])
    print('入选起点分布：', dict(kinds), '；超过基线的方案数', sum(r['总分'] > base['总分'] for r in ok))


if __name__ == '__main__':
    calibrate() if sys.argv[1] == 'calibrate' else rank(sys.argv[2] if len(sys.argv) > 2 else 'typed')
