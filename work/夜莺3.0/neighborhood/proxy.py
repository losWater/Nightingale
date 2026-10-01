"""正式赛总分的快速近似：门禁罚分 + n30_rank 评分（实打三项用引擎指法统计校准）。F 越小越好。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tournament'))
import n30_rank as R
import engine_eval as E

R.SCORE['字词冲突6万'] = (15, 631, 315)   # 作者 2026-10-01：全部字 × 虎码词库 6 万词（常用 4 万 + 新码位 2 万），按条数，软约束
LOW = {'字词冲突6万': -1.5}                  # 该项下限放宽，避免 NB46 一类方案被截断后失去梯度


def _score(m):
    total, parts = 0.0, {}
    for k, (w, zero, full_) in R.SCORE.items():
        x = max(LOW.get(k, -0.5), min(1.2, (m[k] - zero) / (full_ - zero)))
        parts[k] = round(100 * x, 1); total += w * x
    return total, parts
CAL = json.load(open(Path(__file__).parent / 'calib.json'))
B = E.META['layout']; G = E.META['groups']


def full(w, lay):
    w.p.stdin.write(json.dumps(lay) + '\n'); w.p.stdin.flush()
    s = json.loads(w.p.stdout.readline())
    lines = []
    while True:
        l = w.p.stderr.readline()
        if l.startswith('BATCH_END'):
            break
        lines.append(l)
    import re
    r = {}
    y = [l for l in lines if l.startswith('YOZAKURA exclusive')][-1]
    r['excl'] = json.loads(re.search(r'exclusive=(\[[^\]]*\])', y).group(1))
    r['mutex'] = int(re.search(r'mutex=(\d+)', y).group(1))
    sh = dict(re.findall(r'(\w+)=([0-9.]+)', [l for l in lines if l.startswith('YOZAKURA_SHAPE')][-1]))
    r.update({k: float(v) for k, v in sh.items()})
    r['clash'] = json.loads([l for l in lines if l.startswith('YOZAKURA_CLASH')][-1].split(' ', 1)[1])
    m = s['metric']; cs, cf = m['characters_short'], m['characters_full']
    x = [cs['fingering'][1], cs['fingering'][3], cs['pair_equivalence'], cf['fingering'][1], cf['fingering'][3], cf['pair_equivalence'], 1.0]
    r['typing'] = {k: sum(a * b for a, b in zip(CAL[k], x)) for k in CAL}
    r['moved'] = sum(1 for g in G if lay[g] != B[g])
    r['gates'] = E.gates(r)
    pen = (r['excl'][2] + max(0, r['excl'][3] - 9) + r['clash'][0] + max(0, r['clash'][2] - 5)
           + max(0, r['four_top'] - 125) + r['mutex'])
    met = {'形码成本': r['cost'], 'p占比': r['p_share'], '撞码②': r['clash'][1], '撞码③': r['clash'][2], '三简': r['san'],
           '换键根组': r['moved'], '小指干扰%': r['typing']['小指干扰%'], '同指大跨排%': r['typing']['同指大跨排%'],
           '键均当量': r['typing']['键均当量'], '字词冲突6万': r['clash'][3]}
    r['S'], r['parts'] = _score(met)
    r['pen'] = pen
    r['F'] = 1000 * pen - r['S']
    return r
