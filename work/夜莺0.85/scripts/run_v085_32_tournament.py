#!/usr/bin/env python3
"""夜莺0.85第二届32强：16组×16卡，五项核心指标等权秩和选2。"""
from __future__ import annotations

import argparse, copy, json, math, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml

TZ = timezone(timedelta(hours=10))

def now(): return datetime.now(TZ).isoformat(timespec="minutes")
def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
def run(cmd, cwd: Path, log: Path):
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n[{now()}] RUN {json.dumps([str(x) for x in cmd], ensure_ascii=False)}\n"); f.flush()
        p = subprocess.run([str(x) for x in cmd], cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    if p.returncode: raise RuntimeError(f"命令失败 {p.returncode}: {cmd}")
def complete(suite: Path):
    p=suite/"manifest.json"
    if not p.is_file(): return False
    d=json.loads(p.read_text(encoding="utf-8"))
    return d.get("status")=="complete" and len(d.get("cards",[]))==16 and all(Path(x.get("output_directory",''),"metric.json").is_file() for x in d["cards"])
def ranks(values, high=False):
    order=sorted(range(len(values)), key=lambda i: ((-values[i]) if high else values[i], i))
    result=[0.0]*len(values); n=max(1,len(values)-1)
    for pos,i in enumerate(order): result[i]=pos/n
    return result
def score_group(suite: Path, group: int):
    man=json.loads((suite/"manifest.json").read_text(encoding="utf-8"))
    core=json.loads((suite/"core_metrics.json").read_text(encoding="utf-8"))
    hand=json.loads((suite/"handfeel.json").read_text(encoding="utf-8"))["candidates"]
    rows=[]
    for card in man["cards"]:
        name=f"G{group}C{int(card['card']):02d}"; c=core[name]; h=hand[name]["1500"]
        metric=json.loads((Path(card["output_directory"])/"metric.json").read_text(encoding="utf-8"))["metric"]
        rows.append({"name":name,"group":group,"card":card["card"],"seed":card["seed"],"output_directory":card["output_directory"],
          "three":int(c["layers"]["6000"]["three_code_count"]),"pair":float(c["short_pair_equivalence"]),
          "cross":float(metric["character_word_collision"]["soft"]),"short_dup":float(c["short_duplication"]),
          "separation":float(h["phonetic_shape_hand_separation"]["separation_rate"]),
          "front300":int(c["layers"]["300"]["effective_full_duplication"]),
          "front1500":int(c["front1500_effective_full_duplication"]),"full_dup":float(c["full_duplication"]),
          "micro":float(h["single_finger_move"]["event_rate"]),"pinky":float(h["pinky_linkage"]["event_rate"])})
    eligible=[x for x in rows if x["front300"]==0]
    if len(eligible)<2: raise RuntimeError(f"第{group}组硬门禁后不足2张")
    dimensions=[("three",True),("pair",False),("cross",False),("short_dup",False),("separation",True)]
    for key,high in dimensions:
        rr=ranks([x[key] for x in eligible],high)
        for x,v in zip(eligible,rr): x.setdefault("rank_components",{})[key]=v
    for x in eligible: x["five_rank_score"]=sum(x["rank_components"].values())/5
    eligible.sort(key=lambda x:(x["five_rank_score"],x["front1500"],x["full_dup"],x["micro"],x["pinky"],x["name"]))
    report={"schema_version":1,"generated_at":now(),"eligible":eligible,"rejected":[x for x in rows if x["front300"]!=0],"winners":eligible[:2]}
    save(suite/"group_selection.json",report)
    return copy.deepcopy(eligible[:2])
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--master",type=Path,required=True); ap.add_argument("--elements",type=Path,required=True); ap.add_argument("--chai",type=Path,required=True); ap.add_argument("--distribution",type=Path,required=True); ap.add_argument("--equivalence",type=Path,required=True); ap.add_argument("--steps",type=int,default=100000); a=ap.parse_args()
    for k in ("root","master","elements","chai","distribution","equivalence"): setattr(a,k,getattr(a,k).resolve())
    scripts=Path(__file__).resolve().parent; legacy=Path(r"D:/nightingale/work/重开工程/scripts"); a.root.mkdir(parents=True,exist_ok=True); log=a.root/"tournament.log"; state_path=a.root/"state.json"
    state={"schema_version":1,"status":"running","updated_at":now(),"completed_groups":[],"winners":[]}; save(state_path,state)
    winners=[]
    for group in range(1,17):
        suite=a.root/f"group_{group:02d}"; seed=860000+group*1000
        if not (suite/"manifest.json").is_file(): run([sys.executable,legacy/"build_random_card_suite.py","--master",a.master,"--elements",a.elements,"--output-dir",suite,"--count","16","--seed-start",str(seed)],a.root,log)
        if not complete(suite): run([sys.executable,legacy/"run_card_suite.py","--suite",suite,"--chai",a.chai,"--elements",a.elements,"--distribution",a.distribution,"--equivalence",a.equivalence,"--jobs","16"],a.root,log)
        if not complete(suite): raise RuntimeError(f"第{group}组退火不完整")
        man=json.loads((suite/"manifest.json").read_text(encoding="utf-8"))
        if not (suite/"core_metrics.json").is_file():
            cmd=[sys.executable,legacy/"report_smoke_core_metrics.py","--elements",a.elements]
            for x in man["cards"]: cmd += ["--run",f"G{group}C{int(x['card']):02d}={x['output_directory']}"]
            run(cmd+["--output-json",suite/"core_metrics.json","--output-md",suite/"core_metrics.md"],a.root,log)
        if not (suite/"handfeel.json").is_file():
            cmd=[sys.executable,legacy/"report_postdraw_handfeel_extras.py","--elements",a.elements]
            for x in man["cards"]: cmd += ["--candidate",f"G{group}C{int(x['card']):02d}={Path(x['output_directory'])/'code.txt'}"]
            run(cmd+["--output-json",suite/"handfeel.json","--output-md",suite/"handfeel.md"],a.root,log)
        winners += score_group(suite,group)
        state.update(updated_at=now(),completed_groups=list(range(1,group+1)),winners=winners); save(state_path,state)
    # 32强在同一五维范围内重新计算秩和，得出终局种子排名。
    dimensions=[("three",True),("pair",False),("cross",False),("short_dup",False),("separation",True)]
    for key,high in dimensions:
        rr=ranks([x[key] for x in winners],high)
        for x,v in zip(winners,rr): x.setdefault("final_rank_components",{})[key]=v
    for x in winners: x["final_five_rank_score"]=sum(x["final_rank_components"].values())/5
    winners.sort(key=lambda x:(x["final_five_rank_score"],x["front1500"],x["full_dup"],x["micro"],x["pinky"],x["name"]))
    for i,x in enumerate(winners,1): x["rank"]=i
    save(a.root/"final_32_ranking.json",{"schema_version":1,"generated_at":now(),"ranking":winners})
    state.update(status="complete",updated_at=now(),final_ranking=winners); save(state_path,state)
if __name__=="__main__": main()
