# -*- coding: utf-8 -*-
"""按键手感指标（数据源：形码盒子 yb6b/schema-box，GPL-2.0）。

当量表：46键（字母/数字/常用标点/空格）两两组合的击键当量；
布局：按标准指法推手指与键盘行。提供对任意按键流的统计：
加权当量、同键连击率、同指异键率、同指小/大跨排率、左右互击率、
左右手与各指负担分布。
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

_EQ: dict[str, float] = {}
for _line in (Path(__file__).resolve().parent.parent /
              "data/reference/当量表_形码盒子.tsv").read_text(encoding="utf-8").splitlines():
    if _line.startswith("#") or "\t" not in _line:
        continue
    _k, _v = _line.split("\t")
    if len(_k) == 2:
        _EQ[_k] = float(_v)

# 手指编号：1-5左(小无中食拇) 6-10右(拇食中无小)，空格=拇指
_COLS = {
    1: "1qaz", 2: "2wsx", 3: "3edc", 4: "4rfv5tgb",
    7: "6yhn7ujm", 8: "8ik,", 9: "9ol.", 10: "0p;/-['=]",
}
FINGER: dict[str, int] = {" ": 5}
for _f, _ks in _COLS.items():
    for _k in _ks:
        FINGER[_k] = _f
_ROWS = ["1234567890-=", "qwertyuiop[]", "asdfghjkl;'", "zxcv bnm,./"]
ROW: dict[str, int] = {" ": 4}
for _r, _ks in enumerate(_ROWS):
    for _k in _ks:
        if _k != " ":
            ROW[_k] = _r
_LEFT = set("12345qwertasdfgzxcvb")


def analyze(keyseq: str) -> dict:
    """对按键流（含空格/选重键）计算手感指标。"""
    n_pairs = 0
    eq_sum = 0.0
    dc = same_finger = ss = ms = dh = 0
    finger_load: Counter = Counter()
    for ch in keyseq:
        finger_load[FINGER.get(ch, 0)] += 1
    for a, b in zip(keyseq, keyseq[1:]):
        pair = a + b
        if pair not in _EQ:
            continue
        n_pairs += 1
        eq_sum += _EQ[pair]
        fa, fb = FINGER.get(a), FINGER.get(b)
        if a == b:
            dc += 1
        elif fa == fb and fa not in (5, 6):
            same_finger += 1
            dist = abs(ROW.get(a, 4) - ROW.get(b, 4))
            if dist == 1:
                ss += 1
            elif dist >= 2:
                ms += 1
        if (a in _LEFT) != (b in _LEFT) and a != " " and b != " ":
            dh += 1
    total_keys = len(keyseq)
    left = sum(v for f, v in finger_load.items() if 1 <= f <= 5)
    right = sum(v for f, v in finger_load.items() if 6 <= f <= 10)
    return {
        "键数": total_keys,
        "加权当量": eq_sum / n_pairs if n_pairs else 0,
        "同键连击率": dc / n_pairs if n_pairs else 0,
        "同指异键率": same_finger / n_pairs if n_pairs else 0,
        "同指小跨排率": ss / n_pairs if n_pairs else 0,
        "同指大跨排率": ms / n_pairs if n_pairs else 0,
        "左右互击率": dh / n_pairs if n_pairs else 0,
        "左手负担": left / (left + right) if (left + right) else 0,
        "小指负担": (finger_load[1] + finger_load[10]) / total_keys if total_keys else 0,
    }
