"""正式单字表重建：改了拆分（data/baseline/splits.json）、根组或手动调整之后跑这一条。
1. 重建引擎输入 build/out/n30（一二简固定取 data/inputs/一二简.json）
2. NB46 布局重跑引擎，结果固定放在 runs/n30_v30/current（不再每次另起目录）
3. 出普通单字表（含手动二简/三简 data/inputs/手动调整.json）→ release/tables/普通单字表.txt
4. 门禁（只作参考）＋ 与上一版表的码变化清单
用法：.venv/bin/python build/rebuild_table.py [--check 试算表]   # --check：核对新表与试算结果逐字节一致
"""
import collections, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / '.venv/bin/python')
INP = ROOT / 'build/out/n30'
RUN = ROOT / 'runs/n30_v30/current'
FORM = ROOT / 'release/NB46_form.json'                     # NB46 的引擎 form（布局），与具体哪次运行无关
TABLE = ROOT / 'release/tables/普通单字表.txt'
FIX = ROOT / 'data/inputs/一二简.json'
MANUAL = ROOT / 'data/inputs/手动调整.json'

if not FORM.exists():                                       # 首次：从现有运行取出 form 存档
    json.dump(json.load(open(ROOT / 'runs/n30_v30/nb46_fu/run.json', encoding='utf-8'))['form'], open(FORM, 'w', encoding='utf-8'), ensure_ascii=False)

# 1. 引擎输入
env = dict(os.environ, YZ_FIX=str(FIX))
w = (INP / 'weights.json').read_text(encoding='utf-8')
subprocess.run([PY, str(ROOT / 'build/make_inputs.py'), INP.name, w], env=env, check=True, stdout=subprocess.DEVNULL)

# 2. 引擎
if RUN.exists(): shutil.rmtree(RUN)
RUN.mkdir(parents=True)
cfg = json.load(open(INP / 'run.json', encoding='utf-8'))
cfg['form'] = json.load(open(FORM, encoding='utf-8'))
json.dump(cfg, open(RUN / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
eenv = dict(os.environ, NIGHTINGALE_YOZAKURA=str(INP / 'yozakura.json'), NIGHTINGALE_TARGET_DIR=str(INP), NIGHTINGALE_TARGET_WEIGHT='0')
subprocess.run([str(ROOT / 'engine/target/release/chai'), 'encode', 'run.json', '-e', str(INP / 'elements.yaml'),
                '-k', str(INP / 'distribution.txt'), '-p', str(INP / 'equivalence.txt')], cwd=RUN, env=eenv,
               stdout=subprocess.DEVNULL, stderr=open(RUN / 'stderr.log', 'w'), check=True)

# 3. 出表
tmp = RUN / 'table'
subprocess.run([PY, str(ROOT / 'build/make_plain_table.py'), str(RUN), str(tmp), 'xiaohe'], env=dict(env, YZ_MANUAL=str(MANUAL)), check=True, stdout=subprocess.DEVNULL)
new = next(tmp.glob('*.txt'))
if '--check' in sys.argv:
    ref = Path(sys.argv[sys.argv.index('--check') + 1])
    assert new.read_bytes() == ref.read_bytes(), f'新表与试算 {ref} 不一致'
    print('与试算逐字节一致')


def load(p):
    d = collections.defaultdict(list)
    for l in open(p, encoding='utf-8-sig'):
        if '\t' in l:
            ch, c = l.rstrip('\n').split('\t')[:2]; d[ch].append(c)
    return d


old, nw = load(TABLE), load(new)
diff = sorted(c for c in set(old) | set(nw) if sorted(old.get(c, [])) != sorted(nw.get(c, [])))
shutil.copy(new, TABLE)
print('码变化', len(diff), '字：', ' '.join(f'{c} {"/".join(sorted(old.get(c, []), key=len))}→{"/".join(sorted(nw.get(c, []), key=len))}' for c in diff))

# 4. 门禁（参考）
subprocess.run([PY, str(ROOT / 'release/check_table.py'), str(TABLE), '1'], check=True)
