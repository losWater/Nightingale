# -*- coding: utf-8 -*-
"""只读审计 documents 中外来词库的格式、规模与重叠，不改写原文件。"""
from collections import Counter
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
DOCS = BASE / "documents"
HAN = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+$")


def read_file(path):
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    elif raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        try:
            raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = "gb18030"
    lines = raw.decode(encoding).splitlines()
    codetable = any(line.strip() == "[CODETABLE]" for line in lines[:30])
    records = []
    rejected = Counter()
    in_table = not codetable
    columns = Counter()
    numeric = []
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            rejected["空行"] += 1
            continue
        if codetable and not in_table:
            if line == "[CODETABLE]":
                in_table = True
            else:
                rejected["头部"] += 1
            continue
        parts = line.split("\t")
        columns[len(parts)] += 1
        if codetable:
            if len(parts) < 2:
                rejected["列不足"] += 1
                continue
            code, word = parts[0].strip(), parts[1].strip()
            value = parts[2].strip() if len(parts) >= 3 else ""
            if value.isdigit():
                numeric.append(int(value))
            records.append((word, code, value, lineno))
        else:
            records.append((parts[0].strip(), "", "", lineno))
    return lines, records, rejected, columns, numeric, encoding


def main():
    datasets = {}
    report = ["# 外来词库格式审计", "", "原始文件只读；本报告未生成合并词库。", ""]
    for path in sorted(DOCS.glob("*")):
        if not path.is_file():
            continue
        lines, records, rejected, columns, numeric, encoding = read_file(path)
        words = [r[0] for r in records]
        unique = set(words)
        valid = {w for w in unique if HAN.fullmatch(w)}
        multi = {w for w in valid if len(w) >= 2}
        lengths = Counter(len(w) for w in valid)
        datasets[path.name] = multi
        report += [f"## {path.name}", "",
                   f"- 编码：{encoding}；文件大小：{path.stat().st_size:,} 字节；总行数：{len(lines):,}",
                   f"- 解析记录：{len(records):,}；唯一词条：{len(unique):,}；纯汉字：{len(valid):,}；二字及以上：{len(multi):,}",
                   f"- 重复记录：{len(words)-len(unique):,}；列数分布：{dict(sorted(columns.items()))}",
                   "- 词长分布：" + "、".join(f"{k}字={v:,}" for k,v in sorted(lengths.items()) if k <= 10)]
        if numeric:
            report.append(f"- 第三列数值：{len(numeric):,}项；范围 {min(numeric):,}～{max(numeric):,}；含义尚待来源文档确认，暂不作为词频。")
        if rejected:
            report.append("- 跳过：" + "、".join(f"{k}={v:,}" for k,v in rejected.items()))
        report += [""]

    names = list(datasets)
    report += ["## 词库重叠", ""]
    for i, a in enumerate(names):
        for b in names[i+1:]:
            inter = datasets[a] & datasets[b]
            report.append(f"- `{a}` ∩ `{b}`：{len(inter):,}")
    if datasets:
        all_inter = set.intersection(*datasets.values())
        union = set.union(*datasets.values())
        report += [f"- 四库共同交集：{len(all_inter):,}", f"- 四库并集：{len(union):,}", ""]

    out = BASE / "work" / "外来词库格式审计.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
