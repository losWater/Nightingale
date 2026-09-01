#!/usr/bin/env python3
"""并行运行设计0048卡池；每张卡独立工作目录和日志。"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path


def run_card(card: dict, chai: Path, elements: Path, distribution: Path, equivalence: Path) -> dict:
    directory = Path(card["directory"])
    command = [str(chai), "optimize", "config.yaml", "-e", str(elements),
               "-k", str(distribution), "-p", str(equivalence), "-t", "1"]
    result = subprocess.run(command, cwd=directory, text=True, encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (directory / "launcher_stdout.txt").write_text(result.stdout, encoding="utf-8")
    (directory / "launcher_stderr.txt").write_text(result.stderr, encoding="utf-8")
    outputs = sorted(p for p in directory.iterdir() if p.is_dir() and p.name.startswith("output-"))
    valid = []
    for output in outputs:
        # libchai单线程直接写在output目录，多线程才写output/线程号。
        if (output / "metric.json").is_file() and (output / "code.txt").is_file():
            valid.append(output)
        elif (output / "0" / "metric.json").is_file() and (output / "0" / "code.txt").is_file():
            valid.append(output / "0")
    return {**card, "returncode": result.returncode,
            "status": "complete" if result.returncode == 0 and len(valid) == 1 else "failed",
            "output_directory": str(valid[0].resolve()) if len(valid) == 1 else None,
            "command": command}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--chai", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--distribution", type=Path, required=True)
    parser.add_argument("--equivalence", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--recover-existing", action="store_true")
    args = parser.parse_args()
    manifest_path = args.suite / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.recover_existing:
        if manifest["status"] not in {"failed", "complete"}:
            raise ValueError("恢复模式只接受failed或complete套件")
        recovered = []
        for card in manifest["cards"]:
            directory = Path(card["directory"])
            outputs = sorted(p for p in directory.iterdir() if p.is_dir() and p.name.startswith("output-"))
            valid = []
            for output in outputs:
                if (output / "metric.json").is_file() and (output / "code.txt").is_file(): valid.append(output)
                elif (output / "0" / "metric.json").is_file() and (output / "0" / "code.txt").is_file(): valid.append(output / "0")
            if card.get("returncode") != 0 or len(valid) != 1:
                raise ValueError(f"card {card['card']}无法无损恢复：return={card.get('returncode')} valid={len(valid)}")
            recovered.append({**card, "status": "complete", "output_directory": str(valid[0].resolve())})
        manifest["cards"] = recovered
        manifest["status"] = "complete"
        manifest["recovered_from_false_failure"] = True
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "complete", "recovered": len(recovered)}, ensure_ascii=False))
        return
    if manifest["status"] != "built_pending_validation_and_run":
        raise ValueError(f"套件状态不允许运行：{manifest['status']}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_card, card, args.chai.resolve(), args.elements.resolve(),
                               args.distribution.resolve(), args.equivalence.resolve())
                   for card in manifest["cards"]]
        cards = [future.result() for future in futures]
    manifest["cards"] = sorted(cards, key=lambda x: x["card"])
    manifest["status"] = "complete" if all(x["status"] == "complete" for x in cards) else "failed"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "complete": sum(x["status"] == "complete" for x in cards),
                      "total": len(cards)}, ensure_ascii=False))
    if manifest["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
