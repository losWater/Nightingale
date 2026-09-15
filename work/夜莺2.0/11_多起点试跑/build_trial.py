from pathlib import Path
from collections import Counter,defaultdict
import json,yaml,csv,runpy,random,copy,hashlib
O=Path(__file__).resolve().parent;P=O.parent;R=P.parents[1]
state=runpy.run_path(str(P/'04_逐根删除评估/current_state.py'))
rootdoc=json.loads((P/'07_当前完整根表/夜莺2.0当前完整根表.json').read_text(encoding='utf-8'))
groups=rootdoc['根组'];gid={x:'G'+str(g['序号']).zfill(3) for g in groups for x in g['根形ID']}
gnames={'G'+str(g['序号']).zfill(3):g['根组'] for g in groups}
old=runpy.run_path(str(P/'03_字音频率审计/rebuild.py'));dc=lambda py: {'ng':'ng','m':'mm','hng':'hg'}.get(py) or old['double_code'](py)
freq=list(csv.DictReader((P/'03_字音频率审计/分读音字频_审计版.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
# New audited frequency order; no historical manual order inherited.
freq.sort(key=lambda x:(-int(x['已分配频率']),x['汉字'],x['拼音']))
locks=json.loads((P/'10_历史简码分配追溯/一简锁定名单.json').read_text(encoding='utf-8'))['锁定']
locks2=json.loads((P/'10_历史简码分配追溯/二码位锁定名单.json').read_text(encoding='utf-8'))
chosen={}
for code,w in {**locks,**locks2['单字二简']}.items():
 matches=[r for r in freq if r['汉字']==w and dc(r['拼音']) and dc(r['拼音']).startswith(code)]
 assert matches,(code,w)
 chosen[w,matches[0]['拼音']]=len(code)
elements=[];unenc=[]
for r in freq:
 w,py=r['汉字'],r['拼音'];phon=dc(py)
 if not phon:
  unenc.append(r);continue
 seq=state['rows'][w];assert seq
 names=['P_'+c for c in phon]+[gid[seq[0]],gid[seq[-1]]]
 e={'词':w,'拼音':py,'元素序列':[{'element':n,'index':0} for n in names],'频率':int(r['已分配频率'])}
 if (w,py) in chosen:e['简码长度']=chosen[w,py]
 elements.append(e)
for c,w in locks2['简词保留位'].items():
 elements.append({'词':w,'拼音':'reserved','元素序列':[{'element':'P_'+k,'index':0} for k in c],'频率':0})
assert len(chosen)==26
(O/'elements.yaml').write_text(yaml.safe_dump(elements,allow_unicode=True,sort_keys=False),encoding='utf-8')
# Keep alternative split propagated differences; both are evaluated as separate runs.
rawdir=P/'04_逐根删除评估'
raw=json.loads((rawdir/'fou-niu-wu-ma-xie-raw.json').read_text(encoding='utf-8'))
alt=copy.deepcopy(elements);changes=[]
for e in alt:
 w=e['词']
 if len(w)!=1 or w not in raw['er'] or raw['er'][w]==raw['ju'][w]:continue
 before,after=raw['er'][w],raw['ju'][w];cur=state['rows'][w]
 # Change only the first/tail boundary when the earlier two variants differ there.
 for ix,pos in [(0,2),(-1,3)]:
  if before[ix]!=after[ix]:
   assert cur[ix]==before[ix],(w,cur,before)
   e['元素序列'][pos]['element']=gid[after[ix]]
 changes.append(w)
(O/'elements_ji_ju.yaml').write_text(yaml.safe_dump(alt,allow_unicode=True,sort_keys=False),encoding='utf-8')
basepath=O/'历史C19配置.yaml'
base=yaml.safe_load(basepath.read_text(encoding='utf-8'))
# Copy for fully local provenance, not a live dependency.
(O/'历史C19配置.yaml').write_text(basepath.read_text(encoding='utf-8'),encoding='utf-8')
layout=yaml.safe_load((R/'releases/v1.0/01_正式码表/夜莺码v1.0键位布局.yaml').read_text(encoding='utf-8'))['form']['mapping']
def resolve(k,visited=()):
 v=layout.get(k)
 if isinstance(v,str) and len(v)==1 and v.isascii():return v
 return None
projection={};projection_detail={};rng=random.Random(12001)
for g in groups:
 name='G'+str(g['序号']).zfill(3);votes=Counter(resolve(x) for x in g['根形ID']);votes.pop(None,None)
 projection[name]=votes.most_common(1)[0][0] if votes else rng.choice('abcdefghijklmnopqrstuvwxyz')
 projection_detail[name]={'名称':g['根组'],'旧键投票':dict(votes),'投影键':projection[name]}
obj=base['optimization']['objective'];obj.pop('words_full',None)
for t in obj['characters_short']['tiers']:
 if t['top']==6000:t['levels']=[{'length':3,'frequency':-90.0}]
obj['characters_full']['tiers'][-1]['phonetic_shape_transition_equivalence']=0.25
# Expose all historical diagnostic fields with zero weight; retain calibrated historical nonzero ones.
for part in ['characters_full','characters_short']:
 obj[part]['key_distribution']=0.0
 obj[part]['pair_equivalence']=0.0
 obj[part]['fingering']=[0.0]*8
codes={json.loads(l)['实验码'] for l in (P/'09_字词避重选词实验/常用加补位词集.jsonl').open(encoding='utf-8')}
weights=[json.loads(l) for l in (P/'09_字词避重选词实验/全候选码位权重.jsonl').open(encoding='utf-8')]
avg=sum(r['排序指数合计'] for r in weights if r['码位'] in codes)/len(codes)
obj['character_word_collision']={'weight':0.1,'hard_penalty':0.0,'hard_character_top':0,'character_tiers':[{'top':1674,'factor':1.0},{'top':3527,'factor':0.5},{'top':6000,'factor':0.2}],'targets':{r['码位']:{'soft':r['排序指数合计']/avg,'hard':False} for r in weights if r['码位'] in codes}}
# Same objective and budget across all starts; init seed does not imply seeded engine RNG.
cards=[]
for i,kind in enumerate(['projection','perturbed','random','random','random','random']):
 seed=12001+i;rr=random.Random(seed)
 mapping=dict(projection)
 if kind=='random':mapping={g:rr.choice('abcdefghijklmnopqrstuvwxyz') for g in mapping}
 elif kind=='perturbed':
  for g in rr.sample(list(mapping),round(len(mapping)*.6)):mapping[g]=rr.choice('abcdefghijklmnopqrstuvwxyz')
 cfg={'version':'2.3','source':None,'info':{'name':'夜莺2.0短程试跑','version':'trial'},'form':{'alphabet':'abcdefghijklmnopqrstuvwxyz','mapping_type':1,'mapping':{**mapping,**{'P_'+k:k for k in 'abcdefghijklmnopqrstuvwxyz'}}},'encoder':copy.deepcopy(base['encoder']),'optimization':{'objective':copy.deepcopy(obj),'metaheuristic':{'algorithm':'SimulatedAnnealing','parameters':{'t_max':0.05,'t_min':0.00005,'steps':3000},'update_interval':500,'report_after':0.8,'search_method':{'random_move':.90,'random_swap':.09,'random_full_key_swap':.01}}}}
 cfg['generated_mapping_space']={g:[{'value':k,'score':0.0} for k in 'abcdefghijklmnopqrstuvwxyz'] for g in mapping}
 cfg['generated_mapping_space'].update({'P_'+k:[{'value':k,'score':0.0}] for k in 'abcdefghijklmnopqrstuvwxyz'})
 cfg['encoder'].pop('short_code_schemes',None)
 cfg['encoder']['auto_select_length']=4
 directory=O/f'{i+1:02d}_{kind}';directory.mkdir(exist_ok=True)
 (directory/'config.yaml').write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False),encoding='utf-8')
 cards.append({'id':directory.name,'kind':kind,'initialization_seed':seed,'engine_rng':'unseeded native rand; initial layout reproducible only','elements':'elements_ji_ju.yaml' if i==5 else 'elements.yaml','directory':str(directory)})
report={'status':'built_pending_validation','groups':len(groups),'char_readings':len(elements)-8,'excluded_unencodable':unenc,'fixed_short_identities':len(chosen),'reserved_words':locks2['简词保留位'],'ji_alternative_affected':sorted(set(changes)),'cards':cards,'projection':projection_detail,'group_names':gnames,'frequency_source':'03_字音频率审计/分读音字频_审计版.tsv','word_targets':len(codes),'notes':['8个简词用零频固定全码占位实体保留二码空间，不参与词频指标','历史权重只作短跑初值；分配为零但无证据项仍保留身份','2.0新词频尚未回灌单字频率，沿用已审计分读音字频；非旧退火字频','击两种拆法分别输入，末一个随机起点采用另一拆法']}
(O/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['projection','group_names','cards','excluded_unencodable']},ensure_ascii=False));print('excluded',unenc)
