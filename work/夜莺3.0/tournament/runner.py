"""夜桜正式赛第一轮：512 次退火（32 大组 × 4 小队 × 4 起点），权重统一，仅起点与种子不同。

起点（每小队 4 个）：random ×2（每个根组随机键）、proj（夜莺2.5 布局）、shuf50（随机一半根组各换一个不同的键）。
同时最多 MAX_PAR 个进程；每个任务完成写 done.txt；重启时跳过已完成任务（断点续跑）。

用法：python tournament/runner.py init   # 生成共享输入与任务表
      python tournament/runner.py run    # 执行（建议在 caffeinate -i 下）
"""
import json, os, random, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOUR = os.environ.get('TOUR', 'formal')              # 赛事名：runs/<TOUR>、build/out/<TOUR>
T = ROOT / 'runs' / TOUR
INP = ROOT / 'build/out' / TOUR
GROUPS = int(os.environ.get('GROUPS', 32))
SQUADS = int(os.environ.get('SQUADS', 4))
ENGINE = ROOT / 'engine/target/release/chai'
STEPS = 100_000
MAX_PAR = int(os.environ.get('MAX_PAR', 4))
WEIGHTS = {"fix25": True, "eff1500": 100, "eff3500": 10, "excl1500": 3, "excl3500": 1,
           "overload": 0, "rank_gate": 0, "eq23": 300, "eq34": 300, "cross": 1.0}
WEIGHTS.update(json.loads(os.environ.get('WEIGHTS_EXTRA', '{}')))
KEYS = 'abcdefghijklmnopqrstuvwxyz'


def init():
    subprocess.run([sys.executable, str(ROOT / 'build/make_inputs.py'), TOUR, json.dumps(WEIGHTS)], check=True)
    base = json.load(open(INP / 'run.json', encoding='utf-8'))
    base['optimization']['metaheuristic']['parameters']['steps'] = STEPS
    groups = sorted(k for k in base['form']['mapping'] if k.startswith('G'))
    proj = {g: base['form']['mapping'][g] for g in groups}
    jobs = []
    for g in range(1, GROUPS + 1):
        for q in range(1, SQUADS + 1):
            kinds = tuple(os.environ.get('SQUAD_KINDS', 'random,random,proj,shuf50').split(','))
            for s, kind in enumerate(kinds, 1):
                jid = f'g{g:02d}q{q}s{s}'
                seed = 20260930_000000 + g * 1000 + q * 10 + s + (0 if TOUR == 'formal' else 7_000_000)
                rng = random.Random(seed)
                if kind == 'random':
                    start = {k: rng.choice(KEYS) for k in groups}
                elif kind == 'proj':
                    start = dict(proj)
                else:
                    start = dict(proj)
                    frac = 4 if kind == 'shuf25' else 2      # shuf25：打乱 1/4；shuf50：打乱 1/2
                    for k in rng.sample(groups, len(groups) // frac):
                        start[k] = rng.choice([x for x in KEYS if x != proj[k]])
                jobs.append({'id': jid, 'group': g, 'squad': q, 'kind': kind, 'seed': seed, 'start': start})
    T.mkdir(parents=True, exist_ok=True)
    json.dump({'weights': WEIGHTS, 'steps': STEPS, 'jobs': jobs}, open(T / 'jobs.json', 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('任务', len(jobs), '共享输入', INP)


def launch(job):
    d = T / job['id']
    d.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(INP / 'run.json', encoding='utf-8'))
    cfg['optimization']['metaheuristic']['parameters']['steps'] = STEPS
    cfg['form']['mapping'].update(job['start'])
    json.dump(cfg, open(d / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
    env = dict(os.environ, NIGHTINGALE_YOZAKURA=str(INP / 'yozakura.json'), NIGHTINGALE_TARGET_DIR=str(INP),
               NIGHTINGALE_TARGET_WEIGHT='0', NIGHTINGALE_TRIAL_SEED=str(job['seed']))
    cmd = [str(ENGINE), 'optimize', 'run.json', '-e', str(INP / 'elements.yaml'), '-k', str(INP / 'distribution.txt'),
           '-p', str(INP / 'equivalence.txt'), '-t', '1']
    return subprocess.Popen(cmd, cwd=d, env=env, stdout=open(d / 'stdout.log', 'w'), stderr=open(d / 'stderr.log', 'w'))


def run():
    jobs = json.load(open(T / 'jobs.json', encoding='utf-8'))['jobs']
    todo = [j for j in jobs if not (T / j['id'] / 'done.txt').exists()]
    live = {}
    print(time.strftime('%H:%M'), '待跑', len(todo), '/', len(jobs), flush=True)
    while todo or live:
        while todo and len(live) < MAX_PAR:
            j = todo.pop(0)
            live[j['id']] = launch(j)
        time.sleep(5)
        for jid, p in list(live.items()):
            rc = p.poll()
            if rc is not None:
                d = T / jid
                if rc == 0:
                    # 只保留编码与指标，删去大体积日志以省空间
                    (d / 'stdout.log').unlink(missing_ok=True)
                (d / 'done.txt').write_text(f'rc={rc}\n')
                del live[jid]
                n = sum(1 for x in jobs if (T / x['id'] / 'done.txt').exists())
                print(time.strftime('%H:%M'), jid, f'rc={rc}', f'完成 {n}/{len(jobs)}', flush=True)


if __name__ == '__main__':
    {'init': init, 'run': run}[sys.argv[1]]()
