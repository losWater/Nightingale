# -*- coding: utf-8 -*-
"""Audit historical reading/frequency and 8455 element assets without mutation."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
READINGS = ROOT / "work" / "readings.json"
ELEMENTS = ROOT / "夜莺B" / "work" / "analysis_elements.yaml"
CONFIG = ROOT / "夜莺B" / "work" / "analysis_config.yaml"
CURRENT_8105 = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
OUT = PROJECT / "03_字音频率"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    readings = json.loads(READINGS.read_text(encoding="utf-8"))
    elements = yaml.safe_load(ELEMENTS.read_text(encoding="utf-8"))
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    mapping = config["form"]["mapping"]
    with CURRENT_8105.open("r", encoding="utf-8-sig", newline="") as f:
        current_chars = {x["汉字"] for x in csv.DictReader(f, delimiter="\t")}

    reading_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    reading_count_by_char: Counter[str] = Counter()
    raw_rows = 0
    for char, rows in readings.items():
        raw_rows += len(rows)
        sounds = set()
        for frequency, code in rows:
            key = str(code)[:2]
            sounds.add(key)
            reading_groups[(char, key)].append({"frequency": int(frequency), "code": str(code)})
        reading_count_by_char[char] = len(sounds)

    element_sound_groups: dict[tuple[str, tuple[str, str]], list[dict]] = defaultdict(list)
    element_key_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    element_count_by_char: Counter[str] = Counter()
    for index, item in enumerate(elements):
        char = str(item["词"])
        sound = tuple(str(x["element"]) for x in item["元素序列"][:2])
        if len(sound) != 2:
            raise ValueError(f"element row lacks two sound slots: {index} {char}")
        try:
            key = "".join(str(mapping[x]) for x in sound)
        except KeyError as exc:
            raise ValueError(f"unmapped sound element in row {index}: {sound}") from exc
        row = {"index": index, "sound": list(sound), "frequency": int(item.get("频率", 0))}
        element_sound_groups[(char, sound)].append(row)
        element_key_groups[(char, key)].append(row)
    for char, _ in element_sound_groups:
        element_count_by_char[char] += 1

    anomalies = []
    chars = sorted(set(readings) | {str(x["词"]) for x in elements})
    for char in chars:
        if reading_count_by_char[char] != element_count_by_char[char]:
            anomalies.append({
                "类型": "每字项目数不一致", "汉字": char, "双拼音码": "",
                "readings详情": str(reading_count_by_char[char]),
                "elements详情": str(element_count_by_char[char]),
            })
    for (char, key), rows in sorted(reading_groups.items()):
        freqs = sorted({x["frequency"] for x in rows})
        if len(rows) > 1:
            anomalies.append({
                "类型": "readings同字同音码多行" if len(freqs) == 1 else "readings同字同音码频率冲突",
                "汉字": char, "双拼音码": key,
                "readings详情": json.dumps(rows, ensure_ascii=False), "elements详情": "",
            })
    for (char, key), rows in sorted(element_key_groups.items()):
        sounds = {tuple(x["sound"]) for x in rows}
        if len(sounds) > 1:
            anomalies.append({
                "类型": "元素不同声韵映射同一双拼键", "汉字": char, "双拼音码": key,
                "readings详情": "", "elements详情": json.dumps(rows, ensure_ascii=False),
            })
        reading_freqs = {x["frequency"] for x in reading_groups.get((char, key), [])}
        element_freqs = {x["frequency"] for x in rows}
        if not reading_freqs or not element_freqs.issubset(reading_freqs):
            anomalies.append({
                "类型": "元素频率无法由同键readings解释", "汉字": char, "双拼音码": key,
                "readings详情": json.dumps(sorted(reading_freqs), ensure_ascii=False),
                "elements详情": json.dumps(rows, ensure_ascii=False),
            })

    readings_chars = set(readings)
    element_chars = {str(x["词"]) for x in elements}
    counts = {
        "readings_glyphs": len(readings_chars),
        "readings_raw_rows": raw_rows,
        "readings_char_double_key_items": len(reading_groups),
        "element_rows": len(elements),
        "element_char_sound_items": len(element_sound_groups),
        "element_char_double_key_items": len(element_key_groups),
        "same_syllable_extra_reading_rows": raw_rows - len(reading_groups),
        "reading_zero_key_items": sum(all(x["frequency"] == 0 for x in rows) for rows in reading_groups.values()),
        "element_zero_rows": sum(int(x.get("频率", 0)) == 0 for x in elements),
        "per_char_item_count_mismatches": sum(reading_count_by_char[c] != element_count_by_char[c] for c in chars),
        "anomaly_rows": len(anomalies),
    }
    payload = {
        "status": "read_only_unverified_frequency_provenance",
        "counts": counts,
        "glyph_sets": {
            "readings_equals_current_8105": readings_chars == current_chars,
            "elements_equals_current_8105": element_chars == current_chars,
            "readings_minus_current": sorted(readings_chars - current_chars),
            "current_minus_readings": sorted(current_chars - readings_chars),
            "elements_minus_current": sorted(element_chars - current_chars),
            "current_minus_elements": sorted(current_chars - element_chars),
        },
        "per_glyph_reading_item_distribution": dict(sorted(Counter(reading_count_by_char.values()).items())),
        "inputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [READINGS, ELEMENTS, CONFIG, CURRENT_8105, Path(__file__)]},
        "provenance_conclusion": "Git可追溯到v0.4初始入库及后续人工修改，但当前资产内未发现语料名称、版本、统计脚本与原始生成清单；分读音频率来源未证实。",
    }
    json_path = OUT / "历史字音退火资产审计.json"
    tsv_path = OUT / "历史字音退火资产异常.tsv"
    md_path = OUT / "历史字音退火资产审计.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["类型", "汉字", "双拼音码", "readings详情", "elements详情"]
    with tsv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(anomalies)
    focus = [x for x in anomalies if x["汉字"] in {"咯", "哼", "谁"}]
    lines = [
        "# 历史字音退火资产审计", "", "- 状态：只读；频率来源未证实。",
        *[f"- {k}: {v}" for k, v in counts.items()], "", "## 三个项目数不一致字", "",
        *[f"- {x['汉字']} `{x['双拼音码']}` {x['类型']}：readings={x['readings详情']}；elements={x['elements详情']}" for x in focus],
        "", "## 来源结论", "", f"- {payload['provenance_conclusion']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"counts": counts, "glyph_sets": payload["glyph_sets"], "focus": focus}, ensure_ascii=False))


if __name__ == "__main__":
    main()
