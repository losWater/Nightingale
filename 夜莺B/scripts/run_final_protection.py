# -*- coding: utf-8 -*-
"""以不可变输入副本和manifest运行历史终局保护实验。"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_run(source_run: Path, output_run: Path, *, steps: int, threads: int,
                elements: Path, executable: Path, distribution: Path,
                equivalence: Path) -> tuple[list[str], dict]:
    source_run = source_run.resolve()
    output_run = output_run.resolve()
    source_config = source_run / "input_config.yaml"
    if steps < 1 or threads < 1:
        raise ValueError("steps和threads必须是正整数")
    for label, path in (("源配置", source_config), ("元素资产", elements),
                        ("引擎", executable), ("键位资产", distribution),
                        ("当量资产", equivalence)):
        if not path.resolve().is_file():
            raise FileNotFoundError(f"{label}不存在：{path.resolve()}")
    if output_run.exists():
        raise FileExistsError(f"输出运行目录已存在，拒绝覆盖：{output_run}")

    config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    meta = config["optimization"]["metaheuristic"]
    meta["parameters"]["steps"] = steps
    meta["update_interval"] = 10_000

    output_run.mkdir(parents=True, exist_ok=False)
    run_config = output_run / "input_config.yaml"
    run_config.write_text(yaml.safe_dump(
        config, allow_unicode=True, sort_keys=False, width=10_000
    ), encoding="utf-8")
    command = [str(executable.resolve()), "optimize", "input_config.yaml",
               "-e", str(elements.resolve()), "-k", str(distribution.resolve()),
               "-p", str(equivalence.resolve()), "-t", str(threads)]
    manifest = {
        "schema_version": 1,
        "status": "prepared",
        "created_utc": utc_now(),
        "source_run": str(source_run),
        "output_run": str(output_run),
        "parameters": {"steps": steps, "threads": threads, "update_interval": 10_000},
        "files": {
            "source_config": {"path": str(source_config), "sha256": sha256(source_config)},
            "run_config": {"path": str(run_config), "sha256": sha256(run_config)},
            "elements": {"path": str(elements.resolve()), "sha256": sha256(elements.resolve())},
            "executable": {"path": str(executable.resolve()), "sha256": sha256(executable.resolve())},
            "distribution": {"path": str(distribution.resolve()), "sha256": sha256(distribution.resolve())},
            "equivalence": {"path": str(equivalence.resolve()), "sha256": sha256(equivalence.resolve())},
        },
        "command": command,
    }
    write_manifest(output_run / "manifest.json", manifest)
    return command, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run", type=Path)
    parser.add_argument("--output-run", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=100_000)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--elements", type=Path)
    args = parser.parse_args()

    elements = args.elements.resolve() if args.elements else WORK / "analysis_elements.yaml"
    executable = ROOT / "repos/libchai/target/release/chai.exe"
    distribution = ROOT / "tools/chai-win/assets/distribution.txt"
    equivalence = ROOT / "tools/chai-win/assets/equivalence.txt"
    command, manifest = prepare_run(
        args.source_run, args.output_run, steps=args.steps, threads=args.threads,
        elements=elements, executable=executable, distribution=distribution,
        equivalence=equivalence,
    )
    output_run = args.output_run.resolve()
    manifest_path = output_run / "manifest.json"
    manifest["status"] = "running"
    manifest["started_utc"] = utc_now()
    write_manifest(manifest_path, manifest)
    try:
        with (output_run / "stdout.log").open("x", encoding="utf-8") as stdout, \
             (output_run / "stderr.log").open("x", encoding="utf-8") as stderr:
            result = subprocess.run(command, cwd=output_run, stdout=stdout, stderr=stderr)
        manifest["returncode"] = result.returncode
        manifest["status"] = "complete" if result.returncode == 0 else "failed"
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, command)
    except BaseException:
        manifest["status"] = "failed"
        raise
    finally:
        manifest["finished_utc"] = utc_now()
        write_manifest(manifest_path, manifest)
    print(f"RUN={output_run}")


if __name__ == "__main__":
    main()
