#!/usr/bin/env python3
"""对冻结普通单字表应用显式码位补丁，并派生搜狗表。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_base(path: Path) -> dict[str, list[str]]:
    slots: dict[str, list[str]] = defaultdict(list)
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 2 or len(fields[0]) != 1 or not fields[1]:
            raise ValueError(f"基线第{line_no}行异常")
        char, code = fields
        if char in slots[code]:
            raise ValueError(f"基线同码同字重复：{code} {char}")
        slots[code].append(char)
    return dict(slots)


def read_operations(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"操作编号", "裁决来源", "操作", "码", "最终候选", "说明"}
    if not rows or set(rows[0]) != required:
        raise ValueError("操作表列不符合设计0070")
    ids: set[str] = set(); codes: set[str] = set()
    for row in rows:
        if row["操作编号"] in ids or row["码"] in codes:
            raise ValueError("操作编号或目标码位重复")
        ids.add(row["操作编号"]); codes.add(row["码"])
        if row["操作"] != "SET_SLOT":
            raise ValueError(f"暂不支持操作：{row['操作']}")
        candidates = row["最终候选"].split("/")
        if any(len(char) != 1 for char in candidates) or len(candidates) != len(set(candidates)):
            raise ValueError(f"{row['操作编号']}候选异常")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--operations", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--release-name",
        help="正式发布文件的基础名称；省略时生成隔离验证用的‘假码表’文件名",
    )
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("输出目录必须不存在")
    before = read_base(args.base)
    after = {code: chars[:] for code, chars in before.items()}
    operations = read_operations(args.operations)
    changes = []
    target_codes = {row["码"] for row in operations}
    for row in operations:
        code = row["码"]
        old = after.get(code, [])[:]
        new = row["最终候选"].split("/")
        after[code] = new
        changes.append({"operation": row["操作编号"], "source": row["裁决来源"],
                        "code": code, "before": old, "after": new, "note": row["说明"]})

    for code, chars in before.items():
        if code not in target_codes and after.get(code) != chars:
            raise ValueError(f"未声明码位发生变化：{code}")
    for row in operations:
        if after[row["码"]] != row["最终候选"].split("/"):
            raise ValueError(f"目标码位未正确写入：{row['码']}")

    args.output.mkdir(parents=True)
    base_name = args.release_name or "假码表_应用当前裁决"
    plain = args.output / f"{base_name}.txt"
    sogou = args.output / f"{base_name}_搜狗.txt"
    codes = sorted(after, key=lambda code: (len(code), code))
    plain_lines = [f"{char}\t{code}" for code in codes for char in after[code]]
    plain.write_text("\n".join(plain_lines) + "\n", encoding="utf-8")
    if args.release_name:
        headers = [f"; {args.release_name}",
                   "; 冻结C19基线＋已登记人工码位裁决；无词、无快符"]
    else:
        headers = ["; 夜莺0.8 C19 人工裁决隔离测试表",
                   "; 冻结基线＋显式码位补丁；无词、无快符；仅供验证"]
    sogou_lines = [*headers, ""]
    sogou_lines += [f"{code},{position}={char}" for code in codes
                    for position, char in enumerate(after[code], 1)]
    sogou.write_text("\n".join(sogou_lines) + "\n", encoding="utf-8")

    if read_base(plain) != after:
        raise ValueError("普通表反读不一致")
    parsed_sogou: dict[str, list[str]] = defaultdict(list)
    for line in sogou.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith(";"):
            continue
        left, char = line.split("=", 1); code, position = left.rsplit(",", 1)
        if int(position) != len(parsed_sogou[code]) + 1:
            raise ValueError(f"搜狗候选序号不连续：{code}")
        parsed_sogou[code].append(char)
    if dict(parsed_sogou) != after:
        raise ValueError("搜狗表反读不一致")

    report = {"schema_version": 1, "status": "pass",
              "inputs": {str(args.base.resolve()): sha256(args.base),
                         str(args.operations.resolve()): sha256(args.operations)},
              "base_slots": len(before), "base_entries": sum(map(len, before.values())),
              "result_slots": len(after), "result_entries": sum(map(len, after.values())),
              "target_slots": len(target_codes), "changes": changes,
              "outputs": {plain.name: sha256(plain), sogou.name: sha256(sogou)}}
    (args.output / "补丁验证报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
