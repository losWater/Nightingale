"""Assemble two public schemas; keep the earlier baseline as a local archive."""
from pathlib import Path
import hashlib
import json
import shutil

from paths import ROOT, CODE, VERSION
SOURCE = ROOT / 'package-v5'

def build():
    for flavor in ('dual', 'shape'):
        out = ROOT / ('release-' + flavor)
        out.mkdir(exist_ok=True)
        for source in SOURCE.rglob('*'):
            if not source.is_file(): continue
            rel = source.relative_to(SOURCE)
            name = str(rel)
            if name in ('yeying25_mac.schema.yaml', 'lua/yeying25_mac_mix.lua',
                        'manifest.json', 'v5-manifest.json', 'README.md'):
                continue
            if flavor == 'shape' and not (
                name in ('yeying25_mac_rime_fixed.schema.yaml', 'yeying25_mac_rime_fixed.dict.yaml') or
                name.startswith('lua/yeying25_mac_')):
                continue
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        shutil.copy2(CODE / 'src/yeying25_shape.schema.yaml', out)
        for name in ('yeying25_shape_table.lua', 'yeying25_shape_comment.lua', 'yeying25_shape_lookup_input.lua'):
            shutil.copy2(CODE / 'src' / name, out / 'lua')
        shutil.copy2(CODE / 'DUAL-README.md', out / 'README.md')
        choices = ['yeying25_v5', 'yeying25_shape'] if flavor == 'dual' else ['yeying25_shape']
        (out / 'default.custom.yaml.example').write_text(
            '# Merge schema_list entries into your existing configuration.\npatch:\n  schema_list:\n' +
            ''.join('    - schema: ' + schema + '\n' for schema in choices))
        (out / 'squirrel.custom.yaml.example').write_text(
            'patch:\n  style/candidate_list_layout: linear\n  style/text_orientation: horizontal\n')
        report = {'version': '2.5-mac-dual.1', 'schemas': choices,
                  'files': {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'manifest.json'}}
        (out / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(flavor, len(report['files']), choices)

if __name__ == '__main__': build()
