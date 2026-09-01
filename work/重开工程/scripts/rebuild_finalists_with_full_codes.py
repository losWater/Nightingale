#!/usr/bin/env python3
"""从32强身份映射的原始code重建“出简仍出全”码表。"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
from pathlib import Path

from build_candidate_single_char_tables import write_one


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity", type=Path, required=True)
    ap.add_argument("--elements", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("输出目录必须不存在")
    data = json.loads(args.identity.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    if len(candidates) != 32:
        raise ValueError(f"预期32强，实际{len(candidates)}")
    args.output.mkdir(parents=True)
    flat = args.output / "普通单字码表集合"
    flat.mkdir()
    def build(pair):
        index, item = pair
        if item["final"] != f"C{index:02d}":
            raise ValueError("终局编号错位")
        code = Path(item["output_directory"]) / "code.txt"
        summary = write_one(index, int(item["seed"]), code, args.elements, args.output)
        source = Path(summary["directory"]) / "纯单字试用表.txt"
        target = flat / f"C{index:02d}_{item['source']}_seed_{item['seed']}_纯单字试用表.txt"
        shutil.copyfile(source, target)
        return {"final": f"C{index:02d}", "source": item["source"], "seed": item["seed"],
                "output_directory": item["output_directory"], "table": str(target.resolve()), **summary}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        summaries = list(pool.map(build, enumerate(candidates, 1)))
    (args.output / "身份映射_保留全码.json").write_text(
        json.dumps({"schema_version": 1, "candidates": summaries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({"status": "pass", "candidates": 32,
                      "entries": sum(x["practical"] for x in summaries),
                      "retained_full": sum(x["retained_full"] for x in summaries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
