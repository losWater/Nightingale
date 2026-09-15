"""2.0用可追溯分读音字频。原始来源和1.0历史表均不改写。"""
from pathlib import Path
from collections import Counter, defaultdict
import csv, hashlib, json, re, unicodedata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT/'work/重开工程/03_字音频率'
RAW = OLD/'数据源/SUBTLEX-CH/SUBTLEX_CH_131210_CE.utf8'
LEX = ROOT/'repos/webchai/packages/hanzi-chai/src/data/dictionary.txt'
BASE = OLD/'SUBTLEX阶段性分读音频率表_人工定案版.tsv'
OVERRIDES = HERE/'整词读音裁决.json'
REFDIR=ROOT/'releases/v0.9.1/99_参考资料/参考'
JD=REFDIR/'简单鹤V9.3.0纯词库 (1).txt'
JL=REFDIR/'鲸凉鹤1.1手心挂接.txt'
PREVIOUS=ROOT/'data/maintenance/polyphonic-word-codes.tsv'
FLY={('百','be'):'bd',('几','jo'):'ji',('一','ei'):'yi',('鹤','eh'):'he'}

def double_code(s):
    if s in ('a','o','e'):return s+s
    if s in ('ai','ei','ao','ou','an','en','er'):return s
    if s in ('ang','eng'):return s[0]+'g' if s=='eng' else 'ah'
    onset=s[:2] if s[:2] in ('zh','ch','sh') else s[:1]
    final=s[len(onset):]
    endings={'a':'a','o':'o','e':'e','i':'i','u':'u','v':'v','ai':'d','ei':'w','ao':'c','ou':'z','an':'j','en':'f','ang':'h','eng':'g','ong':'s','iong':'s','ia':'x','ua':'x','ie':'p','iao':'n','iu':'q','ian':'m','in':'b','iang':'l','uang':'l','ing':'k','uai':'k','uan':'r','un':'y','uo':'o','ue':'t','ve':'t','ui':'v'}
    return {'zh':'v','ch':'i','sh':'u'}.get(onset,onset)+endings[final] if final in endings else None

def read_reference(path,palm,allowed):
    result=defaultdict(set);invalid=[];fly_rows=[]
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if palm:
            match=re.fullmatch(r'([a-z]+)=\d+,(.+)',line)
            if not match:continue
            code,word=match.groups()
        else:
            parts=line.split('\t')
            if len(parts)!=2:continue
            word,code=parts
        # 三字以上四码通常是缩写，不解码为逐字拼音。
        if len(word)!=2 or not re.fullmatch('[a-z]{4}',code):continue
        normalized=''.join(FLY.get((c,code[2*i:2*i+2]),code[2*i:2*i+2]) for i,c in enumerate(word))
        if code!=normalized:fly_rows.append({'来源':path.name,'词':word,'原码':code,'去飞键':normalized})
        decoded=[{s for s in allowed.get(c,set()) if double_code(s)==normalized[2*i:2*i+2]} for i,c in enumerate(word)]
        if all(len(s)==1 for s in decoded):result[word].add(tuple(next(iter(s)) for s in decoded))
        else:invalid.append({'来源':path.name,'词':word,'原码':code,'去飞键':normalized,'原因':'未知飞键、非音码或读音集合未覆盖；不猜测'})
    return result,invalid,fly_rows

def table(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))

def write(name, rows, fields):
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t');w.writeheader();w.writerows(rows)

def syllable(s):
    s=s.lower().replace('u:','v').replace('ü','v')
    s=''.join(c for c in unicodedata.normalize('NFD',s) if not unicodedata.combining(c))
    s=re.sub('[1-5]','',s)
    return 'er' if s=='r' else s

def options(text):
    return [set(syllable(v) for v in s.split('/')) for s in text.split()]

def input_join(text):
    # 无分隔连写只作核验，不据此自行切分或选择读音；多候选保留待核标记。
    if '/' in text or '#' in text:return None
    text=syllable(text).replace("'",'').replace(' ','').replace('-','')
    return text if re.fullmatch('[a-z]+',text) else None

