# -*- coding: utf-8 -*-
"""从正式抽卡的真实 code.txt 生成隔离的纯单字试用码表。"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Row:
    index: int
    word: str
    pinyin: str
    frequency: int
    full: str
    full_rank: int
    actual: str
    actual_rank: int


@dataclass(frozen=True)
class Entry:
    row: Row
    code: str
    rank: int
    source: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(code_path: Path, elements_path: Path) -> list[Row]:
    elements = yaml.safe_load(elements_path.read_text(encoding="utf-8"))
    code_lines = code_path.read_text(encoding="utf-8").splitlines()
    if len(elements) != 8454 or len(code_lines) != 8454:
        raise ValueError(f"预期8454行，实际 elements={len(elements)}, code={len(code_lines)}")
    rows: list[Row] = []
    for index, (item, line) in enumerate(zip(elements, code_lines), 1):
        fields = line.split("\t")
        if len(fields) != 5:
            raise ValueError(f"code.txt第{index}行不是5列")
        word, full, full_rank, actual, actual_rank = fields
        if word != str(item["词"]):
            raise ValueError(f"第{index}行错位：elements={item['词']} code={word}")
        if len(full) != 4 or len(actual) not in (1, 2, 3, 4):
            raise ValueError(f"第{index}行码长异常：{word} {full} {actual}")
        rows.append(Row(index, word, str(item["拼音"]), int(item["频率"]), full,
                        int(full_rank), actual, int(actual_rank)))
    if len({row.word for row in rows}) != 8105:
        raise ValueError("不同汉字数不是8105")
    return rows


def practical_rows(rows: list[Row]) -> list[Entry]:
    """物化实际码，并按“出简让全”把保留全码追加到原候选之后。"""
    grouped: dict[str, list[Entry]] = defaultdict(list)
    for row in rows:
        # actual_rank正是“出简让全”后的实际候选序号：有简码者退出全码首选竞争。
        grouped[row.actual].append(Entry(row, row.actual, row.actual_rank, "实际码"))
        if row.full != row.actual:
            grouped[row.full].append(Entry(row, row.full, row.full_rank, "保留全码"))
    result: list[Entry] = []
    for code in sorted(grouped, key=lambda value: (len(value), value)):
        candidates = grouped[code]
        actual_candidates = [entry for entry in candidates if entry.source == "实际码"]
        retained_candidates = [entry for entry in candidates if entry.source == "保留全码"]
        ranks: dict[int, set[str]] = defaultdict(set)
        for entry in actual_candidates:
            ranks[entry.rank].add(entry.row.word)
        conflicts = {rank: words for rank, words in ranks.items() if len(words) > 1}
        if conflicts:
            raise ValueError(f"码位{code}存在候选序号冲突：{conflicts}")
        # 先完整保持旧表的实际候选顺序，再把所有保留全码放到末尾。
        # retained的full_rank只用于彼此间稳定排序，绝不能插回原全码首选序列。
        ordered = sorted(actual_candidates, key=lambda entry: (
            entry.rank, -entry.row.frequency, entry.row.index))
        ordered += sorted(retained_candidates, key=lambda entry: (
            entry.rank, -entry.row.frequency, entry.row.index))
        seen_words: set[str] = set()
        for entry in ordered:
            if entry.row.word not in seen_words:
                result.append(entry)
                seen_words.add(entry.row.word)
    return result


def validate_short_yields_full(rows: list[Row], practical: list[Entry]) -> None:
    """保证新增全码只追加，不改变任何原实际码位的候选序列。"""
    expected: dict[str, list[str]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (
            len(item.actual), item.actual, item.actual_rank, -item.frequency, item.index)):
        if row.word not in expected[row.actual]:
            expected[row.actual].append(row.word)
    actual: dict[str, list[str]] = defaultdict(list)
    for entry in practical:
        if entry.source == "实际码":
            actual[entry.code].append(entry.row.word)
    if actual != expected:
        raise ValueError("出简让全门禁失败：新增全码改变了原实际码候选序列")

    by_code: dict[str, list[Entry]] = defaultdict(list)
    for entry in practical:
        by_code[entry.code].append(entry)
    for code, entries in by_code.items():
        seen_retained = False
        for entry in entries:
            if entry.source == "保留全码":
                seen_retained = True
            elif seen_retained:
                raise ValueError(f"出简让全门禁失败：{code}的保留全码没有位于原候选之后")


def validate_written_tables(plain_path: Path, sogou_path: Path,
                            expected: list[Entry]) -> None:
    plain = []
    for line_no, line in enumerate(plain_path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 2:
            raise ValueError(f"普通表第{line_no}行不是2列")
        plain.append((fields[1], fields[0]))

    sogou = []
    for line_no, line in enumerate(sogou_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith(";"):
            continue
        left, word = line.split("=", 1)
        code, position = left.rsplit(",", 1)
        sogou.append((code, word, int(position)))

    positions: Counter[str] = Counter()
    expected_tuples = []
    for entry in expected:
        positions[entry.code] += 1
        expected_tuples.append((entry.code, entry.row.word, positions[entry.code]))
    if plain != [(code, word) for code, word, _ in expected_tuples]:
        raise ValueError("普通表反向读取结果与预期不一致")
    if sogou != expected_tuples:
        raise ValueError("搜狗表反向读取结果或候选次序与预期不一致")


def write_one(card: int, seed: int, code_path: Path, elements_path: Path,
              output_root: Path) -> dict:
    rows = load_rows(code_path, elements_path)
    practical = practical_rows(rows)
    validate_short_yields_full(rows, practical)
    card_dir = output_root / f"C{card:02d}_seed_{seed}"
    card_dir.mkdir(parents=True, exist_ok=True)

    detail_path = card_dir / "编码审计明细.tsv"
    with detail_path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target, delimiter="\t", lineterminator="\n")
        writer.writerow(("原始行号", "字", "拼音", "频率", "全码", "全码候选序号",
                         "实际码", "实际码候选序号", "实际码长"))
        for row in rows:
            writer.writerow((row.index, row.word, row.pinyin, row.frequency, row.full,
                             row.full_rank, row.actual, row.actual_rank, len(row.actual)))

    plain_path = card_dir / "纯单字试用表.txt"
    plain_path.write_text("".join(f"{entry.row.word}\t{entry.code}\n" for entry in practical),
                          encoding="utf-8")

    sogou_path = card_dir / "纯单字试用表_搜狗.txt"
    header = [
        f"; 夜莺码 v0.8 C{card:02d} seed {seed} 纯单字试用表",
        "; 每个出简身份同时保留全码，且按“出简让全”排在原有码位候选之后；未加入快符、无理码、谕旨或词表",
        "",
    ]
    positions: Counter[str] = Counter()
    sogou_lines = header[:]
    for entry in practical:
        positions[entry.code] += 1
        sogou_lines.append(f"{entry.code},{positions[entry.code]}={entry.row.word}")
    sogou_path.write_text("\n".join(sogou_lines) + "\n", encoding="utf-8")
    validate_written_tables(plain_path, sogou_path, practical)

    length_counts = Counter(len(row.actual) for row in rows)
    practical_length_counts = Counter(len(entry.code) for entry in practical)
    collision_codes = Counter(entry.code for entry in practical)
    retained_full = sum(entry.source == "保留全码" for entry in practical)
    report_path = card_dir / "生成报告.md"
    report = [
        f"# C{card:02d} 纯单字试用表生成报告", "",
        f"- seed：{seed}",
        f"- 审计身份：{len(rows)}（不同汉字 {len(set(r.word for r in rows))}）",
        f"- 试用表条目：{len(practical)}（实际码与保留全码物化后按同字同码去重）",
        f"- 出简身份额外保留全码条目：{retained_full}",
        f"- 原始身份实际码长：一码 {length_counts[1]}，二码 {length_counts[2]}，三码 {length_counts[3]}，四码 {length_counts[4]}",
        f"- 试用条目码长：一码 {practical_length_counts[1]}，二码 {practical_length_counts[2]}，三码 {practical_length_counts[3]}，四码 {practical_length_counts[4]}",
        f"- 有多候选的实际码位：{sum(v > 1 for v in collision_codes.values())}",
        f"- 最大候选数：{max(collision_codes.values())}", "",
        "## SHA-256", "",
        f"- 输入 code.txt：`{sha256(code_path)}`",
        f"- 输入 elements：`{sha256(elements_path)}`",
        f"- 编码审计明细.tsv：`{sha256(detail_path)}`",
        f"- 纯单字试用表.txt：`{sha256(plain_path)}`",
        f"- 纯单字试用表_搜狗.txt：`{sha256(sogou_path)}`", "",
        "校验通过：8454身份、8105字、逐行对齐、实际简码与全码双路径、出简让全、原候选序列不变及两种试用格式一致。", "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")
    return {
        "card": card, "seed": seed, "rows": len(rows), "glyphs": 8105,
        "practical": len(practical), "deduplicated": len(rows) + sum(r.full != r.actual for r in rows) - len(practical),
        "retained_full": retained_full,
        "lengths": dict(sorted(length_counts.items())),
        "collision_codes": sum(v > 1 for v in collision_codes.values()),
        "max_candidates": max(collision_codes.values()), "directory": str(card_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cards", type=int, nargs="+", default=[7, 10, 15])
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()

    nested_manifest = args.suite / "cards" / "manifest.json"
    direct_manifest = args.suite / "manifest.json"
    existing = [path for path in (nested_manifest, direct_manifest) if path.is_file()]
    if len(existing) != 1:
        raise ValueError(
            "suite必须且只能解析到一个清单：支持实验根目录/cards/manifest.json"
            "或独立卡池根目录/manifest.json"
        )
    manifest = json.loads(existing[0].read_text(encoding="utf-8"))
    by_card = {int(item["card"]): item for item in manifest["cards"]}
    args.output.mkdir(parents=True, exist_ok=True)
    if args.jobs <= 0:
        raise ValueError("jobs必须为正数")

    def build(card: int) -> dict:
        item = by_card[card]
        output_directory = item.get("output_directory")
        if not output_directory:
            raise ValueError(f"C{card:02d} manifest缺少output_directory")
        code_path = Path(output_directory) / "code.txt"
        return write_one(card, int(item["seed"]), code_path, args.elements, args.output)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        summaries = list(pool.map(build, args.cards))

    collection = args.output / "普通单字码表集合"
    collection.mkdir(parents=True, exist_ok=True)
    expected_collection = set()
    for item in summaries:
        name = f"C{item['card']:02d}_seed_{item['seed']}_纯单字试用表.txt"
        expected_collection.add(name)
        source = Path(item["directory"]) / "纯单字试用表.txt"
        (collection / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    unexpected = [path for path in collection.glob("*.txt") if path.name not in expected_collection]
    if unexpected:
        raise ValueError("普通表集合含不属于本次候选的旧文件：" + "、".join(x.name for x in unexpected))

    summary_path = args.output / "候选纯单字试用表汇总.md"
    lines = ["# 候选纯单字试用表汇总", "", "| 候选 | seed | 审计身份 | 试用条目 | 去重 | 一/二/三/四码身份 | 多候选码位 | 最大候选 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for item in summaries:
        lengths = item["lengths"]
        lines.append(f"| C{item['card']:02d} | {item['seed']} | {item['rows']} | {item['practical']} | {item['deduplicated']} | {lengths.get(1,0)}/{lengths.get(2,0)}/{lengths.get(3,0)}/{lengths.get(4,0)} | {item['collision_codes']} | {item['max_candidates']} |")
    lines += ["", "各候选彼此隔离，均未加入任何退火后的人工码位调整；主测与对照角色以当次实验设计为准。",
              "所有普通表另平铺于`普通单字码表集合/`，便于连续切换测试。", ""]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
