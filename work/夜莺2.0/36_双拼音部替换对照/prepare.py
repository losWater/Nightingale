from pathlib import Path
from collections import defaultdict,Counter
import json,yaml,re,ast,unicodedata,hashlib
P=Path(__file__).resolve().parent;W=P.parent;S=P/'sources';OLD=W/'35_同种子三字频对照';F=W/'27_删利根参数0晋级赛/frozen'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
files={'小鹤':'double_pinyin_flypy.schema.yaml','自然码':'double_pinyin.schema.yaml','拼音加加':'double_pinyin_pyjj.schema.yaml','智能ABC':'double_pinyin_abc.schema.yaml'}
algebra={k:yaml.safe_load((S/v).read_text(encoding='utf-8'))['speller']['algebra'] for k,v in files.items()}
# The canonical path does not take optional derive aliases. Only use an alias if canonical output is not two keys (e.g. PYJJ o -> oo).
def apply(rule,s):
 op,pattern,replacement,*_=rule.split('/')
 if op=='xlit':return s.translate(str.maketrans(pattern,replacement))
 if op in ('xform','derive'):
  replacement=re.sub(r'\$(\d+)',lambda m:'\\g<'+m[1]+'>',replacement)
  return re.sub(pattern,replacement,s)
 return s

def code(label,py):
 if py in {'ng','m','hng'}:return {'ng':'ng','m':'mm','hng':'hg'}[py]
 rules=algebra[label];current=py;variants=[py]
 for rule in rules:
  op=rule.split('/')[0]
  if op=='erase':continue
  if op=='derive':variants=list(dict.fromkeys(variants+[apply(rule,s) for s in variants]))
  elif op in ('xform','xlit'):
   current=apply(rule,current);variants=list(dict.fromkeys(apply(rule,s) for s in variants))
  else:raise ValueError(rule)
 if re.fullmatch('[a-z]{2}',current):return current
 valid=[s for s in variants if re.fullmatch('[a-z]{2}',s)]
 assert valid,(label,py,current,variants)
 return valid[0]

base=read(F/'字音基准.json');cfg=read(OLD/'共同起点.json');els=yaml.safe_load((OLD/'新表_elements.yaml').read_text(encoding='utf-8'))
words=[json.loads(l) for l in (W/'09_字词避重选词实验/常用加补位词集.jsonl').read_text(encoding='utf-8').splitlines()]
syllables={r['拼音'] for r in base}
for r in words:syllables.update((r.get('主读音') or r.get('采用拼音')).split())
# All candidate-pool sources contain no two-character words with the isolated nasal readings.
for name in ['二字词60000_鲸凉鹤补全后.jsonl','读音通过_候选.jsonl']:
 for line in (W/'08_词库与词频重建'/name).open(encoding='utf-8'):
  r=json.loads(line)
  if r.get('词长')==2:assert not set((r.get('主读音') or r.get('采用拼音') or '').split()) & {'ng','m','hng'}
