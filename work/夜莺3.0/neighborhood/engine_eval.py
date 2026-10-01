"""用引擎 encode 给一个布局打分（与退火同一目标函数），解析 YOZAKURA 指标。
score(mapping_overrides) -> dict(total=引擎总分, 及各项)
"""
import json, os, re, subprocess, tempfile, glob
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / 'build/out' / os.environ.get('NB_INP', 'n30')
ENGINE = ROOT / 'engine/target/release/chai'
BASE = json.load(open(ROOT / 'runs/n30/g05q4s4/run.json', encoding='utf-8'))
META = json.load(open(INP / 'meta.json', encoding='utf-8'))
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
ENV = dict(os.environ, NIGHTINGALE_YOZAKURA=str(INP / 'yozakura.json'), NIGHTINGALE_TARGET_DIR=str(INP),
           NIGHTINGALE_TARGET_WEIGHT='0')


def champion():
    out = sorted((ROOT / 'runs/n30/g05q4s4').glob('output-*'))[0]
    m = yaml.load(open(out / 'config.yaml', encoding='utf-8'), Loader=L)['form']['mapping']
    return {k: m[k] for k in META['groups']}


def score(layout, keep=False):
    cfg = json.loads(json.dumps(BASE))
    cfg['form']['mapping'].update(layout)
    with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
        json.dump(cfg, open(Path(d) / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
        p = subprocess.run([str(ENGINE), 'encode', 'run.json', '-e', str(INP / 'elements.yaml'),
                            '-k', str(INP / 'distribution.txt'), '-p', str(INP / 'equivalence.txt')],
                           cwd=d, env=ENV, capture_output=True, text=True)
        txt = p.stdout + p.stderr
        if p.returncode:
            raise RuntimeError(txt[-500:])
        mj = json.load(open(glob.glob(d + '/output-*/metric.json')[0], encoding='utf-8'))
        r = {'total': mj['score'], 'move': mj['metric']['complexity'], 'q': mj['score'] - mj['metric']['complexity']}
        y = [l for l in txt.splitlines() if l.startswith('YOZAKURA exclusive')][-1]
        r['excl'] = json.loads(re.search(r'exclusive=(\[[^\]]*\])', y).group(1))
        r['mutex'] = int(re.search(r'mutex=(\d+)', y).group(1))
        r['yoz'] = float(re.search(r'total=([0-9.]+)', y).group(1))
        sh = dict(re.findall(r'(\w+)=([0-9.]+)', [l for l in txt.splitlines() if l.startswith('YOZAKURA_SHAPE')][-1]))
        r.update({k: float(v) for k, v in sh.items()})
        r['clash'] = json.loads([l for l in txt.splitlines() if l.startswith('YOZAKURA_CLASH')][-1].split(' ', 1)[1])
        if keep:
            r['code'] = open(glob.glob(d + '/output-*/code.txt')[0], encoding='utf-8').read()
        r['gates'] = gates(r)
        return r


def gates(r):
    g = {'撞①=0': r['clash'][0] == 0, '撞③≤5': r['clash'][2] <= 5, '1521重=0': r['excl'][2] == 0,
         '3571重≤9': r['excl'][3] <= 9, '四码≤125': r['four_top'] <= 125, '虫鸟': r['mutex'] == 0}
    return [k for k, v in g.items() if not v]


if __name__ == '__main__':
    import time
    t = time.time(); c = champion(); print(score(c), time.time() - t)
    t = time.time(); print(score(META['layout']), time.time() - t)
