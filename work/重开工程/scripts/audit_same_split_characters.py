# -*- coding: utf-8 -*-
"""Audit structural same-split candidates and same head/tail skeleton groups."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT / "02_规范拆分"
DEFAULT_CURRENT = OUT_DIR / "最终规范拆分表_待核验.tsv"
DEFAULT_JSON = OUT_DIR / "同拆字检查.json"
DEFAULT_EXACT_TSV = OUT_DIR / "同拆字检查_结构候选组.tsv"
DEFAULT_SKELETON_TSV = OUT_DIR / "同拆字检查_同首末骨架组.tsv"
DEFAULT_MD = OUT_DIR / "同拆字检查.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    required = {"汉字", "最终规范拆分", "编码首根", "编码末根"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"invalid canonical split table columns: {path}")
    chars = [row["汉字"] for row in rows]
    if len(rows) != 8105 or len(set(chars)) != 8105:
        raise ValueError(f"expected 8105 unique glyphs, got rows={len(rows)} unique={len(set(chars))}")
    for index, row in enumerate(rows, start=2):
        if any(not row[name].strip() for name in required):
            raise ValueError(f"empty required field at {path}:{index}")
    return rows


def exact_groups(rows: list[dict[str, str]]) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[row["最终规范拆分"]].append(row["汉字"])
    return {
        split: tuple(sorted(chars))
        for split, chars in groups.items()
        if len(chars) > 1
    }


def skeleton_groups(rows: list[dict[str, str]]) -> dict[tuple[str, str], tuple[str, ...]]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in rows:
        groups[(row["编码首根"], row["编码末根"])].append(row["汉字"])
    return {
        pair: tuple(sorted(chars))
        for pair, chars in groups.items()
        if len(chars) > 1
    }


def exact_delta(
    old: dict[str, tuple[str, ...]], new: dict[str, tuple[str, ...]]
) -> dict[str, list[dict[str, object]]]:
    added = []
    removed = []
    changed = []
    for split in sorted(set(old) | set(new)):
        before = old.get(split)
        after = new.get(split)
        if before is None:
            added.append({"拆分": split, "成员": list(after or ())})
        elif after is None:
            removed.append({"拆分": split, "成员": list(before)})
        elif before != after:
            changed.append({"拆分": split, "旧成员": list(before), "新成员": list(after)})
    return {"新增": added, "消失": removed, "成员变化": changed}


def write_tsv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def audit(
    current: Path = DEFAULT_CURRENT,
    previous: Path | None = None,
    json_path: Path = DEFAULT_JSON,
    exact_tsv: Path = DEFAULT_EXACT_TSV,
    skeleton_tsv: Path = DEFAULT_SKELETON_TSV,
    md_path: Path = DEFAULT_MD,
) -> dict[str, object]:
    now = datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes")
    current_rows = read_rows(current)
    exact = exact_groups(current_rows)
    skeleton = skeleton_groups(current_rows)
    old_exact = exact_groups(read_rows(previous)) if previous else None
    delta = exact_delta(old_exact, exact) if old_exact is not None else None

    exact_records = [
        {"拆分": split, "成员数": len(chars), "成员": list(chars)}
        for split, chars in sorted(exact.items())
    ]
    skeleton_records = [
        {"首根": pair[0], "末根": pair[1], "成员数": len(chars), "成员": list(chars)}
        for pair, chars in sorted(skeleton.items())
    ]
    payload: dict[str, object] = {
        "generated_at": now,
        "scope": "pure_structural_8105",
        "current": {"path": str(current), "sha256": sha256(current), "glyphs": 8105},
        "previous": ({"path": str(previous), "sha256": sha256(previous)} if previous else None),
        "structural_same_split_candidates": {"group_count": len(exact_records), "groups": exact_records},
        "same_head_tail_skeleton": {"group_count": len(skeleton_records), "groups": skeleton_records},
        "structural_candidate_delta": delta,
        "confirmed_same_split": None,
        "not_checked": "真正同拆字及真实音形重码（当前8105表没有编码音节）",
    }

    write_tsv(
        exact_tsv,
        ["完整规范拆分", "候选成员数", "结构候选成员"],
        [[x["拆分"], x["成员数"], " ".join(x["成员"])] for x in exact_records],
    )
    write_tsv(
        skeleton_tsv,
        ["编码首根", "编码末根", "成员数", "成员"],
        [[x["首根"], x["末根"], x["成员数"], " ".join(x["成员"])] for x in skeleton_records],
    )
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    delta_text = "未提供上一版"
    if delta is not None:
        delta_text = "新增{}，消失{}，成员变化{}".format(
            len(delta["新增"]), len(delta["消失"]), len(delta["成员变化"])
        )
    exact_lines = "\n".join(
        f"- `{x['拆分']}`：{'、'.join(x['成员'])}" for x in exact_records
    ) or "- 无"
    largest = sorted(skeleton_records, key=lambda x: (-int(x["成员数"]), str(x["首根"]), str(x["末根"])))[:20]
    skeleton_lines = "\n".join(
        f"- `{x['首根']}／{x['末根']}`：{x['成员数']}字（{'、'.join(x['成员'][:30])}"
        + ("……" if len(x["成员"]) > 30 else "") + "）"
        for x in largest
    ) or "- 无"
    md_path.write_text(
        f"""# 同拆字检查

- 生成时间：{now}
- 当前表：`{current}`
- 当前表SHA-256：`{sha256(current)}`
- 结构同拆候选组：{len(exact_records)}组
- 真正同拆字组：未知（当前8105表没有编码音节）
- 同首末骨架组：{len(skeleton_records)}组
- 相比上一版：{delta_text}
- 尚未检查：真正同拆字及真实音形重码

## 全部结构同拆候选组

{exact_lines}

## 最大的20个同首末骨架组

完整清单见`同拆字检查_同首末骨架组.tsv`。

{skeleton_lines}
""",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="检查8105规范拆分表中的结构同拆候选和同首末骨架")
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    payload = audit(current=args.current, previous=args.previous)
    delta = payload["structural_candidate_delta"]
    print(json.dumps({
        "结构同拆候选组": payload["structural_same_split_candidates"]["group_count"],
        "同首末骨架组": payload["same_head_tail_skeleton"]["group_count"],
        "变化": None if delta is None else {name: len(items) for name, items in delta.items()},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
