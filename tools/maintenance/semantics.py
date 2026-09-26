"""Explicit code types and impact checks; never infer candidate priority."""
from collections import defaultdict
import copy
import json
import re

TYPES = {'全码','简码','容错码','自定义码','全码词','简词'}

def json_file(path, default):
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(default)

def metadata(active):
    value=json_file(active/'配置/编码类型.json',{'entries':[]})
    seen=set()
    for r in value['entries']:
        pair=(r['text'],r['code'])
        if pair in seen or r['type'] not in TYPES: raise ValueError('编码类型重复或未知：'+str(pair))
        seen.add(pair)
    return value

def type_map(meta): return {(r['text'],r['code']):r['type'] for r in meta['entries']}

def kind(text,code,meta):
    index=type_map(meta) if 'entries' in meta else meta
    if (text,code) in index: return index[text,code]
    if len(text)==1: return '全码' if len(code)==4 else '简码'
    return '简词' if len(code)<4 else '全码词'

def full_codes(rows,meta):
    index=type_map(meta); result=defaultdict(list)
    for text,code in rows:
        if kind(text,code,index)=='全码' and len(text)==1 and re.fullmatch('[a-z]{4}',code):
            result[text,code[:2]].append(code)
    return result

def splits(active):
    path=active/'资料/拆分原本.html'
    if not path.exists(): return {}
    def get(text,name):
        m=re.search(r'\b(?:const|let)\s+'+name+r'\s*=\s*',text)
        if not m: raise ValueError('拆分原本缺少 '+name)
        return json.JSONDecoder().raw_decode(text[m.end():])[0]
    return get(get(path.read_text(encoding='utf-8-sig'),'views')['query'],'D')

def evolve(active,pending,before,after):
    meta=metadata(active); index=type_map(meta); changes={}
    for row in pending:
        op=row['操作'];target=row['目标码表']
        if target not in ('单字表','字词表') or op not in ('新增','改码','改词'): continue
        text=row['新字词'] if op in ('新增','改词') else row['原字词']
        code=row['原编码'] if op=='改词' else row['新编码']
        m=re.search(r'(?:^|[;；\s])类型=([^;；\s]+)',row['备注'])
        typ=m[1] if m else None
        if typ is None and op in ('改码','改词'):
            typ=kind(row['原字词'],row['原编码'],index)
        if typ is None and len(text)==1 and len(code)==4:
            raise ValueError(row['问题ID']+'：新增四码字必须注明 类型=全码 或 类型=容错码')
        typ=typ or kind(text,code,index)
        if typ not in TYPES: raise ValueError('未知类型：'+typ)
        if typ=='全码' and (len(text)!=1 or len(code)!=4): raise ValueError('全码必须是单字四码')
        if typ=='简码' and (len(text)!=1 or not 1<=len(code)<=3): raise ValueError('简码必须是单字一至三码；跨类型改码请明确类型')
        if typ=='简词' and (len(text)<2 or len(code)>=4): raise ValueError('简词类型与码长不符')
        if typ=='全码词' and (len(text)<2 or len(code)<4): raise ValueError('全码词类型与码长不符')
        pair=(text,code)
        if pair in changes and changes[pair]!=typ: raise ValueError('两表对同一编码的类型声明不一致')
        changes[pair]=typ
    old_pairs=set(before['单字表'])|set(before['字词表'])
    new_pairs=set(after['单字表'])|set(after['字词表'])
    for pair in old_pairs-new_pairs: index.pop(pair,None)
    index.update({pair:typ for pair,typ in changes.items() if pair in new_pairs})
    meta['entries']=[{'text':t,'code':c,'type':typ} for (t,c),typ in sorted(index.items())]
    old_full=full_codes(before['单字表'],metadata(active)); new_full=full_codes(after['单字表'],meta)
    old_chars={t for t,c in before['单字表']}; new_chars={t for t,c in after['单字表']}
    full_chars={t for t,s in new_full}
    lost=({t for t,s in old_full}&new_chars)-full_chars
    missing=(new_chars-old_chars)-full_chars
    if lost or missing: raise ValueError('不能留下只有简码/容错码而没有正式全码的字：'+''.join(sorted(lost|missing)))
    added=set(after['单字表'])-set(before['单字表'])
    need={t for t,c in added if kind(t,c,meta)=='全码'}
    missing_split=need-set(splits(active))
    if missing_split: raise ValueError('请先登记拆分（edit_split.py --add）：'+''.join(sorted(missing_split)))
    for text,code in added:
        if kind(text,code,meta)=='简码' and not any(c.startswith(code) for (t,s),cs in new_full.items() if t==text for c in cs):
            raise ValueError('正常简码必须是该字正式全码前缀；特殊打法需声明类型：'+text+'/'+code)
    warnings=[]
    for text,sound in sorted(set(old_full)-set(new_full)):
        warnings.append(f'{text}/{sound}：该读音的正式全码已移除，反查和整句入口随之移除；不会自动删除其他简码或相关词')
    for text,code in old_pairs-new_pairs:
        if any(t==text for t,c in new_pairs):warnings.append(f'仅删除 {text}/{code}，该字词的其他编码仍保留')
    if changes: warnings.append('新增/改码未自动处理简码兼占、出简让全或词序；须按台账核对相关候选位')
    new_words={t for t,c in after['字词表'] if len(t)>1}-{t for t,c in before['字词表'] if len(t)>1}
    readings=json_file(active/'配置/词语读音.json',{})
    validate_readings(readings,new_full)
    for text in sorted(new_words):
        inferred=(len(text)==2 and any(t==text and len(c)==4 and (text[0],c[:2]) in new_full and (text[1],c[2:]) in new_full
                                      for t,c in after['字词表']))
        if text not in readings and not inferred: warnings.append(f'{text}：未登记逐字读音，固定入口可用，整句词条需另查导出报告')
    slots=defaultdict(list)
    for text,code in after['单字表']+after['符号表']:
        if len(text)==1: slots[code].append(text)
    apply_overrides(slots,json_file(active/'配置/单字版差异.json',[]))
    return meta,warnings

def validate_readings(readings,full):
    for word,sounds in readings.items():
        if (not isinstance(word,str) or len(word)<2 or not isinstance(sounds,list)
            or len(sounds)!=len(word) or not all(isinstance(s,str) and (c,s) in full for c,s in zip(word,sounds))):
            raise ValueError('词语读音与正式全码不匹配：'+str(word))

def apply_overrides(slots,changes):
    original={(t,c) for c,ts in slots.items() for t in ts}
    for change in changes:
        code,text=change['code'],change['text'];bucket=slots[code]
        if 'expected_candidates' not in change or bucket!=change['expected_candidates']:
            raise ValueError('单字版差异与主表冲突：'+change['record']+' '+code)
        if any(tuple(pair) not in original for pair in change.get('requires',[])):
            raise ValueError('单字版差异依赖已删除/改码：'+change['record'])
        if change['operation']=='delete':
            if text not in bucket: raise ValueError('单字差异重复删除')
            bucket.remove(text)
        elif change['operation']=='insert':
            if text in bucket: raise ValueError('单字差异重复新增')
            pos=change['position']
            if not 1<=pos<=len(bucket)+1: raise ValueError('单字差异候选位越界')
            bucket.insert(pos-1,text)
        else: raise ValueError('未知单字差异操作')
