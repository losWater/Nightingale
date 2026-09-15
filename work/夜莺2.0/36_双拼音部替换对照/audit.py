from pathlib import Path
import json,yaml,re,hashlib
P=Path(__file__).resolve().parent;W=P.parent;read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
labels=['小鹤','自然码','拼音加加','智能ABC'];checks={};forms=[];params=[];structure=[];maps=read(P/'全音节映射.json')
for label in labels:
 d=P/label;cfg=read(d/'initial.json');forms.append(cfg['form']);obj=json.loads(json.dumps(cfg['optimization']));obj['objective']['character_word_collision'].pop('targets');params.append(obj)
 el=yaml.load((d/'elements.yaml').read_text(encoding='utf-8'),Loader=yaml.CSafeLoader)
 structure.append([{**e,'元素序列':e['元素序列'][2:]} for e in el])
 assert all(e['元素序列'][0]['element'].startswith('P_') and e['元素序列'][1]['element'].startswith('P_') for e in el)
 for e in el:
  if e['拼音']!='reserved':assert ''.join(x['element'][2:] for x in e['元素序列'][:2])==maps[label][e['拼音']]
 code_map={}
 for row in read(d/'同步词码.json'):
  old,new=row['原码'],row['新码'];code_map.setdefault(old,set()).add(new)
 assert all(len(v)==1 for v in code_map.values())
 original=read(P/'小鹤/initial.json')['optimization']['objective']['character_word_collision']['targets'];translated=cfg['optimization']['objective']['character_word_collision']['targets']
 for old,vs in code_map.items():
  new=next(iter(vs));assert new in translated
  assert abs(translated[new]['soft']-original[old]['soft'])<1e-10
 result=read(d/'result.json');assert result['复核'];assert result['缓存差异']<1e-7
 assert re.search(r'已执行 50000 步',(d/'五万步/stdout.log').read_text(encoding='utf-8'))
 checks[label]={'完成步数':50000,'复核':True,'缓存差异':result['缓存差异'],'单字表SHA256':hashlib.sha256((P/(label+'_五万步单字表.txt')).read_bytes()).hexdigest()}
assert all(x==forms[0] for x in forms);assert all(x==params[0] for x in params);assert all(x==structure[0] for x in structure)
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text().splitlines()]
v={'共同形根起点':True,'剔除随双拼重编码的字词目标后参数完全一致':True,'剔除前两音键后输入结构频率及简码限制完全一致':True,'全部60000词逐码与碰撞目标对应':True,'seed':202609121701,'各组':checks,'最低可用内存GiB':min(x['availableGiB'] for x in resources),'资源采样跨度秒':resources[-1]['time']-resources[0]['time']};(P/'最终核验.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=False));r=read(P/'双拼交叉测评.json')
for a in r:
 if a['阶段']=='五万步' and a['测评字频']=='盒子表':print(a['双拼'],[round(s['键均当量'],6) for s in a['分档']])
for a in read(P/'固定200字纯音部.json'):print('纯音部',a['双拼'],a['固定200字音部双键当量'])
