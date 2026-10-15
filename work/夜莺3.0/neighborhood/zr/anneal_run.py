"""夜桜退火：自然码输入 build/out/zr31m，起点 3.1 NB46，换键代价相对 NB46（move_cost 可变），多种子。
用法：.venv/bin/python neighborhood/zr/anneal_run.py <move_cost,...> <种子数> [步数]"""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUTD = ROOT / 'runs/zr_anneal'   # 运行目录（runs/ 不入库）
INP = ROOT / 'build/out/zr31m'; T = OUTD; T.mkdir(parents=True, exist_ok=True)
ENGINE = ROOT / 'engine/target/release/chai'
NB46 = json.load(open(ROOT / 'release/NB46_form.json', encoding='utf-8'))['mapping']
mcs = [float(x) for x in sys.argv[1].split(',')]; seeds = int(sys.argv[2]); steps = int(sys.argv[3]) if len(sys.argv) > 3 else 100_000
jobs = [(mc, s) for mc in mcs for s in range(1, seeds + 1)]
live = {}
def launch(mc, s):
    d = T / f'mc{mc:g}_s{s}'
    if (d / 'done.txt').exists(): return None
    subprocess.run(['rm', '-rf', str(d)]); d.mkdir(parents=True)
    cfg = json.load(open(INP / 'run.json', encoding='utf-8'))
    cfg['optimization']['metaheuristic']['parameters']['steps'] = steps
    cfg['form']['mapping'].update({g: NB46[g] for g in cfg['form']['mapping'] if g.startswith('G')})
    for g, opts in cfg['generated_mapping_space'].items():
        if g.startswith('G'):
            for o in opts: o['score'] = 0.0 if o['value'] == NB46[g] else mc
    json.dump(cfg, open(d / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
    env = dict(os.environ, NIGHTINGALE_YOZAKURA=str(INP / 'yozakura.json'), NIGHTINGALE_TARGET_DIR=str(INP),
               NIGHTINGALE_TARGET_WEIGHT='0', NIGHTINGALE_TRIAL_SEED=str(20261013_000000 + int(mc) * 100 + s))
    return d, subprocess.Popen([str(ENGINE), 'optimize', 'run.json', '-e', str(INP / 'elements.yaml'), '-k', str(INP / 'distribution.txt'),
                                '-p', str(INP / 'equivalence.txt'), '-t', '1'], cwd=d, env=env,
                               stdout=subprocess.DEVNULL, stderr=open(d / 'stderr.log', 'w'))
t0 = time.time()
while jobs or live:
    while jobs and len(live) < int(os.environ.get('MAX_PAR', 4)):
        x = launch(*jobs.pop(0))
        if x: live[x[0]] = x[1]
    time.sleep(5)
    for d, p in list(live.items()):
        if p.poll() is not None:
            (d / 'done.txt').write_text(f'rc={p.returncode}\n'); del live[d]
            print(f'{time.time() - t0:.0f}s 完成 {d.name} rc={p.returncode}', flush=True)
