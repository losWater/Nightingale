"""把正向路径上的若干状态做成运行目录，用正式赛评测（实打 set1–5 平均）与评分。"""
import json, os, subprocess, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parent.parent / 'tournament'))
import engine_eval as E
import n30_eval as NE, n30_rank as R

OUT = E.ROOT / 'runs/n30_fw'
NE.T = OUT
fw = json.load(open(Path(__file__).parent / 'forward.json', encoding='utf-8'))
steps = [int(x) for x in sys.argv[1:]]
lay = dict(E.META['layout'])
for p in fw['path'][1:]:
    for g, _, _, k in p['move']:
        lay[g] = k
    if p['step'] in steps:
        jid = f"fw{p['n']:02d}"
        d = OUT / jid; d.mkdir(parents=True, exist_ok=True)
        cfg = json.loads(json.dumps(E.BASE)); cfg['form']['mapping'].update(lay)
        json.dump(cfg, open(d / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
        for o in d.glob('output-*'):
            subprocess.run(['rm', '-rf', str(o)])
        subprocess.run([str(E.ENGINE), 'encode', 'run.json', '-e', str(E.INP / 'elements.yaml'), '-k', str(E.INP / 'distribution.txt'),
                        '-p', str(E.INP / 'equivalence.txt')], cwd=d, env=E.ENV, stdout=subprocess.DEVNULL,
                       stderr=open(d / 'stderr.log', 'w'), check=True)
        ev = NE.evaluate(jid)
        ts = [NE.typing_only(jid, (k,)) for k in range(1, 6)]
        avg = {k: statistics.mean(t[k] for t in ts) for k in ts[0]}
        s, parts = R.score(R.metrics(ev, avg))
        fails = [k for k, v in ev['门禁'].items() if not v]
        print(jid, '步', p['step'], '换键', ev['换键根组'], '总分', round(s, 2), parts, '门禁失败', fails, flush=True)
