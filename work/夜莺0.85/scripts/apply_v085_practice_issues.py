#!/usr/bin/env python3
"""按机器参数表对指定码表增删改查；默认预演，--apply 才落盘。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


FIELDS = [
    "问题ID", "原文摘录", "状态", "目标码表", "格式", "操作",
    "原编码", "原字词", "新编码", "新字词", "目标候选位", "备注",
    "处理时间", "处理结果", "修改前SHA256", "修改后SHA256",
]
ACTIVE = "待处理"
DONE = "已修复"
SKIP = "忽略"
FORMATS = {"纯表", "搜狗", "手心"}
OPERATIONS = {"查询", "新增", "删除", "改码", "改词", "调序"}
ALLOWED_TARGETS = {
    Path("releases/v0.8.5/01_正式码表/夜莺码v0.8.5单字版.txt"),
    Path("releases/v0.8.5/01_正式码表/夜莺0.8.5字词表.txt"),
}


@dataclass
class Entry:
    code: str
    rank: int
    text: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_format(path: Path, declared: str) -> str:
    if declared:
        if declared not in FORMATS:
            raise ValueError(f"未知格式：{declared}")
        return declared
    lines = [x for x in path.read_text(encoding="utf-8-sig").splitlines() if x and not x.startswith(";")]
    sample = lines[0] if lines else ""
    if "=" in sample and "," in sample.split("=", 1)[0]:
        return "搜狗"
    if "=" in sample and "," in sample.split("=", 1)[1]:
        return "手心"
    if "\t" in sample:
        return "纯表"
    raise ValueError(f"无法自动识别格式：{path}")


def parse(path: Path, fmt: str) -> tuple[list[str], list[Entry]]:
    headers: list[str] = []
    entries: list[Entry] = []
    counts: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw or raw.startswith(";"):
            headers.append(raw)
            continue
        if fmt == "纯表":
            text, code = raw.split("\t")
            counts[code] = counts.get(code, 0) + 1
            entries.append(Entry(code, counts[code], text))
        elif fmt == "搜狗":
            left, text = raw.split("=", 1)
            code, rank = left.rsplit(",", 1)
            entries.append(Entry(code, int(rank), text))
        else:
            code, right = raw.split("=", 1)
            rank, text = right.split(",", 1)
            entries.append(Entry(code, int(rank), text))
    return headers, entries


def render(headers: list[str], entries: list[Entry], fmt: str) -> bytes:
    if fmt == "纯表":
        # 主表的全局行序承载简码层级和频率顺序，禁止按编码重新分组。
        # 调序只交换同一码的既有行槽，其他所有行保持原位。
        ordered = list(entries)
        positions_by_code: dict[str, list[int]] = defaultdict(list)
        for index, entry in enumerate(entries):
            positions_by_code[entry.code].append(index)
        for code, positions in positions_by_code.items():
            candidates = sorted((entries[i] for i in positions), key=lambda x: x.rank)
            for rank, (position, entry) in enumerate(zip(positions, candidates), 1):
                entry.rank = rank
                ordered[position] = entry
        lines = headers + [f"{entry.text}\t{entry.code}" for entry in ordered]
        return ("\n".join(lines) + "\n").encode("utf-8")
    code_order = list(OrderedDict.fromkeys(entry.code for entry in entries))
    grouped = {code: [] for code in code_order}
    for entry in entries:
        grouped.setdefault(entry.code, []).append(entry)
    data = []
    for code in code_order:
        rows = sorted(grouped[code], key=lambda x: x.rank)
        if fmt == "搜狗":
            data.extend(f"{x.code},{x.rank}={x.text}" for x in rows)
        else:
            data.extend(f"{x.code}={x.rank},{x.text}" for x in rows)
    lines = headers + data
    return ("\n".join(lines) + "\n").encode("utf-8")


def find(entries: list[Entry], code: str, text: str) -> list[Entry]:
    return [x for x in entries if (not code or x.code == code) and (not text or x.text == text)]


def occupied(entries: list[Entry], code: str, rank: int, exclude: Entry | None = None) -> Entry | None:
    return next((x for x in entries if x is not exclude and x.code == code and x.rank == rank), None)


def apply_row(entries: list[Entry], row: dict[str, str], fmt: str) -> str:
    op = row["操作"].strip()
    if op not in OPERATIONS:
        raise ValueError(f"未知操作：{op}")
    old_code, old_text = row["原编码"].strip(), row["原字词"]
    new_code = row["新编码"].strip() or old_code
    new_text = row["新字词"] or old_text
    rank = int(row["目标候选位"]) if row["目标候选位"].strip() else None
    matches = find(entries, old_code, old_text)
    if op == "查询":
        return "；".join(f"{x.code},{x.rank}={x.text}" for x in matches) or "未找到"
    if op == "新增":
        if find(entries, new_code, new_text):
            raise ValueError(f"新增项已存在：{new_text} {new_code}")
        if rank is None:
            rank = max((x.rank for x in entries if x.code == new_code), default=0) + 1
        if occupied(entries, new_code, rank):
            raise ValueError(f"新增目标位已占用：{new_code},{rank}")
        entries.append(Entry(new_code, rank, new_text))
        return f"新增 {new_code},{rank}={new_text}"
    if len(matches) != 1:
        raise ValueError(f"{op}要求唯一命中，实际{len(matches)}条：{old_code} {old_text}")
    target = matches[0]
    before = f"{target.code},{target.rank}={target.text}"
    if op == "删除":
        entries.remove(target)
        return f"删除 {before}"
    if op == "改词":
        if find(entries, target.code, new_text):
            raise ValueError(f"新字词已存在：{new_text}")
        target.text = new_text
    elif op == "改码":
        destination_rank = rank or max((x.rank for x in entries if x.code == new_code), default=0) + 1
        blocker = occupied(entries, new_code, destination_rank, target)
        if blocker:
            raise ValueError(f"改码目标位已占用：{new_code},{destination_rank}={blocker.text}")
        target.code, target.rank = new_code, destination_rank
    elif op == "调序":
        if rank is None:
            raise ValueError("调序必须填写目标候选位")
        blocker = occupied(entries, target.code, rank, target)
        old_rank = target.rank
        target.rank = rank
        if blocker:
            blocker.rank = old_rank
    return f"{before} -> {target.code},{target.rank}={target.text}"


def validate(entries: list[Entry], fmt: str) -> None:
    if any(not x.code or not x.text or x.rank < 1 for x in entries):
        raise ValueError("出现空编码、空字词或非法候选位")
    if fmt != "纯表":
        slots = [(x.code, x.rank) for x in entries]
        if len(slots) != len(set(slots)):
            raise ValueError("生成结果存在重复编码候选位")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    ledger = args.ledger.resolve()
    with ledger.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        print(json.dumps({"pending": 0, "message": "参数表暂无问题"}, ensure_ascii=False)); return
    if set(rows[0]) != set(FIELDS):
        raise ValueError("参数表字段不符合脚本版本")
    pending = [row for row in rows if row["状态"].strip() == ACTIVE]
    if not pending:
        print(json.dumps({"pending": 0, "message": "没有待处理问题"}, ensure_ascii=False)); return

    states: dict[Path, tuple[str, list[str], list[Entry], bytes]] = {}
    results: dict[int, str] = {}
    for row in pending:
        relative = Path(row["目标码表"].strip())
        normalized_relative = Path(relative.as_posix())
        if normalized_relative not in ALLOWED_TARGETS:
            raise ValueError(
                f"实战问题只能修改两张主表，拒绝派生表：{relative}"
            )
        target = (root / relative).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"目标逃逸工作区：{target}")
        if not target.is_file():
            raise FileNotFoundError(target)
        if target not in states:
            fmt = detect_format(target, row["格式"].strip())
            if fmt != "纯表":
                raise ValueError(f"两张主表必须是纯表格式：{target}")
            headers, entries = parse(target, fmt)
            states[target] = (fmt, headers, entries, target.read_bytes())
        fmt, _headers, entries, _before = states[target]
        if row["格式"].strip() and row["格式"].strip() != fmt:
            raise ValueError(f"同一文件格式声明不一致：{target}")
        results[id(row)] = apply_row(entries, row, fmt)
    rendered = {}
    for target, (fmt, headers, entries, _before) in states.items():
        validate(entries, fmt)
        rendered[target] = render(headers, entries, fmt)

    preview = {str(path.relative_to(root)): {"before": sha256_bytes(states[path][3]), "after": sha256_bytes(data)}
               for path, data in rendered.items()}
    if not args.apply:
        print(json.dumps({"mode": "dry-run", "pending": len(pending), "files": preview,
                          "results": list(results.values())}, ensure_ascii=False, indent=2)); return

    now = datetime.now(ZoneInfo("Australia/Sydney"))
    backup = args.backup_root.resolve() / now.strftime("%Y%m%d_%H%M%S%z")
    backup.mkdir(parents=True, exist_ok=False)
    for target, (_fmt, _headers, _entries, before) in states.items():
        relative = target.relative_to(root)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(before)
    for target, data in rendered.items():
        temporary = target.with_name(target.name + ".practice.tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)
    for row in pending:
        target = (root / Path(row["目标码表"].strip())).resolve()
        row["状态"] = DONE
        row["处理时间"] = now.isoformat(timespec="seconds")
        row["处理结果"] = results[id(row)]
        row["修改前SHA256"] = preview[str(target.relative_to(root))]["before"]
        row["修改后SHA256"] = preview[str(target.relative_to(root))]["after"]
    with ledger.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    shutil.copy2(ledger, backup / ledger.name)
    print(json.dumps({"mode": "applied", "fixed": len(pending), "backup": str(backup), "files": preview}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
