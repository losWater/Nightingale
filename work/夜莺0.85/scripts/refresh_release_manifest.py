#!/usr/bin/env python3
"""Refresh hashes in an existing audited release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--count", action="append", default=[], help="更新统计数量：键=非负整数")
    args = parser.parse_args()
    manifest_path = args.release / "发布清单.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != args.version:
        raise SystemExit(f"version mismatch: {data.get('version')} != {args.version}")
    for key in ("schema_version", "status", "inputs", "counts"):
        if key not in data:
            raise SystemExit(f"manifest missing {key}")
    for spec in args.count:
        key, separator, raw_value = spec.partition("=")
        if not separator or not key or not raw_value.isdigit():
            raise SystemExit(f"invalid count: {spec!r}")
        data["counts"][key] = int(raw_value)
    files = sorted(path for path in args.release.iterdir() if path.is_file() and path != manifest_path)
    data["outputs"] = {path.name: sha256(path) for path in files}
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = [name for name, digest in verify["outputs"].items()
                  if sha256(args.release / name) != digest]
    if mismatches:
        raise SystemExit(f"manifest verification failed: {mismatches}")
    print(json.dumps({"status": "pass", "outputs": len(files), "mismatches": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
