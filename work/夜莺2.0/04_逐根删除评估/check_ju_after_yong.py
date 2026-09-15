from pathlib import Path
import json,runpy
P=Path(__file__).resolve().parent
ctx={'__file__':str(P/'evaluate_yong_variant.py')}
exec((P/'evaluate_yong_variant.py').read_text(encoding='utf-8').split("r=n['audit']")[0],ctx)
n=ctx['n'];rows=ctx['after'];old=ctx['post'];ju=n['rid']('举字底')
def new(x):return old('王') if x==ju else old(x)
r=n['audit']('MERGE-010','用月与甬字底方案后，举字底归王丰',rows,rows,old,new,'候选')
uses=[{'字':c,'拆分':n['show'](s),'首根':s[0]==ju,'末根':s[-1]==ju} for c,s in rows.items() if ju in s]
G=n['grouping']();base=n['BASE']
def standalone(x):return G('王') if x==ju else G(x)
a=n['audit']('MERGE-010','不启用用月候选，单独举字底归王丰',base,base,G,standalone,'候选')
d={'前提':'用和甬字底归月并删角均为候选；王丰已确认；人旁组仍独立。只移动举字底，扌与手留原组。','联合背景增量':r,'当前已确认背景增量':a,'使用字':uses}
(P/'举字底归王丰_用月后复核.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 举字底归王丰：用月方案后复核','',d['前提'],'',f"当前核心字使用{len(uses)}字，其中首根{sum(x['首根'] for x in uses)}字，末根{sum(x['末根'] for x in uses)}字。",f"联合背景：新增首根冲突{r['新增首根字对']}对，三简位置净减少{r['三码位净减少']}，新增完整重码{r['新增完整重码']}对，消除完整重码{r['消除完整重码']}对。",f"不启用用月候选：新增首根冲突{a['新增首根字对']}对，新增完整重码{a['新增完整重码']}对。",'','使用字：'+'、'.join(x['字'] for x in uses)]
(P/'举字底归王丰_用月后复核.md').write_text('\n\n'.join(md),encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';ledger=json.loads(f.read_text(encoding='utf-8-sig'));e=next(x for x in ledger['entries'] if x['id']=='MERGE-010');e.setdefault('history',[]).append({'date':'2026-09-12','event':'按用户要求复核：分别在当前已确认方案、用及甬字底归月删角候选背景下评估，详见04_逐根删除评估/举字底归王丰_用月后复核.json；仍待裁定。'});f.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](ledger)
print('JOINT',r['新增首根字对'],r['三码位净减少'],r['新增完整重码'],r['消除完整重码'])
print('BASE',a['新增首根字对'],a['新增完整重码']);print('USES',len(uses),sum(x['首根'] for x in uses),sum(x['末根'] for x in uses));print(uses[:12])
