"""Generate a local single-character split lookup for all three Rime schemas."""
from pathlib import Path
import csv, json, re
import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/rime_v1'
splits = {}
core = {row['汉字'] for row in csv.DictReader((ROOT/'releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt').open(encoding='utf-8-sig'), delimiter='\t')}
for path in [ROOT/'work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv', ROOT/'releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt']:
    for row in csv.DictReader(path.open(encoding='utf-8-sig'), delimiter='\t'):
        splits[row['汉字']] = row['最终规范拆分']
names = yaml.safe_load((ROOT/'work/重开工程/01_根集/根集_待完整性复核.yaml').read_text(encoding='utf-8'))['presentation_names']
for char, split in splits.items():
    splits[char] = '＋'.join(names.get(p, p) for p in split.split(' ＋ '))

finals = {'iu':'q','ei':'w','uan':'r','ue':'t','ve':'t','un':'y','uo':'o','ie':'p','ong':'s','iong':'s','ai':'d','en':'f','eng':'g','ang':'h','an':'j','ing':'k','uai':'k','iang':'l','uang':'l','ou':'z','ia':'x','ua':'x','ao':'c','ui':'v','in':'b','iao':'n','ian':'m'}
def flypy(py):
    if py in ('a','o','e'): return py*2
    if py in ('ai','an','ao','ei','en','er','ou'): return py
    if py in ('ang','eng'): return py[0]+'h' if py=='ang' else 'eg'
    match = re.fullmatch(r'(zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])(.+)', py)
    if not match: return None
    initial, final = match.groups()
    tail = finals.get(final, final if len(final)==1 else None)
    return {'zh':'v','ch':'i','sh':'u'}.get(initial, initial)+tail if tail else None

# Accepted full syllables come from the maintained reading table.
syllables = {}
frequencies = {}
for row in csv.DictReader((ROOT/'work/重开工程/03_字音频率/SUBTLEX阶段性分读音频率表_人工定案版.tsv').open(encoding='utf-8-sig'), delimiter='\t'):
    py = row['拼音']; code = flypy(py)
    if code: syllables[py] = code
    frequencies[row['汉字']] = frequencies.get(row['汉字'], 0) + float(row['人工定案后阶段频率'])

for kind in ('main','light'):
    pkg=BASE/'packages'/kind
    rows=(pkg/'yeying_rime_fixed.dict.yaml').read_text(encoding='utf-8').split('...',1)[1].splitlines()
    items={}
    for line in rows:
        fields=line.split('\t')
        if len(fields)<3: continue
        char,code,weight=fields[:3]
        if len(char)!=1 or len(code)!=4 or char not in splits: continue
        key=(code[:2],char)
        if key not in items: items[key]=[char,splits[char],[],int(weight),1 if char in core else 0]
        items[key][2].append(code)
        items[key][3]=max(items[key][3],int(weight))
    data={}
    for (sound,char),item in items.items(): data.setdefault(sound,[]).append(item)
    for rows in data.values(): rows.sort(key=lambda x:(-frequencies.get(x[0],0),x[0]))
    def lua(value):
        if isinstance(value,str): return json.dumps(value,ensure_ascii=False)
        if isinstance(value,list): return '{'+','.join(lua(x) for x in value)+'}'
        if isinstance(value,dict): return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
        return str(value)
    (pkg/'lua').mkdir(exist_ok=True)
    (pkg/'lua/yeying_lookup_data.lua').write_text('return '+lua({'sounds':data,'pinyin':syllables})+'\n',encoding='utf-8')
    (pkg/'lua/yeying_lookup.lua').write_text((BASE/'tools/yeying_lookup.lua').read_text(encoding='utf-8'),encoding='utf-8')
    (pkg/'lua/yeying_lookup_key.lua').write_text((BASE/'tools/yeying_lookup_key.lua').read_text(encoding='utf-8'),encoding='utf-8')
    for schema in pkg.glob('yeying_*.schema.yaml'):
        config=yaml.safe_load(schema.read_text(encoding='utf-8'))
        if 'engine' not in config: continue
        translators=config['engine']['translators']
        entry='lua_translator@*yeying_lookup'
        if entry not in translators: translators.insert(0,entry)
        processors=config['engine']['processors']
        if 'lua_processor@*yeying_lookup_key' not in processors: processors.insert(0,'lua_processor@*yeying_lookup_key')
        config.setdefault('recognizer',{}).setdefault('patterns',{})['yeying_lookup']='^([`~][a-z]*|~~[a-z]*)$'
        schema.write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
    # Even if a segment has the abc tag, lookup must bypass sentence decoding.
    p=pkg/'lua/yeying_mix.lua';s=p.read_text(encoding='utf-8')
    guard="  if input:match('^[`~]') then return end\n"
    if guard not in s:s=s.replace('function M.func(input, seg, env)\n','function M.func(input, seg, env)\n'+guard)
    p.write_text(s,encoding='utf-8')
    print(kind, len(items), 'character-reading entries;',len(syllables),'full syllables')
