#!/usr/bin/env python3
"""Overlay a compact optimizer solution onto a complete legal config."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    parser.add_argument("solution", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(args.template.read_text(encoding="utf-8"))
    solution = yaml.safe_load(args.solution.read_text(encoding="utf-8"))
    mapping = config["form"]["mapping"]
    for element, value in solution["form"]["mapping"].items():
        if element in mapping:
            mapping[element] = value
    # Preserve the objective used by the solution while retaining the full
    # mapping and decision space from the template.
    config["optimization"]["objective"] = solution["optimization"]["objective"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10_000),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
