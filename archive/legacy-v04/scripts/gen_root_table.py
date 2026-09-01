# -*- coding: utf-8 -*-
"""夜莺码字根总表生成器: 键位布局.yaml -> 字根总表.md（PUA 部件附示例字）"""
import io, re, sys
from collections import defaultdict
from pathlib import Path
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "releases/v0.4"

cfg = yaml.safe_load(open(REL / "夜莺码v0.4键位布局.yaml", encoding="utf-8"))
mains = defaultdict(list); attach = defaultdict(list)
for k, v in cfg["form"]["mapping"].items():
    k = str(k)
    if k.startswith(("szm-", "mzm-")):
        continue
    if isinstance(v, str):
        mains[v].append(k)
    elif isinstance(v, dict):
        attach[str(v["element"])].append(k)

ex = defaultdict(list); cur = None
for line in open(BASE / "work/optimize/elements_v04.yaml", encoding="utf-8"):
    s = line.strip()
    m = re.match(r"- 词: (.+)$", s)
    if m:
        cur = m.group(1); continue
    m = re.match(r"- element: '?(.+?)'?$", s)
    if m and cur:
        el = m.group(1)
        if len(el) == 1 and 0xE000 <= ord(el) <= 0xF8FF and len(ex[el]) < 3 and cur not in ex[el]:
            ex[el].append(cur)

STROKES = {"1": "横1", "2": "竖2", "3": "撇3", "4": "点4", "5": "折5"}
LABELS = {"𰀁": "养字头"}
def disp(c):
    if c in STROKES: return STROKES[c]
    if c == "6": return "折²"
    if c in LABELS: return LABELS[c]
    if len(c) == 1 and 0xE000 <= ord(c) <= 0xF8FF:
        s = "".join(ex.get(c, []))
        return f"□({s}中部件)" if s else "□"
    return c

n_m = sum(len(v) for v in mains.values()); n_a = sum(len(v) for v in attach.values())
out = [f"# 夜莺码 v0.4 字根总表（字根定稿）", "",
       f"**{n_m} 主根 + {n_a} 附属形**（括注＝挂靠在该主根下的附属形；□＝PUA 变体部件，括注示例字）", "",
       "音码＝小鹤双拼 · 字根决不落 P 键 · 数据源: 夜莺码v0.4键位布局.yaml", "",
       "| 键 | 主根（附属形） |", "|----|----------------|"]
for row in ["qwertyuiop", "asdfghjkl", "zxcvbnm"]:
    for key in row:
        if key not in mains:
            out.append(f"| {key.upper()} | —（无形根） |"); continue
        parts = []
        for mr in mains[key]:
            a = attach.get(mr, [])
            s = disp(mr)
            if a: s += "(" + "、".join(disp(x) for x in a) + ")"
            parts.append(s)
        out.append(f"| {key.upper()} | " + " ".join(parts) + " |")
out += ["", "## 易混框对照", "",
        "- **冂（H）**：同冈网冉再肉冏…；附属形含 门 与丹周框（丹周彤凋等的 ⺆ 形框全部归此，打 H）",
        "- **册（J）**：册删姗…；附属形含扁字框（扁匾嗣等）",
        "- **月（Y）**：月字旁/月字底（俞佾等变体亦归 月）",
        "- **干（H）**：附属 千、于——干千于一家，于族（宇芋盂迂等）末根全打 H",
        "- **口（A）vs 囗（V）**：口是吃叫只中的小口，打 A；囗是国因团围困圆的外框，打 V",
        "- v0.2 及以前 j 键上的独立根 ⺆ 已移除（幽灵根，无字使用）", ""]
open(REL / "夜莺码v0.4字根总表.md", "w", encoding="utf-8", newline="\n").write("\n".join(out))
print(f"{n_m} 主根 + {n_a} 附属形 -> 字根总表.md")
