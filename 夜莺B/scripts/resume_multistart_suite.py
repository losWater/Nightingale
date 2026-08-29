#!/usr/bin/env python3
"""Resume every seed run in a multi-start suite from its latest checkpoints."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", type=Path)
    parser.add_argument("--threads-per-seed", type=int, required=True)
    args = parser.parse_args()

    suite = args.suite.resolve()
    experiment = suite.parent
    elements = experiment / "analysis_elements_1674_3527.yaml"
    exe = ROOT / "repos" / "libchai" / "target" / "release" / "chai.exe"
    distribution = ROOT / "tools" / "chai-win" / "assets" / "distribution.txt"
    equivalence = ROOT / "tools" / "chai-win" / "assets" / "equivalence.txt"

    processes: list[tuple[str, subprocess.Popen, object, object]] = []
    for run in sorted(path for path in suite.iterdir() if path.is_dir()):
        outputs = sorted(run.glob("output-*"), key=lambda path: path.stat().st_mtime)
        if not outputs:
            raise FileNotFoundError(f"no output directory in {run}")
        resume = outputs[-1]
        checkpoints = list(resume.rglob("checkpoint-*.yaml"))
        if len(checkpoints) != args.threads_per_seed:
            raise ValueError(
                f"{run.name}: expected {args.threads_per_seed} checkpoints, got {len(checkpoints)}"
            )
        stdout = (run / "resume_stdout.log").open("a", encoding="utf-8")
        stderr = (run / "resume_stderr.log").open("a", encoding="utf-8")
        process = subprocess.Popen(
            [
                str(exe), "optimize", "input_config.yaml",
                "-e", str(elements), "-k", str(distribution),
                "-p", str(equivalence), "-t", str(args.threads_per_seed),
                "-r", str(resume),
            ],
            cwd=run,
            stdout=stdout,
            stderr=stderr,
        )
        processes.append((run.name, process, stdout, stderr))
        print(f"RESUMED {run.name} pid={process.pid} from={resume.name}", flush=True)

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
