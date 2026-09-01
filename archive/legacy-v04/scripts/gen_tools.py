# -*- coding: utf-8 -*-
"""生成夜莺码配套工具：
1. releases/v0.3.1/夜莺码查码.html   —— 单文件查码页（编码+候选位+首末根拆分，内嵌 ChaiPUA）
2. releases/v0.3.1/夜莺码字根练习.txt —— 配 jdeV1 字根练习器的数据文件
3. releases/v0.3.1/夜莺码字根练习器.html —— 练习器本体复制（GPL 单文件）
"""
import base64
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "releases/v0.4"
JDEV1 = Path("D:/mbpy/jdeV1")

NAMES = {"\uE0C6": "足旁", "\uE0C8": "车旁", "\uE0D0": "雨头", "\uE0D2": "青字底",
         "\uE414": "其字头", "\uF000": "禺字底", "\U00030001": "羊字身(羊半样泽共用件,羊=丷+它)", "": "学字头(学觉鲎的帽子)", "": "党字头(常党堂尝赏的帽子)", "": "官字腹(官管馆的身子)"}
STROKES = {"1": "横", "2": "竖", "3": "撇", "4": "点", "5": "折", "6": "折²"}

# ---------- 数据 ----------
cfg = yaml.safe_load(open(REL / "夜莺码v0.4键位布局.yaml", encoding="utf-8"))
mapping = {str(k): v for k, v in cfg["form"]["mapping"].items()}
attach = defaultdict(list)
mains_key = {}
for k, v in mapping.items():
    if k.startswith("szm-") or k.startswith("mzm-"):
        continue
    if isinstance(v, str):
        mains_key[k] = v
    elif isinstance(v, dict):
        attach[str(v["element"])].append(k)

NO_GLYPH = {"": "(龙下角)", "": "(止旁)", "": "(鬼无厶)", "": "(学头)", "": "(党头)", "": "(官腹)"}

def disp(r):
    if r in STROKES:
        return STROKES[r]
    if r in NO_GLYPH:
        return NO_GLYPH[r]
    return r

# 码表 → 查码反查
by_char = defaultdict(list)
by_code = defaultdict(list)
for line in open(REL / "夜莺码v0.4纯单版.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2 and len(p[0]) == 1:
        by_code[p[1]].append(p[0])
for code, chs in by_code.items():
    for i, ch in enumerate(chs, 1):
        by_char[ch].append(f"{code} {i}")

# 拆分（首末根）：v031_final 优先（含 v0.3.1 拆分补丁），扩展字回退 v03_assembled
split = {}
for line in open(BASE / "work/v04_final.tsv", encoding="utf-8").readlines() + open(BASE / "work/v03_assembled.tsv", encoding="utf-8").readlines():
    p = line.rstrip("\n").split("\t")
    if len(p) < 3 or len(p[0]) != 1 or p[0] in split:
        continue
    roots = [json.loads(t)["element"] for t in p[1].split(" ")]
    roots = [r for r in roots if not (r.startswith("szm-") or r.startswith("mzm-"))]
    if roots:
        split[p[0]] = "".join(disp(r) for r in roots)

# 一字多拆登记：备选拆法追加到拆分显示（如 重 = 千垂土 / ㇒垂土）
alt_path = BASE / "work/多拆登记.tsv"
if alt_path.exists():
    for line in open(alt_path, encoding="utf-8"):
        if line.startswith(";"):
            continue
        q = line.rstrip("\n").split("\t")
        if len(q) >= 2 and q[0] in split:
            split[q[0]] += " / " + "".join(disp(r) for r in q[1].split(" "))

# 全量扩展字（扩B+仅查码不进打字表）：追加码表外字符
ext_all = BASE / "work/扩展字集_全量.tsv"
if ext_all.exists():
    occ = {k: len(v) for k, v in by_code.items()}
    n_extra = 0
    for line in open(ext_all, encoding="utf-8"):
        q = line.rstrip().split(chr(9))
        if len(q) >= 2 and q[0] not in by_char:
            pos = occ.get(q[1], 0) + 1
            occ[q[1]] = pos
            by_char[q[0]].append(f"{q[1]} {pos}")
            n_extra += 1
    print(f"查码页额外收录扩展字 {n_extra} 条")

data = {}
for ch, codes in by_char.items():
    codes = sorted(codes, key=lambda x: (len(x.split()[0]), x))
    data[ch] = ";".join(codes) + "|" + split.get(ch, "")
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

# ChaiPUA base64（从练习器里提取现成的）
prac = open(JDEV1 / "字根练习器.html", encoding="utf-8").read()
m = re.search(r"url\(data:font/ttf;base64,([A-Za-z0-9+/=]+)\)", prac)
fontb64 = m.group(1) if m else base64.b64encode(open(BASE / "data/jdhe/ChaiPUA.ttf", "rb").read()).decode()

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>夜莺码 v0.4 查码</title>
<style>
  @font-face { font-family:'Chai Sans'; src:url(data:font/ttf;base64,__FONT__); }
  :root { --bg:#f6f7f9; --card:#fff; --text:#1a1d21; --muted:#6b7280; --accent:#7c3aed; --chip:#f3eeff; --border:#e5e7eb; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#111418; --card:#1b1f26; --text:#e8eaed; --muted:#9aa0a8; --accent:#b79aff; --chip:#2d2447; --border:#2a2f38; }
  }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; background:var(--bg); color:var(--text);
    font-family:'Chai Sans',"Segoe UI","Microsoft YaHei",sans-serif;
    display:flex; justify-content:center; padding:8vh 16px 40px; }
  .wrap { width:100%; max-width:560px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:var(--muted); font-size:13px; margin-bottom:18px; }
  input { width:100%; font-size:22px; padding:12px 16px; border:1px solid var(--border);
    border-radius:12px; background:var(--card); color:var(--text); outline:none; }
  input:focus { border-color:var(--accent); }
  .results { margin-top:18px; display:flex; flex-direction:column; gap:12px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }
  .char { font-size:34px; margin-right:12px; }
  .split { color:var(--muted); font-size:15px; margin-left:4px; }
  .split b { color:var(--accent); font-weight:600; font-size:19px; }
  .codes { margin-top:8px; display:flex; flex-wrap:wrap; gap:8px; }
  .chip { background:var(--chip); color:var(--accent); border-radius:8px; padding:4px 10px;
    font-size:17px; font-family:Consolas,monospace; }
  .chip small { color:var(--muted); margin-left:5px; }
  .empty { color:var(--muted); text-align:center; padding:30px 0; }
