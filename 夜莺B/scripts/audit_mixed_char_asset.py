# -*- coding: utf-8 -*-
"""构造双字频表的高频保护候选，并用既有码表审计重码。"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
DEFAULT_PUBLIC = BASE / "releases/v0.7/单字/11.合集1-前1500.txt"
PUBLIC_CONTINUATIONS = (
    BASE / "releases/v0.7/单字/12.合集2-1501-3500.txt",
    BASE / "releases/v0.7/单字/8.3501-4000.txt",
    BASE / "releases/v0.7/单字/9.4001-4500.txt",
)
DEFAULT_READINGS = BASE / "work/readings.json"
DEFAULT_CODE = (
    BASE / "夜莺B/work/final_protection_runs/"
    "hard_1500x15000_3500x5000_novel5000_20260825_074509/"
    "output-08-25+07_45_25/0/code.txt"
)
DEFAULT_OUT = BASE / "夜莺B/work/混合高频保护资产"


def lines(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def internal_order(path: Path) -> list[str]:
    readings = json.loads(path.read_text(encoding="utf-8"))
    # 多音字必须取最高读音频率；不能假定第一项就是主读音。
    return sorted(readings, key=lambda char: (-max(x[0] for x in readings[char]), char))


def code_rows(path: Path) -> list[dict[str, str]]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        result.append({"char": fields[0], "full": fields[1], "short": fields[3]})
    return result


def collision_groups(rows, chars, field):
    by_code = defaultdict(set)
    for row in rows:
        if row["char"] in chars:
            by_code[row[field]].add(row["char"])
    return {code: sorted(group) for code, group in by_code.items() if len(group) > 1}


def external_blockers(rows, chars, rank, field):
    """按当前内部字频候选顺序，找出被集合外字符占据首位的入选字。"""
    by_code = defaultdict(set)
    for row in rows:
        by_code[row[field]].add(row["char"])
    blocked = []
    for code, group in by_code.items():
        if len(group) < 2:
            continue
        winner = min(group, key=lambda char: rank.get(char, 10**9))
        for char in group & chars:
            if char != winner and winner not in chars:
                blocked.append((char, code, winner))
    return sorted(blocked, key=lambda x: rank.get(x[0], 10**9))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal-top", type=int, default=1500)
    ap.add_argument("--public-top", type=int, default=1400)
    ap.add_argument("--public", type=Path, default=DEFAULT_PUBLIC)
    ap.add_argument("--readings", type=Path, default=DEFAULT_READINGS)
    ap.add_argument("--code", type=Path, default=DEFAULT_CODE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--add", nargs="*", default=[], help="人工补选字")
    args = ap.parse_args()

    internal = internal_order(args.readings)
    public = lines(args.public)
    # 默认公开榜拆成多个连续文件保存；需要越过1500时自动续接。
    if args.public == DEFAULT_PUBLIC and args.public_top > len(public):
        for path in PUBLIC_CONTINUATIONS:
            public.extend(lines(path))
            if len(public) >= args.public_top:
                break
    if args.public_top > len(public):
        raise SystemExit(f"外部榜只有{len(public)}字，无法截取前{args.public_top}")
    irank = {char: rank for rank, char in enumerate(internal, 1)}
    prank = {char: rank for rank, char in enumerate(public, 1)}
    chosen = set(internal[: args.internal_top]) | set(public[: args.public_top])
    chosen.update(args.add)

    # 双表最佳百分位排序只用于人工浏览；是否入选仍严格按上面的并集规则。
    ordered = sorted(
        chosen,
        key=lambda char: (
            min(irank.get(char, 10**9) / args.internal_top,
                prank.get(char, 10**9) / args.public_top),
            irank.get(char, 10**9),
            prank.get(char, 10**9),
            char,
        ),
    )
    rows = code_rows(args.code)
    short = collision_groups(rows, chosen, "short")
    full = collision_groups(rows, chosen, "full")
    blockers = external_blockers(rows, chosen, irank, "short")

    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"内部前{args.internal_top}_并_外部前{args.public_top}"
    list_path = args.out / f"{stem}_{len(chosen)}字.txt"
    detail_path = args.out / f"{stem}_{len(chosen)}字_明细.tsv"
    report_path = args.out / f"{stem}_{len(chosen)}字_审计.md"
    list_path.write_text("\n".join(ordered) + "\n", encoding="utf-8")
    detail = ["字\t内部名次\t外部名次\t来源"]
    for char in ordered:
        sources = []
        if irank.get(char, 10**9) <= args.internal_top: sources.append("内部")
        if prank.get(char, 10**9) <= args.public_top: sources.append("外部")
        if char in args.add: sources.append("人工补选")
        detail.append(f"{char}\t{irank.get(char, '')}\t{prank.get(char, '')}\t{'+'.join(sources)}")
    detail_path.write_text("\n".join(detail) + "\n", encoding="utf-8")

    def group_lines(groups):
        if not groups:
            return ["- 无"]
        def key(item):
            chars = item[1]
            return min(min(irank.get(c, 10**9), prank.get(c, 10**9)) for c in chars), item[0]
        return [
            f"- `{code}`：" + "、".join(
                f"{c}(内{irank.get(c, '—')}/外{prank.get(c, '—')})" for c in chars
            ) for code, chars in sorted(groups.items(), key=key)
        ]

    internal_set = set(internal[: args.internal_top])
    public_set = set(public[: args.public_top])
    both = len(internal_set & public_set)
    report = [
        f"# {stem}：{len(chosen)}字审计", "",
        f"- 共同入选：{both}字",
        f"- 仅内部入选：{len(internal_set - public_set)}字",
        f"- 仅外部入选：{len(public_set - internal_set)}字",
        f"- 人工补选：{'、'.join(args.add) if args.add else '无'}",
        f"- 当前布局普通（简码）重码：{len(short)}组，{sum(len(x)-1 for x in short.values())}个重复项",
        f"- 按当前内部字频候选顺序，被集合外字符挡住：{len(blockers)}字",
        f"- 当前布局全码重码：{len(full)}组，{sum(len(x)-1 for x in full.values())}个重复项",
        "", "## 普通（简码）重码", "",
        *group_lines(short), "", "## 集合外候选占位", "",
        *([f"- `{code}`：{winner} → {char}" for char, code, winner in blockers] or ["- 无"]),
        "", "## 全码重码", "", *group_lines(full), "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(list_path)
    print(detail_path)
    print(report_path)
    print(f"chars={len(chosen)} short_groups={len(short)} full_groups={len(full)}")


if __name__ == "__main__":
    main()
