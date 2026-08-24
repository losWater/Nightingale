# -*- coding: utf-8 -*-
"""比较退火解中 Q/A/Z/P 承载的形码频率。"""
import sys
from collections import Counter
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1]
elements = yaml.safe_load((BASE / "work" / "analysis_elements.yaml").read_text(encoding="utf-8"))

for raw in sys.argv[1:]:
    path = Path(raw)
    mapping = yaml.safe_load(path.read_text(encoding="utf-8"))["form"]["mapping"]
    counts = Counter(); total = 0
    for item in elements:
        frequency = int(item.get("频率", 0))
        for slot in item["元素序列"][2:4]:
            value = mapping[str(slot["element"])]
            while isinstance(value, dict):
                value = mapping[str(value["element"])]
            counts[value] += frequency; total += frequency
    values = [counts[key] / total * 100 for key in "qazp"]
    print(f"{path.parent.name}/{path.name}\t小指合计={sum(values):.3f}%\t"
          + "\t".join(f"{key.upper()}={value:.3f}%" for key, value in zip("qazp", values)))
