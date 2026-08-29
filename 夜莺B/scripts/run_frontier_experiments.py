# -*- coding: utf-8 -*-
"""顺序运行夜莺 B 的平衡／单字／手感三条 100K 性能边界实验。"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from copy import deepcopy
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"


def profiles(base):
    balanced = deepcopy(base)

    character = deepcopy(base)
    obj = character["optimization"]["objective"]
    obj["characters_full"]["duplication"] = 300
    obj["characters_full"]["pair_equivalence"] = 5
    obj["characters_full"]["tiers"] = [
        {"top": 1500, "duplication": 160, "duplication_squared": 160},
        {"top": 3500, "duplication": 90, "duplication_squared": 50},
        {"top": 6000, "duplication": 50, "duplication_squared": 20},
    ]
    obj["characters_short"]["duplication"] = 260
    obj["characters_short"]["pair_equivalence"] = 5
    obj["characters_short"]["tiers"] = [
        {"top": 1500, "duplication": 150, "duplication_squared": 80,
         "levels": [{"length": 3, "frequency": -70}]},
        {"top": 3500, "duplication": 80, "duplication_squared": 30,
         "levels": [{"length": 3, "frequency": -30}]},
    ]
    obj["character_word_collision"]["weight"] = 0.03

    hand = deepcopy(base)
    obj = hand["optimization"]["objective"]
    obj["characters_full"]["pair_equivalence"] = 40
    obj["characters_short"]["pair_equivalence"] = 40
    obj["regularization_strength"] = 2.5

    return {"balanced": balanced, "character": character, "hand": hand}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=100000)
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()

    base = yaml.safe_load((WORK / "analysis_config_compat.yaml").read_text(encoding="utf-8"))
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    suite = WORK / "frontier_runs" / f"tiered_hard_3profiles_{args.threads}x{args.steps}_{stamp}"
    suite.mkdir(parents=True)
    elements = WORK / "analysis_elements.yaml"
    exe = ROOT / "repos" / "libchai" / "target" / "release" / "chai.exe"
    distribution = ROOT / "tools" / "chai-win" / "assets" / "distribution.txt"
    equivalence = ROOT / "tools" / "chai-win" / "assets" / "equivalence.txt"
    manifest = {
        "started": stamp, "steps": args.steps, "threads": args.threads,
        "hard_layers": ["1500x10000", "3500x2000"],
        "profiles": list(profiles(base)),
    }
    (suite / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SUITE={suite}", flush=True)

    for name, config in profiles(base).items():
        run = suite / name
        run.mkdir()
        config["optimization"]["metaheuristic"]["parameters"]["steps"] = args.steps
        config["optimization"]["metaheuristic"]["update_interval"] = 10000
        config_path = run / "input_config.yaml"
        config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
        subprocess.run([str(exe), "optimize", "input_config.yaml", "-e", str(elements),
                        "-k", str(distribution), "-p", str(equivalence), "-t", str(args.threads)],
                       cwd=run, stdout=(run / "stdout.log").open("w", encoding="utf-8"),
                       stderr=(run / "stderr.log").open("w", encoding="utf-8"), check=True)
        print(f"DONE={name}", flush=True)

    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
