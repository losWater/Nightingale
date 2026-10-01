"""第一轮评测：对已完成的退火逐个计算原始指标并存 eval.json（与打分公式分离，改公式无需重算）。

每个方案计算两套口径：
- typed：实际打法（简码优先，引擎临时简码），与形码盒子惯例一致；
- full：只用全码（作者原则“简码无法预知，按全码看”）。
内容：门禁（gates.py）、形码盒子（两口径）、实打 set0（两口径）、字词避重软分、引擎分项、布局。
用法：python tournament/evaluate.py loop   # 循环处理新完成的方案，全部完成后退出
"""
import json, subprocess, sys, time, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval'))
from make_table import build
import type_sim
import yaml
sys.path.insert(0, str(ROOT / 'build'))
import gates as GT
GT.setup(str(ROOT / 'build/out/formal'))

T = ROOT / 'runs/formal'
INP = ROOT / 'build/out/formal'
EL = str(INP / 'elements.yaml')
BASE_CODE = sorted((ROOT / 'build/out/fixtest').glob('output-*'))[0] / 'code.txt'
NODE = str(ROOT / 'tools/node/bin/node')
S0 = json.load(open(ROOT / 'eval/sentences/set0.json', encoding='utf-8'))
R0 = json.load(open(ROOT / 'eval/sentences/set0.readings.json', encoding='utf-8'))


def box(items):
    with tempfile.TemporaryDirectory() as t:
        tab, out = Path(t) / 't.tsv', Path(t) / 'o.json'
        tab.write_text(''.join(f'{ch}\t{code}\n' for code, _, _, ch, _ in items), encoding='utf-8')
        subprocess.run([NODE, str(ROOT / 'eval/box/box_eval.mjs'), str(tab), str(out)], check=True)
        return json.load(open(out, encoding='utf-8'))


def evaluate(jid):
    d = T / jid
    out = sorted(d.glob('output-*'))[0]
    code = out / 'code.txt'
    g = GT.check(str(code), str(BASE_CODE))
    items = build(EL, str(code))
    res = {'id': jid, 'gates': g}
    for name, its in (('typed', items), ('full', full_only(items, code))):
        b = box(its)
        t = type_sim.simulate(type_sim.code_book(its), S0, R0)
        res[name] = {'box': b['sections'], 'type': t}
    m = json.load(open(out / 'metric.json', encoding='utf-8'))
    res['cross'] = m['metric']['character_word_collision']['soft']
    res['engine_score'] = m['score']
    y = [l for l in (d / 'stderr.log').read_text(encoding='utf-8').splitlines() if l.startswith('YOZAKURA')]
    res['yozakura'] = y[-1] if y else None
    cfg = yaml.safe_load(open(out / 'config.yaml', encoding='utf-8'))
    res['layout'] = {k: v for k, v in cfg['form']['mapping'].items() if k.startswith('G')}
    json.dump(res, open(d / 'eval.json', 'w', encoding='utf-8'), ensure_ascii=False)
    return res


def full_only(items, code_txt, elements=None):
    """全码口径：去掉引擎临时简码（三简等），只保留全码；
    固定一二简（已知、沿用 2.5）照常保留（作者 2026-10-01）。"""
    from make_table import load_elements
    E = load_elements(elements or EL)
    rows = [l.rstrip('\n').split('\t') for l in open(code_txt, encoding='utf-8')]
    keep = []
    for code, rank, i, ch, py in items:
        if code == rows[i][1] or (E[i].get('简码长度') and len(code) == E[i]['简码长度']):
            keep.append((code, rank, i, ch, py))
    return sorted(keep)


def loop():
    jobs = [j['id'] for j in json.load(open(T / 'jobs.json', encoding='utf-8'))['jobs']]
    while True:
        pending = [j for j in jobs if (T / j / 'done.txt').exists() and not (T / j / 'eval.json').exists()]
        for j in pending:
            if 'rc=0' not in (T / j / 'done.txt').read_text():
                json.dump({'id': j, 'failed': True}, open(T / j / 'eval.json', 'w'))
                continue
            try:
                evaluate(j)
                print(time.strftime('%H:%M'), j, '已评', flush=True)
            except Exception as e:
                print(time.strftime('%H:%M'), j, '评测出错', repr(e), flush=True)
        done = sum(1 for j in jobs if (T / j / 'eval.json').exists())
        if done == len(jobs):
            print('全部评完', flush=True)
            return
        time.sleep(30)


if __name__ == '__main__':
    if sys.argv[1] == 'loop':
        loop()
    else:
        print(json.dumps(evaluate(sys.argv[1]), ensure_ascii=False)[:2000])
