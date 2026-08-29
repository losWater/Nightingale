#!/usr/bin/env python3
"""构建论文实验用20万纯二字词库和20万普通混合词库。"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
DOCS = BASE / "documents"
PUBLIC = DOCS / "public_sources"
OUT = BASE / "work" / "paper_lexicons_200k"
HAN = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+$")
LIMIT = 200_000
TIER_BOUNDS = (2_000, 10_000, 50_000, 100_000, 200_000)
TIER_NAMES = ("S_前2000", "A_前10000", "B_前50000", "C_前100000", "D_前200000")


def valid(word: str, charset: set[str]) -> bool:
    return 2 <= len(word) <= 10 and bool(HAN.fullmatch(word)) and all(c in charset for c in word)


def read_bcc(path: Path) -> dict[str, float]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            try:
                result[row["token"]] = float(row["count"])
            except (KeyError, TypeError, ValueError):
                pass
    return result


def read_subtlex(path: Path) -> dict[str, float]:
    return {row["Word"]: float(row["WCount"]) for row in json.loads(path.read_text(encoding="utf-8"))["data"]
            if row.get("Word") and row.get("WCount") is not None}


def read_cld(path: Path) -> dict[str, float]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            try:
                value = float(row.get("FrequencyRawWeibo", ""))
            except (TypeError, ValueError):
                continue
            if value > 0:
                result[row.get("Word", "")] = value
    return result


def read_jieba(path: Path) -> dict[str, float]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 2:
            try:
                result[fields[0]] = float(fields[1])
            except ValueError:
                pass
    return result


def read_thuocl(directory: Path) -> dict[str, float]:
    result = defaultdict(float)
    for path in directory.glob("THUOCL_*.txt"):
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            fields = line.rsplit("\t", 1)
            if len(fields) != 2:
                fields = line.rsplit(maxsplit=1)
            if len(fields) == 2:
                try:
                    result[fields[0]] += float(fields[1])
                except ValueError:
                    pass
    return dict(result)


def read_ime(path: Path) -> set[str]:
    raw = path.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    lines = raw.decode(encoding, errors="replace").splitlines()
    table = any(line.strip() == "[CODETABLE]" for line in lines[:30])
    active = not table
    result = set()
    for line in lines:
        if table and not active:
            active = line.strip() == "[CODETABLE]"
            continue
        fields = line.strip().split("\t")
        if not fields:
            continue
        word = fields[1].strip() if table and len(fields) >= 2 else fields[0].strip()
        if HAN.fullmatch(word):
            result.add(word)
    return result


def rank_sources(raw_sources: dict[str, dict[str, float]], charset: set[str]):
    ranks, sizes = {}, {}
    for name, source in raw_sources.items():
        rows = [(word, value) for word, value in source.items() if value > 0 and valid(word, charset)]
        rows.sort(key=lambda item: (-item[1], item[0]))
        ranks[name] = {word: rank for rank, (word, _) in enumerate(rows, 1)}
        sizes[name] = len(rows)
    return ranks, sizes


def rank_score(rank: int | None, size: int) -> float:
    if not rank or size <= 1:
        return 0.0
    return max(0.0, 1.0 - math.log(rank) / math.log(size + 1))


def tier(rank: int) -> str:
    return next(name for bound, name in zip(TIER_BOUNDS, TIER_NAMES) if rank <= bound)


def write_dataset(name: str, candidates: list[dict], predicate) -> list[dict]:
    selected = [row for row in candidates if predicate(row["word"])][:LIMIT]
    if len(selected) < LIMIT:
        raise RuntimeError(f"{name}只有{len(selected):,}个合格候选，不足{LIMIT:,}")
    output = []
    for rank, row in enumerate(selected, 1):
        item = dict(row)
        item["rank"] = rank
        item["tier"] = tier(rank)
        output.append(item)
    fields = ["rank", "word", "tier", "length", "usage_score", "selection_score",
              "corpus_support", "all_support", "sources"]
    with (OUT / f"{name}.tsv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in output)
    (OUT / f"{name}.txt").write_text("\n".join(row["word"] for row in output) + "\n", encoding="utf-8")
    return output


def main() -> None:
    charset = set(json.loads((ROOT / "work" / "readings.json").read_text(encoding="utf-8")))
    raw_sources = {
        "bcc_balanced": read_bcc(PUBLIC / "multi_domain_total_word_freq" / "multi_domain_total_word_freq.txt"),
        "bcc_dialogue": read_bcc(PUBLIC / "dialogue_word_freq" / "dialogue_word_freq.txt"),
        "bcc_news": read_bcc(PUBLIC / "news_total_word_freq" / "news_total_word_freq.txt"),
        "bcc_literature": read_bcc(PUBLIC / "literature_word_freq" / "literature_word_freq.txt"),
        "subtlex": read_subtlex(PUBLIC / "SUBTLEX-CH-WF.json"),
        "cld_weibo": read_cld(PUBLIC / "CLD-2.1" / "chineselexicaldatabase2.1.csv"),
        "jieba": read_jieba(PUBLIC / "jieba_dict_big.txt"),
        "thuocl": read_thuocl(PUBLIC / "THUOCL-master" / "THUOCL-master" / "data"),
    }
    corpus_names = {"bcc_balanced", "bcc_dialogue", "bcc_news", "bcc_literature", "subtlex", "cld_weibo"}
    usage_weights = {"bcc_balanced": 1.4, "bcc_dialogue": 1.3, "bcc_news": .7,
                     "bcc_literature": .7, "subtlex": 1.3, "cld_weibo": 1.3,
                     "jieba": .65, "thuocl": .2}
    ranks, sizes = rank_sources(raw_sources, charset)
    ime_sets = {}
    for path in DOCS.glob("*.txt"):
        if any(label in path.name for label in ("冰凌", "冰虎", "简单鹤", "取交集")):
            ime_sets[path.stem] = {w for w in read_ime(path) if valid(w, charset)}

    words = set().union(*(set(source) for source in ranks.values()), *ime_sets.values())
    rows = []
    for word in words:
        support = [name for name, source in ranks.items() if word in source]
        ime_support = [name for name, source in ime_sets.items() if word in source]
        usage = sum(usage_weights[name] * rank_score(ranks[name].get(word), sizes[name]) for name in support)
        corpus_support = sum(name in corpus_names for name in support)
        # selection只负责同usage下提高多源可信词的顺序，不伪装成真实使用频率。
        selection = usage + .08 * len(support) + .04 * len(ime_support)
        rows.append({"word": word, "length": len(word), "usage_score": f"{usage:.8f}",
                     "selection_score": f"{selection:.8f}", "corpus_support": corpus_support,
                     "all_support": len(support) + len(ime_support),
                     "sources": ",".join(support + ime_support), "_usage": usage, "_selection": selection})
    rows.sort(key=lambda row: (-row["_usage"], -row["corpus_support"], -row["_selection"], row["word"]))
    OUT.mkdir(parents=True, exist_ok=True)
    two = write_dataset("纯二字词库_200000", rows, lambda word: len(word) == 2)
    mixed = write_dataset("普通混合词库_200000", rows, lambda word: 2 <= len(word) <= 10)

    def summary(items):
        lengths = Counter(row["length"] for row in items)
        tiers = Counter(row["tier"] for row in items)
        supports = Counter(row["corpus_support"] for row in items)
        return {"count": len(items), "lengths": dict(sorted(lengths.items())),
                "tiers": dict(tiers), "corpus_support": dict(sorted(supports.items()))}

    manifest = {
        "tier_bounds": dict(zip(TIER_NAMES, TIER_BOUNDS)),
        "sources": sizes,
        "candidate_union": len(rows),
        "two_char": summary(two),
        "mixed": summary(mixed),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ["# 论文实验20万级词库", "", "## 分档", "",
              "- " + "；".join(f"{name}≤{bound:,}" for name, bound in zip(TIER_NAMES, TIER_BOUNDS)), "",
              "## 规模", "", f"- 候选并集：{len(rows):,}",
              f"- 纯二字词：{len(two):,}", f"- 普通混合词：{len(mixed):,}",
              "- 混合词长：" + "、".join(f"{k}字={v:,}" for k, v in summary(mixed)["lengths"].items()), "",
              "Jieba与THUOCL用于补充长尾和领域覆盖；高频排序仍以BCC、SUBTLEX、CLD等真实语料证据为主。"]
    (OUT / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
