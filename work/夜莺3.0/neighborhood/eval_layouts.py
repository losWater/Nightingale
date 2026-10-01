"""用正式赛评测（实打 set1–5 平均）验证若干布局。用法：python eval_layouts.py <曲线上的换键数...>"""
import json, os, subprocess, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tournament'))
import engine_eval as E
import n30_eval as NE, n30_rank as R

OUT = E.ROOT / 'runs/n30_nb'; NE.T = OUT
curve = {c['moved']: c['layout'] for c in json.load(open(os.environ.get('CURVE', 'curve.json'), encoding='utf-8'))}
res = {}
for n in map(int, sys.argv[1:]):
    jid = os.environ.get('PREFIX', 'nb') + f'{n:02d}'; d = OUT / jid; d.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(json.dumps(E.BASE)); cfg['form']['mapping'].update(curve[n])
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
    res[jid] = {'总分': s, '分项': parts, '指标': R.metrics(ev, avg), '门禁失败': [k for k, v in ev['门禁'].items() if not v]}
    print(jid, round(s, 2), {k: round(v, 4) for k, v in R.metrics(ev, avg).items()}, res[jid]['门禁失败'], flush=True)
json.dump(res, open(os.environ.get('PREFIX', 'nb') + '_verified.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