</style>
</head>
<body>
<div class="wrap">
  <h1>夜莺码 v0.4 查码</h1>
  <div class="sub">输入汉字（可多个）· 显示全部编码、候选位与首末根拆分 · 纯单版</div>
  <input id="q" placeholder="输入汉字…" autofocus>
  <div class="results" id="out"></div>
</div>
<script>
const DATA = __DATA__;
const q = document.getElementById('q'), out = document.getElementById('out');
function render() {
  const s = [...q.value].filter(c => /\\S/.test(c));
  out.innerHTML = '';
  if (!s.length) return;
  for (const ch of s.slice(0, 20)) {
    const card = document.createElement('div');
    card.className = 'card';
    const v = DATA[ch];
    if (!v) { card.innerHTML = `<span class="char">${ch}</span><span class="split">（不在码表中）</span>`; }
    else {
      const [codes, split] = v.split('|');
      const chips = codes.split(';').map(x => {
        const [c, r] = x.split(' ');
        return `<span class="chip">${c}<small>${r == 1 ? '首选' : '第' + r + '候选'}</small></span>`;
      }).join('');
      card.innerHTML = `<span class="char">${ch}</span>` +
        (split ? `<span class="split">拆分 <b>${split}</b></span>` : '') +
        `<div class="codes">${chips}</div>`;
    }
    out.appendChild(card);
  }
}
q.addEventListener('input', render);
</script>
</body>
</html>"""
html = html.replace("__FONT__", fontb64).replace("__DATA__", blob)
open(REL / "夜莺码查码.html", "w", encoding="utf-8").write(html)
print(f"查码页: {len(data)} 字, {len(html)//1024}KB")

# ---------- 练习器数据 ----------
rows = []
for r, key in sorted(mains_key.items(), key=lambda kv: (kv[1], kv[0])):
    name = disp(r)
    if r in STROKES:
        name = f"{STROKES[r]}(笔画)"
    if r in NAMES:
        name = r  # PUA 用字形本体（练习器内嵌 ChaiPUA 可渲染）
    hint_parts = []
    if r == "㇒":
        name = "㇒(平撇)"
        hint_parts.append("对比: 丿斜撇在x; 平撇用于丘乒兵升乎乐等字头")
    if r == "口":
        name = "口(口字)"
        hint_parts.append("对比: 囗大口框在v; 口是吃叫只中的小口")
    if r == "囗":
        name = "囗(大口框)"
        hint_parts.append("对比: 口在a; 囗是国因团围困圆的外框")
    if r in NAMES:
        hint_parts.append(NAMES[r])
    if r in attach:
        hint_parts.append("附属: " + " ".join(disp(a) for a in attach[r]))
    rows.append(f"{name}\t{key}\t{'；'.join(hint_parts)}")
open(REL / "夜莺码字根练习.txt", "w", encoding="utf-8").write("\n".join(rows))
print(f"练习数据: {len(rows)} 根")

# ---------- 练习器本体（改标题后另存） ----------
prac2 = prac.replace("简单鹤V1.0", "夜莺码v0.4").replace("简单鹤 V1.0", "夜莺码 v0.4")
open(REL / "夜莺码字根练习器.html", "w", encoding="utf-8").write(prac2)
print("练习器已复制（数据文件需在页面内导入一次）")
