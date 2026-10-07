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
    shutil.copy2(stage/'default.custom.yaml.example', stage/'default.custom.yaml')
    inputs, commits, sentence, punct = release_checks.checks(stage, schema)   # 测试码取自包内码表，不写死版本
    r = subprocess.run([str(ROOT/'rime_probe'), str(stage), schema, '--deploy']+inputs,
                       capture_output=True, text=True, timeout=120, check=True,
                       env={**os.environ, 'SHOW_SOURCE': '1'})
    for keys, text in commits + (punct or []):
        assert f'COMMIT\t{keys}\t{text}' in r.stdout, (keys, text, r.stdout[-4000:])
    if sentence:
        assert sentence[1] in r.stdout and '\tV5' in r.stdout, r.stdout[-4000:]
    for log in stage.glob('*ERROR*'):
        assert not log.read_text(), log.read_text()
    print(entry['name'], 'PASS', stage, flush=True)
