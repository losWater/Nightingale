#!/usr/bin/env python3
"""同口径比较简单鹤 9.3 与夜莺 0.9 的单字性能。"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


TIERS = (300, 500, 1500, 1674, 3527, 6000)
KEY = {
    **{k: ("L", f) for k, f in zip("qwert", "PRMII")},
    **{k: ("R", f) for k, f in zip("yuiop", "IIMRP")},
    **{k: ("L", f) for k, f in zip("asdfg", "PRMII")},
    **{k: ("R", f) for k, f in zip("hjkl", "IIMR")},
    **{k: ("L", f) for k, f in zip("zxcv", "PRMI")},
    **{k: ("R", f) for k, f in zip("bnm", "III")},
}
ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
ROW = {key: i for i, row in enumerate(ROWS) for key in row}
CHAI_LAYOUT = ("trewq", "gfdsa", "bvcxz", "yuiop", "hjkl", "nm")
COL = {key: i for row in CHAI_LAYOUT for i, key in enumerate(row)}


def chai_pairs() -> tuple[set[str], set[str]]:
    """复现 libchai 同指跨排定义，但按用户习惯把 B 归右食指。"""
    large, small = set(), set()
    keys = "".join(ROWS)
    for a in keys:
        for b in keys:
            if KEY[a][1] != KEY[b][1] or KEY[a][0] != KEY[b][0]:
                continue
            delta = abs(ROW[a] - ROW[b])
            if delta >= 2:
                large.add(a + b)
            elif delta == 1 or abs(COL[a] - COL[b]) == 1:
                small.add(a + b)
    return large, small


LARGE, SMALL = chai_pairs()


def is_char(text: str) -> bool:
    return len(text) == 1


def load_frequency(path: Path) -> dict[str, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for char, rows in raw.items():
        # code 的前两位就是音节身份；同音多拆取最大，不同音相加。
        by_sound: dict[str, int] = {}
        for freq, code in rows:
            sound = str(code)[:2]
            by_sound[sound] = max(by_sound.get(sound, 0), int(freq))
        result[char] = sum(by_sound.values())
    return result


def load_table(path: Path) -> dict[str, list[tuple[str, int]]]:
    slots: dict[str, list[str]] = defaultdict(list)
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 2 or not is_char(fields[0]):
            continue
        char, code = fields[0], fields[1].strip().lower()
        if not (1 <= len(code) <= 4 and code.isascii() and code.isalpha()):
            raise ValueError(f"{path}:{number}: 非法单字编码 {char!r} {code!r}")
        if char not in slots[code]:
            slots[code].append(char)
    result: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for code, chars in slots.items():
        for rank, char in enumerate(chars, 1):
            result[char].append((code, rank))
    if not result:
        raise ValueError(f"{path}: 没有读到单字条目")
    return dict(result)


def preferred(entries: list[tuple[str, int]], first_only: bool) -> tuple[str, int] | None:
    choices = [(code, rank) for code, rank in entries if not first_only or rank == 1]
    if not choices:
        return None
    return min(choices, key=lambda x: (len(x[0]), x[1], x[0]))


def safe_rate(a: int | float, b: int | float) -> float:
    if not b:
        raise ValueError("统计分母为零")
    value = a / b
    if not math.isfinite(value):
        raise ValueError("统计结果不是有限数")
    return value


def analyze(name: str, table: dict[str, list[tuple[str, int]]], chars: list[str], freq: dict[str, int]) -> dict:
    first_choice = {c: preferred(table[c], True) for c in chars}
    any_code = {c: preferred(table[c], False) for c in chars}
    if any(value is None for value in any_code.values()):
        raise ValueError(f"{name}: 存在没有任何编码的字")
    operational = {c: any_code[c][0] for c in chars}

    def one_tier(part: list[str]) -> dict:
        weight = sum(freq[c] for c in part)
        transitions = 0
        micro = pinky = large = small = split = split_base = 0
        first_three = any_three = key_sum = burden = 0
        full_slots: dict[str, list[str]] = defaultdict(list)
        for c in part:
            w, code = freq[c], operational[c]
            first_three += (first_choice[c] is not None and len(first_choice[c][0]) <= 3) * w
            any_three += (len(any_code[c][0]) <= 3) * w
            key_sum += len(code) * w
            burden += (any_code[c][1] - 1) * w
            if len(code) == 4:
                full_slots[code].append(c)
            transitions += max(0, len(code) - 1) * w
            for a, b in zip(code, code[1:]):
                pair = a + b
                ha, fa = KEY[a]
                hb, fb = KEY[b]
                if a != b and ha == hb and fa == fb:
                    micro += w
                if ha == hb and ({fa, fb} == {"P", "R"} or {fa, fb} == {"P", "M"}):
                    pinky += w
                large += (pair in LARGE) * w
                small += (pair in SMALL) * w
            if len(code) >= 3:
                split_base += w
                split += (KEY[code[1]][0] != KEY[code[2]][0]) * w
        full_losers = sum(max(0, len(v) - 1) for v in full_slots.values())
        full_collision_slots = sum(len(v) > 1 for v in full_slots.values())
        return {
            "characters": len(part), "weight": weight,
            "first_three_count": sum(first_choice[c] is not None and len(first_choice[c][0]) <= 3 for c in part),
            "first_three_rate": safe_rate(first_three, weight),
            "any_three_count": sum(len(any_code[c][0]) <= 3 for c in part),
            "any_three_rate": safe_rate(any_three, weight),
            "weighted_key_length": safe_rate(key_sum, weight),
            "candidate_burden": safe_rate(burden, weight),
            "effective_full_collision_slots": full_collision_slots,
            "effective_full_collision_losers": full_losers,
            "large_cross_rate": safe_rate(large, transitions),
            "small_cross_rate": safe_rate(small, transitions),
            "single_finger_move_rate": safe_rate(micro, transitions),
            "pinky_linkage_rate": safe_rate(pinky, transitions),
            "second_third_hand_separation_rate": safe_rate(split, split_base),
        }

    tiers = {str(n): one_tier(chars[:n]) for n in TIERS}
    tiers["all"] = one_tier(chars)
    lengths = Counter(len(operational[c]) for c in chars)
    return {"name": name, "covered_characters": len(table), "tiers": tiers,
            "characters_without_any_first_choice": sum(first_choice[c] is None for c in chars),
            "operational_code_length_counts": dict(sorted(lengths.items()))}


def pct(x: float) -> str:
    return f"{x * 100:.3f}%"


def render(data: dict) -> str:
    a, b = data["schemes"]
    names = (a["name"], b["name"])
    aa, bb = a["tiers"]["all"], b["tiers"]["all"]
    lines = ["# 简单鹤 9.3 × 夜莺 0.9 单字性能对比", "",
             f"共同字集：{data['common_characters']} 字；统一字频：`work/readings.json`；B 按右手食指。", "",
             "## 核心指标", "", f"| 指标 | {names[0]} | {names[1]} |", "|---|---:|---:|",
             f"| 首选三码率（无翻选） | {pct(aa['first_three_rate'])} | {pct(bb['first_three_rate'])} |",
             f"| 含次选三码率（能打出） | {pct(aa['any_three_rate'])} | {pct(bb['any_three_rate'])} |",
             f"| 没有任何首选码的字 | {a['characters_without_any_first_choice']} | {b['characters_without_any_first_choice']} |",
             f"| 最短可用码加权键长 | {aa['weighted_key_length']:.4f} | {bb['weighted_key_length']:.4f} |",
             f"| 含次选的候选负担 | {pct(aa['candidate_burden'])} | {pct(bb['candidate_burden'])} |",
             f"| 有效全码重码：槽 / 后置字 | {aa['effective_full_collision_slots']} / {aa['effective_full_collision_losers']} | {bb['effective_full_collision_slots']} / {bb['effective_full_collision_losers']} |",
             f"| 大跨 / 小跨 | {pct(aa['large_cross_rate'])} / {pct(aa['small_cross_rate'])} | {pct(bb['large_cross_rate'])} / {pct(bb['small_cross_rate'])} |",
             f"| 单指微移 | {pct(aa['single_finger_move_rate'])} | {pct(bb['single_finger_move_rate'])} |",
             f"| 小指联动 | {pct(aa['pinky_linkage_rate'])} | {pct(bb['pinky_linkage_rate'])} |",
             f"| 二三键换手 | {pct(aa['second_third_hand_separation_rate'])} | {pct(bb['second_third_hand_separation_rate'])} |",
             "", "## 高频分层", "",
             f"| 层级 | {names[0]}首选三码 | {names[1]}首选三码 | {names[0]}含次选三码 | {names[1]}含次选三码 | {names[0]}有效全码重 | {names[1]}有效全码重 |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for n in TIERS:
        x, y = a["tiers"][str(n)], b["tiers"][str(n)]
        lines.append(f"| {n} | {x['first_three_count']} ({pct(x['first_three_rate'])}) | {y['first_three_count']} ({pct(y['first_three_rate'])}) | {x['any_three_count']} | {y['any_three_count']} | {x['effective_full_collision_losers']} | {y['effective_full_collision_losers']} |")
    lines += ["", "## 解释", "",
              "- 首选三码率描述无需翻页的实际输入；最短可用码键长展示账面键程，必须结合候选负担一起阅读。含次选三码率展示多重简码能覆盖多少字。",
              "- ‘候选负担’是所选最短码的候选序号减一后按字频加权；它不是传统 Chai 选重率，专门用于揭示‘短码但要翻选’的成本。",
              "- 有效全码重码只看实际仍需四键输入的字，因此不会把已经出简并让出全码的字重复处罚。",
              "- 手感指标按最短可用码、统一字频加权；没有任何首选码的字仍如实带入候选成本。数值除二三键换手外均越低越好。", ""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--frequency", type=Path, required=True)
    p.add_argument("--jdhe", type=Path, required=True)
    p.add_argument("--nightingale", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    p.add_argument("--output-md", type=Path, required=True)
    args = p.parse_args()
    freq = load_frequency(args.frequency)
    tables = (("简单鹤 9.3", load_table(args.jdhe)), ("夜莺 0.9", load_table(args.nightingale)))
    common = [c for c in freq if all(c in table for _, table in tables) and freq[c] > 0]
    common.sort(key=lambda c: (-freq[c], c))
    if len(common) < 6000:
        raise ValueError(f"共同正频字集只有 {len(common)} 字")
    result = {"schema_version": 1, "common_characters": len(common),
              "frequency": str(args.frequency.resolve()),
              "schemes": [analyze(name, table, common, freq) for name, table in tables]}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render(result), encoding="utf-8")
    print(json.dumps({"status": "pass", "common": len(common)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
