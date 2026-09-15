"""Prepare isolated ablations; never modify the maintained root inventory."""
from pathlib import Path
import json, runpy, yaml, hashlib, functools
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    runpy.run_path(str(HERE.parent/'03_字音频率审计/rebuild.py'))['check_current']()
    a=runpy.run_path(str(ROOT/'work/重开工程/scripts/audit_manual_split_propagation.py'))
    base=yaml.safe_load(a['BASELINE_PATH'].read_text(encoding='utf-8'))
    roots=yaml.safe_load(a['ROOTS_PATH'].read_text(encoding='utf-8'))
    rules=yaml.safe_load(a['RULES_PATH'].read_text(encoding='utf-8'))['component_splits']
    names,labels=a['repertoire_maps'](base)
    resolve=functools.lru_cache(None)(lambda x:a['resolve'](x,names))
    cfg=a['compile_config'](base,roots,rules,names)
    # Physical key letters must not affect the counterfactual or group scores.
    cfg['form']['mapping']={x:'a' for x in cfg['form']['mapping']}
    _,expected=a['load_table']()
    ledger=json.loads((HERE.parent/'02_改动台账/改动台账.json').read_text(encoding='utf-8'))
    removed={e['proposal']['root']:e['proposal']['replacement'] for e in ledger['entries'] if e['decision']=='已确认'}
    for r,ts in removed.items():
        cfg['form']['mapping'].pop(resolve(r),None)
        for c,seq in expected.items():expected[c]=[x for t in seq for x in (ts if t==r else [t])]
        for c,seq in cfg['analysis']['customize'].items():
            cfg['analysis']['customize'][c]=[x for t in seq for x in ([resolve(v) for v in ts] if t==resolve(r) else [t])]
        cfg['analysis']['customize'][resolve(r)]=[resolve(v) for v in ts]
    inventory={}
    edges=[]
    for section,kind in [('roots','附属'),('anchors','锚定')]:
        for host,children in roots[section].items():
            for label,role in [(host,'主根')]+[(c,kind) for c in children]:
                ident=resolve(label)
                item=inventory.setdefault(ident,{'id':ident,'names':[],'roles':[]})
                if label not in item['names']:item['names'].append(label)
                if role not in item['roles']:item['roles'].append(role)
            edges.extend((resolve(host),resolve(c)) for c in children)
    # Two legacy labels duplicate an explicitly named current root. Removing
    # only one engine ID would merely fall back to its alias and fake zero cost.
    aliases={resolve(n):resolve(d) for n,d in roots.get('presentation_names',{}).items() if any(d in r['names'] for r in inventory.values()) and resolve(n)!=resolve(d)}
    for old,new in aliases.items():
        source=inventory.pop(old);target=inventory[new]
        target['names']=list(dict.fromkeys(target['names']+source['names']))
        target['roles']=list(dict.fromkeys(target['roles']+source['roles']))
    for ident,item in inventory.items():item['ids']=[ident]+[old for old,new in aliases.items() if new==ident]
    edges=[(aliases.get(a,a),aliases.get(b,b)) for a,b in edges]
    traditional=set('魚車鳥門長馬龜黽戶')
    norm={}
    for ident,item in inventory.items():
        norm[ident]=ident
        norm[labels.get(ident,ident)]=ident
        for n in item['names']:norm[n]=ident
        for old in item['ids']:norm[old]=ident;norm[labels.get(old,old)]=ident
    norm['6']='5';norm['折']='5'
    for name,ident in a['STROKES'].items():norm[name]=ident
    exclusions=[];targets=[]
    for ident,item in inventory.items():
        reason='已确认删除，计入累计基线' if any(n in removed for n in item['names']) else '繁体根，本轮不删除' if ident in traditional else '五种基础笔画，不能撤掉底层拆分能力' if ident in '12345' else ''
        item['display']=' / '.join(dict.fromkeys(roots.get('presentation_names',{}).get(n,n) for n in item['names']))
        if reason:exclusions.append({**item,'reason':reason})
        else:targets.append(item)
    expected={c:[norm.get(t,resolve(t)) for t in ts] for c,ts in expected.items()}
    (HERE/'active.yaml').write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False),encoding='utf-8')
    dump(HERE/'input.json',{'expected':expected,'norm':norm,'targets':targets,'excluded':exclusions,'inventory':list(inventory.values()),'edges':edges,'confirmed':removed})
    sources=[a[k] for k in ['ROOTS_PATH','RULES_PATH','BASELINE_PATH','TABLE_PATH','NAME_ALIASES_PATH','REPERTOIRE_PATH','FRAME_RULES_PATH']]+[HERE.parent/'02_改动台账/改动台账.json',HERE.parent/'03_字音频率审计/审计摘要.json']+list((ROOT/'repos/webchai/packages/hanzi-chai/src').rglob('*.ts'))
    dump(HERE/'source-fingerprints.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    print('targets',len(targets),'excluded',len(exclusions))
if __name__=='__main__':main()
