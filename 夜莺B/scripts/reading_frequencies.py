#!/usr/bin/env python3
"""多音字频率的唯一聚合口径。

readings.json 的每行是 ``[频率, 编码]``。多个完整编码可能折叠到同一个
双拼音码；消费方必须累加这些行，禁止 dict 推导式的 last-wins，也禁止
用 max 悄悄低估该音码的总使用量。
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any


def validate_readings(readings: Any) -> dict[str, list[list[Any]]]:
    if not isinstance(readings, dict):
        raise ValueError("readings 必须是字到读音列表的映射")
    for char, rows in readings.items():
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError(f"readings 键必须是单字: {char!r}")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{char} 的读音列表不能为空")
        for index, row in enumerate(rows, 1):
            if not isinstance(row, list) or len(row) != 2:
                raise ValueError(f"{char} 第{index}条读音必须是[频率, 编码]")
            frequency, code = row
            if not isinstance(frequency, int) or frequency < 0:
                raise ValueError(f"{char} 第{index}条频率必须是非负整数")
            if not isinstance(code, str) or len(code) < 2:
                raise ValueError(f"{char} 第{index}条编码必须至少含两个字符")
    return readings


def aggregate_syllable_frequencies(readings: Any) -> dict[tuple[str, str], int]:
    """按 ``(字, 双拼音码)`` 累加所有读音行的频率。"""
    validated = validate_readings(readings)
    result: defaultdict[tuple[str, str], int] = defaultdict(int)
    for char, rows in validated.items():
        for frequency, code in rows:
            result[(char, code[:2])] += frequency
    return dict(result)


def normalize_reading_order(readings: Any) -> dict[str, list[list[Any]]]:
    """返回新对象；每字按频率稳定降序，首条即主读音。"""
    validated = validate_readings(readings)
    return {
        char: sorted(([frequency, code] for frequency, code in rows), key=lambda row: -row[0])
        for char, rows in validated.items()
    }


def assert_reading_order(readings: Any) -> None:
    validated = validate_readings(readings)
    for char, rows in validated.items():
        for index in range(1, len(rows)):
            if rows[index - 1][0] < rows[index][0]:
                raise ValueError(
                    f"{char} 的读音未按频率降序: 第{index}条{rows[index - 1][0]} < "
                    f"第{index + 1}条{rows[index][0]}"
                )


def primary_readings(readings: Any) -> tuple[dict[str, int], dict[str, str]]:
    assert_reading_order(readings)
    return (
        {char: rows[0][0] for char, rows in readings.items()},
        {char: rows[0][1] for char, rows in readings.items()},
    )


def load_readings(path: str | Path) -> dict[str, list[list[Any]]]:
    readings = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_reading_order(readings)
    return readings
