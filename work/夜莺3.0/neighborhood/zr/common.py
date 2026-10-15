"""夜桜：以 3.1 NB46 为起点、自然码输入（build/out/zr31）的打分。移动量按相对 NB46 计。"""
import json, os, sys
from pathlib import Path
os.environ.setdefault('NB_INP', 'zr31')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import engine_eval as E
ROOT = E.ROOT
NB46 = json.load(open(ROOT / 'release/NB46_form.json', encoding='utf-8'))
E.BASE = json.load(open(E.INP / 'run.json', encoding='utf-8')); E.BASE['form'] = NB46
from batch_eval import Worker
import proxy, re
CAL = proxy.CAL
G = sorted(E.META['groups'])
B = {g: NB46['mapping'][g] for g in G}
NAME = {g: ''.join(E.META['groups'][g][:2]) for g in G}


def moved(lay):
    return sum(1 for g in G if lay[g] != B[g])


def score(w, lay):
    w.p.stdin.write(json.dumps(lay) + '\n'); w.p.stdin.flush()
    s = json.loads(w.p.stdout.readline())
    lines = []
    while True:
        l = w.p.stderr.readline()
        if l.startswith('BATCH_END'):
            break
        lines.append(l)
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
    r['nb_moved'] = moved(lay)
    r['pen'] = (r['excl'][2] + max(0, r['excl'][3] - 9) + r['clash'][0] + max(0, r['clash'][2] - 5)
                + max(0, int(r['four_top']) - 125) + r['mutex'])
    return r


def line(r):
    t = r['typing']
    return (f"换键{r['nb_moved']} 罚{r['pen']} 形{r['cost']:.4f} 撞{r['clash'][:3]} 重{r['excl'][2:]} "
            f"四{int(r['four_top'])} 三简{int(r['san'])} p{r['p_share']:.3f} 大跨≈{t['同指大跨排%']:.3f} 小指≈{t['小指干扰%']:.3f} 键均≈{t['键均当量']:.4f}")
