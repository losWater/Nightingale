#!/usr/bin/env python3
"""审计夜莺现有读音频率资产，不修改任何输入文件。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def load(path: Path) -> dict[str, list[list[object]]]:
    return json.loads(path.read_text(encoding="utf-8"))


def syllables(data: dict[str, list[list[object]]]):
    result: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    for char, rows in data.items():
        for frequency, code in rows:
            result[(char, str(code)[:2])].append((int(frequency), str(code)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base, current = load(args.base), load(args.current)
    bm, cm = syllables(base), syllables(current)
    polyphones = Counter()
    for char, rows in current.items():
        groups = {str(code)[:2] for _, code in rows}
        polyphones[len(groups)] += 1

    added = sorted(set(cm) - set(bm))
    removed = sorted(set(bm) - set(cm))
    changed = sorted(
        (key, sorted({x[0] for x in bm[key]}), sorted({x[0] for x in cm[key]}))
        for key in set(bm) & set(cm)
        if {x[0] for x in bm[key]} != {x[0] for x in cm[key]}
    )
    same_syllable_extra = sum(len(rows) - len({str(code)[:2] for _, code in rows}) for rows in current.values())
    zero_entries = sum(all(frequency == 0 for frequency, _ in rows) for rows in cm.values())
    conflicts = sorted(
        (key, rows) for key, rows in cm.items() if len({frequency for frequency, _ in rows}) > 1
    )
    raw_frequency = sum(frequency for rows in cm.values() for frequency, _ in rows)
    one_per_syllable_frequency = sum(max(frequency for frequency, _ in rows) for rows in cm.values())
    inflation = raw_frequency - one_per_syllable_frequency

    lines = [
        "# 现有读音频率资产审计",
        "",
        f"- 基线：`{args.base.as_posix()}`",
        f"- 当前：`{args.current.as_posix()}`",
        f"- 基线：{len(base)} 个字形，{sum(map(len, base.values()))} 行，{len(bm)} 个（字形＋双拼音码）项。",
        f"- 当前：{len(current)} 个字形，{sum(map(len, current.values()))} 行，{len(cm)} 个（字形＋双拼音码）项。",
        f"- 当前有 {same_syllable_extra} 行是同字同音码的额外编码行，不能另算一个字音项。",
        f"- 当前有 {zero_entries} 个零频字音项。",
        f"- 每字字音项数分布：`{dict(sorted(polyphones.items()))}`。",
        f"- 若把每个编码行直接求和，总权重为 {raw_frequency}；每个字音项只取一份频率时为 {one_per_syllable_frequency}，虚增 {inflation}（{inflation / one_per_syllable_frequency:.2%}）。",
        f"- 同字同音码内部频率相互矛盾：{len(conflicts)} 组。",
        "",
        "## 同字同音的频率冲突",
        "",
    ]
    for (char, sound), rows in conflicts:
        lines.append(f"- {char}/{sound}: " + "、".join(f"{code}={frequency}" for frequency, code in rows))
    lines += [
        "",
        "## 相对基线的字音变化",
        "",
        f"- 新增：{len(added)} 项：" + ("、".join(f"{c}/{s}" for c, s in added) or "无") + "。",
        f"- 删除：{len(removed)} 项：" + ("、".join(f"{c}/{s}" for c, s in removed) or "无") + "。",
        f"- 频率值变化：{len(changed)} 项。",
    ]
    for (char, sound), old, new in changed:
        lines.append(f"  - {char}/{sound}: {old} → {new}")
    lines += [
        "",
        "## 口径结论",
        "",
        "1. 排名单位应是（字形＋读音），同字不同读音不去重。",
        "2. 同字同读音的多个完整码是副码/多拆，必须共享一份频率，不得求和或重复计权。",
        "3. 基线资产只能说是现有历史频率骨架；在找到其语料来源和统计方法前，不应称为已验证的真实分读音频率。",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
