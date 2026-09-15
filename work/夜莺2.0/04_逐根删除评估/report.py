"""Score per-root structural ablations, including explicit manual-rule boundaries."""
from pathlib import Path
from collections import defaultdict
from itertools import combinations
from difflib import SequenceMatcher
import json,csv,html,hashlib,runpy,yaml
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def tsv(p,rows,fields):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',extrasaction='ignore');w.writeheader();w.writerows(rows)
def read(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f,delimiter='\t'))
def pair_sets(rows,readings,find):
    buckets=[defaultdict(list),defaultdict(list)]
    for c,seq in rows.items():
        for sound in readings[c]:
            for side,i in enumerate([0,-1]):buckets[side][sound,find(seq[i])].append(c)
    return tuple({(s,*sorted(pair)) for (s,_),cs in bs.items() for pair in combinations(cs,2)} for bs in buckets)
def added_sets(old,new):
    h=new[0]-old[0];t=new[1]-old[1]
    return h,t,h|t,(new[0]&new[1])-(old[0]&old[1])
def local_recovery(canonical,raw,target):
    """Only replace a uniquely aligned target span; do not undo adjacent decisions."""
    result=[];found=False
    for op,i,j,k,l in SequenceMatcher(None,canonical,raw,autojunk=False).get_opcodes():
        part=canonical[i:j]
        if target in part:
            if part!=[target] or not raw[k:l]:raise ValueError('无法隔离删根部位')
            result.extend(raw[k:l]);found=True
        else:result.extend(part)
    if not found or target in result:raise ValueError('未得到完整恢复')
    return result
