# -*- coding: utf-8 -*-
"""顺序运行词位训练 A/B 正式实验，避免两组同时抢占全部 CPU。"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", type=Path)
    ap.add_argument("--steps", type=int, default=100000)
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()
    suite = args.suite.resolve()
    exe = ROOT / "repos" / "libchai" / "target" / "release" / "chai.exe"
    elements = WORK / "analysis_elements.yaml"
    distribution = ROOT / "tools" / "chai-win" / "assets" / "distribution.txt"
    equivalence = ROOT / "tools" / "chai-win" / "assets" / "equivalence.txt"
    manifest = {"steps": args.steps, "threads": args.threads, "variants": []}
    print(f"SUITE={suite}", flush=True)
    for variant in ("A_frequency15000", "B_core10000_novel5000"):
        source = yaml.safe_load((suite / variant / "input_config.yaml").read_text(encoding="utf-8"))
        source["optimization"]["metaheuristic"]["parameters"]["steps"] = args.steps
        source["optimization"]["metaheuristic"]["update_interval"] = 10000
        run = suite / variant / f"formal_{args.threads}x{args.steps}"
        run.mkdir(exist_ok=True)
        config = run / "input_config.yaml"
        config.write_text(yaml.safe_dump(source, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
        with (run / "stdout.log").open("w", encoding="utf-8") as stdout, \
             (run / "stderr.log").open("w", encoding="utf-8") as stderr:
            subprocess.run([str(exe), "optimize", "input_config.yaml", "-e", str(elements),
                            "-k", str(distribution), "-p", str(equivalence), "-t", str(args.threads)],
                           cwd=run, stdout=stdout, stderr=stderr, check=True)
        outputs = sorted(run.glob("output-*"))
        manifest["variants"].append({"name": variant, "run": str(run),
                                     "output": str(outputs[-1]) if outputs else ""})
        print(f"DONE={variant}", flush=True)
    (suite / "formal_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