# Use a frozen legacy conversion for phonetic codes present in collision targets.
scope={'re':re,'unicodedata':unicodedata};tree=ast.parse((W/'03_字音频率审计/rebuild.py').read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='double_code'],type_ignores=[]),'legacy','exec'),scope)
def legacy(s):return {'ng':'ng','m':'mm','hng':'hg'}.get(s) or scope['double_code'](s)
# Existing syllables and all frozen target syllables should share canonical Xiaohe codes.
for r in base:assert code('小鹤',r['拼音'])==r['音码'],r
maps={label:{py:code(label,py) for py in sorted(syllables)} for label in files}
write(P/'全音节映射.json',maps)
brief_py={'东西':('dong','xi'),'复杂':('fu','za'),'就算':('jiu','suan'),'可谓':('ke','wei'),'了解':('liao','jie'),'知道':('zhi','dao'),'需要':('xu','yao'),'怎样':('zen','yang')}
targets=cfg['optimization']['objective']['character_word_collision']['targets'];audits={}
for label in files:
 out=P/label;out.mkdir(exist_ok=True);mapping=maps[label];phon=defaultdict(set)
 for s in syllables:
  if s in {'ng','m','hng'}:continue
  old=legacy(s)
  if old:phon[old].add(mapping[s])
 ambiguous={k:sorted(v) for k,v in phon.items() if len(v)>1}
 used={c[:2] for c in targets}|{c[2:] for c in targets}
 unknown=sorted(used-set(phon));assert not unknown,('unknown targets',unknown[:20])
 assert not (set(ambiguous)&used),(label,ambiguous)
 remap=lambda c:next(iter(phon[c[:2]]))+next(iter(phon[c[2:]]))
 newtarget={}
 for k,v in targets.items():
  nk=remap(k);t=newtarget.setdefault(nk,{'soft':0.,'hard':False});t['soft']+=v['soft'];t['hard']=t['hard'] or v['hard']
 conf=json.loads(json.dumps(cfg));conf['optimization']['objective']['character_word_collision']['targets']=newtarget
 changed=json.loads(json.dumps(els));unlock=[];prefixes=defaultdict(list)
 for e in changed:
  if e['拼音']=='reserved':
   a,b=brief_py[e['词']];nc=mapping[a][0]+mapping[b][0];e['元素序列']=[{'element':'P_'+c,'index':0} for c in nc]
  else:
   nc=mapping[e['拼音']];e['元素序列'][:2]=[{'element':'P_'+c,'index':0} for c in nc]
   if e['词'] in '啊而哦' and e.get('简码长度')==1:unlock.append(e['词']);e.pop('简码长度')
   if e.get('简码长度')==1:prefixes[nc[0]].append(e['词'])
 assert all(len(v)==1 for v in prefixes.values()),(label,prefixes)
 assert sorted(unlock)==sorted('啊而哦')
 assert conf['form']==cfg['form']
 # Shape components and character frequencies remain identical, including special weight overlay.
 for a,b in zip(els,changed):
  assert a['频率']==b['频率']
  assert a['元素序列'][2:]==b['元素序列'][2:]
 (out/'elements.yaml').write_text(yaml.safe_dump(changed,allow_unicode=True,sort_keys=False),encoding='utf-8');write(out/'initial.json',conf)
 wordrows=[]
 for r in words:
  py=(r.get('主读音') or r.get('采用拼音')).split();nc=''.join(mapping[s] for s in py);assert len(nc)==4
  wordrows.append({'词':r['词'],'拼音':' '.join(py),'原码':r['实验码'],'新码':nc})
 write(out/'同步词码.json',wordrows)
 audits[label]={'字音项':len(base),'词条':len(wordrows),'旧目标数':len(targets),'新目标数':len(newtarget),'目标总权重保持':abs(sum(v['soft'] for v in targets.values())-sum(v['soft'] for v in newtarget.values()))<1e-7,'释放一简':unlock,'音节数':len(mapping),'仅字母双键':all(re.fullmatch('[a-z]{2}',v) for v in mapping.values()),'其余一简锁定':dict(prefixes),'保留简词':{w:mapping[a][0]+mapping[b][0] for w,(a,b) in brief_py.items()},'音节同码组':{c:[py for py,pc in mapping.items() if pc==c] for c,n in Counter(mapping.values()).items() if n>1},'initial_sha256':hashlib.sha256((out/'initial.json').read_bytes()).hexdigest()}
write(P/'输入核验.json',audits)
write(P/'实验约定.json',{'方案':list(files),'训练字频':'35号新表，分音估计及谁的权重规则完全不变','seed':202609121701,'steps':50000,'起点':'与35号相同projection；各组形根物理键完全相同','参数':'参数0不改权重，字词碰撞目标随双拼重编码，总权重不变','锁定':'为兼容ABC零声母，四组统一释放啊、而、哦的一简锁定；其余一简身份及fu=复长度保留；八个简词按双声母映射迁移','特殊音':'ng/m/hng四组统一采用ng/mm/hg；不宣称各商用产品默认键位','零声母':'优先Rime不含derive的主变换；若不是双键才取官方derive两键路径，如加加o采用oo。其他容错别名不用于竞赛','测评':'同一盒子/新表/老表三个整字频率口径，含固定200字音部当量分解；均不带简词测单字','来源':read(P/'来源记录.json'),'局限':'单一种子；不是换双拼后的成熟正式方案，不等于各双拼输入法整体性能'})
print(json.dumps(audits,ensure_ascii=False))
