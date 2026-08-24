# -*- coding: utf-8 -*-
"""整合本地码表与公开词频，生成可溯源的6万词草案。"""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent
DOCS = BASE / "documents"
PUB = DOCS / "public_sources"
OUT = BASE / "work" / "lexicon"
HAN = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+$")
TARGET = 60000


def valid(word, charset):
    return 2 <= len(word) <= 10 and HAN.fullmatch(word) and all(c in charset for c in word)


def load_codetable(path):
    raw = path.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    result = {}
    table = False
    for line in raw.decode(encoding).splitlines():
        line = line.strip()
        if line == "[CODETABLE]":
            table = True
            continue
        if not table or not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        word = parts[1].strip()
        value = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
        result[word] = max(result.get(word, 0), value)
    return result


def load_wordlist(path):
    return {line.strip(): 1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()}


def load_bcc(path):
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                result[row["token"]] = int(row["count"])
            except (KeyError, ValueError):
                pass
    return result


def load_subtlex(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["Word"]: int(row["WCount"]) for row in data["data"] if row.get("Word") and row.get("WCount") is not None}


def load_cld_weibo(path):
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            word = row.get("Word", "")
            raw = row.get("FrequencyRawWeibo", "")
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                result[word] = value
    return result


def rank_map(values, charset):
    rows = [(w, v) for w, v in values.items() if valid(w, charset) and v > 0]
    rows.sort(key=lambda x: (-x[1], x[0]))
    return {word: rank for rank, (word, _) in enumerate(rows, 1)}, len(rows)


def rank_score(rank, size):
    if not rank or size <= 1:
        return 0.0
    return max(0.0, 1.0 - math.log(rank) / math.log(size + 1))


def main():
    readings = json.loads((ROOT / "work" / "readings.json").read_text(encoding="utf-8"))
    charset = set(readings)
    local = {p.name: p for p in DOCS.glob("*.txt")}
    ice86 = load_codetable(next(p for n,p in local.items() if "86五笔" in n))
    ice98 = load_codetable(next(p for n,p in local.items() if "98五笔" in n))
    tiger = load_codetable(next(p for n,p in local.items() if "冰虎" in n))
    core = load_wordlist(next(p for n,p in local.items() if "取交集" in n))
    ice = dict(ice86)
    for word, value in ice98.items():
        ice[word] = max(ice.get(word, 0), value)

    raw_sources = {
        "ice": ice,
        "tiger": tiger,
        "bcc_balanced": load_bcc(PUB / "multi_domain_total_word_freq" / "multi_domain_total_word_freq.txt"),
        "bcc_dialogue": load_bcc(PUB / "dialogue_word_freq" / "dialogue_word_freq.txt"),
        "bcc_news": load_bcc(PUB / "news_total_word_freq" / "news_total_word_freq.txt"),
        "bcc_literature": load_bcc(PUB / "literature_word_freq" / "literature_word_freq.txt"),
        "subtlex": load_subtlex(PUB / "SUBTLEX-CH-WF.json"),
        "cld_weibo": load_cld_weibo(PUB / "CLD-2.1" / "chineselexicaldatabase2.1.csv"),
    }
    ranks = {}
    sizes = {}
    for source, values in raw_sources.items():
        ranks[source], sizes[source] = rank_map(values, charset)

    # 选入可信度：来源出现本身有基础分，源内高排名再加分；同源BCC四频道控制总权重。
    selection_weights = {
        "ice": 0.7, "tiger": 0.5, "bcc_balanced": 1.4, "bcc_dialogue": 1.2,
        "bcc_news": 0.7, "bcc_literature": 0.7, "subtlex": 1.3, "cld_weibo": 1.3,
    }
    # 常用等级：只用真实语料频率，不使用“是否被码表收录”和核心交集加成。
    usage_weights = {
        "bcc_balanced": 1.4, "bcc_dialogue": 1.3, "bcc_news": 0.7,
        "bcc_literature": 0.7, "subtlex": 1.3, "cld_weibo": 1.3,
    }
    candidates = set(w for w in core if valid(w, charset))
    for rank in ranks.values():
        candidates.update(rank)

    rows = []
    for word in candidates:
        is_core = word in core
        selection = 3.0 if is_core else 0.0
        usage = 0.0
        support = []
        rank_values = {}
        for source, rank in ranks.items():
            r = rank.get(word)
            rank_values[source] = r
            if r:
                support.append(source)
                rs = rank_score(r, sizes[source])
                selection += selection_weights[source] * (0.35 + 0.65 * rs)
                usage += usage_weights.get(source, 0.0) * rs
        rows.append({"word": word, "core": is_core, "selection": selection, "usage": usage,
                     "support": support, "ranks": rank_values})

    # 共同交集优先保留，其余按多来源选入得分补足到6万。
    rows.sort(key=lambda x: (not x["core"], -x["selection"], -x["usage"], x["word"]))
    selected = rows[:TARGET]
    selected.sort(key=lambda x: (-x["usage"], -x["selection"], x["word"]))
    for i, row in enumerate(selected, 1):
        row["usage_rank"] = i
        row["tier"] = "核心2000" if i <= 2000 else ("常用20000" if i <= 20000 else "精选60000")

    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["rank", "word", "tier", "length", "core_intersection", "selection_score", "usage_score",
              "support_count", "sources"] + [f"rank_{s}" for s in raw_sources]
    with (OUT / "精选词库60000.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in selected:
            item = {"rank": row["usage_rank"], "word": row["word"], "tier": row["tier"],
                    "length": len(row["word"]), "core_intersection": int(row["core"]),
                    "selection_score": f"{row['selection']:.6f}", "usage_score": f"{row['usage']:.6f}",
                    "support_count": len(row["support"]), "sources": ",".join(row["support"])}
            item.update({f"rank_{s}": row["ranks"][s] or "" for s in raw_sources})
            writer.writerow(item)
    (OUT / "精选词库60000.txt").write_text("\n".join(row["word"] for row in selected) + "\n", encoding="utf-8")

    lengths = Counter(len(row["word"]) for row in selected)
    tiers = Counter(row["tier"] for row in selected)
    supports = Counter(len(row["support"]) for row in selected)
    core_kept = sum(row["core"] for row in selected)
    report = ["# 精选词库6万第一版整合报告", "",
              "本版为透明可复算草案；尚未经过词长配额、专名／整句人工抽查和最终权重确认。", "",
              f"- 候选并集：{len(rows):,}", f"- 入选：{len(selected):,}",
              f"- 四库共同交集可编码词：{sum(valid(w,charset) for w in core):,}；保留：{core_kept:,}",
              "- 词长：" + "、".join(f"{k}字={v:,}" for k,v in sorted(lengths.items())),
              "- 层级：" + "、".join(f"{k}={v:,}" for k,v in tiers.items()),
              "- 外部／码表来源支持数：" + "、".join(f"{k}源={v:,}" for k,v in sorted(supports.items())), "",
              "## 各来源有效规模", ""]
    report += [f"- {s}: {sizes[s]:,}" for s in raw_sources]
    report += ["", "## 常用排名前100", "", " ".join(row["word"] for row in selected[:100]), "",
               "## 下一轮必须检查", "",
               "- 按词长抽样，防止四字成语或长短语比例失衡。",
               "- 检查专名、机构名、地名、整句、古语和分词碎片。",
               "- 比较前2000／前20000与主人实际输入直觉。",
               "- 确认最终分层边界后，才把词库接入退火元素序列。"]
    (OUT / "整合报告.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
