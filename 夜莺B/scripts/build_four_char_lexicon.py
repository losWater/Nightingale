# -*- coding: utf-8 -*-
"""构建夜莺退火使用的四字简词障碍集。"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DOCS = BASE / "documents"
PUBLIC = DOCS / "public_sources"
OUT = BASE / "work" / "lexicon"
HAN4 = re.compile(r"^[\u3400-\u9fff]{4}$")
CODE4 = re.compile(r"^[a-z]{4}$")
CODE_OVERRIDES = {"长幼有序": "vyyx", "修旧利废": "xjlf"}


def simple_crane() -> dict[str, str]:
    path = next(DOCS.glob("简单鹤*.txt"))
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 2 and HAN4.fullmatch(parts[0]) and CODE4.fullmatch(parts[1]):
            result.setdefault(parts[0], parts[1])
    return result


def thuocl() -> dict[str, int]:
    result = {}
    path = PUBLIC / "THUOCL_chengyu.txt"
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split("\t")
        word = parts[0].strip() if parts else ""
        if len(parts) >= 2 and HAN4.fullmatch(word):
            result[word] = int(parts[-1].strip())
    return result


def xinhua() -> dict[str, str]:
    rows = json.loads((PUBLIC / "chinese-xinhua_idiom.json").read_text(encoding="utf-8"))
    result = {}
    for row in rows:
        word = row.get("word", "")
        code = str(row.get("abbreviation", "")).strip().lower()
        if HAN4.fullmatch(word):
            result[word] = code
    return result


def corpus_counts(words: set[str]) -> dict[str, dict[str, int]]:
    result = defaultdict(dict)
    names = ["dialogue_word_freq", "literature_word_freq",
             "multi_domain_total_word_freq", "news_total_word_freq"]
    for name in names:
        path = PUBLIC / name / f"{name}.txt"
        for row in csv.DictReader(path.open(encoding="utf-8")):
            word = row.get("token", "")
            if word in words:
                result[word][name] = int(row.get("count", 0))
    payload = json.loads((PUBLIC / "SUBTLEX-CH-WF.json").read_text(encoding="utf-8"))
    for row in payload.get("data", payload):
        word = row.get("Word", "")
        if word in words:
            result[word]["subtlex"] = int(row.get("WCount", 0))
    return result


def local_dict_words(path: Path) -> set[str]:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "gb18030"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    result = set()
    for line in text.splitlines():
        parts = line.strip().split("\t")
        word = parts[1] if len(parts) >= 2 and parts[0].isascii() else (parts[0] if parts else "")
        if HAN4.fullmatch(word):
            result.add(word)
    return result


def main() -> None:
    simple = simple_crane()
    thu = thuocl()
    xin = xinhua()
    confirmed = set(thu) & set(xin)
    additions = confirmed - set(simple)

    records = []
    review = []
    for word, code in simple.items():
        records.append({
            "word": word, "code": code, "source": "简单鹤",
            "thuocl_df": thu.get(word, ""), "xinhua": int(word in xin),
        })
    for word in additions:
        code = CODE_OVERRIDES.get(word, xin[word])
        row = {
            "word": word, "code": code, "source": "THUOCL+新华补充",
            "thuocl_df": thu[word], "xinhua": 1,
        }
        if CODE4.fullmatch(code):
            records.append(row)
        else:
            review.append(row)

    records.sort(key=lambda r: (-int(r["thuocl_df"] or 0), r["code"], r["word"]))
    review.sort(key=lambda r: (-int(r["thuocl_df"]), r["word"]))
    OUT.mkdir(parents=True, exist_ok=True)

    fields = ["word", "code", "source", "thuocl_df", "xinhua"]
    with (OUT / "四字简词.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(records)
    (OUT / "四字简词.txt").write_text(
        "\n".join(f"{r['word']}\t{r['code']}" for r in records) + "\n", encoding="utf-8"
    )
    with (OUT / "四字简词_编码待复核.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(review)

    report = [
        "# 四字简词整合报告", "",
        f"- 简单鹤四汉字四码：{len(simple):,}",
        f"- THUOCL 与新华共同确认：{len(confirmed):,}",
        f"- 双源确认且简单鹤缺失：{len(additions):,}",
        f"- 编码有效并已补入：{len(additions) - len(review):,}",
        f"- 编码异常待复核：{len(review):,}",
        f"- 最终四字简词：{len(records):,}", "",
        "规则：简单鹤原码优先；补充词仅取 THUOCL 与新华交集，使用新华自带简拼。",
    ]
    (OUT / "四字简词整合报告.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))

    # 精选：真实语料 / 成语双源 / 两个独立输入法家族，满足任一条件。
    all_words = {r["word"] for r in records}
    corpora = corpus_counts(all_words)
    tiger_path = DOCS / "冰虎词库3.0.txt"
    tiger = local_dict_words(tiger_path)
    ice_family = set()
    for path in DOCS.glob("冰凌词库*.txt"):
        ice_family |= local_dict_words(path)

    selected = []
    rejected = []
    for row in records:
        word = row["word"]
        corpus_names = sorted(k for k, v in corpora.get(word, {}).items() if v > 0)
        idiom_dual = word in confirmed
        ime_dual = word in tiger and word in ice_family
        reasons = []
        if corpus_names:
            reasons.append("真实语料:" + ",".join(corpus_names))
        if idiom_dual:
            reasons.append("成语双源")
        if ime_dual:
            reasons.append("输入法双源")
        enriched = dict(row)
        enriched.update({
            "keep_reason": ";".join(reasons),
            "corpus_source_count": len(corpus_names),
            "corpus_total_count": sum(corpora.get(word, {}).values()),
            "idiom_dual": int(idiom_dual), "ime_dual": int(ime_dual),
        })
        (selected if reasons else rejected).append(enriched)

    selected.sort(key=lambda r: (-r["corpus_source_count"], -r["corpus_total_count"],
                                 -int(r["thuocl_df"] or 0), r["code"], r["word"]))
    rejected.sort(key=lambda r: (r["code"], r["word"]))
    out_fields = fields + ["keep_reason", "corpus_source_count", "corpus_total_count",
                           "idiom_dual", "ime_dual"]
    for filename, rows in (("四字简词_精选.tsv", selected), ("四字简词_淘汰.tsv", rejected)):
        with (OUT / filename).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "四字简词_精选.txt").write_text(
        "\n".join(f"{r['word']}\t{r['code']}" for r in selected) + "\n", encoding="utf-8"
    )
    reason_counts = {
        "真实语料": sum(r["corpus_source_count"] > 0 for r in selected),
        "成语双源": sum(r["idiom_dual"] for r in selected),
        "输入法双源": sum(r["ime_dual"] for r in selected),
    }
    filter_report = ["# 四字简词筛选报告", "", f"- 候选：{len(records):,}",
                     f"- 精选：{len(selected):,}", f"- 淘汰：{len(rejected):,}"]
    filter_report += [f"- 命中{k}：{v:,}" for k, v in reason_counts.items()]
    filter_report += ["", "三项会重叠；保留条件为至少命中一项。",
                      "编码特例：长幼有序=vyyx，修旧利废=xjlf。"]
    (OUT / "四字简词筛选报告.md").write_text("\n".join(filter_report) + "\n", encoding="utf-8")
    print("\n" + "\n".join(filter_report))


if __name__ == "__main__":
    main()
