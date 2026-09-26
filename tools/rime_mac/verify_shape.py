from collections import defaultdict
from pathlib import Path
import json
import os
import random
import shutil
import subprocess
import tempfile

from paths import ROOT, VERSION

def main():
    package = ROOT / 'release-shape'
    stage = Path(tempfile.mkdtemp(prefix='verify-shape-', dir=ROOT))
    shutil.copytree(package, stage, dirs_exist_ok=True)
    (stage / 'default.custom.yaml').write_text('patch:\n  schema_list:\n    - schema: yeying25_shape\n')
    fixed = defaultdict(list)
    for line in (package / 'yeying25_mac_rime_fixed.dict.yaml').read_text().split('...', 1)[1].splitlines():
        if line and not line.startswith('#'):
            word, code, _ = line.split('\t')
            fixed[code].append(word)
    sample = random.Random(25).sample(sorted(c for c in fixed if len(c) <= 4), 250)
    # Four-key entries must wait for selection or the next code letter.
    sample += [c for c in fixed if len(c) == 4 and len(fixed[c]) == 1][:50]
    sample += ['nihc', 'ufk', 'oot', 'ait', 'sl', 'gm', 'bt']
    page_code = next(c for c in sorted(fixed) if len(fixed[c]) > 9 and c.isalpha())
    keys = ['nihcn', 'nihcnihc{space}', '~shuang', '~shuang{space}', 'nihc{space}', '[{space}', ']{space}', 'ni;', "sl'", 'ni{Tab}',
            'ni{Right}{space}', 'ni{Right}{Left}{space}', '~ni', 'ni{F2}',
            'ni{F2}b', 'ni{F2}{F2}', page_code+'{equal}', page_code+'{equal}{minus}',
            'ni{Control+j}', 'ufk{Control+j}', 'nihc{Control+Return}',
            'ni{Control+2}', 'ni', 'sl{Control+o}', 'sl{Control+o}']
    cmd = [str(ROOT/'rime_probe'), str(stage), 'yeying25_shape']
    p = subprocess.run(cmd+['--deploy']+sample+keys, env={**os.environ, 'SHOW_SOURCE':'1'},
                       capture_output=True, text=True, timeout=60)
    (stage/'probe-output.txt').write_text(p.stdout)
    (stage/'probe-stderr.txt').write_text(p.stderr)
    assert p.returncode == 0, p.stderr
    result, source, commits, metrics = {}, defaultdict(dict), {}, None
    for line in p.stdout.splitlines():
        row = line.split('\t')
        if row[0] == 'SOURCE': source[row[1]][int(row[2])] = row[3]
        elif row[0] == 'COMMIT': commits[row[1]] = row[2]
        elif row[0] == 'METRICS': metrics = row[1:]
        else: result[row[0]] = row[2:]
    for code in sample:
        assert result[code][0] == code, ('input prematurely cleared', code, result[code])
        assert result[code][1:] == fixed[code][:9], (code, fixed[code][:9], result[code])
        assert code not in commits, ('unexpected auto commit', code)
    for key in ['nihc{space}', '[{space}', ']{space}', 'nihc{Control+Return}']:
        assert commits[key] == '你好', (key, commits.get(key))
    assert commits['nihcn'] == '你好' and result['nihcn'][0] == 'n'
    assert commits['nihcnihc{space}'] == '你好你好'
    assert result['~shuang'][0] == '~shuang' and '双' in result['~shuang'][1:]
    assert commits['ni;'] == '拿出' and commits["sl'"] == '思路'
    assert commits['ni{Right}{space}'] == '拿出'
    assert commits['ni{Right}{Left}{space}'] == '泥'
    assert result['ni{Tab}'][0] == ''
    assert result[page_code+'{equal}'][1:] == fixed[page_code][9:18]
    assert result[page_code+'{equal}{minus}'][1:] == fixed[page_code][:9]
    assert result['ni{F2}'][0] == '~~ni' and '你' in result['~ni'][1:]
    assert result['ni{F2}b'][0] == '~~nib'
    assert result['ni{F2}{F2}'][0] == 'ni'
    assert '氵' in source['ni{Control+j}'][0]
    assert result['ni'][1] == '拿出'
    assert not list(stage.glob('*v5*')) and not list(stage.rglob('*.dylib'))
    for error in stage.glob('*ERROR*'): assert not error.read_text(), error.read_text()
    assert float(metrics[1]) < 20
    report = {'version':VERSION, 'fixed_code_tests':len(sample),
              'four_key_manual_selection':'passed', 'fifth_key_commit':'passed', 'long_pinyin_lookup':'passed',
              'lookup_pin_history_navigation':'passed', 'model_dependencies':False,
              'measured_keys':int(metrics[0]), 'p95_ms':float(metrics[1]),
              'max_ms':float(metrics[2]), 'test_directory':str(stage)}
    (ROOT/'verification-shape.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