def decide(word, source, auxiliary, lex, allowed, override=None, jd=(), jl=()):
    opts=options(source)
    valid_source=len(opts)==len(word) and all(o and all(re.fullmatch('[a-z]+',s) for s in o) for o in opts)
    unique=tuple(next(iter(o)) for o in opts) if valid_source and all(len(o)==1 for o in opts) else None
    aux=input_join(auxiliary)
    refs={tuple(syllable(s) for s in r) for r in lex if len(r)==len(word)}
    ref=next(iter(refs)) if len(refs)==1 else None
    supported=lambda r: r is not None and all(s in allowed.get(c,set()) for c,s in zip(word,r))
    matches_source=lambda r: valid_source and all(s in o for s,o in zip(r,opts))
    issues=[]
    if unique and aux and ''.join(unique)!=aux:issues.append('原始两拼音字段矛盾')
    if aux is None:issues.append('辅助拼音不可唯一核验')
    if ref and valid_source and not matches_source(ref):issues.append('整词词典与原始拼音矛盾')
    if ref and aux and ''.join(ref)!=aux:issues.append('整词词典与辅助拼音矛盾')
    if override:
        chosen=tuple(override['syllables'])
        if not supported(chosen):raise ValueError(f'人工裁决越出读音集合：{word} {chosen}')
        return chosen,'整词人工裁决',issues
    a,b=set(jd),set(jl)
    if a or b:
        common=a&b if a and b else a or b
        if not common:
            return None,'简单鹤与鲸凉鹤读音不相交；待分配',issues+['两份参考分歧']
        if len(common)>1:
            if unique==ref and unique in common and supported(unique):
                return unique,'原始音节与Chai一致且获两参考支持；兼容异读未当频次',issues+['参考含多个读音；未均摊词频']
            return None,'参考异读无法消歧；待分配',issues+['两份参考不能唯一确定']
        selected=next(iter(common))
        if a and b and supported(selected):
            if unique==ref and unique is not None and selected!=unique:
                return None,'两鹤与原始音节、Chai相互矛盾；待裁决',issues+['不能仅靠两鹤一致覆盖另一组一致证据']
            if not matches_source(selected):issues.append('两鹤一致但原始拼音不同')
            if ref and ref!=selected:issues.append('两鹤一致但Chai不同')
            return selected,'简单鹤与鲸凉鹤去飞键后一致',issues
        if supported(selected) and (matches_source(selected) or selected==ref or aux==''.join(selected)):
            return selected,'单份鹤参考与其他证据一致',issues
        return None,'单份鹤参考与其他证据冲突；待分配',issues+['鹤参考分歧']
    if ref and supported(ref) and matches_source(ref):
        return ref,'整词词典与原始音节一致',issues
    if ref and supported(ref) and aux==''.join(ref):
        return ref,'整词词典与辅助字段一致；修正原始音节',issues
    if unique and supported(unique) and aux==''.join(unique) and (not refs or unique in refs):
        return unique,'原始双字段一致（非独立语料证据）',issues
    return None,'证据不足或仍冲突；待分配',issues

def source_files():
    return [RAW,LEX,BASE,JD,JL,PREVIOUS,OVERRIDES,Path(__file__).resolve(),
            OLD/'SUBTLEX单字多音高置信分配.tsv',OLD/'封闭读音集合新增定案.tsv',OLD/'多音字人工频率定案.tsv']

def fingerprint():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files()}

def check_current():
    report=json.loads((HERE/'审计摘要.json').read_text(encoding='utf-8'))
    if report['source_hashes']!=fingerprint():raise RuntimeError('字频输入或规则已变化，必须先重建审计表')
    for name,digest in report['output_hashes'].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('审计产物被修改：'+name)
    return report

