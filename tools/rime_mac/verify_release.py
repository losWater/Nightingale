"""Smoke-test the actual ZIP payloads using isolated librime directories."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from paths import ROOT
import release_checks

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('directory', type=Path)
a = p.parse_args()
for entry in json.loads((a.directory/'assets.json').read_text()):
    stage = Path(tempfile.mkdtemp(prefix='verify-release-', dir=ROOT))
    with zipfile.ZipFile(a.directory/entry['name']) as z:
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(stage)
    manifest = json.loads((stage/'manifest.json').read_text())
    schema = manifest['schema']
    # 只做用户会做的事：解压 + 部署（不复制、不改名任何文件）
    inputs, commits, sentence, punct = release_checks.checks(stage, schema)   # 测试码取自包内码表，不写死版本
    r = subprocess.run([str(ROOT/'rime_probe'), str(stage), schema, '--deploy']+inputs,
                       capture_output=True, text=True, timeout=120, check=True,
                       env={**os.environ, 'SHOW_SOURCE': '1'})
    for keys, text in commits + (punct or []):
        assert f'COMMIT\t{keys}\t{text}' in r.stdout, (keys, text, r.stdout[-4000:])
    if sentence:
        assert sentence[1] in r.stdout and '\tV5' in r.stdout, r.stdout[-4000:]
    assert schema in release_checks.deployed_schemas(stage), ('解压部署后方案不在切换列表里', schema)
    assert not release_checks.deploy_errors(stage), release_checks.deploy_errors(stage)
    print(entry['name'], 'PASS', stage, flush=True)

# 先后解压几个包到同一个用户文件夹再部署：每个方案都要还在切换列表里、都能打字
entries = json.loads((a.directory/'assets.json').read_text())
for order in (entries, entries[::-1]):
    stage = Path(tempfile.mkdtemp(prefix='verify-release-all-', dir=ROOT))
    schemas = []
    for entry in order:
        with zipfile.ZipFile(a.directory/entry['name']) as z:
            z.extractall(stage)
            schemas.append(json.loads(z.read('manifest.json'))['schema'])
    args = [str(ROOT/'rime_probe'), str(stage), schemas[0], '--deploy']
    for s in schemas:
        args += [f'--switch={s}', release_checks.checks(stage, s)[1][0][0]]
    r = subprocess.run(args, capture_output=True, text=True, timeout=180, check=True)
    listed = release_checks.deployed_schemas(stage)
    assert all(s in listed for s in schemas), ('先后安装后有方案被挡住', schemas, listed)
    assert r.stdout.count('COMMIT\t') == len(schemas), r.stdout[-2000:]
    assert not release_checks.deploy_errors(stage), release_checks.deploy_errors(stage)
    print('先后安装', ' → '.join(schemas), 'PASS', flush=True)
