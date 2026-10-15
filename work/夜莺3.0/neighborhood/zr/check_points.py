"""把 greedy.json 中若干步的布局实际出表：分段当量（排除固定一二简，全码）、门禁（check_table）、实打。
用法：../../.venv/bin/python check_points.py 0 5 12 18 29"""
import glob, json, os, subprocess, sys, collections
from pathlib import Path
import yaml
import common as C
ROOT = C.ROOT; PY = str(ROOT / '.venv/bin/python'); INP = C.E.INP
sys.path.insert(0, str(ROOT / 'eval'))
from real_typing import run as rt
M = json.load(open(ROOT / 'eval/box/combo.json'))
Ev = yaml.load(open(INP / 'elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
meta = json.load(open(INP / 'meta.json', encoding='utf-8'))
N = sum(1 for e in Ev if e['拼音'] != 'reserved')
sel = [i for i in range(N) if not Ev[i].get('简码长度')]
curve = {c['step']: c for c in json.load(open(os.environ.get('CURVE', 'greedy.json'), encoding='utf-8'))}
curve.setdefault(0, {'layout': dict(C.B)})  # greedy.json 的第 0 步已含起点
for st in map(int, sys.argv[1:]):
    lay = curve[st]['layout']; R = Path(f"pts/{os.environ.get('TAG', '')}s{st}"); subprocess.run(['rm', '-rf', str(R)]); R.mkdir(parents=True)
    cfg = json.load(open(INP / 'run.json', encoding='utf-8')); cfg['form'] = json.loads(json.dumps(C.NB46)); cfg['form']['mapping'].update(lay)
    json.dump(cfg, open(R / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.run([str(C.E.ENGINE), 'encode', 'run.json', '-e', str(INP / 'elements.yaml'), '-k', str(INP / 'distribution.txt'),
                    '-p', str(INP / 'equivalence.txt')], cwd=R, env=C.E.ENV, capture_output=True, check=True)
    code = [l.split('\t')[1] for l in open(glob.glob(str(R / 'output-*/code.txt'))[0], encoding='utf-8')][:N]
    seg = {}
    for t in ('500', '1500', '3500'):
        idx = set(meta['tier_indices'][t]); s = [i for i in sel if i in idx]; W = sum(Ev[i]['频率'] for i in s)
        seg[t] = [sum(Ev[i]['频率'] * M[code[i][k:k + 2]]['eq'] for i in s) / W for k in range(3)]
    env = dict(os.environ, YZ_INP=INP.name, YZ_FIX=str(ROOT / 'data/inputs/一二简.json'), YZ_SCHEME='ziranma')
    subprocess.run([PY, str(ROOT / 'build/make_plain_table.py'), str(R), str(R / 'table'), 'ziranma'], env=env, check=True, capture_output=True)
    tb = glob.glob(str(R / 'table/*.txt'))[0]
    g = subprocess.run([PY, str(ROOT / 'release/check_table.py'), tb, '1'], env=env, capture_output=True, text=True).stdout
    t = rt(tb, 'ziranma')
    gl = [l.split(' [')[0] if '[' in l else l for l in g.splitlines()]
    print(f"== 步{st}（换键 {C.moved(lay)}）")
    print('  2→3 前500/1500/3500:', ' / '.join(f'{seg[x][1]:.4f}' for x in seg), '  3→4:', ' / '.join(f'{seg[x][2]:.4f}' for x in seg))
    print('  门禁:', g.replace('\n', ' | ')[:400])
    print('  实打: 键均当量 %.4f 字均当量 %.4f 大跨排 %.3f%% 小指干扰 %.3f%% 互击 %.2f%% 四码 %.2f%%' % (t['键均当量'], t['字均当量'], t['同指大跨排%'], t['小指干扰%'], t['互击%'], t['四码%']))
