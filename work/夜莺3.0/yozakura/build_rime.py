"""夜桜 Rime Mac 三包一条命令：搭台（release/stage_rime.py + yozakura/rime_patch.py）→ 夜莺构建工具出包并验证 → 打包 → 发布验证（解压即用、不同安装顺序）
→ 复制到 ~/Downloads/<名称>_发布附件/。只在本地生成，不安装、不发布。
魔虎自然码运行库与发布信息放在 ~/.cache/yozakura-rime（rime-mohu-zrm-latest.zip、mohu-release.json；模型 zip 链接夜莺缓存）。
用法：.venv/bin/python yozakura/build_rime.py
"""
import os, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault('YZ_BRAND', str(ROOT / 'yozakura/品牌.json'))
sys.path.insert(0, str(ROOT / 'release'))
from config import C
PY = str(ROOT / '.venv/bin/python')
OUT = Path.home() / f'Downloads/{C.NAME}_发布附件'
run = lambda *a, **k: subprocess.run([str(x) for x in a], check=True, **k)
for name in ('rime-mohu-zrm-latest.zip', 'mohu-sentence-ngram-v5.bin.zip', 'mohu-release.json'):
    assert (C.RIME_CACHE / name).exists(), f'缺 {C.RIME_CACHE / name}'
print('== 搭台', flush=True); run(PY, ROOT / 'release/stage_rime.py')
print('== 构建与验证（约 2 分钟）', flush=True)
with open(C.STAGE / 'build.log', 'w') as log:
    run(PY, C.STAGE / 'tools/maintenance/build_mac.py', '--root', C.STAGE, '--verify', stdout=log, stderr=subprocess.STDOUT)
pub = C.MAC_OUT / 'publication' / C.STAMP
if pub.exists(): shutil.rmtree(pub)
print('== 打包与发布验证', flush=True)
run(PY, C.STAGE / 'tools/rime_mac/package_release.py', '--stamp', C.STAMP, cwd=C.STAGE,
    env=dict(os.environ, NIGHTINGALE_REPO=str(C.STAGE)), stdout=subprocess.DEVNULL)
run(PY, C.STAGE / 'tools/rime_mac/verify_release.py', pub, cwd=C.STAGE)
OUT.mkdir(parents=True, exist_ok=True)
for p in pub.iterdir():
    if p.name.endswith('.zip') or p.name.startswith('SHA256SUMS'): shutil.copy(p, OUT / p.name)
print('输出', OUT)
