"""Add the verified MoHu V5 runtime; generate its lexicon from Nightingale data."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

from paths import ROOT, CODE, VERSION
UP = ROOT / 'upstream'
OUT = ROOT / 'package-v5'

def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def dict_rows(path):
    return [line.split('\t') for line in path.read_text().split('...', 1)[1].splitlines()
            if line and not line.startswith('#')]

def build():
    release = json.loads((UP / 'mohu-release.json').read_text())
    assets = {a['name']: a for a in release['assets']}
    for name in ('rime-mohu-flypy-latest.zip', 'mohu-sentence-ngram-v5.bin.zip'):
        assert 'sha256:' + sha(UP / name) == assets[name]['digest'], name
    shutil.copytree(ROOT / 'package', OUT, dirs_exist_ok=True)
    runtime = OUT / 'yeying25_v5/runtime'
    model = OUT / 'yeying25_v5/model'
    data = OUT / 'yeying25_v5/data'
    for directory in (runtime, model, data, OUT / 'yeying25_v5/config'):
        directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(UP / 'mohu-sentence-ngram-v5.bin.zip') as z:
        name = 'mohu-sentence-ngram-v5.bin'
        with z.open(name) as source, (model / name).open('wb') as dest:
            shutil.copyfileobj(source, dest)
    assert 'sha256:' + sha(model / name) == assets[name]['digest']
    with zipfile.ZipFile(UP / 'rime-mohu-flypy-latest.zip') as z:
        for name in ('libtigerengine.dylib', 'libonnxruntime.1.dylib'):
            (runtime / name).write_bytes(z.read('mohu/runtime/' + name))
        (OUT / 'LICENSE-mohu').write_bytes(z.read('LICENSE'))
        for name in ('mohu_tiger_sentence', 'mohu_runtime', 'mohu_personal_lexicon'):
            source = z.read('lua/' + name + '.lua').decode('utf-8-sig')
            # Private Lua module names and private model/user-state root. The
            # engine and its algorithms otherwise stay at the release version.
            for module in ('mohu_tiger_sentence', 'mohu_runtime', 'mohu_personal_lexicon'):
                source = source.replace(module, module.replace('mohu_', 'yeying25_v5_'))
            source = source.replace('"mohu"', '"yeying25_v5"').replace('"mohu/', '"yeying25_v5/')
            if name == 'mohu_tiger_sentence':
                needle = "Candidate(candidate_type, seg.start, seg._end, text, \"\")"
                assert needle in source
                source = source.replace(needle, "Candidate(candidate_type, seg.start, seg._end, text, \"V5\")")
                needle = '  local scheme = config_string(cfg, "tiger/scheme") or "zrm"'
                assert needle in source
                source = source.replace(needle,
                    '  candidate_limit = math.max(1, math.min(20, tonumber(config_string(cfg, "tiger/candidate_limit")) or 20))\n' + needle)
            (OUT / 'lua' / (name.replace('mohu_', 'yeying25_v5_') + '.lua')).write_text(source)
    shutil.copy2(CODE / 'src/yeying25_v5_mix.lua', OUT / 'lua')
    schema = (CODE / 'src/yeying25_mac.schema.yaml').read_text()
    schema = schema.replace('schema_id: yeying25_mac', 'schema_id: yeying25_v5', 1)
    schema = schema.replace('name: 夜莺2.5·Mac', 'name: 夜莺2.5·V5')
    schema = schema.replace('2.5-mac.1', '2.5-v5.1')
    schema = schema.replace('lua_translator@*yeying25_mac_mix', 'lua_translator@*yeying25_v5_mix')
    schema = schema.replace('user_dict: yeying25_mac_sentence', 'user_dict: yeying25_v5_sentence')
    schema += '\n' + (CODE / 'src/v5-tiger.yaml').read_text()
    schema = schema.replace('switches:\n', 'switches:\n  - name: contextual_order\n    reset: 1\n    states: [独立整句, 上下文整句]\n', 1)
    (OUT / 'yeying25_v5.schema.yaml').write_text(schema)

    # (character, canonical double-pinyin) frequency and first/last roots come
    # exclusively from Nightingale 2.5. No Tiger auxiliary codes are imported.
    entries = dict_rows(ROOT / 'package/yeying25_mac_rime.dict.yaml')
    charfreq = defaultdict(int)
    readings = defaultdict(int)
    full = defaultdict(set)
    for word, spelling, frequency in entries:
        if len(word) == 1 and re.fullmatch('[a-z]{2};[a-z]{2}', spelling):
            code = spelling.replace(';', '')
            frequency = int(frequency)
            full[word, code[:2]].add(code)
            readings[word, code[:2]] = max(readings[word, code[:2]], frequency)
            charfreq[word] = max(charfreq[word], frequency)
    rank = {c: i+1 for i, c in enumerate(sorted(charfreq, key=lambda c: (-charfreq[c], c)))}
    lex = {}
    for (char, sound), codes in full.items():
        for code in codes:
            for form in (sound, code[:3], code):
                lex[form, char] = (rank[char], readings[char, sound], sound)
    words = 0
    for word, spelling, frequency in entries:
        if len(word) < 2: continue
        tokens = spelling.split()
        if len(tokens) == len(word) and all(re.fullmatch('[a-z]{2};[a-z]{2}', t) for t in tokens):
            sound = ''.join(t[:2] for t in tokens)
        elif len(word) == 2 and re.fullmatch('[a-z]{4}', spelling):
            sound = spelling
        else:
            continue
        key = sound, word
        old = lex.get(key, (20001, 0, ''))
        lex[key] = (20001, max(old[1], int(frequency)), '')
        words += 1
    # Rank each code bucket by frequency; original fixed order stays in Rime's
    # fixed translator, which always precedes this long-input model stream.
    slots = defaultdict(list)
    for (code, word), (freq_rank, freq, canonical) in lex.items():
        slots[code].append((word, freq_rank, freq, canonical))
    lines = []
    for code in sorted(slots):
        for pos, (word, freq_rank, freq, canonical) in enumerate(sorted(slots[code], key=lambda r: (-r[2], r[0])), 1):
            lines.append('\t'.join(map(str, (code, word, pos, freq_rank, freq, canonical))))
    (data / 'nightingale.lexicon.txt').write_text('\n'.join(lines) + '\n')
    shutil.copy2(CODE / 'V5-README.md', OUT / 'V5-README.md')
    report = {'version': '2.5-v5.1', 'mohu_release': release['html_url'],
              'release_description': release['body'], 'lexicon_rows': len(lines),
              'characters': len(charfreq), 'word_rows': sum(len(word)>1 for _, word in lex),
              'assets': {n: assets[n]['digest'] for n in ('rime-mohu-flypy-latest.zip', 'mohu-sentence-ngram-v5.bin')},
              'changes_to_mohu': ['private module/data names', 'V5 candidate comment', 'honor tiger/candidate_limit'],
              'files': {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob('*'))
                        if p.is_file() and p.name != 'v5-manifest.json'}}
    (OUT / 'v5-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','release_description')}, ensure_ascii=False, indent=2))

if __name__ == '__main__': build()
