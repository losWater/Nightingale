"""Official single-character table with the local Tiger single-mode settings."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import shutil
import re
import build_dual

from paths import ROOT, CODE, ACTIVE, VERSION

def main():
    build_dual.build()
    out = ROOT / 'release-single'
    out.mkdir(exist_ok=True)
    (out/'lua').mkdir(exist_ok=True)
    for name in ('yeying25_mac_lookup.lua', 'yeying25_mac_lookup_key.lua',
                 'yeying25_mac_lookup_data.lua', 'yeying25_shape_comment.lua',
                 'yeying25_shape_lookup_input.lua'):
        shutil.copy2(ROOT/'release-shape/lua'/name, out/'lua'/name)
    positions = Counter()
    prefixes = set()
    rows = []
    for line in (ROOT/'upstream/official-single.txt').read_text(encoding='utf-8-sig').splitlines():
        if not line: continue
        word, code = line.split('\t')
        if len(word) != 1: continue  # Exclude multi-character kana/symbol strings too.
        positions[code] += 1
        prefixes.update(code[:n] for n in range(1, len(code)+1))
        rows.append(f'{word}\t{code}\t{100000-positions[code]}')
    slots = defaultdict(list)
    for row in rows:
        char, code, _ = row.split('\t')
        slots[code].append(char)
    # Explicit platform differences live with the active version, not in shared code.
    for change in json.loads((ACTIVE/'配置/单字版差异.json').read_text()):
        bucket = slots[change['code']]; text = change['text']
        if change['operation']=='delete':
            if text in bucket: bucket.remove(text)
        elif change['operation']=='insert':
            if text in bucket: bucket.remove(text)
            position = change['position']
            if not 1 <= position <= len(bucket)+1: raise ValueError('单字差异候选位越界')
            bucket.insert(position-1,text)
            prefixes.update(change['code'][:n] for n in range(1,len(change['code'])+1))
        else: raise ValueError('未知单字版差异操作')
    # Restore Nightingale's letter-code candidate positions, not Tiger's ;x codes.
    for line in (ROOT/'upstream/nightingale-v25-symbo.txt').read_text().splitlines():
        match = re.fullmatch(r'([a-z]+),(\d+)=(.+)', line)
        assert match, line
        code, position, symbol = match.groups()
        position = int(position)
        if symbol in slots[code]: slots[code].remove(symbol)
        assert len(slots[code]) >= position-1, (code,position,slots[code])
        slots[code].insert(position-1, symbol)
        prefixes.update(code[:n] for n in range(1,len(code)+1))
    rows = [f'{symbol}\t{code}\t{100000-position}' for code in sorted(slots)
            for position,symbol in enumerate(slots[code],1)]
    (out/'yeying25_single.dict.yaml').write_text(
        '# Source: Nightingale v2.5 official single-character table\n---\n'
        'name: yeying25_single\nversion: "2.5-single.5"\nsort: by_weight\n'
        'use_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n'+'\n'.join(rows)+'\n')
    schema = (CODE/'src/yeying25_shape.schema.yaml').read_text()
    schema = schema.replace('yeying25_shape', 'yeying25_single')
    # Shared lookup/comment helpers are independent of the selected dictionary.
    schema = schema.replace('yeying25_single_lookup_input', 'yeying25_shape_lookup_input')
    schema = schema.replace('yeying25_single_comment', 'yeying25_shape_comment')
    schema = schema.replace('夜莺2.5·形码', '夜莺2.5·单字').replace('2.5-shape.2', '2.5-single.3')
    schema = schema.replace('2.5-single.3', '2.5-single.5')
    schema = schema.replace('  dependencies: [yeying25_mac_rime_fixed]\n', '')
    schema = schema.replace('    - lua_processor@*yeying25_mac_pin_key\n', '')
    schema = schema.replace('    - ascii_composer', '    - lua_processor@*yeying25_single_prefix\n    - ascii_composer', 1)
    schema = schema.replace('    - speller', '    - lua_processor@*yeying25_single_english_guard\n    - speller', 1)
    schema = schema.replace('lua_translator@*yeying25_single_table', 'table_translator')
    schema = schema.replace('dictionary: yeying25_mac_rime_fixed', 'dictionary: yeying25_single')
    schema = schema.replace('auto_clear: max_length', 'auto_clear: manual')
    schema = schema.replace('max_code_length: 4', 'max_code_length: 9')
    schema = schema.replace('auto_select: false', "auto_select: true\n  auto_select_pattern: '^;\\w+'").replace(
        '  # Some valid Nightingale words have no exact three-key prefix candidate.\n'
        '  # Do not clear that unfinished prefix before the fourth key arrives.\n', '')
    schema = schema.replace('  # Keep four keys pending; the next letter confirms the selected candidate.\n', '')
    schema = schema.replace('  page_size: 9', '  page_size: 9\n  alternative_select_labels: [㊀, ㊁, ㊂, ㊃, ㊄, ㊅, ㊆, ㊇, ㊈]')
    (out/'yeying25_single.schema.yaml').write_text(schema)
    (out/'lua/yeying25_single_prefix_data.lua').write_text('return {' + ','.join('['+json.dumps(p)+']=true' for p in sorted(prefixes)) + '}\n')
    shutil.copy2(CODE/'src/yeying25_single_prefix.lua', out/'lua')
    shutil.copy2(CODE/'src/yeying25_single_english_guard.lua', out/'lua')
    (out/'README.md').write_text(
        '# 夜莺2.5·单字\n\n数据为夜莺2.5正式普通单字表，不混入词组或模型候选。\n'
        '最大码长9、四码不自动上屏、空码手动清除，与本机虎码单字一致。\n'
        '英文串保护：无候选时继续输入字母不清屏；五码起按英文串保留，空格原样上屏。\n'
        '九候选，使用虎码的圈字序号；空格/分号/引号选词，减号/等号翻页，左右键移动候选。\n'
        '快符使用夜莺v2.5的symbo.txt：字母后二选/三选，例如 a;→！，w;→？，s;→……，i;→——。\n'
        '分号选第二项，单引号选第三项；不是分号引导的虎码快符。多字符快符原样保留。\n'
        'Tab/Esc清屏，Ctrl+J拆分，Ctrl+O简繁，Ctrl+句号标点，方括号重复上屏。\n'
        '保留 ~ 或反引号读音反查、F2筛字。单字版不加载主动造词或词组钉选数据。\n'
        '复制包内文件至Rime用户目录，在方案列表加入 yeying25_single 后重新部署。\n'
        '源码数据：https://github.com/losWater/Nightingale/releases/tag/v2.5\n')
    (out/'default.custom.yaml.example').write_text('patch:\n  schema_list:\n    - schema: yeying25_single\n')
    combined = ROOT/'release-dual'
    for name in ('yeying25_single.schema.yaml', 'yeying25_single.dict.yaml'):
        shutil.copy2(out/name, combined/name)
    for name in ('yeying25_single_prefix.lua', 'yeying25_single_prefix_data.lua', 'yeying25_single_english_guard.lua'):
        shutil.copy2(out/'lua'/name, combined/'lua'/name)
    shutil.copy2(out/'README.md', combined/'SINGLE-README.md')
    (combined/'default.custom.yaml.example').write_text('patch:\n  schema_list:\n'
        '    - schema: yeying25_v5\n    - schema: yeying25_shape\n    - schema: yeying25_single\n')
    for directory, schemas in ((out,['yeying25_single']), (combined,['yeying25_v5','yeying25_shape','yeying25_single'])):
        report = {'schemas':schemas, 'single_character_rows':len(rows),
                  'files':{str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'manifest.json'}}
        (directory/'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('single-character rows:', len(rows))

if __name__ == '__main__': main()
