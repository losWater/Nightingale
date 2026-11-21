"""夜桜单字表一条命令重建（夜莺改了拆分、根组、一二简、手动简码之后跑）：
1. 重建自然码引擎输入 build/out/zr31（权重同夜莺 n30，只换双拼；一二简取 data/inputs/一二简.json）
2. ZR27 布局跑引擎 encode（runs/zr27）
3. 出未套手动简码的表 → yozakura/port_manual.py 换算夜莺手动简码（报告争码双方全码手感，供复核）
4. 套 yozakura/手动调整.json 出正式表 → 门禁（实际选重口径）→ 与上一版的码变化清单 → 覆盖 yozakura/夜桜_ZR27_普通单字表.txt
用法：.venv/bin/python yozakura/rebuild.py [--dry]   # --dry：不覆盖留存表
"""
import collections, glob, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / '.venv/bin/python')
INP = ROOT / 'build/out/zr31'
RUN = ROOT / 'runs/zr27'
TABLE = ROOT / 'yozakura/夜桜_ZR27_普通单字表.txt'
FIX = ROOT / 'data/inputs/一二简.json'

# 1. 输入
w = json.load(open(ROOT / 'build/out/n30/weights.json', encoding='utf-8')); w['scheme'] = 'ziranma'
env = dict(os.environ, YZ_FIX=str(FIX))
subprocess.run([PY, str(ROOT / 'build/make_inputs.py'), INP.name, json.dumps(w)], env=env, check=True, stdout=subprocess.DEVNULL)

# 2. 引擎
if RUN.exists(): shutil.rmtree(RUN)
RUN.mkdir(parents=True)
cfg = json.load(open(INP / 'run.json', encoding='utf-8'))
cfg['form'] = json.load(open(ROOT / 'yozakura/ZR27_form.json', encoding='utf-8'))
json.dump(cfg, open(RUN / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
eenv = dict(os.environ, NIGHTINGALE_YOZAKURA=str(INP / 'yozakura.json'), NIGHTINGALE_TARGET_DIR=str(INP), NIGHTINGALE_TARGET_WEIGHT='0')
subprocess.run([str(ROOT / 'engine/target/release/chai'), 'encode', 'run.json', '-e', str(INP / 'elements.yaml'),
                '-k', str(INP / 'distribution.txt'), '-p', str(INP / 'equivalence.txt')], cwd=RUN, env=eenv,
               stdout=subprocess.DEVNULL, stderr=open(RUN / 'stderr.log', 'w'), check=True)
tenv = dict(env, YZ_INP=INP.name)


def make(out, manual=None):
    e = dict(tenv); e.pop('YZ_MANUAL', None)
    if manual: e['YZ_MANUAL'] = str(manual)
    subprocess.run([PY, str(ROOT / 'build/make_plain_table.py'), str(RUN), str(out), 'ziranma'], env=e, check=True, stdout=subprocess.DEVNULL)
    return Path(glob.glob(str(out / '*.txt'))[0])


# 3. 换算手动简码
base = make(RUN / 'table_base')
print('== 手动简码换算（夜莺 → 夜桜）', flush=True)
subprocess.run([PY, str(ROOT / 'yozakura/port_manual.py'), str(base)], check=True)

# 4. 正式表、门禁、码变化
new = make(RUN / 'table', ROOT / 'yozakura/手动调整.json')
print('\n== 门禁（实际选重口径）', flush=True)
subprocess.run([PY, str(ROOT / 'release/check_table.py'), str(new), '1'], env=dict(tenv, YZ_SCHEME='ziranma'), check=True)


def load(p):
    d = collections.defaultdict(list)
    for l in open(p, encoding='utf-8-sig'):
        x = l.rstrip('\n').split('\t')
        if len(x) >= 2: d[x[0]].append(x[1])
    return d


old, nw = load(TABLE), load(new)
diff = sorted(c for c in set(old) | set(nw) if sorted(old.get(c, [])) != sorted(nw.get(c, [])))
print(f'\n== 与上一版相比码变化 {len(diff)} 字：' + ' '.join(f"{c} {'/'.join(sorted(old.get(c, []), key=len))}→{'/'.join(sorted(nw.get(c, []), key=len))}" for c in diff))
if '--dry' not in sys.argv:
    shutil.copy(new, TABLE); print('已覆盖', TABLE)
