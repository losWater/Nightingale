#!/usr/bin/env python3
"""封存完整卡池结果哈希，不修改任何Chai结果。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.suite / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or len(manifest.get("cards", [])) != 16:
        raise ValueError("套件未完整完成或卡数不为16")
    lines = ["# 正式抽卡结果封存", "", "| 卡 | 种子 | config | code | metric |", "|---:|---:|---|---|---|"]
    for card in manifest["cards"]:
        if card.get("returncode") != 0 or card.get("status") != "complete":
            raise ValueError(f"card {card['card']}状态异常")
        directory = Path(card["output_directory"])
        files = {name: directory / name for name in ("config.yaml", "code.txt", "metric.json")}
        if not all(path.is_file() for path in files.values()):
            raise ValueError(f"card {card['card']}结果文件不完整")
        hashes = {name: sha256(path) for name, path in files.items()}
        card["result_sha256"] = hashes
        lines.append(f"| {card['card']:02d} | {card['seed']} | `{hashes['config.yaml']}` | `{hashes['code.txt']}` | `{hashes['metric.json']}` |")
    manifest["results_finalized"] = True
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.suite / "finalization_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "cards": len(manifest["cards"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
