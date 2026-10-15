"""评 runs/zr_anneal 下各次退火结果（自然码打分，换键相对 NB46）。"""
import glob, json, sys
from pathlib import Path
import yaml
import common as C
w = C.Worker(); rows = []
for d in sorted(glob.glob(str(C.ROOT / 'runs/zr_anneal/*/done.txt'))):
    d = Path(d).parent; outs = sorted(d.glob('output-*'))
    if not outs: continue
    m = yaml.load(open(outs[-1] / 'config.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)['form']['mapping']
    lay = {g: m[g] for g in C.G}; r = C.score(w, lay)
    rows.append((d.name, r, lay))
    print(f'{d.name:12s}', C.line(r), flush=True)
json.dump({n: l for n, _, l in rows}, open('anneal_layouts.json', 'w', encoding='utf-8'), ensure_ascii=False)
