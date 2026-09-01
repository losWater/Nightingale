#!/usr/bin/env python3
"""按 Chai 封闭集合频率生成低影响多音字尾部分配预览。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def split_counts(value: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for item in value.split(";"):
        if item:
            reading, frequency = item.rsplit(":", 1)
            result[reading] += int(frequency)
    return result


def largest_remainder(total: int, weights: Counter[str]) -> dict[str, int]:
    weight_sum = sum(weights.values())
    exact = {key: Decimal(total) * Decimal(value) / Decimal(weight_sum) for key, value in weights.items()}
    result = {key: int(value) for key, value in exact.items()}
    remainder = total - sum(result.values())
    order = sorted(exact, key=lambda key: (-(exact[key] - result[key]), key))
    for key in order[:remainder]:
        result[key] += 1
    if sum(result.values()) != total:
        raise AssertionError("最大余数法分配不守恒")
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--manual-decisions", type=Path, required=True)
    parser.add_argument("--special-weights", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manually_decided = {row["汉字"] for row in read_tsv(args.manual_decisions)}
    special_data = json.loads(args.special_weights.read_text(encoding="utf-8"))
    special_chars = {rule["character"] for rule in special_data["rules"]}
    excluded = manually_decided | special_chars

    preview: list[dict[str, str | int]] = []
    anomalies: list[dict[str, str | int]] = []
    pending_rows = [row for row in read_tsv(args.audit) if row["状态"] == "继续待复核"]
    for row in pending_rows:
        char = row["汉字"]
        if char in excluded:
            continue
        current = {item for item in row["当前8454集合"].split("/") if item}
        chai_all = split_counts(row["Chai频率"])
        positive = Counter({reading: chai_all[reading] for reading in current if chai_all[reading] > 0})
        total = int(row["SUBTLEX单字总频"])
        maximum = max(positive.values(), default=0)
        leaders = sorted(reading for reading, frequency in positive.items() if frequency == maximum)

        if not positive:
            reason = "封闭集合内Chai无正频"
        elif len(leaders) != 1:
            reason = "封闭集合内Chai最高正频并列:" + "/".join(leaders)
        else:
            allocation = largest_remainder(total, positive)
            basis = "唯一正频全量归入" if len(positive) == 1 else "按Chai封闭集合正频比例分配"
            preview.append({
                "影响排名": int(row["影响排名"]),
                "汉字": char,
                "待分配频率": total,
                "当前封闭读音集合": "/".join(sorted(current)),
                "Chai封闭集合正频": ";".join(f"{key}:{positive[key]}" for key in sorted(positive)),
                "分配结果": ";".join(f"{key}:{allocation[key]}" for key in sorted(allocation)),
                "分配依据": basis,
                "守恒": "是" if sum(allocation.values()) == total else "否",
            })
            continue

        anomalies.append({
            "影响排名": int(row["影响排名"]),
            "汉字": char,
            "待分配频率": total,
            "当前封闭读音集合": "/".join(sorted(current)),
            "Chai全部频率": row["Chai频率"],
            "异常原因": reason,
        })

    preview.sort(key=lambda row: int(row["影响排名"]))
    anomalies.sort(key=lambda row: int(row["影响排名"]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    preview_path = args.output_dir / "低影响多音字尾部分配预览.tsv"
    anomaly_path = args.output_dir / "低影响多音字尾部分配异常.tsv"
    with preview_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["影响排名", "汉字", "待分配频率", "当前封闭读音集合", "Chai封闭集合正频", "分配结果", "分配依据", "守恒"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(preview)
    with anomaly_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["影响排名", "汉字", "待分配频率", "当前封闭读音集合", "Chai全部频率", "异常原因"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(anomalies)

    report = {
        "original_pending_items": len(pending_rows),
        "excluded_manual_or_special_items": len([row for row in pending_rows if row["汉字"] in excluded]),
        "preview_allocated_items": len(preview),
        "preview_allocated_frequency": sum(int(row["待分配频率"]) for row in preview),
        "anomaly_items": len(anomalies),
        "anomaly_frequency": sum(int(row["待分配频率"]) for row in anomalies),
        "all_preview_allocations_conserved": all(row["守恒"] == "是" for row in preview),
        "preview_sha256": sha256(preview_path),
        "anomaly_sha256": sha256(anomaly_path),
    }
    (args.output_dir / "低影响多音字尾部分配预览报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 低影响多音字尾部分配预览报告", "",
        f"- 原待复核：{report['original_pending_items']} 项",
        f"- 排除人工／特殊裁决：{report['excluded_manual_or_special_items']} 项",
        f"- 可按规则预览分配：{report['preview_allocated_items']} 项，频率 {report['preview_allocated_frequency']:,}",
        f"- 异常：{report['anomaly_items']} 项，频率 {report['anomaly_frequency']:,}",
        f"- 全部分配守恒：{'是' if report['all_preview_allocations_conserved'] else '否'}", "",
        "本轮只生成预览，没有覆盖任何阶段频率表或退火输入。", ""
    ]
    (args.output_dir / "低影响多音字尾部分配预览报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
