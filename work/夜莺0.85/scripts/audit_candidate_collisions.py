#!/usr/bin/env python3
"""展开候选的具体有效全码重码与实际码重码。"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path

def load(path: Path):
    rows=[]
    for i,line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        word,full,full_rank,actual,actual_rank=line.split("\t")
        rows.append({"index":i,"word":word,"full":full,"full_rank":int(full_rank),"actual":actual,"actual_rank":int(actual_rank)})
    return rows
def groups(rows, key):
    out=defaultdict(list)
    for x in rows: out[x[key]].append(x)
    return out
def audit(name,path,top):
    rows=load(path); layer=rows[:top]; fg=groups(layer,"full"); ag=groups(layer,"actual")
    effective=[]
    for x in layer:
        if x["full_rank"]>0 and len(x["actual"])>2:
            effective.append({"code":x["full"],"word":x["word"],"full_rank":x["full_rank"],"actual":x["actual"],"members":[{"word":y["word"],"actual":y["actual"],"protected_by_one_two_short":len(y["actual"])<=2} for y in fg[x["full"]]]})
    short=[]
    for code,members in ag.items():
        if len(members)>1:
            short.append({"code":code,"members":[{"word":x["word"],"rank":x["actual_rank"],"full":x["full"]} for x in sorted(members,key=lambda z:z["actual_rank"])]})
    return {"name":name,"code_path":str(path.resolve()),"top":top,"effective_full_count":len(effective),"effective_full":effective,"short_collision_extra":sum(len(x["members"])-1 for x in short),"short_collisions":short}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--candidate",action="append",required=True); ap.add_argument("--top",type=int,default=1500); ap.add_argument("--output-json",type=Path,required=True); ap.add_argument("--output-md",type=Path,required=True); a=ap.parse_args()
    data=[]
    for spec in a.candidate:
        name,sep,path=spec.partition("=")
        if not sep: raise ValueError("candidate必须为名称=code.txt")
        data.append(audit(name,Path(path),a.top))
    a.output_json.write_text(json.dumps({"schema_version":1,"candidates":data},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"# 前{a.top}具体重码展开",""]
    for d in data:
        lines += [f"## {d['name']}","",f"- 有效全码重码：{d['effective_full_count']}",f"- 实际码额外候选：{d['short_collision_extra']}","","### 有效全码重码",""]
        lines += [f"- `{x['code']}`："+"、".join(y['word']+("（一二简可绕）" if y['protected_by_one_two_short'] else f"（实际码 `{y['actual']}`）") for y in x['members']) for x in d['effective_full']] or ["- 无"]
        lines += ["","### 实际码重码（可能是简码或四码）",""]
        lines += [f"- `{x['code']}`："+"、".join(f"{y['word']}（{y['rank']+1}选，全码 `{y['full']}`）" for y in x['members']) for x in d['short_collisions']] or ["- 无"]
        lines.append("")
    a.output_md.write_text("\n".join(lines)+"\n",encoding="utf-8")
if __name__=="__main__": main()
