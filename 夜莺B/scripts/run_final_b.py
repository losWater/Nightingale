# -*- coding: utf-8 -*-
"""运行 B 词位训练策略的终局长程退火。"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_suite", type=Path)
    ap.add_argument("--steps", type=int, default=1_000_000)
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()

    source = args.source_suite / "B_core10000_novel5000" / "input_config.yaml"
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    meta = config["optimization"]["metaheuristic"]
    meta["parameters"]["steps"] = args.steps
    meta["update_interval"] = 50_000
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run = WORK / "final_runs" / f"B_core10000_novel5000_{args.threads}x{args.steps}_{stamp}"
    run.mkdir(parents=True)
    config_path = run / "input_config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    manifest = {
        "strategy": "B_core10000_novel5000", "threads": args.threads, "steps_per_thread": args.steps,
        "total_steps": args.threads * args.steps, "source_suite": str(args.source_suite.resolve()),
        "unreasonable_codes": False, "started": stamp,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RUN={run}", flush=True)
    exe = ROOT / "repos" / "libchai" / "target" / "release" / "chai.exe"
    elements = WORK / "analysis_elements.yaml"
    distribution = ROOT / "tools" / "chai-win" / "assets" / "distribution.txt"
    equivalence = ROOT / "tools" / "chai-win" / "assets" / "equivalence.txt"
    subprocess.run([str(exe), "optimize", "input_config.yaml", "-e", str(elements),
                    "-k", str(distribution), "-p", str(equivalence), "-t", str(args.threads)],
                   cwd=run, check=True)
    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
