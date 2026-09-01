#!/usr/bin/env python3
"""实装黄部件末根由㐅/交(n)修正为八(a)，并维护候选顺序。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.8.5"
TABLES = RELEASE / "01_正式码表"
SPLITS = RELEASE / "03_字根与拆分"
CORE_SPLITS = ROOT / "work" / "重开工程" / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
READABLE_SPLITS = ROOT / "夜莺B" / "work" / "最终规范拆分表_人工阅读.tsv"
EXT_SPLITS = ROOT / "work" / "夜莺0.85" / "10_扩展字Chai实验" / "20260830_034806+1000" / "扩展字规范拆分_候选.tsv"
SINGLE = TABLES / "夜莺码v0.8.5单字版.txt"
COMBINED = TABLES / "夜莺0.8.5字词表.txt"
EXTENSION = TABLES / "夜莺码v0.8.5扩展字表.tsv"
RELEASE_SPLIT_TXT = SPLITS / "夜莺鹤0.8.5拆分表.txt"
RELEASE_SPLIT_HTML = SPLITS / "夜莺鹤0.8.5拆分表.html"
OLD = "龷 ＋ 一 ＋ 日 ＋ 㐅"
NEW = "龷 ＋ 一 ＋ 日 ＋ 八"


def replace_splits(path: Path) -> int:
    text = path.read_text(encoding="utf-8-sig")
    count = text.count(OLD)
    text = text.replace(OLD, NEW)
    lines = []
    normalized = 0
    for raw in text.splitlines():
        fields = raw.split("\t")
        if len(fields) >= 4 and NEW in fields[1] and fields[1].endswith("八"):
            fields[-1] = "八"
            normalized += 1
        lines.append("\t".join(fields))
    if not normalized:
        raise ValueError(f"{path} 没有找到黄部件末根记录")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return count


def read_plain(path: Path) -> list[tuple[str, str]]:
    return [tuple(line.split("\t")) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


def affected_chars(path: Path) -> set[str]:
    result = set()
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        fields = raw.split("\t")
        if len(fields) >= 2 and NEW in fields[1] and fields[1].endswith("八"):
            result.add(fields[0])
    return result


def transform(rows: list[tuple[str, str]], affected: set[str]) -> list[tuple[str, str]]:
    return [(text, code[:-1] + "a" if text in affected and len(code) == 4 and code.endswith("n") else code)
            for text, code in rows]


def extension_set() -> set[str]:
    rows = EXTENSION.read_text(encoding="utf-8-sig").splitlines()[1:]
    return {raw.split("\t", 1)[0] for raw in rows if raw}


def reorder_single(rows: list[tuple[str, str]], extensions: set[str], target_codes: set[str]) -> list[tuple[str, str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for text, code in rows:
        groups[code].append(text)
    for code in target_codes:
        groups[code] = [x for x in groups[code] if x not in extensions] + [x for x in groups[code] if x in extensions]
    return [(text, code) for code in sorted(groups, key=lambda x: (len(x), x)) for text in groups[code]]


def reorder_combined(rows: list[tuple[str, str]], single_rows: list[tuple[str, str]], extensions: set[str], target_codes: set[str]) -> list[tuple[str, str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for text, code in rows:
        groups[code].append(text)
    short_chars = {text for text, code in single_rows if len(code) < 4}
    for code in target_codes:
        items = groups[code]
        if code == "hlma":
            required = ["皇马", "蟥", "黄妈", "黄麻", "黄"]
            missing = [x for x in required if x not in items]
            if missing:
                raise ValueError(f"hlma缺少裁决候选：{missing}")
            rest = [x for x in items if x not in required and x not in extensions]
            ext = [x for x in items if x in extensions]
            groups[code] = required + rest + ext
            continue
        normal_chars = [x for x in items if len(x) == 1 and x not in extensions]
        words = [x for x in items if len(x) != 1]
        no_short = [x for x in normal_chars if x not in short_chars]
        has_short = [x for x in normal_chars if x in short_chars]
        ext = [x for x in items if x in extensions]
        groups[code] = no_short + words + has_short + ext
    return [(text, code) for code in sorted(groups, key=lambda x: (len(x), x)) for text in groups[code]]


def write_plain(path: Path, rows: list[tuple[str, str]]) -> None:
    path.write_text("".join(f"{text}\t{code}\n" for text, code in rows), encoding="utf-8")


def refresh_release_split_copies(core_chars: set[str]) -> None:
    RELEASE_SPLIT_TXT.write_bytes(CORE_SPLITS.read_bytes())
    html = RELEASE_SPLIT_HTML.read_text(encoding="utf-8").replace(OLD, NEW)
    for char in core_chars:
        pattern = rf"(<tr><td>{re.escape(char)}</td><td>[^<]*{re.escape(NEW)}</td><td>[^<]*</td><td>)[^<]*(</td></tr>)"
        html, count = re.subn(pattern, rf"\g<1>八\2", html, count=1)
        if count != 1:
            raise ValueError(f"发布拆分HTML未找到{char}行")
    RELEASE_SPLIT_HTML.write_text(html, encoding="utf-8")


def rewrite_extension_ranks(combined_rows: list[tuple[str, str]]) -> None:
    ranks = {}
    counters: dict[str, int] = defaultdict(int)
    for text, code in combined_rows:
        counters[code] += 1
        ranks[(text, code)] = counters[code]
    old_rows = []
    with EXTENSION.open("r", encoding="utf-8-sig", newline="") as stream:
        old_rows = list(csv.DictReader(stream, delimiter="\t"))
    affected = affected_chars(EXT_SPLITS)
    affected_target_codes = set()
    for row in old_rows:
        if row["字"] in affected:
            affected_target_codes.add(row["码"][:-1] + "a" if len(row["码"]) == 4 and row["码"].endswith("n") else row["码"])
    for row in old_rows:
        if row["字"] in affected and len(row["码"]) == 4 and row["码"].endswith("n"):
            row["码"] = row["码"][:-1] + "a"
        if row["码"] in affected_target_codes:
            row["候选位"] = str(ranks[(row["字"], row["码"])])
    with EXTENSION.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["字", "码", "候选位"], delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(old_rows)


def main() -> None:
    core_count = replace_splits(CORE_SPLITS)
    readable_count = replace_splits(READABLE_SPLITS)
    ext_count = replace_splits(EXT_SPLITS)
    if core_count != readable_count:
        raise ValueError(f"两份核心拆分改动数不一致：{core_count}/{readable_count}")
    affected = affected_chars(CORE_SPLITS) | affected_chars(EXT_SPLITS)
    old_single = read_plain(SINGLE)
    old_combined = read_plain(COMBINED)
    changed = {(text, code) for text, code in old_single if text in affected and len(code) == 4 and code.endswith("n")}
    target_codes = {code[:-1] + "a" for _text, code in changed}
    extensions = extension_set()
    new_single = reorder_single(transform(old_single, affected), extensions, target_codes)
    new_combined = reorder_combined(transform(old_combined, affected), new_single, extensions, target_codes)
    write_plain(SINGLE, new_single)
    write_plain(COMBINED, new_combined)
    rewrite_extension_ranks(new_combined)
    refresh_release_split_copies(affected_chars(CORE_SPLITS))
    hlma = [text for text, code in new_combined if code == "hlma"]
    if hlma[:5] != ["皇马", "蟥", "黄妈", "黄麻", "黄"]:
        raise ValueError(f"hlma裁决未落地：{hlma}")
    print(f"core_splits={core_count} extension_splits={ext_count} full_entries={len(changed)} target_codes={len(target_codes)} hlma={hlma}")


if __name__ == "__main__":
    main()
