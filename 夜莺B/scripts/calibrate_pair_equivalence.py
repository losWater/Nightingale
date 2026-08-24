# -*- coding: utf-8 -*-
"""随机合法布局采样：比较重码指标与组合当量的自然波动。"""
import argparse, csv, random, re, subprocess
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"
KEYS = "abcdefghijklmnopqrstuvwxyz"
FIXED = {"1": "h", "2": "u", "3": "p", "4": "d", "5": "v"}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("-n",type=int,default=80);ap.add_argument("--seed",type=int,default=20260824)
    args=ap.parse_args(); rng=random.Random(args.seed)
    cfg=yaml.safe_load((WORK/"analysis_config_compat.yaml").read_text(encoding="utf-8"))
    mapping=cfg["form"]["mapping"]
    movable=[k for k,v in mapping.items() if isinstance(v,str) and not k.startswith(("szm-","mzm-")) and k not in FIXED]
    testdir=WORK/"pair_calibration";testdir.mkdir(exist_ok=True)
    exe=ROOT/"tools/chai-win/chai.exe"; elements=WORK/"analysis_elements.yaml"
    dist=ROOT/"tools/chai-win/assets/distribution.txt"; equiv=ROOT/"tools/chai-win/assets/equivalence.txt"
    rows=[]
    pattern=re.compile(r"选重率：([\d.]+)%；组合当量：([\d.]+)")
    for i in range(args.n):
        for k in movable: mapping[k]=rng.choice(KEYS)
        mapping.update(FIXED)
        cp=testdir/"sample.yaml";cp.write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False,width=10000),encoding="utf-8")
        run=subprocess.run([str(exe),"encode",str(cp),"-e",str(elements),"-k",str(dist),"-p",str(equiv)],cwd=testdir,capture_output=True,text=True,encoding="utf-8")
        if run.returncode: raise RuntimeError(run.stdout+run.stderr)
        hits=pattern.findall(run.stdout)
        if len(hits)<2: raise RuntimeError(run.stdout)
        rows.append({"sample":i+1,"full_dup_pct":float(hits[0][0]),"full_pair":float(hits[0][1]),
                     "short_dup_pct":float(hits[1][0]),"short_pair":float(hits[1][1])})
    out=WORK/"pair_equivalence_calibration.tsv"
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter="\t");wr.writeheader();wr.writerows(rows)
    import statistics as st
    for key in ("full_dup_pct","short_dup_pct","full_pair","short_pair"):
        xs=[r[key] for r in rows];print(f"{key}: mean={st.mean(xs):.6f} sd={st.stdev(xs):.6f} min={min(xs):.6f} max={max(xs):.6f}")
    print(f"movable={len(movable)} samples={len(rows)} -> {out}")

if __name__=="__main__":main()
