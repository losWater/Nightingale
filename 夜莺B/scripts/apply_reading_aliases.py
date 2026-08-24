# -*- coding: utf-8 -*-
"""把夜莺 B 登记的输入音别名同步到主 readings.json。"""
import json
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
rules = yaml.safe_load((BASE / "work" / "拆分规则.yaml").read_text(encoding="utf-8"))
path = ROOT / "work" / "readings.json"
readings = json.loads(path.read_text(encoding="utf-8"))
added = 0
updated = 0
for char, aliases in rules.get("reading_aliases", {}).items():
    if char not in readings:
        raise KeyError(f"读音别名字不在 readings.json: {char}")
    existing = {code[:2] for _, code in readings[char]}
    suffix = readings[char][0][1][2:]
    for alias in aliases:
        code = str(alias["code"])
        if len(code) != 2:
            raise ValueError(f"音码必须恰为两键: {char}={code}")
        if code not in existing:
            readings[char].append([int(alias.get("frequency", 0)), code + suffix])
            existing.add(code); added += 1
for char, overrides in rules.get("reading_frequency_overrides", {}).items():
    if char not in readings:
        raise KeyError(f"读音频率覆写字不在 readings.json: {char}")
    found = set()
    for reading in readings[char]:
        code = reading[1][:2]
        if code in overrides:
            frequency = int(overrides[code])
            if reading[0] != frequency:
                reading[0] = frequency; updated += 1
            found.add(code)
    missing = set(overrides) - found
    if missing:
        raise KeyError(f"读音频率覆写入口不存在: {char}={sorted(missing)}")
path.write_text(json.dumps(readings, ensure_ascii=False), encoding="utf-8")
print(f"读音别名新增 {added} 条，频率更新 {updated} 条")
