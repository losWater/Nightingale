"""校准：引擎指法统计 → 实打指标（256 组 n30 + 前向状态）。"""
import json, glob, numpy as np
from pathlib import Path
from batch_eval import Worker
import engine_eval as E

w = Worker()


def feats(lay):
    w.p.stdin.write(json.dumps(lay) + '\n'); w.p.stdin.flush()
    m = json.loads(w.p.stdout.readline())['metric']
    while not w.p.stderr.readline().startswith('BATCH_END'):
        pass
    cs, cf = m['characters_short'], m['characters_full']
    return [cs['fingering'][1], cs['fingering'][3], cs['pair_equivalence'], cf['fingering'][1], cf['fingering'][3], cf['pair_equivalence']]


X, Y, ids = [], [], []
for p in glob.glob(str(E.ROOT / 'runs/n30*/*/n30eval.json')):
    ev = json.load(open(p, encoding='utf-8'))
    if ev.get('failed') or 'layout' not in ev:
        continue
    X.append(feats(ev['layout'])); Y.append([ev['实打'][k] for k in ('同指大跨排%', '小指干扰%', '键均当量')]); ids.append(p)
X, Y = np.array(X), np.array(Y)
names = ['短大跨', '短干扰', '短当量', '全大跨', '全干扰', '全当量']
print('样本', len(X))
models = {}
for j, t in enumerate(('同指大跨排%', '小指干扰%', '键均当量')):
    print(t, '单项相关', {n: round(float(np.corrcoef(X[:, i], Y[:, j])[0, 1]), 3) for i, n in enumerate(names)})
    A = np.c_[X, np.ones(len(X))]
    coef, *_ = np.linalg.lstsq(A, Y[:, j], rcond=None)
    pred = A @ coef
    print('  线性拟合 R²', round(1 - ((Y[:, j] - pred) ** 2).sum() / ((Y[:, j] - Y[:, j].mean()) ** 2).sum(), 3), '残差标准差', round(float(np.std(Y[:, j] - pred)), 4), '目标标准差', round(float(Y[:, j].std()), 4))
    models[t] = coef.tolist()
json.dump(models, open('calib.json', 'w'), ensure_ascii=False)
