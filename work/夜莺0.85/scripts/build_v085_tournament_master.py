#!/usr/bin/env python3
"""从C19完整工程配置生成第二届32强统一母配置。"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import yaml
from build_v085_random_paired_suite import cross_objective, targets
from build_v085_random_grid_suite import set_three_code_weight, set_separation_weight

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--base",type=Path,required=True); ap.add_argument("--lexicon",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--mapping-solution",type=Path); ap.add_argument("--steps",type=int,default=100000); a=ap.parse_args()
    if a.output.exists(): raise ValueError("输出已存在")
    cfg=yaml.safe_load(a.base.read_text(encoding="utf-8"))
    if a.mapping_solution:
        solution=yaml.safe_load(a.mapping_solution.read_text(encoding="utf-8"))
        cfg["form"]["mapping"]=solution["form"]["mapping"]
    obj=cfg["optimization"]["objective"]
    obj.pop("words_full",None); obj["character_word_collision"]=cross_objective(0.1,targets(a.lexicon)); set_three_code_weight(cfg,-90.0); set_separation_weight(cfg,0.25)
    cfg["optimization"]["metaheuristic"]["parameters"]["steps"]=a.steps
    cfg.setdefault("info",{})["name"]="夜莺0.85第二届32强统一母配置"; cfg["info"]["version"]="v0.85-tournament-2"
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False,width=10000),encoding="utf-8")
    print(json.dumps({"status":"pass","output":str(a.output.resolve()),"steps":a.steps},ensure_ascii=False))
if __name__=="__main__": main()
