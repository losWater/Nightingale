"""Build all three Mac schemes from active masters. Never installs or publishes."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from context import load, sha, atomic, json_bytes
from export import export

def build(root=None, verify=False):
    root, active, meta = load(root,writable=True)
    for name in ('rime-mohu-flypy-latest.zip','mohu-sentence-ngram-v5.bin.zip'):
        if not (root/'.cache/rime'/name).is_file(): raise FileNotFoundError('缺少本地依赖 '+name)
    mac = export(root)
    code = root/'tools/rime_mac'
    env = {**os.environ,'NIGHTINGALE_REPO':str(root)}
    # Generated directories must not retain files removed by later builds.
    # Recoverable move, never delete a broad directory.
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    for name in ('package','package-v5','release-dual','release-shape','release-single'):
        p = mac/name
        if p.exists():
            backup = active/'备份/构建'/stamp; backup.mkdir(parents=True,exist_ok=True)
            shutil.move(str(p),backup/name)
    for script in ('build.py','build_v5.py','build_single.py'):
        subprocess.run([sys.executable,str(code/script)],env=env,check=True)
    # Stable schema/user-data identifiers retain compatibility; display version is dynamic.
    for directory in ('package','package-v5','release-dual','release-shape','release-single'):
        out = mac/directory
        for p in out.rglob('*'):
            if p.is_file() and p.suffix in ('.yaml','.md'):
                text = p.read_text()
                text = text.replace('夜莺2.5','夜莺'+meta['version']).replace('夜莺 2.5','夜莺 '+meta['version'])
                text = text.replace('"2.5-', '"'+meta['version']+'-')
                p.write_text(text)
        manifest = {'version':meta['version'],'source':json.loads((active/'产物/生成清单.json').read_text()),
                    'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                             if p.is_file() and p.name not in ('manifest.json','v5-manifest.json')}}
        atomic(out/'manifest.json',json_bytes(manifest))
    if verify:
        subprocess.run(['clang','-O2',str(code/'rime_probe.c'),'-o',str(mac/'rime_probe')],check=True)
        for script in ('verify_single.py','verify_shape.py','verify_v5.py'):
            subprocess.run([sys.executable,str(code/script)],env=env,check=True)
    record = {'time':datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
              'version':meta['version'],'operation':'build_mac','verified':verify,
              'source_manifest_sha256':sha(active/'产物/生成清单.json')}
    with (active/'记录/构建记录.jsonl').open('a') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n')
    print('生成完成，未安装。目录：',mac/'release-dual')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root');p.add_argument('--verify',action='store_true')
    a=p.parse_args();build(a.root,a.verify)
