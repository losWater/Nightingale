"""试算：新增一个归并根会怎样（不动正式数据，全部输出到独立目录）。
把指定字拆分里的一段（如 八＋㐅）合并成新根并入某根组，或换成已有字根（如 贝字框＋二 → 曰）；重建引擎输入 → NB46 重跑引擎 → 出表（含手动调整）→ 门禁 → 与正式表对比 → 实打统计。
用法：.venv/bin/python release/whatif_root.py <名字> <新根> <并入组> <原序列,逗号分隔> [只作用于这些字 | -排除这些字]
例：  .venv/bin/python release/whatif_root.py fuA 父 G007 八,㐅 父爸爷爹斧釜
"""
import collections, json, os, subprocess, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval'))
from real_typing import run as real_typing

name, root, group, pat = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',')
sel = sys.argv[5] if len(sys.argv) > 5 else ''
only = set(sel) if sel and not sel.startswith('-') else None
skip = set(sel[1:]) if sel.startswith('-') else set()
OUT = ROOT / 'build/out' / f'wi_{name}'; RUN = ROOT / 'runs/whatif' / name; TBL = RUN / 'table'
PY = str(ROOT / '.venv/bin/python')

# 1. 改拆分
sp = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
changed = []
for c, rs in sp.items():
    if (only is not None and c not in only) or c in skip: continue
    n = [x[0] for x in rs]
    for i in range(len(n) - len(pat) + 1):
        if n[i:i + len(pat)] == pat:
            sp[c] = rs[:i] + [[root, '?']] + rs[i + len(pat):]; changed.append(c); break
RUN.mkdir(parents=True, exist_ok=True)
spath = RUN / 'splits.json'
json.dump(sp, open(spath, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'改拆分 {len(changed)} 字：{"".join(changed)}')

# 2. 引擎输入
known = {r for rs in json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))['groups'].values() for r in rs}
env = dict(os.environ, YZ_SPLITS=str(spath), YZ_EXTRA_ROOTS=json.dumps({} if root in known else {group: [root]}, ensure_ascii=False),   # 已有字根（如 曰）不重复加
           YZ_FIX=str(ROOT / 'data/inputs/一二简.json'))
w = (ROOT / 'build/out/n30/weights.json').read_text(encoding='utf-8')
subprocess.run([PY, str(ROOT / 'build/make_inputs.py'), OUT.name, w], env=env, check=True, stdout=subprocess.DEVNULL)

# 3. NB46 重跑引擎
cfg = json.load(open(OUT / 'run.json', encoding='utf-8'))
cfg['form'] = json.load(open(ROOT / 'runs/n30_v30/nb46_fu/run.json', encoding='utf-8'))['form']
for o in RUN.glob('output-*'): subprocess.run(['rm', '-rf', str(o)])
json.dump(cfg, open(RUN / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
eenv = dict(os.environ, NIGHTINGALE_YOZAKURA=str(OUT / 'yozakura.json'), NIGHTINGALE_TARGET_DIR=str(OUT), NIGHTINGALE_TARGET_WEIGHT='0')
subprocess.run([str(ROOT / 'engine/target/release/chai'), 'encode', 'run.json', '-e', str(OUT / 'elements.yaml'),
                '-k', str(OUT / 'distribution.txt'), '-p', str(OUT / 'equivalence.txt')], cwd=RUN, env=eenv,
               stdout=subprocess.DEVNULL, stderr=open(RUN / 'stderr.log', 'w'), check=True)

# 4. 出表（含手动调整）
tenv = dict(env, YZ_INP=OUT.name, YZ_MANUAL=str(ROOT / 'data/inputs/手动调整.json'))
subprocess.run([PY, str(ROOT / 'build/make_plain_table.py'), str(RUN), str(TBL), 'xiaohe'], env=tenv, check=True, stdout=subprocess.DEVNULL)
new = next(TBL.glob('*.txt'))

# 5. 门禁
print('== 门禁（试算）'); subprocess.run([PY, str(ROOT / 'release/check_table.py'), str(new), '1'], env=tenv, check=True)
print('== 门禁（现行）'); subprocess.run([PY, str(ROOT / 'release/check_table.py'), str(ROOT / 'release/tables/普通单字表.txt'), '1'], check=True)

# 6. 对比
def load(p):
    d = collections.defaultdict(list)
    for l in open(p, encoding='utf-8'):
        ch, c = l.rstrip('\n').split('\t'); d[ch].append(c)
    return d
old, nw = load(ROOT / 'release/tables/普通单字表.txt'), load(new)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
fr = collections.Counter()
for e in E:
    if e['拼音'] != 'reserved': fr[e['词']] += e['频率']
tot = sum(fr.values())
diff = sorted((c for c in set(old) | set(nw) if sorted(old.get(c, [])) != sorted(nw.get(c, []))), key=lambda c: -fr[c])
print(f'\n== 码变化的字 {len(diff)} 个（按字频）')
for c in diff:
    o, n = sorted(old.get(c, []), key=len), sorted(nw.get(c, []), key=len)
    print(f'  {c} {1e6 * fr[c] / tot:7.1f}/百万  {"/".join(o)}  →  {"/".join(n)}')

# 7. 实打
a, b = real_typing(str(ROOT / 'release/tables/普通单字表.txt'), 'xiaohe'), real_typing(str(new), 'xiaohe')
print('\n== 实打（6 套 88 万字）')
for k in ('字均键数', '键均当量', '四码%', '选重%', '小指干扰%', '同指大跨排%'):
    print(f'  {k}: {a[k]:.4f} → {b[k]:.4f}')
