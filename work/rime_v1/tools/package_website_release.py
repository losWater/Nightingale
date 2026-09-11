"""Package the tested engines for the website launch, without local user state."""
from pathlib import Path
import zipfile, shutil, hashlib, json

ROOT = Path(__file__).resolve().parents[3]
B = ROOT / 'work/rime_v1'
OUT = ROOT / '.tmp/lookup-release'
OUT.mkdir(parents=True, exist_ok=True)
for kind, label in [('main', '主力V5版'), ('light', '轻量版')]:
    target = OUT / f'Nightingale-Rime-1.0-{kind}-lookup-20260911.zip'
    overrides = [f'yeying_{kind}.schema.yaml', 'lua/yeying_mix.lua', 'lua/yeying_lookup.lua', 'lua/yeying_lookup_data.lua']
    with zipfile.ZipFile(B / 'dist' / f'夜莺Rime1.0_{label}_test1.zip') as old, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as new:
        for entry in old.infolist():
            if entry.filename in ['user.yaml', 'default.custom.yaml.example', '使用说明.md']: continue
            if entry.filename in overrides: continue
            with old.open(entry) as src, new.open(entry.filename, 'w') as dst: shutil.copyfileobj(src, dst)
        new.write(B / 'packages' / kind / 'yeying_xm.schema.yaml', 'yeying_xm.schema.yaml')
        for relative in overrides: new.write(B / 'packages' / kind / relative, relative)
        schemas = ['yeying_light', 'yeying_xm']
        if kind == 'main':
            new.write(B / 'packages/light/yeying_light.schema.yaml', 'yeying_light.schema.yaml')
            schemas.insert(0, 'yeying_main')
        new.writestr('default.custom.yaml.example', 'patch:\n  schema_list:\n' + ''.join(f'    - schema: {s}\n' for s in schemas))
        notes = (B / 'packages' / kind / '使用说明.md').read_text(encoding='utf-8')
        notes += '\n\n本次网站发布包同时提供形码模式（固定码表、四码定长、五码顶屏）；主力包包含主力、轻量和形码三个方案，轻量包包含轻量和形码两个方案。形码模式不使用整句模型。\n'
        notes += '全新安装可按示例配置方案列表；已有配置请合并 schema_list，避免覆盖个人设置。本包不包含个人学习数据。\n'
        notes += '\n拆分反查：输入 ~ 或反引号，再输入全拼或小鹤双拼，如 ~han、~hj。候选旁显示规范拆分与四码。空格或数字选字，Esc取消；三个方案均支持，查询不调用整句模型。\n'
        new.writestr('使用说明.md', notes)
    with zipfile.ZipFile(target) as z: assert z.testzip() is None and 'user.yaml' not in z.namelist()
    print(target.name, target.stat().st_size, flush=True)
palm = OUT / 'Nightingale-Palm-1.0-20260911.zip'
with zipfile.ZipFile(palm, 'w', zipfile.ZIP_DEFLATED) as z:
    source = ROOT / 'releases/v1.0/02_输入法挂接/手心输入法'
    for path in source.rglob('*'):
        if path.is_file(): z.write(path, '手心输入法/' + path.relative_to(source).as_posix())
with zipfile.ZipFile(palm) as z: assert z.testzip() is None
lines = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name for p in sorted(OUT.glob('*.zip'))]
(OUT / 'SHA256SUMS-lookup-20260911.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print('Packages verified.', flush=True)
