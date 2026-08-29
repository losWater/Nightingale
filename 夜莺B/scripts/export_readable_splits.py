#!/usr/bin/env python3
"""将机器用最终拆分表导出为无乱码的 TSV 和 HTML。"""
from __future__ import annotations

import argparse
import csv
from html import escape
import io
from pathlib import Path
import sys
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b_roots  # noqa: E402

STROKE_NAMES = {"1": "横", "2": "竖", "3": "撇", "4": "点", "5": "折", "6": "折"}


def display(element: str) -> str:
    return STROKE_NAMES.get(element, b_roots.name(element))


def read_rows(path: Path) -> list[tuple[str, list[str]]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        char, separator, raw = line.partition("\t")
        if not separator or not char or not raw.strip():
            raise ValueError(f"{path}:{number}: 拆分行格式错误")
        rows.append((char, raw.split()))
    if len({char for char, _ in rows}) != len(rows):
        raise ValueError("最终拆分表存在重复汉字")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True,
                        help="退火实际使用的元素序列；人工表只导出其中的单字")
    parser.add_argument("--tsv", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    args = parser.parse_args()
    all_rows = read_rows(args.input)
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    used = {str(item["词"]) for item in elements if len(str(item.get("词", ""))) == 1}
    available = {char for char, _ in all_rows}
    missing = used - available
    if missing:
        raise ValueError("退火单字缺少最终拆分: " + " ".join(sorted(missing)))
    rows = [(char, sequence) for char, sequence in all_rows if char in used]
    if len(rows) != len(used):
        raise AssertionError("人工拆分表未与退火单字集一一对齐")
    rendered = []
    for char, sequence in rows:
        head, _ = b_roots.root_of(char, 0)
        tail, _ = b_roots.root_of(char, -1)
        rendered.append((char, " ＋ ".join(map(display, sequence)), str(head), str(tail)))

    args.tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.tsv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("汉字", "最终规范拆分", "编码首根", "编码末根"))
        writer.writerows(rendered)

    body = "\n".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in rendered
    )
    html = f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">
<title>夜莺最终规范拆分表</title>
<style>body{{font-family:\"Microsoft YaHei\",sans-serif;margin:24px;color:#172033}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3dd;padding:6px 10px;text-align:left}}
th{{position:sticky;top:0;background:#e8f1f5}}tr:nth-child(even){{background:#f7f9fb}}</style></head>
<body><h1>夜莺最终规范拆分表</h1>
<p>拆分来源：{escape(str(args.input))}；退火字集：{escape(str(args.elements))}；共 {len(rendered)} 字。数字笔画和 PUA 部件已转为可读名称。</p>
<table><thead><tr><th>汉字</th><th>最终规范拆分</th><th>编码首根</th><th>编码末根</th></tr></thead>
<tbody>{body}</tbody></table></body></html>"""
    args.html.write_text(html, encoding="utf-8-sig")
    print(f"导出 {len(rendered)} 字：{args.tsv} / {args.html}")


if __name__ == "__main__":
    main()
