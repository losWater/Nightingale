#!/usr/bin/env python3
"""Run one protection experiment from several layouts in parallel."""

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


def parse_seed(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("seed must be NAME=YAML_PATH")
    name, path = raw.split("=", 1)
    if not name:
        raise argparse.ArgumentTypeError("seed name cannot be empty")
    return name, Path(path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--seed", action="append", type=parse_seed, required=True)
    parser.add_argument(
        "--template",
        type=Path,
        help="complete legal config whose mapping space is used for every seed",
    )
    parser.add_argument("--steps", type=int, default=4_200_000)
    parser.add_argument("--threads-per-seed", type=int, default=4)
    parser.add_argument("--aux-weight", type=float, default=0.0)
    parser.add_argument("--single-weight-multiplier", type=float, default=1.0)
    args = parser.parse_args()

    experiment = args.experiment.resolve()
    base_config = yaml.safe_load(
        (experiment / "input_config.yaml").read_text(encoding="utf-8")
    )
    template = (
        yaml.safe_load(args.template.resolve().read_text(encoding="utf-8"))
        if args.template
        else base_config
    )
    elements = experiment / "analysis_elements_1674_3527.yaml"
    exe = ROOT / "repos" / "libchai" / "target" / "release" / "chai.exe"
    distribution = ROOT / "tools" / "chai-win" / "assets" / "distribution.txt"
    equivalence = ROOT / "tools" / "chai-win" / "assets" / "equivalence.txt"

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    suite = experiment / f"multistart_{len(args.seed)}x{args.threads_per_seed}_{stamp}"
    suite.mkdir(parents=True)
    manifest = {
        "experiment": str(experiment),
        "steps": args.steps,
        "threads_per_seed": args.threads_per_seed,
        "auxiliary_weight": args.aux_weight,
        "seeds": [{"name": name, "path": str(path)} for name, path in args.seed],
    }
    (suite / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    processes: list[tuple[str, subprocess.Popen, object, object]] = []
    for name, seed_path in args.seed:
        seed = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
        config = deepcopy(template)
        # Optimizer solutions may omit null/unselected elements from mapping.
        # Overlay their selected keys onto a complete template instead of using
        # a solution document as a config verbatim.
        complete_mapping = config["form"]["mapping"]
        for element, key in seed["form"]["mapping"].items():
            if element in complete_mapping:
                complete_mapping[element] = key
        # The experiment owns the objective; the seed contributes only the
        # existing layout and its legal mapping space/conditions.
        config["optimization"]["objective"] = deepcopy(
            base_config["optimization"]["objective"]
        )
        config["optimization"]["objective"]["auxiliary_two_char"]["weight"] = (
            args.aux_weight
        )
        objective = config["optimization"]["objective"]
        multiplier = args.single_weight_multiplier
        for section_name in ("characters_full", "characters_short"):
            section = objective[section_name]
            if "duplication" in section:
                section["duplication"] *= multiplier
            for tier in section.get("tiers", []):
                for field in ("duplication", "duplication_squared"):
                    if field in tier:
                        tier[field] *= multiplier
                for level in tier.get("levels", []):
                    if "frequency" in level:
                        level["frequency"] *= multiplier
        meta = config["optimization"]["metaheuristic"]
        meta["parameters"]["steps"] = args.steps
        meta["update_interval"] = 10_000

        run = suite / name
        run.mkdir()
        config_path = run / "input_config.yaml"
        config_path.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10_000),
            encoding="utf-8",
        )
        stdout = (run / "stdout.log").open("w", encoding="utf-8")
        stderr = (run / "stderr.log").open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                str(exe), "optimize", "input_config.yaml",
                "-e", str(elements), "-k", str(distribution),
                "-p", str(equivalence), "-t", str(args.threads_per_seed),
            ],
            cwd=run,
            stdout=stdout,
            stderr=stderr,
        )
        processes.append((name, process, stdout, stderr))
        print(f"STARTED {name} pid={process.pid}", flush=True)

    failed = []
    for name, process, stdout, stderr in processes:
        code = process.wait()
        stdout.close()
        stderr.close()
        print(f"FINISHED {name} exit={code}", flush=True)
        if code:
            failed.append((name, code))
    if failed:
        raise SystemExit(f"failed runs: {failed}")
    print(f"ALL_DONE {suite}", flush=True)


if __name__ == "__main__":
    main()
