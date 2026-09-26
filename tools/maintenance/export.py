"""Read active masters only; export tables and Rime dictionaries without deployment."""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import re
import zipfile
from context import load, table_paths, sha, atomic, json_bytes
from apply_ledger import load as read_table, render, checkup

def extract_json(text, name):
    m = re.search(r'\b(?:const|let)\s+'+re.escape(name)+r'\s*=\s*', text)
    if not m: raise ValueError('拆分原本缺少 '+name)
    return json.JSONDecoder().raw_decode(text[m.end():])[0]

def lua(value):
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list): return '{'+','.join(map(lua,value))+'}'
    if isinstance(value, dict): return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    return str(value)

def dictionary(name, rows, version):
    return ('# Generated from active maintenance masters; do not edit.\n---\nname: '+name+
            '\nversion: "'+version+'"\nsort: by_weight\nuse_preset_vocabulary: false\n'
            'columns: [text, code, weight]\n...\n'+''.join('\t'.join(map(str,r))+'\n' for r in rows))

def export(root=None):
    root, active, meta = load(root, writable=True)
    paths = table_paths(active)
    inputs = list(paths.values())+[active/'主表/快符.txt',active/'资料/拆分原本.html',active/'配置/单字版差异.json']
    before = {str(p.relative_to(active)):sha(p) for p in inputs}
    tabs = {n:read_table(p) for n,p in paths.items()}
    bad = checkup(tabs)
    if bad: raise ValueError(str(bad))
    quick = []
    for line in (active/'主表/快符.txt').read_text(encoding='utf-8-sig').splitlines():
        m = re.fullmatch(r'([a-z]+),(\d+)=(.+)', line)
        if not m: raise ValueError('无效快符 '+line)
        code, pos, text = m.groups(); quick.append((text,code,int(pos)))
    groups = defaultdict(list)
    for text,code in tabs['字词表']+tabs['符号表']: groups[code].append(text)
    for text,code,pos in quick:
        if text in groups[code]: groups[code].remove(text)
        if pos > len(groups[code])+1: raise ValueError('快符候选位超出范围')
        groups[code].insert(pos-1,text)
    combined = [(t,c) for c in sorted(groups) for t in groups[c] if not t.startswith('$ddcmd(')]
    single = sorted(tabs['单字表']+tabs['符号表'], key=lambda r:r[1])
    out = active/'产物'; out.mkdir(exist_ok=True)
    (out/'普通单字表.txt').write_bytes(render(single))
    (out/'综合字词表.txt').write_bytes(render(combined))
    mac = out/'mac'; up = mac/'upstream'; up.mkdir(parents=True,exist_ok=True)
    (up/'official-single.txt').write_bytes(render(single))
    (up/'official-combined.txt').write_bytes(render(combined))
    (up/'nightingale-v25-symbo.txt').write_bytes((active/'主表/快符.txt').read_bytes())
    # Legacy filenames identify pinned adapter dependencies, not active table sources.
    for name in ('nightingale-2.5-light.zip','mohu-release.json','rime_api.h'):
        target = root/'assets/rime'/name
        link = up/name
        if not link.exists(): link.symlink_to(target)
    for name in ('rime-mohu-flypy-latest.zip','mohu-sentence-ngram-v5.bin.zip'):
        link = up/name
        if not link.exists(): link.symlink_to(root/'.cache/rime'/name)

    generated = mac/'generated'; generated.mkdir(exist_ok=True)
    fixed = [(t,c,100000-n) for c in sorted(groups) for n,t in enumerate(groups[c],1)
             if not t.startswith('$ddcmd(')]
    (generated/'yeying25_mac_rime_fixed.dict.yaml').write_text(dictionary('yeying25_mac_rime_fixed',fixed,meta['version']))

    # Reuse only linguistic metadata (frequencies/readings), never old fixed codes.
    with zipfile.ZipFile(root/'assets/rime/nightingale-2.5-light.zip') as archive:
        base = archive.read('yeying20_rime_short.dict.yaml').decode('utf-8-sig')
        lookup = archive.read('lua/yeying20_lookup_data.lua').decode('utf-8-sig')
    entries = [line.split('\t') for line in base.split('...',1)[1].splitlines() if line and not line.startswith('#')]
    full = defaultdict(list); freq = defaultdict(lambda:1); words = set(t for t,c in tabs['字词表'] if len(t)>1)
    for text,code in tabs['单字表']:
        if re.fullmatch('[a-z]{4}',code): full[text,code[:2]].append(code)
    word_freq = defaultdict(lambda:1); readings = {}
    for text,code,weight in entries:
        if len(text)==1: freq[text] = max(freq[text],int(weight))
        else:
            word_freq[text] = max(word_freq[text],int(weight))
            tokens = code.split()
            if len(tokens)==len(text) and all(re.fullmatch('[a-z]{2};[a-z]{2}',t) for t in tokens):
                readings[text] = [t[:2] for t in tokens]
    fallback = {}; short = set()
    def add(text,code,weight): fallback[text,code] = max(fallback.get((text,code),0),weight)
    for (text,sound), codes in full.items():
        for code in codes: add(text,code[:2]+';'+code[2:],freq[text])
    quickset = {(t,c) for t,c,n in quick}
    for text,code,weight in fixed:
        if len(text)<2 or (text,code) in quickset or len(code)>4 or not all('\u3400'<=c<='\u9fff' for c in text): continue
        add(text,code,max(word_freq[text],100000//(100000-weight)) if len(code)<4 else word_freq[text])
        if len(code)<4: short.add((text,code))
        sounds = [code[:2],code[2:]] if len(text)==2 and len(code)==4 else readings.get(text)
        if sounds and len(sounds)==len(text) and all((c,s) in full for c,s in zip(text,sounds)):
            codes = [full[c,s][0] for c,s in zip(text,sounds)]
            add(text,' '.join(c[:2]+';'+c[2:] for c in codes),word_freq[text])
            if len(text)==2: add(text,sounds[0]+' '+sounds[1]+codes[0][2],word_freq[text])
    for suffix,rows in [('',[(t,c,f) for (t,c),f in sorted(fallback.items()) if (t,c) not in short]),
                        ('_short',[(t,c,f) for (t,c),f in sorted(fallback.items())])]:
        name = 'yeying25_mac_rime'+suffix
        (generated/(name+'.dict.yaml')).write_text(dictionary(name,rows,meta['version']))
    pinyin_part = lookup.split('["pinyin"]=',1)[1]
    pinyin = dict(re.findall(r'\["([a-z]+)"\]="([a-z]+)"',pinyin_part))
    if not pinyin: raise ValueError('拼音元数据解析失败')
    views = extract_json((active/'资料/拆分原本.html').read_text(encoding='utf-8-sig'),'views')
    splits = extract_json(views['query'],'D')
    sounds = defaultdict(list)
    for (text,sound),codes in full.items():
        if text not in splits: raise ValueError('拆分缺字 '+text)
        sounds[sound].append([text,splits[text]['新拆'],codes,99999,1])
    for rows in sounds.values(): rows.sort(key=lambda r:(-freq[r[0]],r[0]))
    (generated/'yeying25_mac_lookup_data.lua').write_text('return '+lua({'sounds':dict(sounds),'pinyin':pinyin})+'\n')
    if before != {str(p.relative_to(active)):sha(p) for p in inputs}:
        raise ValueError('导出期间主表或配置发生变化')
    report = {'version':meta['version'],'input_sha256':before,'combined_rows':len(combined),
              'single_rows':len(single),'quick_entries':len(quick),'split_characters':len(splits)}
    atomic(out/'生成清单.json',json_bytes(report))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return mac

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--root')
    export(parser.parse_args().root)
