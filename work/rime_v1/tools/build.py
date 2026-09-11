from pathlib import Path
import json, collections, re, csv, shutil, hashlib
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/rime_v1'; OLD=ROOT/'releases/v1.0/02_输入法挂接/rime/yeying'; TABLE=ROOT/'releases/v1.0/01_正式码表'; REF=ROOT/'.tmp/rime-mohu-reference'; PKG=ROOT/'.tmp/mohu-v5/package'
def readrows(p):return [x.split('\t') for x in p.read_text(encoding='utf-8-sig').splitlines() if x and not x.startswith('#')]
def dictionary(p):return [x.split('\t') for x in p.read_text(encoding='utf-8-sig').split('...',1)[1].splitlines() if x and not x.startswith('#')]
def write_dict(p,name,rows,sort='by_weight'):
 p.write_text('# Rime dictionary\n---\nname: '+name+'\nversion: "1.0-rime-test1"\nsort: '+sort+'\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n'+'\n'.join('\t'.join(map(str,r)) for r in rows)+'\n',encoding='utf-8')
def build():
 old=dictionary(OLD/'yeying.dict.yaml'); freq={}; oldwords={}
 for row in old:
  if len(row)<3:continue
  w,c,f=row[:3];f=int(f)
  if len(w)==1:freq[w,c[:2]]=max(f,freq.get((w,c[:2]),0))
  elif w not in oldwords or f>oldwords[w][1]:oldwords[w]=(c,f)
 singles=readrows(TABLE/'夜莺码v1.0单字版.txt'); combined=readrows(TABLE/'夜莺1.0字词表.txt')
 # Add post-release maintenance decisions without overwriting the released snapshot.
 for patch in sorted((ROOT/'data/maintenance').glob('*.json')):
  decision=json.loads(patch.read_text(encoding='utf-8'))
  if 'candidate_orders' not in decision:continue
  existing={tuple(r) for r in singles}
  for entry in decision['entries']:
   pair=(entry['text'],entry['code'])
   if pair not in existing:singles.append(list(pair));existing.add(pair)
  orders=decision['candidate_orders']
  combined=[r for r in combined if r[1] not in orders]
  combined.extend([w,c] for c,words in orders.items() for w in words)
 full=collections.defaultdict(list)
 for w,c in singles:
  if len(c)==4:full[w,c[:2]].append(c)
 charfreq={}
 for (w,py),f in freq.items():charfreq[w]=max(charfreq.get(w,0),f)
 ranks={w:i+1 for i,w in enumerate(sorted({w for w,c in singles},key=lambda w:(-charfreq.get(w,0),w)))}
 maincode={key:codes[0] for key,codes in full.items()}
 # Respect the explicitly corrected primary, retaining other full codes as compatibility.
 maincode['曲','qu']='quea'
 fallback={}; lex={}
 def add(w,c,f):fallback[w,c]=max(fallback.get((w,c),0),max(1,f))
 def native(w,c,f,rank=1):lex[c,w]=(rank,ranks.get(w,20001),max(0,f))
 for (w,py),codes in full.items():
  f=freq.get((w,py),1)
  for c in codes:
   add(w,c[:2]+';'+c[2:],f)
   for spelling in [c[:2],c[:3],c]:native(w,spelling,f)
 # Keep the 1.0 word repertoire; rebuild per-character auxiliary spellings.
 missing=[]
 for w,c in combined:
  if len(w)<2 or not all('\u3400'<=ch<='\u9fff' for ch in w):continue
  previous=oldwords.get(w); tokens=previous[0].split() if previous else []
  pys=[c[:2],c[2:]] if len(w)==2 and len(c)==4 else [t[:2] for t in tokens]
  if len(pys)!=len(w):
   pys=[]
   for ch in w:
    choices=[(f,py) for (x,py),f in freq.items() if x==ch and (x,py) in maincode]
    if not choices:break
    pys.append(max(choices)[1])
  if len(pys)!=len(w) or any((ch,py) not in maincode for ch,py in zip(w,pys)):missing.append([w,c]);continue
  spelling=' '.join(maincode[ch,py][:2]+';'+maincode[ch,py][2:] for ch,py in zip(w,pys))
  f=previous[1] if previous else 1;add(w,spelling,f);native(w,''.join(pys),f)
  # Two-character word auxiliary: attach the first character's root after the two syllables.
  if len(w)==2:
   native(w,''.join(pys)+maincode[w[0],pys[0]][2],f)
   add(w,pys[0]+' '+pys[1]+maincode[w[0],pys[0]][2],f)
 short=[]
 short_positions=collections.Counter()
 for w,c in combined:
  if len(w)==2 and len(c) in (2,3) and all('\u3400'<=ch<='\u9fff' for ch in w):
   short_positions[c]+=1
   f=oldwords.get(w,('',1))[1];add(w,c,max(f,100000//short_positions[c]));native(w,c,f,short_positions[c]);short.append([w,c])
 fixed=[]; slots=collections.defaultdict(dict)
 for w,c in combined:
  pos=len(slots[c])+1
  if '$' not in w:slots[c][pos]=w
  else:slots[c][pos]=None
 for line in (ROOT/'symbo.txt').read_text(encoding='utf-8-sig').splitlines():
  m=re.fullmatch(r'([a-z]+),(\d+)=(.+)',line)
  if m:
   c,p,w=m.groups();pos=int(p)
   # Match official Palm quick-symbol insertion: insert and shift existing candidates.
   ss=slots[c]
   if w not in ss.values():
    for i in sorted(ss,reverse=True):
     if i>=pos:ss[i+1]=ss.pop(i)
    ss[pos]=w
 # Rime trial preference: the scheme name takes the first candidate.
 if 'yeyk' in slots:
  ss=slots['yeyk']
  first=next((p for p,w in ss.items() if w=='夜莺'),None)
  other=next((p for p,w in ss.items() if w=='野营'),None)
  if first is not None and other is not None and first>other:
   ss[first],ss[other]=ss[other],ss[first]
 for c,ss in slots.items():
  for pos,w in sorted(ss.items()):
   if w:fixed.append((w,c,100000-pos))
 for kind in ['light','main']:
  out=BASE/'packages'/kind;out.mkdir(parents=True,exist_ok=True);(out/'lua').mkdir(exist_ok=True)
  write_dict(out/'yeying_rime.dict.yaml','yeying_rime',[(w,c,f) for (w,c),f in sorted(fallback.items())])
  write_dict(out/'yeying_rime_fixed.dict.yaml','yeying_rime_fixed',fixed,'by_weight')
  shutil.copy2(BASE/'tools/yeying_mix.lua',out/'lua/yeying_mix.lua')
  schema='yeying_'+kind
  text='''schema:
  schema_id: SCHEMA
  name: LABEL
  version: "1.0-rime-test1"
  dependencies: [yeying_rime_fixed]
ascii_composer:
  switch_key:
    Shift_L: commit_code
    Shift_R: commit_code
switches:
  - {name: ascii_mode, reset: 0, states: [中文, 西文]}
  - {name: ascii_punct, states: [。，, ．，]}
engine:
  processors: [ascii_composer, recognizer, key_binder, speller, punctuator, selector, navigator, express_editor]
  segmentors: [ascii_segmentor, matcher, abc_segmentor, punct_segmentor, fallback_segmentor]
  translators: [punct_translator, "lua_translator@*yeying_mix"]
  filters: [uniquifier]
speller:
  alphabet: abcdefghijklmnopqrstuvwxyz
  delimiter: " '"
  algebra:
    - derive/^(\\w{2});\\w\\w$/$1/
    - derive/^(\\w{2});(\\w)\\w$/$1$2/
    - xform/^(\\w{2});(\\w)(\\w)$/$1$2$3/
translator:
  dictionary: yeying_rime
  user_dict: SCHEMA
  enable_user_dict: true
  enable_completion: false
  contextual_suggestions: false
  max_homophones: 7
  max_homographs: 7
  max_sentences: 2
fixed:
  dictionary: yeying_rime_fixed
  enable_user_dict: false
  enable_sentence: false
  enable_completion: false
  initial_quality: 100
menu:
  page_size: 9
punctuator:
  import_preset: default
key_binder:
  import_preset: default
  bindings:
    - {when: has_menu, accept: semicolon, send: 2}
    - {when: has_menu, accept: apostrophe, send: 3}
recognizer:
  import_preset: default
yeying:
  native: NATIVE
  model_max_input: 36
'''.replace('SCHEMA',schema).replace('LABEL','夜莺·轻量' if kind=='light' else '夜莺·主力V5').replace('NATIVE','true' if kind=='main' else 'false')
  if kind=='main':
   text+='''tiger:
  scheme: flypy
  candidate_type: yeying_native
  lexicon: mohu/data/yeying.lexicon.txt
  beam: 64
  all_ranks: true
  candidate_limit: 9
  initial_quality: 50
  user_model: true
  user_model_weight: 0.85
  personal_lexicon_namespace: translator
  personal_refresh_interval: 30
  decode_context_chars: 2
'''
   for name in ['mohu_tiger_sentence.lua','mohu_runtime.lua']:
    shutil.copy2(REF/'tiger_sentence_native'/name,out/'lua'/name)
   shutil.copy2(REF/'lua/mohu_personal_lexicon.lua',out/'lua/mohu_personal_lexicon.lua')
   shutil.copytree(PKG/'mohu/runtime',out/'mohu/runtime',dirs_exist_ok=True)
   shutil.copy2(ROOT/'.tmp/libtigerengine-night.dll',out/'mohu/runtime/libtigerengine.dll')
   lua_path=out/'lua/mohu_tiger_sentence.lua'
   lua_path.write_text(lua_path.read_text(encoding='utf-8').replace('#context_input <= 4 and', '#context_input <= 3 and'),encoding='utf-8')
   for sub in ['data','model','config']:(out/'mohu'/sub).mkdir(exist_ok=True)
   shutil.copy2(ROOT/'.tmp/mohu-v5/mohu-sentence-ngram-v5.bin',out/'mohu/model/mohu-sentence-ngram-v5.bin')
   (out/'mohu/data/yeying.lexicon.txt').write_text('\n'.join('\t'.join(map(str,[c,w,*v])) for (c,w),v in sorted(lex.items()))+'\n',encoding='utf-8')
   shutil.copy2(REF/'LICENSE',out/'LICENSE-mohu')
  (out/(schema+'.schema.yaml')).write_text(text,encoding='utf-8')
  (out/'yeying_rime_fixed.schema.yaml').write_text('schema:\n  schema_id: yeying_rime_fixed\n  name: 夜莺固定码表（辅助）\n  version: "1.0"\ntranslator:\n  dictionary: yeying_rime_fixed\n',encoding='utf-8')
  (out/'default.custom.yaml.example').write_text('patch:\n  schema_list:\n    - schema: '+schema+'\n',encoding='utf-8')
 (BASE/'reports/build.json').write_text(json.dumps({'dictionary_entries':len(fallback),'fixed_entries':len(fixed),'native_edges':len(lex),'short_spellings':len(short),'missing_words':missing[:100],'missing_count':len(missing)},ensure_ascii=False,indent=2),encoding='utf-8')
 print('built',len(fallback),len(fixed),len(lex),len(short),'missing',len(missing),flush=True)
if __name__=='__main__':
 build()
 import runpy
 runpy.run_path(str(BASE/'tools/add_lookup.py'), run_name='__main__')
