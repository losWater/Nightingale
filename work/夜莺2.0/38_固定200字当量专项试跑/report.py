
from pathlib import Path
import json,html,hashlib
P=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
a=read(P/'测评明细.json');native=read(P/'原生结果.json')
def tab(h,rows):return '<table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in h)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in r)+'</tr>' for r in rows)+'</table>'
f=lambda x:f'{x:.6f}'
s='<html lang="zh-CN"><meta charset="utf-8"><title>固定200字当量专项试跑</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:30px}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:8px}th{background:#dce9f3}</style><h1>固定200字当量专项试跑</h1><p>根集、字频、音部、原指标权重、种子与起点均相同。每组50000步。额外惩罚为λ×盒子固定301–500字的键均当量近似，λ分别为0、10、40、120。不是原权重的倍数。最终结果下表来自独立盒子原生测评。</p><p>定向优化这200字，结果仅代表对目标集的拟合；不代表所有字或其他语料都更好，也不是多种子显著性检验。</p><h2>分档键均当量</h2>'
s+=tab(['档位']+[x['方案'] for x in a],[[a[0]['分档'][i]['档位']]+[f(x['分档'][i]['键均'])+' ('+f(x['分档'][i]['键均']-a[0]['分档'][i]['键均'])+')' for x in a] for i in range(5)])
s+='<h2>目标200字码长与成本</h2>'+tab(['权重','一简','二简','三简','四码','加权键长','字均当量'],[[x['方案']]+x['码长字数']+[f(x['分档'][1]['键长']),f(x['分档'][1]['字均'])] for x in a])
s+='<h2>字词避重与原目标</h2><p>原指标采用冻结输入字音频率与原先分层规则；不是盒子200字分档。不同λ的总分不可直接排名。</p>'
rows=[]
for x in a:
 k=x['方案'];m=native[k]['原生']['metric'];rows.append([k,m['character_word_collision']['hard'],f(m['character_word_collision']['soft']),f(m['characters_short']['duplication']),f(m['characters_short']['pair_equivalence'])])
s+=tab(['组','字词硬碰撞','字词软碰撞','单字简码加权选重','原生简码键对当量'],rows)
s+='<h2>所有原生指标及变化</h2><p>差值=本组−w0。数量、比例和当量依字段定义读取，负数不总是改善（例如简码覆盖数量）。</p>'
def flatten(o,pre=''):
 out={}
 if isinstance(o,dict):
  for k,v in o.items():out.update(flatten(v,pre+'/'+k))
 elif isinstance(o,list):
  for i,v in enumerate(o):out.update(flatten(v,pre+'/'+str(i)))
 elif isinstance(o,(int,float)):out[pre]=o
 return out
maps={k:flatten(v['原生']['metric']) for k,v in native.items()};keys=list(maps['w0'])
s+=tab(['字段']+list(maps),[[k]+[f(v[k])+' ('+f(v[k]-maps['w0'][k])+')' if k in v else '—' for v in maps.values()] for k in keys])
s+='<h2>200字逐字结果与普通码表</h2>'
s+=tab(['字']+[x['方案'] for x in a],[[r['字']]+[next(z['码']+' / '+f(z['当量']) for z in x['逐字'] if z['字']==r['字']) for x in a] for r in a[0]['逐字']])
for x in a:s+='<p><a href="'+x['方案']+'_五万步单字表.txt">'+x['方案']+'普通单字表</a></p>'
s+='<p>后两档各缺2、38字，各组缺字相同。指标明细见测评明细.json，原生全指标见原生结果.json。</p></html>'
(P/'专项对照.html').write_text(s,encoding='utf8')
old=P.parent/'36_双拼音部替换对照/小鹤_五万步单字表.txt'
assert old.read_bytes()==(P/'w0_五万步单字表.txt').read_bytes(),'zero control differs'
print(json.dumps({'零权重复现36号':True,'结果':rows,'键均':[(x['方案'],[r['键均'] for r in x['分档']]) for x in a]},ensure_ascii=False))
