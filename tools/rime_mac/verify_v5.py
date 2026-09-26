"""Real Squirrel librime tests: model provenance, fixed order, latency, fallback."""
from collections import defaultdict
from pathlib import Path
import json
import os
import random
import shutil
import subprocess
import tempfile

from paths import ROOT, VERSION
PACKAGE = ROOT / 'package-v5'

def sandbox():
    directory = Path(tempfile.mkdtemp(prefix='verify-v5-', dir=ROOT))
    shutil.copytree(PACKAGE, directory, dirs_exist_ok=True, ignore=shutil.ignore_patterns('model'))
    (directory / 'yeying25_v5/model').symlink_to(PACKAGE / 'yeying25_v5/model', target_is_directory=True)
    (directory / 'default.custom.yaml').write_text('patch:\n  schema_list:\n    - schema: yeying25_v5\n    - schema: yeying25_mac\n')
    return directory

def run(directory, inputs, schema='yeying25_v5', deploy=False, short=False):
    cmd = [str(ROOT / 'rime_probe'), str(directory), schema]
    if deploy: cmd.append('--deploy')
    env = {**os.environ, 'SHOW_SOURCE': '1'}
    if short: env['SHORT_WORDS'] = '1'
    p = subprocess.run(cmd + inputs, capture_output=True, text=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr
    results, sources, commits, metrics = {}, defaultdict(dict), {}, None
    for line in p.stdout.splitlines():
        items = line.split('\t')
        if items[0] == 'SOURCE': sources[items[1]][int(items[2])] = items[3]
        elif items[0] == 'COMMIT': commits[items[1]] = items[2]
        elif items[0] == 'METRICS': metrics = items[1:]
        else: results[items[0]] = items[2:]
    return results, sources, commits, metrics, p

def main():
    fixed = defaultdict(list)
    for line in (PACKAGE / 'yeying25_mac_rime_fixed.dict.yaml').read_text().split('...', 1)[1].splitlines():
        if line and not line.startswith('#'):
            word, code, _ = line.split('\t')
            fixed[code].append(word)
    codes = ['ufk', 'oot', 'ait', 'yscz', 'sl', 'gm', 'hg', 'bt', 'nihc', 'urf']
    codes += random.Random(25).sample(sorted(c for c in fixed if c.isascii() and c.isalpha()), 250)
    texts = {
        'jbtmtmqihfhc': '今天天气很好',
        'woxihruurufa': '我喜欢输入法',
        'woxihryeyk': '我喜欢夜莺',
    }
    other = ['womfkeyiyiqixtxi', 'vegeuurufaviiiyikbqiuuruyivgjuhw',
             'jbtmtmqihfhcwoxihruurufa', 'wozdysshuujrdaizi',
             'nihcnkycjibuifmexmuh', 'woxihryeyk'*5, 'abcdefghijklmnopqrstuvwxyz',
             'woxihryeyk'*10]
    keys = ['ni;', "ni'", 'ni{F2}', 'ni{F2}b', 'ni{F2}{F2}', '~ni',
            'woxihryeyk{BackSpace}', 'woxihryeyk{Left}{Right}',
            'woxihryeyk{space}', 'woxihruurufa{Control+Return}',
            'jbtmtmqihfhc{Escape}', 'ni{Control+2}', 'ni']
    directory = sandbox()
    results, sources, commits, metrics, p = run(directory, codes + list(texts) + other + keys, deploy=True)
    (directory / 'probe-output.txt').write_text(p.stdout)
    (directory / 'probe-stderr.txt').write_text(p.stderr)
    for code in codes:
        expected = fixed[code][:9]
        assert results[code][1:1+len(expected)] == expected, (code, expected, results[code])
    for code, text in texts.items():
        assert results[code][1] == text, (code, results[code])
        assert sources[code][0] == 'V5', f'Model silently fell back: {code}'
        assert list(sources[code].values()).count('V5') <= 4
    assert commits['woxihryeyk{space}'] == '我喜欢夜莺'
    assert commits['woxihruurufa{Control+Return}'] == '我喜欢输入法'
    assert commits['ni;'] == '拿出' and commits["ni'"] == '你'
    assert results['ni{F2}'][0] == '~~ni' and '你' in results['ni{F2}'][1:]
    assert results['ni{F2}b'][0] == '~~nib'
    assert results['ni{F2}{F2}'][0] == 'ni'
    assert results['jbtmtmqihfhc{Escape}'][0] == ''
    assert results['ni'][1] == '拿出'
    assert float(metrics[1]) < 40 and float(metrics[2]) < 250, metrics
    assert (directory / 'yeying25_v5/config/user-ngram.snapshot').stat().st_size > 0
    for log in directory.glob('*ERROR*'):
        assert not log.read_text(), log.read_text()
    short_results, short_sources, _, _, _ = run(directory, ['wxhni'], short=True)
    assert short_results['wxhni'][1] == '我喜欢你'
    assert 'V5' not in short_sources['wxhni'].values()
    restarted, restarted_sources, _, _, _ = run(directory, ['woxihryeyk', 'ni'])
    assert restarted_sources['woxihryeyk'][0] == 'V5'
    assert restarted['ni'][1] == '拿出'
    baseline, _, _, _, _ = run(directory, list(texts), schema='yeying25_mac')
    # Intentionally point the model at an absent path, in this disposable test
    # directory only; model load failure must retain usable Rime candidates.
    (directory / 'yeying25_v5.custom.yaml').write_text('patch:\n  tiger/model: /nonexistent/nightingale-v5-test.bin\n')
    fallback, fallback_sources, _, _, _ = run(directory, ['jbtmtmqihfhc'], deploy=True)
    assert fallback['jbtmtmqihfhc'][1] == '今天天气很好'
    assert 'V5' not in fallback_sources['jbtmtmqihfhc'].values()
    report = {
        'version': VERSION, 'engine': 'Squirrel 1.1.2 / librime 1.16.0 / arm64',
        'model_candidates_verified': True, 'fixed_candidate_samples': len(codes),
        'measured_key_events': int(metrics[0]), 'key_latency_p95_ms': float(metrics[1]),
        'key_latency_max_ms': float(metrics[2]),
        'examples': {code: {'baseline': baseline[code][1], 'v5': results[code][1]} for code in texts},
        'selection_lookup_commit_pin_restart': 'passed', 'missing_model_fallback': 'passed',
        'short_mode_fallback': 'passed', 'test_directory': str(directory)}
    (ROOT / 'verification-v5.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
