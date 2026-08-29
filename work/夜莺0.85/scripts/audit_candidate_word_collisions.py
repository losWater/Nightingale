#!/usr/bin/env python3
"""展开候选单字全码与固定词码位的具体碰撞。"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def words(path):
    with path.open(encoding="utf-8-sig",newline="") as f: return {x["code"]:x for x in csv.DictReader(f,delimiter="\t")}
def audit(name,path,target,top):
    rows=[]
    for rank,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        word,full,full_rank,actual,actual_rank=line.split("\t")
        if rank>top: break
        if full not in target: continue
        t=target[full]; listed=(t["two_words"]+" "+t["four_words"]).split()
        if actual!=full: status="已有简码避开"
        elif listed and all(x.startswith(word) for x in listed): status="同首字可保留"
        else: status="直接撞车"
        rows.append({"code":full,"char":word,"char_rank":rank,"actual":actual,"status":status,"two_top_rank":int(t["two_top_rank"]) if t["two_top_rank"] else None,"four_top_rank":int(t["four_top_rank"]) if t["four_top_rank"] else None,"two_words":t["two_words"],"four_words":t["four_words"]})
    def key(x): return ({"直接撞车":0,"同首字可保留":1,"已有简码避开":2}[x["status"]],x["two_top_rank"] or 10**9,x["four_top_rank"] or 10**9,x["char_rank"])
    rows.sort(key=key)
    return {"name":name,"top":top,"total":len(rows),"direct":sum(x["status"]=="直接撞车" for x in rows),"same_initial":sum(x["status"]=="同首字可保留" for x in rows),"protected":sum(x["status"]=="已有简码避开" for x in rows),"direct_top20000":sum(x["status"]=="直接撞车" and x["two_top_rank"] is not None and x["two_top_rank"]<=20000 for x in rows),"rows":rows}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--candidate",action="append",required=True); ap.add_argument("--target-lexicon",type=Path,required=True); ap.add_argument("--top",type=int,default=3527); ap.add_argument("--output-json",type=Path,required=True); ap.add_argument("--output-md",type=Path,required=True); a=ap.parse_args(); target=words(a.target_lexicon); data=[]
    for spec in a.candidate:
        n,s,p=spec.partition("=")
        if not s: raise ValueError("candidate必须为名称=code.txt")
        data.append(audit(n,Path(p),target,a.top))
    a.output_json.write_text(json.dumps({"schema_version":1,"candidates":data},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"# 前{a.top}字与目标词码位碰撞",""]
    for d in data:
        lines += [f"## {d['name']}","",f"- 相撞身份：{d['total']}；直接撞车：{d['direct']}；其中撞前20000二字词：{d['direct_top20000']}；同首字：{d['same_initial']}；已有简码避开：{d['protected']}","","|状态|码|字（排名）|实际码|二字词最高排名|具体二字词|四字词|","|---|---|---|---|---:|---|---|"]
        for x in d["rows"]:
            lines.append(f"|{x['status']}|`{x['code']}`|{x['char']}（{x['char_rank']}）|`{x['actual']}`|{x['two_top_rank'] or ''}|{x['two_words']}|{x['four_words']}|")
        lines.append("")
    a.output_md.write_text("\n".join(lines)+"\n",encoding="utf-8")
if __name__=="__main__": main()
