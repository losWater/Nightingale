"""只在过门禁的方案之间拟合：起点为各过门禁方案，随机挪 1–3 组，保留仍过门禁的。目标 = 近似总分 S。"""
import json, sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../neighborhood'))
os.environ.setdefault('NB_INP', 'n30w')
import engine_eval as E
from batch_eval import Worker
from proxy import full
from fit import feats, G, KEYS
c = {x['moved']: x['layout'] for x in json.load(open(E.ROOT / 'neighborhood/curve.json'))}
w65 = {x['moved']: x['layout'] for x in json.load(open(E.ROOT / 'neighborhood/w65.json'))}
starts = [('冠军', E.champion())] + [(f'NB{n}', c[n]) for n in (40, 43, 46, 50, 57)] + [(f'W{n}', w65[n]) for n in (47, 50, 55, 59, 63)]
wk = Worker(); rng = random.Random(7)
X, y, grp = [], [], []
for name, lay0 in starts:
    got = 0; tries = 0
    while got < 400 and tries < 6000:
        tries += 1
        lay = dict(lay0)
        for g in rng.sample(G, rng.choice([1, 1, 2, 3])):
            lay[g] = rng.choice(KEYS)
        r = full(wk, lay)
        if r['pen'] == 0:
            X.append(feats(lay)); y.append(r['S']); grp.append(name); got += 1
    print(name, got, '/', tries, flush=True)
np.savez(E.ROOT / 'construct/fit_ok.npz', X=np.array(X), y=np.array(y), grp=np.array(grp))
