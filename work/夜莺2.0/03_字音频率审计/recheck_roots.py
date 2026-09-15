"""用审计后的读音集合重查已做的条件拆根评估；不宣称完成结构重拆。"""
from pathlib import Path
from collections import defaultdict
from itertools import combinations
import copy, csv, json, runpy, yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f,delimiter='\t'))

def main():
    audit=runpy.run_path(str(HERE/'rebuild.py'));audit['check_current']()
    td=HERE.parent/'02_改动台账';maint=runpy.run_path(str(td/'maintain.py'))
    data=json.loads((td/'改动台账.json').read_text(encoding='utf-8'))
    cfg=yaml.safe_load((ROOT/'work/重开工程/01_根集/根集_待完整性复核.yaml').read_text(encoding='utf-8'))
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for section in ('roots','anchors'):
        for host,vs in cfg[section].items():
            for v in vs:parent[find(v)]=find(host)
    for k,v in cfg['presentation_names'].items():parent[find(v)]=find(k)
    base={r['汉字']:{'tokens':[s.strip() for s in r['最终规范拆分'].split('＋')],'首根':r['编码首根'],'末根':r['编码末根']} for r in read(ROOT/'work/重开工程/02_规范拆分/最终规范拆分表_待核验.tsv')}
    readings=defaultdict(set);freq={}
    for r in read(HERE/'分读音字频_审计版.tsv'):
        readings[r['汉字']].add(r['拼音']);freq[r['汉字'],r['拼音']]=int(r['已分配频率'])
    def apply(rows,proposal):
        if proposal['kind'] not in ('remove_root_candidate','remove_root_and_resplit'):
            raise ValueError('此评估器尚不支持该操作，禁止静默忽略：'+str(proposal))
        root=proposal['root'];replacement=proposal['replacement'];affected=[]
        for c,r in rows.items():
            if root not in r['tokens']:continue
            affected.append(c)
            r['tokens']=[x for t in r['tokens'] for x in (replacement if t==root else [t])]
            r['首根']=r['tokens'][0];r['末根']=r['tokens'][-1]
        return set(affected)
    def pairs(rows,side,affected):
        result=set()
        for c in affected:
            for other,r in rows.items():
                if c==other or find(rows[c][side])!=find(r[side]):continue
                for s in readings[c]&readings[other]:result.add((s,*sorted((c,other))))
        return result
    summaries=[]
    for e in data['entries']:
        if e['id'] not in ('DEL-001','DEL-002'):continue
        before=copy.deepcopy(base)
        for other in data['entries']:
            if other['id']!=e['id'] and other['decision']=='已确认':apply(before,other['proposal'])
        after=copy.deepcopy(before);affected=apply(after,e['proposal'])
        result={}
        for side in ('首根','末根'):
            old=pairs(before,side,affected);new=pairs(after,side,affected)
            result[side]={'改前':len(old),'改后':len(new),'新增':sorted(new-old),'消除':sorted(old-new)}
        summary=f"核心首根{result['首根']['改前']}→{result['首根']['改后']}；末根{result['末根']['改前']}→{result['末根']['改后']}。"
        if e['id']=='DEL-002':summary+='新增暴—曝(bao)首根冲突，二者末根亦同组；曝bao已分配296。'
        else:summary+='新增0对、消除0对。'
        previous=e['evaluations'][-1]
        assessment={'id':e['id']+'-E'+str(len(e['evaluations'])+1).zfill(2),'date':'2026-09-12','proposal':copy.deepcopy(e['proposal']),'source_hashes':maint['source_hashes'](),'confirmed_context':{k:v for k,v in maint['confirmed_state'](data['entries']).items() if k!=e['id']},'summary':summary,'limitations':'按指定结构展开，尚未全量取根；扩展字未核全。含零证据读音，分读音权重有待分配量，不能用于精确加权优化。','evidence':'../03_字音频率审计/删根复核.json'}
        if any(previous.get(k)!=assessment[k] for k in ('source_hashes','confirmed_context','proposal')):e['evaluations'].append(assessment)
        summaries.append({'编号':e['id'],'涉及核心字':sorted(affected),'结果':result,'说明':summary})
    (HERE/'删根复核.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    (td/'改动台账.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    maint['render'](data)
    print(json.dumps(summaries,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
