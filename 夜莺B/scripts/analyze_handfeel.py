# -*- coding: utf-8 -*-
"""按字频审计码表的键位负担与单字码内手感。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import yaml


KEY_INFO = {
    **{k: ("左", f, 0) for k, f in zip("qwert", ("小", "无", "中", "食", "食"))},
    **{k: ("右", f, 0) for k, f in zip("yuiop", ("食", "食", "中", "无", "小"))},
    **{k: ("左", f, 1) for k, f in zip("asdfg", ("小", "无", "中", "食", "食"))},
    **{k: ("右", f, 1) for k, f in zip("hjkl", ("食", "食", "中", "无"))},
    **{k: ("左", f, 2) for k, f in zip("zxcvb", ("小", "无", "中", "食", "食"))},
    **{k: ("右", f, 2) for k, f in zip("nm", ("食", "食"))},
}
ROW_NAME = {0: "上排", 1: "中排", 2: "下排"}


def pct(value: float, total: float) -> str:
    return f"{value / total * 100:.3f}%" if total else "0%"


def analyze(records: list[tuple[str, str, int]]):
    key = Counter()
    hand = Counter()
    finger = Counter()
    row = Counter()
    events = Counter()
    examples = defaultdict(Counter)
    strokes = 0
    transitions = 0
    for char, code, freq in records:
        if not freq or not code:
            continue
        strokes += freq * len(code)
        for letter in code:
            h, f, r = KEY_INFO[letter]
            key[letter] += freq
            hand[h] += freq
            finger[h + f] += freq
            row[r] += freq
        for a, b in zip(code, code[1:]):
            transitions += freq
            ha, fa, ra = KEY_INFO[a]
            hb, fb, rb = KEY_INFO[b]
            flags = []
            if a == b:
                flags.append("同键连击")
            if ha == hb and fa == fb and a != b:
                flags.append("同指异键")
            if ra != rb:
                flags.append("跨排")
            if abs(ra - rb) == 2:
                flags.append("跨两排")
            if ha != hb:
                flags.append("左右交替")
            for flag in flags:
                events[flag] += freq
                examples[flag][f"{char}({code}:{a}{b})"] += freq
    return {
        "strokes": strokes, "transitions": transitions, "key": key,
        "hand": hand, "finger": finger, "row": row,
        "events": events, "examples": examples,
    }


def sliced(records: list[tuple[str, str, int]], start: int,
           end: int | None = None) -> list[tuple[str, str, int]]:
    return [(char, code[start:end], freq) for char, code, freq in records]


def render_section(title: str, stat: dict) -> list[str]:
    strokes, transitions = stat["strokes"], stat["transitions"]
    out = [f"## {title}", "",
           f"- 加权击键：{strokes:,}；加权码内相邻键对：{transitions:,}",
           f"- 左／右手：{pct(stat['hand']['左'], strokes)}／{pct(stat['hand']['右'], strokes)}",
           f"- 上／中／下排：{pct(stat['row'][0], strokes)}／{pct(stat['row'][1], strokes)}／{pct(stat['row'][2], strokes)}",
           f"- 左小指＋右小指：{pct(stat['finger']['左小'] + stat['finger']['右小'], strokes)}",
           "",
           "| 项目 | 占全部码内键对 | 高频贡献例 |",
           "|---|---:|---|"]
    for name in ("同键连击", "同指异键", "跨排", "跨两排", "左右交替"):
        tops = "、".join(k for k, _ in stat["examples"][name].most_common(12)) or "—"
        out.append(f"| {name} | {pct(stat['events'][name], transitions)} | {tops} |")
    out += ["", "### 各键负担", "",
            "`" + "　".join(f"{k.upper()} {pct(stat['key'][k], strokes)}" for k in "qwertyuiop") + "`", "",
            "`" + "　".join(f"{k.upper()} {pct(stat['key'][k], strokes)}" for k in "asdfghjkl") + "`", "",
            "`" + "　".join(f"{k.upper()} {pct(stat['key'][k], strokes)}" for k in "zxcvbnm") + "`", "",
            "### 各指负担", "",
            "| 手指 | 占比 |", "|---|---:|"]
    for name in ("左小", "左无", "左中", "左食", "右食", "右中", "右无", "右小"):
        out.append(f"| {name} | {pct(stat['finger'][name], strokes)} |")
    out.append("")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", type=Path)
    ap.add_argument("--elements", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    code_rows = []
    for line in args.code.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) >= 4:
            code_rows.append(fields)
    if len(code_rows) != len(elements):
        raise ValueError(f"code/elements 行数不一致：{len(code_rows)} != {len(elements)}")
    full, short = [], []
    for item, fields in zip(elements, code_rows):
        char, freq = str(item["词"]), int(item.get("频率", 0))
        if char != fields[0]:
            raise ValueError(f"code/elements 错位：{char} != {fields[0]}")
        full.append((char, fields[1], freq))
        short.append((char, fields[3], freq))

    sections = ["# 线程0手感全面审计", "",
                "按单字频率加权；只统计单字码内部相邻击键，不推断跨字连击。",
                "实际输出采用一／二／三码与全码的最终简码；全码用于观察完整音形路径。", ""]
    sections += render_section("实际简码输出", analyze(short))
    sections += render_section("完整四码", analyze(full))
    sections += render_section("音形接缝（第二音码→首根）", analyze(sliced(full, 1, 3)))
    sections += render_section("纯形码段（首根→末根）", analyze(sliced(full, 2, 4)))
    args.output.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
