"""Build an isolated macOS baseline from the official Nightingale 2.5 release."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

from paths import ROOT, CODE, VERSION
ARCHIVE = ROOT / 'upstream/nightingale-2.5-light.zip'
OUT = ROOT / 'package'

def build():
    OUT.mkdir(exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as archive:
        for entry in archive.infolist():
            name = entry.filename
            if not (name.startswith('lua/') or name.endswith('.dict.yaml') or
                    name in ('yeying20_rime_fixed.schema.yaml', 'yeying20_rime_short.schema.yaml')):
                continue
            target = OUT / name.replace('yeying20', 'yeying25_mac')
            target.parent.mkdir(parents=True, exist_ok=True)
            text = archive.read(entry).decode('utf-8-sig').replace('yeying20', 'yeying25_mac')
            text = text.replace('2.0-20260915', '2.5-mac.1')
            target.write_text(text, encoding='utf-8', newline='\n')
    shutil.copy2(CODE / 'src/yeying25_mac.schema.yaml', OUT)
    shutil.copy2(CODE / 'src/yeying25_mac_rime_short.schema.yaml', OUT)
    # Only the selected native Rime translator is needed for this baseline.
    shutil.copy2(CODE / 'src/yeying25_mac_mix.lua', OUT / 'lua')
    # Updates to personal data should be atomic. Encoding must use full character
    # codes: a one-key shortcut is not necessarily the first letter of its sound.
    pin = OUT / 'lua/yeying25_mac_pin.lua'
    text = pin.read_text().replace("io.open(user_path(name), 'w')", "io.open(user_path(name) .. '.tmp', 'w')")
    text = text.replace("f:close()\n  return true\nend", "f:close()\n  return os.rename(user_path(name) .. '.tmp', user_path(name)) ~= nil\nend", 1)
    text = text.replace("for c in s:gmatch('%S+') do out[#out + 1] = c end", "for c in s:gmatch('%S+') do if #c == 4 and c:match('^[a-z]+$') then out[#out + 1] = c end end")
    pin.write_text(text)
    shutil.copy2(CODE / 'BASELINE-README.md', OUT / 'README.md')
    # Active masters replace every dictionary and reverse-lookup data from the adapter ZIP.
    for source in (ROOT/'generated').iterdir():
        shutil.copy2(source, OUT/'lua'/source.name if source.suffix=='.lua' else OUT/source.name)
    manifest = {
        'version': '2.5-mac.1',
        'source': 'https://github.com/losWater/Nightingale/releases/tag/v2.5',
        'source_asset': ARCHIVE.name,
        'source_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        'files': {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'manifest.json'},
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'Built {OUT}: {len(manifest["files"])} files')

if __name__ == '__main__':
    build()
