"""Read-only corpus audit and isolated A/B test of single-character prefix protection.

Writes only a new generated test directory. Never deploys to the user's Rime data.
"""
from collections import defaultdict, Counter
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from paths import ROOT, ACTIVE, CODE

source = ROOT / 'release-single'
stage = Path(tempfile.mkdtemp(prefix='prefix-ab-', dir=ROOT))
slots = defaultdict(list)
for row in (source/'yeying25_single.dict.yaml').read_text().split('...',1)[1].splitlines():
    if row:
        text, code, _ = row.split('\t')
        slots[code].append(text)
master = defaultdict(list)
for row in (ACTIVE/'主表/单字表.txt').read_text(encoding='utf-8-sig').splitlines():
    if row:
        text, code = row.split('\t')
        master[code].append(text)

def gaps(table):
    return {code: [code[:n] for n in range(1, len(code)) if code[:n] not in table]
            for code in sorted(table) if re.fullmatch('[a-z]{4}',code)
            and any(code[:n] not in table for n in range(1,len(code)))}

missing = gaps(slots)
summary = {'directory': str(stage), 'master_four_code_gaps':len(gaps(master)),
           'generated_four_code_gaps':len(missing),
           'missing_prefix_lengths':dict(Counter(len(p) for ps in missing.values() for p in ps)),
           'gaps':[{ 'code':c,'characters':slots[c], 'missing':ps,
                     'other_codes': {w:[k for k,vs in master.items() if w in vs] for w in slots[c]}}
                   for c,ps in missing.items()]}
print(json.dumps({k:v for k,v in summary.items() if k != 'gaps'},ensure_ascii=False),flush=True)
print(json.dumps(summary['gaps'][:12],ensure_ascii=False),flush=True)
codes = sorted(slots)

def run(path, sequences, deploy=False):
    out = subprocess.run([str(ROOT/'rime_probe'),str(path),'yeying25_single']
                         + (['--deploy'] if deploy else []) + sequences,
                         capture_output=True,text=True,timeout=60)
    if out.returncode: raise RuntimeError(out.stderr)
    results = {}
    for line in out.stdout.splitlines():
        r = line.split('\t')
        if r[0] == 'COMMIT': results.setdefault(r[1],{})['commit'] = r[2]
        elif r[0] != 'METRICS': results.setdefault(r[0],{}).update(input=r[2],candidates=r[3:])
    return results

all_results = {}
for variant in ('enabled','disabled'):
    path = stage/variant
    shutil.copytree(source,path)
    shutil.copy2(source/'default.custom.yaml.example',path/'default.custom.yaml')
    schema = path/'yeying25_single.schema.yaml'
    schema_text = schema.read_text().replace('    - lua_processor@*yeying25_single_prefix\n','')
    if variant == 'enabled':
        schema_text = schema_text.replace('    - key_binder\n','    - key_binder\n    - lua_processor@*yeying25_single_prefix\n',1)
        shutil.copy2(CODE/'src/yeying25_single_prefix.lua',path/'lua')
        prefixes = {code[:n] for code in slots for n in range(1,len(code)+1)}
        (path/'lua/yeying25_single_prefix_data.lua').write_text('return {' + ','.join('['+json.dumps(p)+']=true' for p in sorted(prefixes)) + '}\n')
    schema.write_text(schema_text)
    run(path,[],deploy=True)
    results = {}
    for i in range(0,len(codes),400):
        results.update(run(path,codes[i:i+400]))
        if i % 4000 == 0: print(f'{variant}: {min(i+400,len(codes))}/{len(codes)}',flush=True)
    checks = [c+'{space}' for c in missing]
    checks += ['rj.','dv.','f.','d.g','r.j','ctrl{space}','hello.world{space}','~shuang','ni{F2}']
    for i in range(0,len(checks),400): results.update(run(path,checks[i:i+400]))
    all_results[variant] = results
    (stage/(variant+'.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    bad = {c:r for c,r in results.items() if c in slots and
           (r.get('input') != c or r.get('candidates') != slots[c][:9] or r.get('commit'))}
    summary[variant] = {'tested_slots':len(codes),'mismatches':len(bad),'examples':dict(list(bad.items())[:15])}
    commit_failures = [c for c in missing if results[c+'{space}'].get('commit') != slots[c][0]
                       or results[c+'{space}'].get('input') != '']
    summary[variant]['gap_commit_failures'] = commit_failures
summary['differences'] = {c:{k:all_results[k].get(c) for k in all_results}
                          for c in all_results['enabled']
                          if all_results['enabled'][c] != all_results['disabled'].get(c)}
summary['source_hashes'] = {name:hashlib.sha256((source/name).read_bytes()).hexdigest()
                           for name in ('yeying25_single.dict.yaml','yeying25_single.schema.yaml')}
(stage/'report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('enabled','disabled')},ensure_ascii=False,indent=2),flush=True)
print('Differences:',len(summary['differences']),'Report:',stage/'report.json',flush=True)