def main():
    HERE.mkdir(parents=True,exist_ok=True)
    original_hashes=fingerprint()
    original=table(BASE);allowed=defaultdict(set)
    for r in original:allowed[r['汉字']].add(r['拼音'])
    jd,invalid_a,fly_a=read_reference(JD,False,allowed)
    jl,invalid_b,fly_b=read_reference(JL,True,allowed)
    lex=defaultdict(set)
    for line in LEX.read_text(encoding='utf-8-sig').splitlines():
        parts=line.split('\t')
        if len(parts)>1 and parts[1]:lex[parts[0]].add(tuple(parts[1].split()))
    overrides=json.loads(OVERRIDES.read_text(encoding='utf-8'))
    for row in table(PREVIOUS):
        word,code=row['词'],row['新码']
        decoded=[{s for s in allowed.get(c,set()) if double_code(s)==code[2*i:2*i+2]} for i,c in enumerate(word)]
        if len(word)==2 and len(code)==4 and all(len(s)==1 for s in decoded):
            overrides.setdefault(word,{'syllables':[next(iter(s)) for s in decoded],'reason':'沿用已有逐词裁决：'+row['依据']})
    priors=defaultdict(Counter)
    for filename,field in [('SUBTLEX单字多音高置信分配.tsv','已定分配频率'),('封闭读音集合新增定案.tsv','新增定案频率')]:
        for r in table(OLD/filename):priors[r['汉字']][r['拼音']]+=int(r[field])
    for r in table(OLD/'多音字人工频率定案.tsv'):
        for item in r['分配结果'].split(';'):
            s,n=item.split(':');priors[r['汉字']][s]+=int(n)
    raw=table(RAW)
    single_totals=Counter()
    for r in raw:
        if len(r['Word'])==1:single_totals[r['Word']]+=int(r['WCount'])
    for c,alloc in priors.items():
        assert sum(alloc.values())<=single_totals[c],(c,alloc,single_totals[c])
        assert all(v>=0 and s in allowed[c] for s,v in alloc.items())
    used_priors=set();assigned=Counter();pending=Counter();total=Counter()
    evidence=[];audit=[];word_pending=[];stats=Counter();prior_freq=Counter()
    for line,r in enumerate(raw,2):
        word=r['Word'];n=int(r['WCount']);assert n>=0
        stats['raw_rows']+=1;stats['raw_word_frequency']+=n
        for c in word:
            if c in allowed:total[c]+=n
        if len(word)==1 and word in priors and sum(priors[word].values()):
            # 单字可能有重复行（常见一行带音、一行#）。历史裁决属于整个单字池，最后统一分配一次。
            used_priors.add(word)
            pending[word]+=n
            evidence.append({'行号':line,'词':word,'词频':n,'原拼音':r['Pinyin'],'辅助拼音':r['Pinyin.Input'],'词典读音':' | '.join(' '.join(s) for s in sorted(lex[word])),'简单鹤':'','鲸凉鹤':'','采用':'进入单字公共池','依据':'历史单字人工/比例裁决单独记账（不是上下文实测）','问题':'重复行合计后仅应用一次'})
            continue
        # 孤立多音字无语境，不用词典默认读音或Pinyin.Input进行分配。
        single_options=options(r['Pinyin'])
        # 统计不分声调：hao3/hao4都是hao，不应错当成两个待分配音节。
        ambiguous_single=len(word)==1 and (len(single_options)!=1 or len(single_options[0])!=1 or not all(re.fullmatch('[a-z]+',s) for s in single_options[0]))
        if ambiguous_single:chosen,reason,issues=None,'孤立多音字无语境；待分配',[]
        else:chosen,reason,issues=decide(word,r['Pinyin'],r['Pinyin.Input'],lex[word],allowed,overrides.get(word),jd.get(word,()),jl.get(word,()))
        if chosen:
            for c,s in zip(word,chosen):assigned[c,s]+=n
            stats['accepted_rows']+=1;stats['accepted_word_frequency']+=n
        else:
            for c in word:
                if c in allowed:pending[c]+=n
            stats['pending_rows']+=1;stats['pending_word_frequency']+=n
        entry={'行号':line,'词':word,'词频':n,'原拼音':r['Pinyin'],'辅助拼音':r['Pinyin.Input'],'词典读音':' | '.join(' '.join(s) for s in sorted(lex[word])),'简单鹤':' | '.join(' '.join(s) for s in sorted(jd.get(word,()))),'鲸凉鹤':' | '.join(' '.join(s) for s in sorted(jl.get(word,()))),'采用':' '.join(chosen) if chosen else '待分配','依据':reason,'问题':'；'.join(issues)}
        evidence.append(entry)
        if issues:audit.append(entry)
        if chosen is None:word_pending.append(entry)
    prior_log=[]
    for c in sorted(used_priors):
        amount=sum(priors[c].values());pending[c]-=amount;assert pending[c]>=0
        for s,v in priors[c].items():assigned[c,s]+=v;prior_freq[c,s]+=v
        stats['prior_allocated_frequency']+=amount
        prior_log.append({'汉字':c,'单字原始池':single_totals[c],'历史分配':amount,'剩余':single_totals[c]-amount,'逐音分配':'；'.join(f'{s}:{v}' for s,v in sorted(priors[c].items()))})
    stats['single_pool_rows']=len(raw)-stats['accepted_rows']-stats['pending_rows']
    stats['single_pool_remaining']=sum(single_totals[c]-sum(priors[c].values()) for c in used_priors)
    assert stats['accepted_word_frequency']+stats['pending_word_frequency']+stats['prior_allocated_frequency']+stats['single_pool_remaining']==stats['raw_word_frequency']
    for c in allowed:assert sum(v for (cc,s),v in assigned.items() if cc==c)+pending[c]==total[c],c
    assert original_hashes==fingerprint(),'构建期间输入发生变化'
    oldcounts={(r['汉字'],r['拼音']):int(r['人工定案后阶段频率']) for r in original}
    output=[];diff=[]
    for c in sorted(allowed):
        for s in sorted(allowed[c]):
            v=assigned[c,s]
            output.append({'汉字':c,'拼音':s,'已分配频率':v,'其中历史单字裁决':prior_freq[c,s],'该字待分配频率':pending[c],'该字原始总频':total[c],'状态':'未观测到分配证据；不等于实际零频' if not v else '有已分配证据；仍须结合待分配量'})
            if v!=oldcounts[c,s]:diff.append({'汉字':c,'拼音':s,'旧频率':oldcounts[c,s],'新已分配频率':v,'变化':v-oldcounts[c,s],'该字待分配频率':pending[c]})
    chars=[{'汉字':c,'原始总频':total[c],'已分配频率':sum(assigned[c,s] for s in allowed[c]),'待分配频率':pending[c]} for c in sorted(allowed)]
    files=[('分读音字频_审计版.tsv',output,list(output[0])),('整字频次守恒.tsv',chars,list(chars[0])),('逐词分配证据.tsv',evidence,list(evidence[0])),('拼音矛盾核对.tsv',sorted(audit,key=lambda r:-r['词频']),list(evidence[0])),('待分配词条.tsv',sorted(word_pending,key=lambda r:-r['词频']),list(evidence[0])),('与旧表差异.tsv',diff,list(diff[0]))]
    files += [('参考码无法解读.tsv',invalid_a+invalid_b,['来源','词','原码','去飞键','原因']),('参考飞键还原.tsv',fly_a+fly_b,['来源','词','原码','去飞键']),('单字历史裁决记账.tsv',prior_log,list(prior_log[0]))]
    for name,rs,fields in files:write(name,rs,fields)
    assert len(evidence)==len(raw)
    report={**stats,'conflict_or_uncheckable_rows':len(audit),'core_characters':len(allowed),'reading_pairs':len(output),'changed_pairs':len(diff),'core_character_occurrences':sum(total.values()),'assigned_character_occurrences':sum(assigned.values()),'pending_character_occurrences':sum(pending.values()),'per_character_conservation':True,'source_hashes':original_hashes,'output_hashes':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name,_,_ in files},'readiness':'可用于保守读音覆盖检查；未解决词条已隔离，分读音权重不代表全量精确频率'}
    (HERE/'审计摘要.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if not k.endswith('hashes')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
