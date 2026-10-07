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
    inputs = ['yce{space}', 'ycee{space}', 'qneo{space}', 'qnv{space}']   # 夜莺3.0：戈无点在 E 键
    if schema == 'yeying25_v5':
        inputs += ['woxihryeyk']
    r = subprocess.run([str(ROOT/'rime_probe'), str(stage), schema, '--deploy']+inputs,
                       capture_output=True, text=True, timeout=120, check=True,
                       env={**os.environ, 'SHOW_SOURCE': '1'})
    for keys, char in [('yce{space}','尧'), ('ycee{space}','尧'), ('qneo{space}','翘'), ('qnv{space}','悄')]:
        assert f'COMMIT\t{keys}\t{char}' in r.stdout, r.stdout
    if schema == 'yeying25_v5':
        assert '我喜欢夜莺' in r.stdout and '\tV5' in r.stdout, r.stdout
    for log in stage.glob('*ERROR*'):
        assert not log.read_text(), log.read_text()
    print(entry['name'], 'PASS', stage, flush=True)
