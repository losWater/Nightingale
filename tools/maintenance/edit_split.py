"""Edit the active split source, with a preview, backup and ledger entry."""
import argparse
import csv
import datetime
import io
import json
import re
import shutil
from context import load, sha, atomic
from export import extract_json
from apply_ledger import FIELDS, load as read_table
from semantics import metadata, full_codes

def replace_json(text,name,obj):
    m=re.search(r'\b(?:const|let)\s+'+re.escape(name)+r'\s*=\s*',text)
    if not m: raise ValueError(name)
    _,size=json.JSONDecoder().raw_decode(text[m.end():])
    return text[:m.end()]+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+text[m.end()+size:]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('changes',nargs='+');p.add_argument('--root');p.add_argument('--apply',action='store_true')
    p.add_argument('--reason',default='');p.add_argument('--add',action='store_true',help='登记尚不存在的新字拆分');a=p.parse_args()
    _,active,_=load(a.root,writable=a.apply)
    source=active/'资料/拆分原本.html'; original=source.read_bytes()
    page=original.decode('utf-8-sig');views=extract_json(page,'views');data=extract_json(views['query'],'D')
    roots={r['根']:r for v in data.values() for r in v['根']}
    table=read_table(active/'主表/单字表.txt');todo=[]
    normal=full_codes(table,metadata(active))
    for change in a.changes:
        char,split=change.split('=',1); names=[s for s in re.split(r'[＋+·\s]+',split) if s]
        if len(char)!=1 or not names or any(n not in roots for n in names): raise ValueError('字或字根无效：'+change)
        if char not in data and not a.add: raise ValueError('新字需显式 --add：'+char)
        if char in data and a.add: raise ValueError('拆分已存在，不能重复新增：'+char)
        new=' ＋ '.join(names); old=data[char]['新拆'] if char in data else ''
        if old==new: continue
        expected=''.join(roots[n]['键'] for n in (names[0],names[-1]))
        if any(c[2:]!=expected for (t,s),codes in normal.items() if t==char for c in codes):
            raise ValueError('首末根与现有码不一致，请先核实并通过台账改码（含容错例外）：'+char)
        todo.append((char,old,new));data.setdefault(char,{'排名':99999,'编码':[]})
        data[char]['新拆']=new;data[char]['根']=[dict(roots[n]) for n in names]
    print(todo)
    if not a.apply or not todo: print('未写入。');return
    if not a.reason: raise ValueError('落盘必须提供 --reason')
    views['query']=replace_json(views['query'],'D',data)
    updated=replace_json(page,'views',views).encode('utf-8-sig')
    ledger=active/'记录/修改台账.tsv'; ledger_bytes=ledger.read_bytes()
    rows=list(csv.DictReader(io.StringIO(ledger_bytes.decode('utf-8-sig')),delimiter='\t'))
    now=datetime.datetime.now().astimezone();batch='SPLIT-'+now.strftime('%Y%m%d%H%M%S%f')
    backup=active/'备份'/batch;backup.mkdir(parents=True)
    shutil.copy2(source,backup/source.name);shutil.copy2(ledger,backup/ledger.name)
    import hashlib
    for n,(char,old,new) in enumerate(todo,1):
        row=dict.fromkeys(FIELDS,'');row.update({'问题ID':f'{batch}-{n:02d}','原文摘录':a.reason,'状态':'已修复',
        '目标码表':'拆分原本','操作':'新增拆分' if not old else '改拆分','原字词':char if old else '', '新字词':char,'备注':f'{old} → {new}',
        '处理时间':now.isoformat(timespec='seconds'),'处理结果':'只改拆分原本，需重新导出',
        '修改前SHA256':hashlib.sha256(original).hexdigest(),'修改后SHA256':hashlib.sha256(updated).hexdigest()});rows.append(row)
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=FIELDS,delimiter='\t',lineterminator='\n');writer.writeheader();writer.writerows(rows)
    if source.read_bytes()!=original or ledger.read_bytes()!=ledger_bytes: raise ValueError('文件发生并发修改')
    try: atomic(source,updated);atomic(ledger,out.getvalue().encode())
    except Exception:
        atomic(source,original);atomic(ledger,ledger_bytes);raise
    print('已记录并修改；未自动导出或部署。')

if __name__=='__main__': main()
