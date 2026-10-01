"""夜桜正式赛评分：门禁 → 0.7 × 理论分（形码盒子 + 字词避重）+ 0.3 × 实打分（1 万句单字）。

每项指标用冻结尺子（eval/calib/scale.json）线性映射到 [0,1]：最好端 1、最差端 0，超出截断。
每部分 = 0.8 × 各类加权平均 + 0.2 × 最弱一类（兼顾各项，防止牺牲某一类换总分）。

用法：
  python eval/score.py calibrate            # 用校准集生成尺子（只做一次，之后冻结）
  python eval/score.py one <运行目录> <句子套号>
"""
import json, glob, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval')); sys.path.insert(0, str(ROOT / 'build'))
SCALE = ROOT / 'eval/calib/scale.json'

SEC_W = [30, 20, 25, 15, 10]                       # 形码盒子五个字频段
BOX_CATS = {                                       # 类别: (占比, [(指标, 权重, 越大越好?)])
    '当量': (25, [('ziEq', 2, False), ('keyEq', 1, False)]),
    '码长': (17, [('keyLength', 1, False)]),
    '选重': (13, [('selectRate', 1, False)]),
    '手感': (30, [('msRate', 10, False), ('ssRate', 8, False), ('pdRate', 8, False),
                ('lfdRate', 4, False), ('tribleRate', 2, False), ('dhRate', 3, True)]),
}
CROSS_W = 15                                       # 字词避重（理论部分的第五类）
TYPE_CATS = {
    '当量': (35, [('字均当量', 25, False), ('键均当量', 10, False)]),
    '码长': (15, [('字均键数', 1, False)]),
    '选重': (15, [('选重率', 1, False)]),
    '手感': (20, [('ms率', 10, False), ('ss率', 8, False), ('pd率', 8, False), ('lfd率', 4, False),
                ('三连击率', 2, False), ('dh率', 3, True)]),
    '键位负荷': (15, [('负荷偏差L1', 7, False), ('最忙键份额', 4, False), ('小指份额', 4, False)]),
}
MARGIN = 0.25
# 最小有意义跨度：低于此的差异视为无实际差别，防止极小差异经线性放大成噪声（('rel', x) 为取值的比例）
FLOOR = {'keyEq': ('rel', .02), 'ziEq': ('rel', .02), 'keyLength': ('rel', .02), 'selectRate': ('abs', .01),
         'msRate': ('abs', .005), 'ssRate': ('abs', .005), 'pdRate': ('abs', .005), 'lfdRate': ('abs', .005),
         'tribleRate': ('abs', .005), 'dhRate': ('abs', .02),
         '字均当量': ('rel', .02), '键均当量': ('rel', .02), '字均键数': ('rel', .02), '选重率': ('abs', .01),
         'ms率': ('abs', .005), 'ss率': ('abs', .005), 'pd率': ('abs', .005), 'lfd率': ('abs', .005),
         '三连击率': ('abs', .005), 'dh率': ('abs', .02), '负荷偏差L1': ('abs', .03), '最忙键份额': ('abs', .01),
         '小指份额': ('abs', .01), '左手份额': ('abs', .02), 'cross': ('rel', .2)}


def raw_metrics(run_dir, set_k):
    from box_run import box
    from type_sim import run as type_run
    run_dir = Path(run_dir)
    out = sorted(run_dir.glob('output-*'))[0]
    el = run_dir / 'elements.yaml'
    if not el.exists():
        el = ROOT / 'build/out/formal/elements.yaml'
    b = box(str(el), str(out / 'code.txt'))
    t = type_run(str(el), str(out / 'code.txt'), set_k)
    t.pop('热力', None); t.pop('最忙键', None)
    cross = json.load(open(out / 'metric.json', encoding='utf-8'))['metric']['character_word_collision']['soft']
    flat = {f'box.{i}.{k}': v for i, s in enumerate(b['sections']) for k, v in s.items() if isinstance(v, (int, float))}
    flat['cross'] = cross
    flat.update({f'type.{k}': v for k, v in t.items() if isinstance(v, (int, float))})
    return flat


def norm(scale, key, v, higher_better):
    lo, hi = scale[key]
    if hi == lo:
        return 1.0
    x = (v - lo) / (hi - lo)
    x = x if higher_better else 1 - x
    return min(1.0, max(0.0, x))


def part(cats, get):
    scores = {}
    for c, (w, ms) in cats.items():
        tw = sum(m[1] for m in ms)
        scores[c] = sum(get(k, hb) * mw for k, mw, hb in ms) / tw
    tw = sum(w for w, _ in cats.values())
    mean = sum(scores[c] * cats[c][0] for c in cats) / tw
    return 100 * (0.8 * mean + 0.2 * min(scores.values())), scores


def score(flat, scale):
    def box_get(k, hb):
        return sum(w * norm(scale, f'box.{i}.{k}', flat[f'box.{i}.{k}'], hb) for i, w in enumerate(SEC_W)) / sum(SEC_W)
    cats = dict(BOX_CATS)
    cats['字词避重'] = (CROSS_W, [('cross', 1, False)])
    def theory_get(k, hb):
        return norm(scale, 'cross', flat['cross'], hb) if k == 'cross' else box_get(k, hb)
    theory, tcat = part(cats, theory_get)
    typing, ycat = part(TYPE_CATS, lambda k, hb: norm(scale, f'type.{k}', flat[f'type.{k}'], hb))
    return {'总分': 0.7 * theory + 0.3 * typing, '理论分': theory, '实打分': typing,
            '理论分项': {k: round(100 * v, 2) for k, v in tcat.items()},
            '实打分项': {k: round(100 * v, 2) for k, v in ycat.items()}}


def calibrate():
    # 只用与正式赛可比的方案：固定 2.5 一二简（b3 起）
    runs = ['build/out/fixtest'] + [d.rstrip('/') for d in sorted(glob.glob('runs/b[3-7]/*/'))
                                    if glob.glob(d + 'output-*') and Path(d, 'elements.yaml').exists()]
    rows = {r: raw_metrics(ROOT / r, 0) for r in runs}
    keys = next(iter(rows.values())).keys()
    scale = {}
    for k in keys:
        vs = [rows[r][k] for r in rows]
        lo, hi = min(vs), max(vs)
        pad = (hi - lo) * MARGIN
        lo, hi = lo - pad, hi + pad
        name = k.split('.')[-1]
        if name in FLOOR:
            kind, x = FLOOR[name]
            need = x * abs((lo + hi) / 2) if kind == 'rel' else x
            if hi - lo < need:
                mid = (lo + hi) / 2
                lo, hi = mid - need / 2, mid + need / 2
        scale[k] = [lo, hi]
    json.dump({'校准方案': runs, '尺子': scale, '原始值': rows}, open(SCALE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('校准方案', len(rows), '指标', len(scale))


if __name__ == '__main__':
    if sys.argv[1] == 'calibrate':
        calibrate()
    else:
        scale = json.load(open(SCALE, encoding='utf-8'))['尺子']
        s = score(raw_metrics(sys.argv[2], int(sys.argv[3])), scale)
        print(json.dumps(s, ensure_ascii=False, indent=1))
