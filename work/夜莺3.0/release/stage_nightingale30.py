"""在独立目录搭一个“夜莺仓库”结构，放入 夜莺3.0 维护目录，供夜莺仓库的构建工具（tools/maintenance/build_mac.py --root）使用。
正式夜莺仓库不动：assets、.cache 用符号链接指向 ~/Nightingale；tools 复制一份并做两处处理：
  1. 标识去掉版本号：yeying25_ → yeying_（方案 id、文件名、Lua 模块、用户词库名；作者 2026-10-07：不要版本标识）。
  2. 验证脚本里写死的 2.5 测试码换成 3.0：子 zip→zie；尧/翘/悄 改为 yce、ycee、qneo、qnv（戈无点在 E）。
夜莺3.0/
  主表：单字表（3.0 普通单字表去符号 + 彩蛋码/容错码）、字词表（release/make_ciku.py）、符号表与快符（沿用 2.5）
  配置：编码类型（3.0 的彩蛋码、容错码）、单字版差异与词语读音（空，同 2.5）
  资料/拆分原本.html：3.0 啾啾工具箱（release/make_toolbox.py）
用法：python release/stage_nightingale30.py [搭台目录]
"""
import collections, json, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
NG = Path.home() / 'Nightingale'; N25 = NG / '夜莺2.5'
STAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.cache/yeying30-build'
V = STAGE / '夜莺3.0'


def rd(p): return [tuple(l.rstrip('\r\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


def render(rows): return ''.join(f'{t}\t{c}\n' for t, c in rows)


STAGE.mkdir(parents=True, exist_ok=True)
link = STAGE / 'assets'
if not link.exists(): link.symlink_to(NG / 'assets')
tools = STAGE / 'tools'
if tools.is_symlink(): tools.unlink()
if tools.exists(): shutil.rmtree(tools)
shutil.copytree(NG / 'tools', tools, ignore=shutil.ignore_patterns('__pycache__'))
for p in sorted(tools.rglob('*'), key=lambda p: -len(p.parts)):
    if p.is_file() and p.suffix in ('.py', '.yaml', '.lua', '.md', '.c', '.json', '.txt', '.sh'):
        t = p.read_text(encoding='utf-8')
        t2 = t.replace('yeying25_', 'yeying_')
        for a, b in (('releases/tag/v2.5', 'releases/tag/v3.0'), ('夜莺v2.5', '夜莺v3.0'), ('Nightingale v2.5', 'Nightingale v3.0'),
                     ('Nightingale 2.5', 'Nightingale 3.0')):        # 说明与注释里的版本号（build_mac 只替换“夜莺2.5”写法）
            t2 = t2.replace(a, b)
        if t2 != t: p.write_text(t2, encoding='utf-8')
    if 'yeying25_' in p.name: p.rename(p.with_name(p.name.replace('yeying25_', 'yeying_')))
TEST_PATCH = [('rime_mac/verify_single.py', "'zip{space}'", "'zie{space}'"),
              ('rime_mac/verify_release.py', "    inputs = ['ycv{space}', 'ycvp{space}', 'ycpp{space}', 'qnvo{space}', 'qnp{space}', 'qnpo', 'qnv{space}']",
               "    inputs = ['yce{space}', 'ycee{space}', 'qneo{space}', 'qnv{space}']"),
              ('rime_mac/verify_release.py', "    for keys, char in [('ycv{space}','尧'), ('ycvp{space}','尧'), ('ycpp{space}','尧'),\n                       ('qnvo{space}','翘'), ('qnp{space}','翘'), ('qnv{space}','悄')]:",
               "    for keys, char in [('yce{space}','尧'), ('ycee{space}','尧'), ('qneo{space}','翘'), ('qnv{space}','悄')]:")]
for f, a, b in TEST_PATCH:
    t = (tools / f).read_text(encoding='utf-8'); assert a in t, (f, a[:40]); (tools / f).write_text(t.replace(a, b), encoding='utf-8')
(STAGE / '.cache').mkdir(exist_ok=True)
if not (STAGE / '.cache/rime').exists(): (STAGE / '.cache/rime').symlink_to(NG / '.cache/rime')
(STAGE / 'maintenance.json').write_text(json.dumps({'active': '夜莺3.0'}, ensure_ascii=False, indent=2) + '\n')
for d in ('主表', '配置', '资料', '记录', '产物', '备份'): (V / d).mkdir(parents=True, exist_ok=True)
(V / '版本.json').write_text(json.dumps({'version': '3.0', 'status': 'active', 'note': '夜莺 3.0（NB46）试构建，由 Yozakura release/stage_nightingale30.py 搭台；不是正式维护目录。'},
                                       ensure_ascii=False, indent=2) + '\n')

# ---- 主表 ----
ci = rd(ROOT / 'release/tables/夜莺3.0_NB46_字词表.txt')
sym = rd(N25 / '主表/符号表.txt'); symset = set(sym)
single = [(t, c) for t, c in ci if len(t) == 1]          # 字词表里的单字（含彩蛋码、容错码），候选序同字词表
plain = [r for r in rd(ROOT / 'release/tables/夜莺3.0_NB46_普通单字表.txt') if r not in symset]
pos = {r: i for i, r in enumerate(plain)}
special = [r for r in single if r not in pos]
by_code = collections.defaultdict(list)
for t, c in plain + special: by_code[c].append(t)
single = [(t, c) for c in sorted(by_code) for t in by_code[c]]   # 单字表：同码按 3.0 普通单字表序，特殊码随后
(V / '主表/单字表.txt').write_text(render(single), encoding='utf-8')
(V / '主表/字词表.txt').write_text(render(ci), encoding='utf-8')
shutil.copy(N25 / '主表/符号表.txt', V / '主表/符号表.txt')
shutil.copy(N25 / '主表/快符.txt', V / '主表/快符.txt')

# ---- 配置 ----
info = json.load(open(ROOT / 'release/tables/夜莺3.0_NB46_字词表_说明.json', encoding='utf-8'))
types = [{'text': t, 'code': c, 'type': k} for t, c, k in info['特殊码']]
(V / '配置/编码类型.json').write_text(json.dumps({'source': 'Yozakura release/make_ciku.py 特殊码（3.0）', 'entries': types},
                                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(V / '配置/单字版差异.json').write_text('[]\n'); (V / '配置/词语读音.json').write_text('{}\n')
for f in ('码表概念与规则.md', '评估规则.md'):
    shutil.copy(N25 / '资料' / f, V / '资料' / f)

# ---- 拆分原本：3.0 啾啾工具箱（release/make_toolbox.py，六个视图全换 3.0）----
import subprocess, tempfile
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, str(ROOT / 'release/make_toolbox.py'), tmp], check=True)
    shutil.copy(Path(tmp) / '夜莺啾啾工具箱.html', V / '资料/拆分原本.html')
print('搭台', STAGE, '；单字表', len(single), '字词表', len(ci), '；特殊码', len(types))
