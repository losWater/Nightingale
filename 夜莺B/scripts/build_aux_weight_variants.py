#!/usr/bin/env python3
"""从同一实验复制仅辅助码权重不同的可比配置。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--weights", default="5,20,50")
    args = parser.parse_args()
    config = yaml.safe_load((args.run / "input_config.yaml").read_text(encoding="utf-8"))
    elements = (args.run / "analysis_elements_1674_3527.yaml").read_text(encoding="utf-8")
    outputs = []
    for raw in args.weights.split(","):
        weight = float(raw)
        variant = args.run.parent / f"{args.run.name}_aux{raw}"
        variant.mkdir(exist_ok=True)
        current = yaml.safe_load(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
        current["optimization"]["objective"]["auxiliary_two_char"]["weight"] = weight
        (variant / "input_config.yaml").write_text(
            yaml.safe_dump(current, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8"
        )
        (variant / "analysis_elements_1674_3527.yaml").write_text(elements, encoding="utf-8")
        (variant / "manifest.json").write_text(
            json.dumps({"source": str(args.run), "auxiliary_weight": weight}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        outputs.append(str(variant))
    print("\n".join(outputs))


if __name__ == "__main__":
    main()
