#!/usr/bin/env python3
"""列出 SUBTLEX 单字多音词的未分配频率，不执行分配。"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


TONE_RE = re.compile(r"[1-5]$")


def toneless(value: str) -> str:
    return TONE_RE.sub("", value.strip().lower()).replace("u:", "v").replace("ü", "v")


def load_candidates(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            result[row["汉字"]].append(row["拼音"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subtlex", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    candidates = load_candidates(args.candidates)
    rows: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    with args.subtlex.open("r", encoding="utf-8-sig", newline="") as handle:
        for line_no, row in enumerate(csv.DictReader(handle, delimiter="\t"), 2):
            word = row["Word"]
            source_options = {toneless(item) for item in row["Pinyin"].split("/") if item.strip()}
            if len(word) != 1 or len(source_options) <= 1:
                continue
            item = {
                "来源行号": line_no,
                "汉字": word,
                "SUBTLEX带调候选": row["Pinyin"],
                "SUBTLEX去调候选": "/".join(sorted(source_options)),
                "当前8454去调候选": "/".join(sorted(candidates.get(word, []))),
                "未分配频率": int(row["WCount"]),
            }
            if word not in candidates:
                item["排除原因"] = "字不在当前8454字音宇宙"
                excluded.append(item)
                continue
            rows.append(item)

    if any(not row["当前8454去调候选"] for row in rows):
        raise AssertionError("待分配清单含当前8454候选为空的项目")

    rows.sort(key=lambda row: (-int(row["未分配频率"]), str(row["汉字"])))
    total = sum(int(row["未分配频率"]) for row in rows)
    cumulative = 0
    for rank, row in enumerate(rows, 1):
        cumulative += int(row["未分配频率"])
        row["影响排名"] = rank
        row["累计未分配频率"] = cumulative
        row["累计占比"] = f"{cumulative / total:.6%}" if total else "0.000000%"

    output = args.output_dir / "SUBTLEX高频单字多音待分配.tsv"
    fields = ["影响排名", "汉字", "SUBTLEX带调候选", "SUBTLEX去调候选", "当前8454去调候选", "未分配频率", "累计未分配频率", "累计占比", "来源行号"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    excluded.sort(key=lambda row: (-int(row["未分配频率"]), str(row["汉字"])))
    excluded_output = args.output_dir / "SUBTLEX单字多音字集外排除.tsv"
    excluded_fields = ["汉字", "SUBTLEX带调候选", "SUBTLEX去调候选", "未分配频率", "来源行号", "排除原因"]
    with excluded_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=excluded_fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(excluded)

    top10 = sum(int(row["未分配频率"]) for row in rows[:10])
    top30 = sum(int(row["未分配频率"]) for row in rows[:30])
    lines = [
        "# SUBTLEX 高频单字多音待分配清单",
        "",
        f"- 单字多音词条：{len(rows):,}",
        f"- 尚未分配总频率：{total:,}",
        f"- 字集外排除：{len(excluded):,} 项，频率 {sum(int(row['未分配频率']) for row in excluded):,}",
        f"- 前 10 项覆盖：{top10:,}（{top10 / total:.2%}）" if total else "- 前 10 项覆盖：0",
        f"- 前 30 项覆盖：{top30:,}（{top30 / total:.2%}）" if total else "- 前 30 项覆盖：0",
        "",
        "## 前 30 项",
        "",
        "| 排名 | 字 | SUBTLEX 候选 | 当前候选 | 未分配频率 | 累计占比 |",
        "|---:|:---:|---|---|---:|---:|",
    ]
    for row in rows[:30]:
        lines.append(
            f"| {row['影响排名']} | {row['汉字']} | {row['SUBTLEX带调候选']} → {row['SUBTLEX去调候选']} | {row['当前8454去调候选']} | {int(row['未分配频率']):,} | {row['累计占比']} |"
        )
    lines.extend(["", "本清单不包含任何读音分配结论。", ""])
    (args.output_dir / "SUBTLEX高频单字多音待分配.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        f"rows={len(rows)} total={total} top10={top10} top30={top30} "
        f"excluded={len(excluded)} excluded_frequency={sum(int(row['未分配频率']) for row in excluded)}"
    )


if __name__ == "__main__":
    main()
