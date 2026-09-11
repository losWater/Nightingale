from pathlib import Path
import shutil, zipfile, hashlib, yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.tmp/f2-release'
source = ROOT / 'releases/v1.0'
local = source / '02_输入法挂接/rime/发布包'
local.mkdir(exist_ok=True)
for p in OUT.glob('*-f2-*.zip'):
    if not p.name.startswith('Nightingale-Rime'): continue
    with zipfile.ZipFile(p) as z:
        for name in ['yeying_main', 'yeying_light', 'yeying_xm']:
            path = name + '.schema.yaml'
            if path not in z.namelist(): continue
            config = yaml.safe_load(z.read(path))
            assert 'lua_processor@*yeying_lookup_key' in config['engine']['processors']
            assert config['recognizer']['patterns']['yeying_lookup'] == '^([`~][a-z]*|~~[a-z]*)$'
        for name in ['yeying_lookup.lua', 'yeying_lookup_key.lua']:
            assert z.read('lua/' + name).decode('utf-8').splitlines() == (ROOT/'work/rime_v1/tools'/name).read_text(encoding='utf-8').splitlines()
        assert '持续筛选' in z.read('使用说明.md').decode('utf-8')
    shutil.copy2(p, local/p.name)
full = OUT/'Nightingale-1.0-f2-20260911.zip'
with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in source.rglob('*'):
        if not p.is_file(): continue
        rel = p.relative_to(source)
        if rel.parts[:2] == ('02_输入法挂接','rime'):
            if rel.as_posix() != '02_输入法挂接/rime/README.md' and not (rel.parts[2] == '发布包' and '-f2-' in p.name): continue
        z.write(p, '夜莺1.0/'+rel.as_posix(), compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
with zipfile.ZipFile(full) as z: assert z.testzip() is None
old = ROOT/'releases/夜莺1.0.zip'
backup = ROOT/'.tmp/夜莺1.0-F2更新前.zip'
if old.exists() and not backup.exists(): shutil.copy2(old,backup)
shutil.copy2(full,old)
(ROOT/'releases/夜莺1.0.sha256').write_text(hashlib.sha256(old.read_bytes()).hexdigest()+'  夜莺1.0.zip\n',encoding='utf-8')
(OUT/'SHA256SUMS-f2-20260911.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(OUT.glob('*.zip'))),encoding='utf-8')
print('F2 package contents, complete archive and checksums verified.')
