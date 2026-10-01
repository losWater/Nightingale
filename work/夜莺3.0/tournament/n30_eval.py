"""夜莺 3.0 正式赛评测：逐个计算原始指标存 n30eval.json（与评分公式分离）。
指标：硬门禁（字词撞①③、前1521/3571 有效重码、前1500 四码、虫鸟）、形码成本、p 占比、三简数、字词撞②③、
换键根组数、实打（set0 或指定句子套）键均当量 / 小指干扰 / 同指大跨排 等。
用法：python tournament/n30_eval.py loop     # 循环评测新完成的方案，全部完成后退出
      python tournament/n30_eval.py one <id>
"""
import json, re, subprocess, sys, time
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval')); sys.path.insert(0, str(ROOT / 'build'))
import gates as GT
from real_typing import run as rt

T = ROOT / 'runs/n30'
INP = ROOT / 'build/out/n30'
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
GT.setup(str(INP))
META = json.load(open(INP / 'meta.json', encoding='utf-8'))
BASE = META['layout']; GROUPS = META['groups']


def evaluate(jid, sets=(0,)):
    d = T / jid
    out = sorted(d.glob('output-*'))[0]
    lines = (d / 'stderr.log').read_text(encoding='utf-8').splitlines()
    sh = dict(re.findall(r'(\w+)=([0-9.]+)', [l for l in lines if l.startswith('YOZAKURA_SHAPE')][-1]))
    clash = json.loads([l for l in lines if l.startswith('YOZAKURA_CLASH')][-1].split(' ', 1)[1])
    g = GT.analyse(GT.read_codes(str(out / 'code.txt')))
    m = yaml.load(open(out / 'config.yaml', encoding='utf-8'), Loader=L)['form']['mapping']
    moved = sum(1 for k in GROUPS if m[k] != BASE[k])
    tmp = Path('/tmp/n30t'); tmp.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / 'build/make_plain_table.py'), str(d), str(tmp), 'xiaohe'],
                   capture_output=True, check=True)
    table = tmp / f'夜桜_小鹤_{jid}_普通单字表.txt'
    typing = rt(str(table), 'xiaohe', sets=list(sets))
    table.unlink()
    res = {'id': jid, '形码成本': float(sh['cost']), '形码前1500': float(sh['top']), '形码1500后': float(sh['rest']),
           '四码': int(sh['four_top']), '三简': int(sh['san']), 'p占比': float(sh['p_share']),
           '撞码': clash, '前1521有效重码': g['前1500有效重码'], '前3571有效重码': g['前3500有效重码'],
           '全表重码对': g['全表重码对'], '虫鸟同键': g['虫鸟同键'], '换键根组': moved,
           '实打': {k: typing[k] for k in ('键均当量', '字均当量', '小指干扰%', '同指大跨排%', '同指小跨排%', '错手%',
                                         '选重%', '三码%', '四码%')},
           'layout': {k: m[k] for k in GROUPS}}
    res['门禁'] = {'字词撞①=0': clash[0] == 0, '字词撞③≤5': clash[2] <= 5, '前1521实际选重=0': res['前1521有效重码'] == 0,
                 '前3571实际选重≤9': res['前3571有效重码'] <= 9, '前1500四码≤125': res['四码'] <= 125,
                 '虫鸟不同键': not res['虫鸟同键']}
    json.dump(res, open(d / 'n30eval.json', 'w', encoding='utf-8'), ensure_ascii=False)
    return res


def typing_only(jid, sets):
    """只算实打指标（第二轮用），不写文件。"""
    d = T / jid
    tmp = Path(f'/tmp/n30r2_{jid}'); tmp.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / 'build/make_plain_table.py'), str(d), str(tmp), 'xiaohe'],
                   capture_output=True, check=True)
    t = rt(str(tmp / f'夜桜_小鹤_{jid}_普通单字表.txt'), 'xiaohe', sets=list(sets))
    return {k: t[k] for k in ('键均当量', '字均当量', '小指干扰%', '同指大跨排%', '同指小跨排%', '错手%', '选重%', '三码%', '四码%')}


def loop():
    jobs = [j['id'] for j in json.load(open(T / 'jobs.json', encoding='utf-8'))['jobs']]
    while True:
        for j in jobs:
            if (T / j / 'done.txt').exists() and not (T / j / 'n30eval.json').exists():
                try:
                    if 'rc=0' in (T / j / 'done.txt').read_text():
                        evaluate(j)
                    else:
                        json.dump({'id': j, 'failed': True}, open(T / j / 'n30eval.json', 'w'))
                    print(time.strftime('%H:%M'), j, '已评', flush=True)
                except Exception as e:
                    print(time.strftime('%H:%M'), j, '出错', repr(e), flush=True)
        if all((T / j / 'n30eval.json').exists() for j in jobs):
            print('全部评完', flush=True)
            return
        time.sleep(30)


if __name__ == '__main__':
    if sys.argv[1] == 'loop':
        loop()
    else:
        print(json.dumps({k: v for k, v in evaluate(sys.argv[2]).items() if k != 'layout'}, ensure_ascii=False, indent=1))
