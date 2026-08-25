# -*- coding: utf-8 -*-
"""逐项核对最终 code.txt 与生成时的一／二／三码资产。"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", type=Path)
    ap.add_argument("--elements", type=Path, default=BASE / "work/analysis_elements.yaml")
    ap.add_argument("--config", type=Path, default=BASE / "work/analysis_config.yaml")
    ap.add_argument("--out", type=Path, default=BASE / "work/v07_unlocked_audit/最终简码逐项核对.md")
    args = ap.parse_args()

    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    mapping = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    expected = {}
    for item in elements:
        sound = "".join(str(mapping[str(x["element"])]) for x in item["元素序列"][:2])
        # 未显式指定的字由编码器按三码位竞争决定，不能预设为三码。
        if "简码长度" in item:
            expected[(str(item["词"]), sound)] = int(item["简码长度"])

    actual = {}
    for line in args.code.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        actual[(fields[0], fields[1][:2])] = (len(fields[3]), fields[1], fields[3])

    missing = sorted(set(expected) - set(actual))
    mismatch = []
    for key in sorted(set(expected) & set(actual)):
        got, full, short = actual[key]
        if got != expected[key]:
            mismatch.append((key[0], key[1], expected[key], got, full, short))

    counts = Counter(length for length, _, _ in actual.values())
    report = [
        "# 最终简码逐项核对", "",
        f"- 显式一／二简资产：{len(expected)} 条字音",
        f"- 最终码表：{len(actual)} 条字音",
        f"- 实际长度分布：一简 {counts[1]}、二简 {counts[2]}、三码 {counts[3]}、全码 {counts[4]}",
        f"- 缺失：{len(missing)}",
        f"- 简码长度不符：{len(mismatch)}", "",
        "## 不符明细", "",
    ]
    report += ([f"- {char} `{sound}`：应{want}码，实{got}码（`{full}` → `{short}`）"
                for char, sound, want, got, full, short in mismatch] or ["- 无"])
    if missing:
        report += ["", "## 缺失", "", *[f"- {c} `{s}`" for c, s in missing]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:8]))
    print(args.out)


if __name__ == "__main__":
    main()
