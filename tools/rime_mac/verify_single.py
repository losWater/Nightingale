from pathlib import Path
from collections import defaultdict
import json, random, shutil, subprocess, tempfile, re
from paths import ROOT
p = ROOT/'release-single'
schema_text = (p/'yeying25_single.schema.yaml').read_text()
assert 'lua_processor@*yeying25_single_period' not in schema_text
assert 'import_preset' not in schema_text.split('key_binder:',1)[1].split('recognizer:',1)[0]
assert 'lua_processor@*yeying25_single_prefix' not in schema_text
stage = Path(tempfile.mkdtemp(prefix='verify-single-', dir=ROOT))
shutil.copytree(p, stage, dirs_exist_ok=True)
shutil.copy2(p/'default.custom.yaml.example', stage/'default.custom.yaml')
table = defaultdict(list)
quick = []
for line in (ROOT/'upstream/nightingale-v25-symbo.txt').read_text().splitlines():
    code,position,symbol = re.fullmatch(r'([a-z]+),(\d+)=(.+)',line).groups()
    quick.append((code,int(position),symbol))
for line in (p/'yeying25_single.dict.yaml').read_text().split('...',1)[1].splitlines():
    if not line: continue
    char, code, weight = line.split('\t')
    assert len(char) == 1 or any(char==symbol and code==c for c,_,symbol in quick)
    assert not code.startswith(';')
    table[code].append(char)
codes = random.Random(25).sample(sorted(c for c in table if not c.startswith(';')), 500)
def quick_keys(code,position): return code + {1:'{space}',2:';',3:"'"}[position]
keys = ['ufk','oot','ait','niky','niky{space}','[{space}','~shuang','ni{F2}','ni{Tab}'] + [quick_keys(c,n) for c,n,_ in quick] + ['niky;']
english = ['ctrl', 'hello', 'control', 'hello_world', 'hello123']
keys += english + [word+'{space}' for word in english] + ['ctrl{BackSpace}', 'ctrl{Escape}']
keys += ['zi{space}', 'zid{space}', 'zip{space}']
period_commits = {'f.':'发。', 'f,':'发，', 'dv.':'对。', 'rj.':'然。',
                  'd.v':'的。', 'r.j':'人。', 'niky{Right}.':'伱。',
                  'hello.world{space}':'hello.world', 'ct.':'ct。', '.':'。',
                  # ASCII punctuation is passed through to the host by native Rime;
                  # the probe only captures the candidate's commit, not the host key.
                  'f{Control+period}.':'发'}
keys += list(period_commits)
paging_code = next(code for code in sorted(table) if len(table[code]) > 9)
keys += ['{Control+period}', paging_code+'=', paging_code+'=-', paging_code+'=.', paging_code+'=,']
proc = subprocess.run([str(ROOT/'rime_probe'),str(stage),'yeying25_single','--deploy']+codes+keys,
                      capture_output=True,text=True,timeout=60)
assert proc.returncode == 0, proc.stderr
results, commits = {}, {}
for line in proc.stdout.splitlines():
    row = line.split('\t')
    if row[0] == 'COMMIT': commits[row[1]] = row[2]
    elif row[0] != 'METRICS': results[row[0]] = row[2:]
for code in codes:
    assert results[code][0] == code, (code,results[code])
    assert results[code][1:] == table[code][:9], (code,results[code],table[code])
    assert code not in commits
assert commits['niky{space}'] == commits['[{space}'] == '你'
assert results['~shuang'][0] == '~shuang' and '双' in results['~shuang'][1:]
assert results['ni{F2}'][0] == '~~ni'
assert results['ni{Tab}'][0] == ''
for code,position,symbol in quick:
    assert table[code][position-1] == symbol
    key = quick_keys(code,position)
    assert commits[key] == symbol, (key,commits.get(key),symbol)
    assert results[key][0] == '', (key,results[key])
assert commits['niky;'] == table['niky'][1]
assert table['zi'][0] == '自' and '子' not in table['zi']
assert commits['zi{space}'] == '自'
assert commits['zip{space}'] == '子'
assert commits['zid{space}'] == '自'
for word in english:
    assert results[word][0] == word, (word,results[word])
    assert word not in commits, (word,commits[word])
    assert commits[word+'{space}'] == word, (word,commits.get(word+'{space}'))
assert results['ctrl{BackSpace}'][0] == 'ctr'
assert results['ctrl{Escape}'][0] == ''
for key, expected in period_commits.items():
    assert commits.get(key) == expected, (key,commits.get(key),expected)
assert results['d.v'][0] == 'v' and results['r.j'][0] == 'j'
assert results[paging_code+'='][1] == table[paging_code][9]
assert results[paging_code+'=-'][1] == table[paging_code][0]
assert commits[paging_code+'=.'] == table[paging_code][9] + '。'
assert commits[paging_code+'=,'] == table[paging_code][9] + '，'
for log in stage.glob('*ERROR*'): assert not log.read_text(),log.read_text()
sequence = ['f.', 'f,', 'dv.', 'rj.', 'rj.', 'rj,', 'd.g', 'r.j'] * 30
expected = {'f.':'发。','f,':'发，','dv.':'对。','rj.':'然。','rj,':'然，','d.g':'的。','r.j':'人。'}
repeated = subprocess.run([str(ROOT/'rime_probe'),str(stage),'yeying25_single']+sequence,
                          capture_output=True,text=True,timeout=60)
assert repeated.returncode == 0, repeated.stderr
commit_rows = []
for line in repeated.stdout.splitlines():
    row = line.split('\t')
    if row[0] == 'COMMIT':
        assert row[2] == expected[row[1]], row
        commit_rows.append(row[1])
    elif row[0] != 'METRICS':
        assert row[2] == {'d.g':'g','r.j':'j'}.get(row[0], ''), row
assert commit_rows == sequence, (len(commit_rows),len(sequence))
compiled = (stage/'build/yeying25_single.schema.yaml').read_text()
bindings = compiled.split('key_binder:',1)[1].split('menu:',1)[0]
assert 'accept: period,' not in bindings and 'accept: comma,' not in bindings
assert 'accept: minus, send: Page_Up' in bindings and 'accept: equal, send: Page_Down' in bindings
report = {'sampled_code_slots':len(codes),'single_character_rows':sum(map(len,table.values())),
          'consecutive_punctuation_cases':len(sequence),'tiger_paging_bindings':'passed',
          'quick_symbol_keys_verified':len(quick),'semicolon_second_selection':'passed',
          'english_guard':'passed',
          'period_commits_and_continuation':'passed',
          'manual_selection_lookup_history':'passed','test_directory':str(stage)}
(ROOT/'verification-single.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