def main():
    runpy.run_path(str(HERE.parent/'03_字音频率审计/rebuild.py'))['check_current']()
    for p,h in load(HERE/'source-fingerprints.json').items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('来源已变化，必须重新prepare和重跑：'+p)
    inp=load(HERE/'input.json');rawbase=load(HERE/'active-baseline.json');base=inp['expected'];norm=inp['norm']
    fingerprint=hashlib.sha256((HERE/'input.json').read_bytes()+(HERE/'active.yaml').read_bytes()+(HERE/'source-fingerprints.json').read_bytes()+(HERE/'ablate.ts').read_bytes()).hexdigest()
    frames_doc=yaml.safe_load((ROOT/'work/重开工程/02_规范拆分/正式字架规则.yaml').read_text(encoding='utf-8'))
    frame_chars={name:set(spec.get('audited_direct_hits',[])+spec.get('audited_nested_hits',[])) for name,spec in frames_doc['frames'].items()}
    inventory={r['id']:r for r in inp['inventory']};parent={x:x for x in inventory}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for a,b in inp['edges']:parent[find(b)]=find(a)
    display=lambda x:inventory.get(x,{}).get('display',x)
    split=lambda seq:'＋'.join(display(x) for x in seq)
    readings=defaultdict(set);freq={};pending={};total={}
    for r in read(HERE.parent/'03_字音频率审计/分读音字频_审计版.tsv'):
        c=r['汉字'];s=r['拼音'];readings[c].add(s);freq[c,s]=int(r['已分配频率']);pending[c]=int(r['该字待分配频率']);total[c]=int(r['该字原始总频'])
    rank={c:i+1 for i,c in enumerate(sorted(total,key=lambda c:(-total[c],c)))}
    def weight(p):s,a,b=p;return min(freq[a,s],freq[b,s])
    def pairinfo(p):
        s,a,b=p;return {'音节':s,'字对':a+'—'+b,'字1':a,'字2':b,'字1分读音频次':freq[a,s],'字2分读音频次':freq[b,s],'权重':weight(p),'字1整字频次排名':rank[a],'字2整字频次排名':rank[b],'字1待分配':pending[a],'字2待分配':pending[b]}
    old=pair_sets(base,readings,find)
    results=[];allpairs=[];changes=[]
    manual=set(rawbase['manual'])
    # These five named roots currently exist only in maintained split rules.
    special={'党字头','冓头','走下','互中间','赢字架'}
    # Removing a frame must restore its two arms around the inner component.
    frame={'衣':(['亠'],['衣省']),'行':(['彳'],['一','丁']),'辡':(['辛旁'],['辛']),'玨':(['王'],['王']),'赢字架':(['亠','折','口','月'],['凡'])}
    for i,target in enumerate(inp['targets']):
        run=load(HERE/'runs'/f'{i:03}.json');rid=target['id'];name=target['names'][0]
        if run.get('fingerprint')!=fingerprint or run['id']!=rid:raise ValueError('缓存版本不一致：'+name)
        result={'根':target['display'],'原名':' / '.join(target['names']),'类型':'、'.join(target['roles']),'id':rid,'组':display(find(rid)),'group_id':find(rid),'使用字数':sum(rid in s for s in base.values()),'状态':'已计算','人工规则涉及字':[],'错误':[]}
        affected=[c for c,s in base.items() if rid in s]
        after=dict(base);repl=run.get('replacement',[])
        if run.get('error') and name not in special:
            result.update({'状态':'未完成','错误':[run['error']]});results.append(result);continue
        result['删后本根拆分']=split(repl) if repl else '按各字已确认结构局部恢复'
        for c in set(run.get('affected',[]))|set(affected):
            canonical=base[c]
            is_frame=name in frame and c in frame_chars.get('赢' if name=='赢字架' else name,set())
            if c not in manual and not is_frame:
                after[c]=run['rows'][c]
            elif rid not in canonical:
                # Preserve accepted corrections even when the old engine changes.
                after[c]=canonical
            else:
                result['人工规则涉及字'].append(c)
                try:
                    if name in frame:
                        before_arm,after_arm=frame[name];pos=canonical.index(rid)
                        a=[norm.get(t,t) for t in before_arm];b=[norm.get(t,t) for t in after_arm]
                        raw=rawbase['rows'][c]
                        ends=[j+len(b) for j in range(len(raw)-len(b)+1) if raw[j:j+len(b)]==b]
                        # Restore the arm before the original external suffix (愆: 心).
                        suffix=raw[ends[-1]:] if ends else []
                        if suffix and canonical[-len(suffix):]!=suffix:raise ValueError('字架外部后缀无法对齐')
                        stop=len(canonical)-len(suffix)
                        after[c]=canonical[:pos]+a+canonical[pos+1:stop]+b+suffix
                    elif name in special:
                        after[c]=local_recovery(canonical,rawbase['rows'][c],rid)
                    else:after[c]=[x for t in canonical for x in (repl if t==rid else [t])]
                    if rid in after[c] or not after[c]:raise ValueError('删根后仍残留目标或空拆分')
                except ValueError as e:result['错误'].append(c+':'+str(e))
        if result['错误']:
            result['状态']='未完成';results.append(result);continue
        if result['人工规则涉及字']:result['状态']='条件试算：含人工结构'
        if any(rid in seq for seq in after.values()):raise ValueError('root remains '+name)
        new=pair_sets(after,readings,find);h,t,u,both=added_sets(old,new)
        result.update({'首根新增':len(h),'末根新增':len(t),'新增对数':len(u),'首末同时新增':len(both),'加权影响':sum(map(weight,u)),'消除对数':len((old[0]-new[0])|(old[1]-new[1])),'涉及未分配的新增对数':sum(pending[a]>0 or pending[b]>0 for s,a,b in u),'前500字对':sum(rank[a]<=500 and rank[b]<=500 for s,a,b in u),'前1500字对':sum(rank[a]<=1500 and rank[b]<=1500 for s,a,b in u),'改拆字数':sum(base[c]!=after[c] for c in base),'新增对':[],'变化':[]})
        for p in sorted(u,key=lambda p:(-weight(p),p)):
            info=pairinfo(p);info['位置']='、'.join(x for x,ps in [('首根',h),('末根',t)] if p in ps);info['首末同时']=p in both
            result['新增对'].append(info);allpairs.append({'根':result['根'],**info})
        for c in base:
            if base[c]!=after[c]:
                info={'字':c,'改前':split(base[c]),'改后':split(after[c]),'整字频次排名':rank[c],'人工结构':c in result['人工规则涉及字']}
                result['变化'].append(info);changes.append({'根':result['根'],**info})
        results.append(result)
    results.sort(key=lambda r:(r.get('加权影响',float('inf')),r.get('新增对数',float('inf')),r['根']))
    groups=[]
    for gid in sorted({r['group_id'] for r in results}):
        members=[r for r in results if r['group_id']==gid];valid=[r for r in members if '加权影响'in r]
        excluded=[e for e in inp['excluded'] if find(e['id'])==gid]
        g={'组':display(gid),'成员数':len(members),'完成数':len(valid),'成员':[r['根'] for r in members],'排除成员':[e['display'] for e in excluded],'状态':'完整' if len(valid)==len(members) else '未完成，不计算平均','含人工结构成员':sum(bool(r['人工规则涉及字']) for r in members)}
        if len(valid)==len(members):
            g.update({'平均加权影响':sum(r['加权影响'] for r in members)/len(members),'平均新增对数':sum(r['新增对数'] for r in members)/len(members),'平均首根新增':sum(r['首根新增'] for r in members)/len(members),'平均末根新增':sum(r['末根新增'] for r in members)/len(members)})
        groups.append(g)
    groups.sort(key=lambda g:(g.get('平均加权影响',float('inf')),g.get('平均新增对数',float('inf')),g['组']))
    summary={'核心字':len(base),'根形总数':len(inventory),'评估根数':len(results),'排除数':len(inp['excluded']),'计算完成':sum('加权影响'in r for r in results),'含人工规则':sum(r['状态'].startswith('条件') for r in results),'未完成':sum(r['状态']=='未完成' for r in results),'零新增':sum(r.get('新增对数')==0 for r in results),'组数':len(groups),'原始引擎与维护表差异字数':len(manual),'基线已删根':inp['confirmed']}
    data={'summary':summary,'roots':results,'groups':groups,'excluded':inp['excluded']}
    dump(HERE/'评估结果.json',data)
    rootfields=['根','原名','类型','组','状态','使用字数','改拆字数','首根新增','末根新增','新增对数','首末同时新增','加权影响','消除对数','前500字对','前1500字对','涉及未分配的新增对数','删后本根拆分']
    tsv(HERE/'逐根影响排行.tsv',results,rootfields)
    tsv(HERE/'组平均影响排行.tsv',groups,['组','成员数','完成数','状态','平均加权影响','平均新增对数','平均首根新增','平均末根新增','含人工结构成员','成员','排除成员'])
    tsv(HERE/'新增冲突对明细.tsv',allpairs,['根','音节','字对','位置','首末同时','权重','字1分读音频次','字2分读音频次','字1整字频次排名','字2整字频次排名','字1待分配','字2待分配'])
    tsv(HERE/'逐字拆分变化.tsv',changes,['根','字','改前','改后','整字频次排名','人工结构'])
    template=(HERE/'template.html').read_text(encoding='utf-8');(HERE/'逐根删除影响排行.html').write_text(template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False));print('failures',[(r['根'],r['错误']) for r in results if r['状态']=='未完成'])
if __name__=='__main__':main()
