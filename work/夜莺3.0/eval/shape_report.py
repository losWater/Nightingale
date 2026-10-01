"""形码管得到的读音上的 2→3/3→4 当量（第二原则），连同门禁、重码、字词避重、三码覆盖、p 占比、实打（set0）一并对比。
用法：python eval/shape_report.py <运行目录>...  （另自动加入 2.5小鹤原版 与 2.5转自然码 参照）"""
import json, glob, sys, subprocess, collections
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'build')); sys.path.insert(0, str(ROOT / 'eval'))
import gates as GT
from real_typing import run as rt
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
GT.setup(str(ROOT / 'build/out/formal'))
E = GT.E; n = GT.N
f = [e['频率'] for e in E[:n]]; fixed = [bool(e.get('简码长度')) for e in E[:n]]
sel = [i for i in range(n) if not fixed[i]]; W = sum(f[i] for i in sel)
M = json.load(open(ROOT / 'eval/box/combo.json'))
BASE = str(sorted((ROOT / 'build/out/fixtest').glob('output-*'))[0] / 'code.txt')

def seg(C):
    return [sum(f[i] * M[C[i][k] + C[i][k + 1]]['eq'] for i in sel) / W for k in (0, 1, 2)]

def row(name, run, table=None):
    O = sorted(Path(run).glob('output-*'))[0]
    C = [l.split('\t')[1] for l in open(O / 'code.txt', encoding='utf-8')][:n]
    g = GT.check(str(O / 'code.txt'), BASE)
    cross = json.load(open(O / 'metric.json'))['metric']['character_word_collision']['soft']
    if table is None:
        subprocess.run([sys.executable, str(ROOT / 'build/make_plain_table.py'), str(run), '/tmp/sr'], capture_output=True)
        table = glob.glob(f'/tmp/sr/*{Path(run).name}_普通单字表.txt')[0]
    t = rt(table, 'ziranma', sets=[0])
    use = collections.Counter()
    for i in range(n):
        use[C[i][2]] += f[i]; use[C[i][3]] += f[i]
    p = use['p'] / sum(use.values())
    s12, s23, s34 = seg(C)
    return [name, s23, s34, g['前1500有效重码'], g['前3500有效重码'], g['全表重码对'], g['前6000三码内'], round(cross), 100 * p,
            t['键均当量'], t['同指大跨排%'], t['小指干扰%'], t['三码%']]

if __name__ == '__main__':
    rows = [row('2.5转自然码', ROOT / 'build/out/fixtest', str(ROOT / 'release/draft/夜桜_fixtest_普通单字表.txt'))]
    for r in sys.argv[1:]:
        rows.append(row(Path(r).parent.name.replace('shape', '') + '/' + Path(r).name, r))
    print('| 方案 | 2→3 | 3→4 | 前1521有效重码 | 前3571有效重码 | 全表重码对 | 前6000三码内 | 字词避重 | 三四码p% | 实打键均当量 | 实打大跨排% | 实打小指干扰% | 实打三码字% |')
    print('|---|' + '---|' * 12)
    for x in rows:
        print('| ' + ' | '.join(f'{v:.3f}' if isinstance(v, float) else str(v) for v in x) + ' |')
