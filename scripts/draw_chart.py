# -*- coding: utf-8 -*-
"""夜莺码字根图渲染器：键盘三排布局，大字主根（红=笔画根），灰小字=附属形。
数据源: releases/v0.4/夜莺码v0.4键位布局.yaml form.mapping
输出:  releases/v0.4/夜莺码v0.4字根图.png"""
import io
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont, TTCollection

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

MSYH = "C:/Windows/Fonts/msyh.ttc"
SIMSUNB = "C:/Windows/Fonts/simsunb.ttf"
EXTG = "C:/Windows/Fonts/SimsunExtG.ttf"
CHAIPUA = str(BASE / "data/jdhe/ChaiPUA.ttf")

def best_cmap(path):
    f = TTCollection(path).fonts[0] if path.endswith(".ttc") else TTFont(path)
    return set(f.getBestCmap())

CMAPS = [(MSYH, best_cmap(MSYH)), (SIMSUNB, best_cmap(SIMSUNB)), (EXTG, best_cmap(EXTG)), (CHAIPUA, best_cmap(CHAIPUA))]
FCACHE = {}
def font_for(ch, size):
    cp = ord(ch)
    for path, cm in CMAPS:
        if cp in cm:
            key = (path, size)
            if key not in FCACHE:
                FCACHE[key] = ImageFont.truetype(path, size)
            return FCACHE[key]
    return None  # 需文字标签兜底

LABELS = {"\U00030001": "养头", "": "学头", "": "党头", "": "官腹"}
STROKES = {"1": "横", "2": "竖", "3": "撇", "4": "点", "5": "折"}

cfg = yaml.safe_load(open(BASE / "releases/v0.4/夜莺码v0.4键位布局.yaml", encoding="utf-8"))
mapping = cfg["form"]["mapping"]
key_mains = {}   # key -> [主根...]
attach = {}      # 宿主 -> [附属...]
for k, v in mapping.items():
    k = str(k)
    if k.startswith("szm-") or k.startswith("mzm-"):
        continue
    if isinstance(v, str):
        key_mains.setdefault(v, []).append(k)
    elif isinstance(v, dict):
        attach.setdefault(str(v["element"]), []).append(k)

ROWS = [list("qwertyuiop"), list("asdfghjkl"), list("zxcvbnm")]
CELL_W, GAP = 264, 14
ROW_OFF = [0, 60, 150]

MAIN_SIZE, ATT_SIZE, LABEL_SIZE = 40, 24, 20
LINE_H = MAIN_SIZE + 18

def measure_lines(key):
    cx = 0
    lines = 1
    for m in key_mains.get(key, []):
        group_w = MAIN_SIZE + 10 + (ATT_SIZE + 4) * len(attach.get(m, []))
        if cx + group_w > CELL_W - 30:
            cx = 0
            lines += 1
        cx += group_w + 8
    return lines

ROW_H = []
for row in ROWS:
    ml = max(measure_lines(k) for k in row)
    ROW_H.append(76 + ml * LINE_H + 14)
W = 10 * (CELL_W + GAP) + 80
H = 150 + sum(h + GAP for h in ROW_H) + 90
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

title_f = ImageFont.truetype(MSYH, 52)
sub_f = ImageFont.truetype(MSYH, 24)
key_f = ImageFont.truetype(MSYH, 40)
d.text((W // 2, 40), "夜莺码 v0.4 字根图·字根定稿", font=title_f, fill="black", anchor="mm")
d.text((W // 2, 92), f"{sum(len(v) for v in key_mains.values())} 主根（红＝笔画根）· 灰小字＝并入该根的附属形 · 音码＝小鹤双拼（未画）· 字根决不落 P 键", font=sub_f, fill="#777", anchor="mm")

def draw_glyph(x, y, ch, size, color):
    """画一个根，返回占用宽度"""
    disp = STROKES.get(ch, ch)
    f = font_for(disp, size)
    if f is None or ch in LABELS:
        lab = LABELS.get(ch, disp)
        lf = ImageFont.truetype(MSYH, LABEL_SIZE if size > 30 else LABEL_SIZE - 4)
        w = d.textlength(lab, font=lf)
        d.rectangle([x, y + 6, x + w + 8, y + size], outline="#bbb")
        d.text((x + 4, y + (size - LABEL_SIZE) // 2), lab, font=lf, fill=color)
        return w + 14
    d.text((x, y), disp, font=f, fill=color)
    return d.textlength(disp, font=f) + 8

y0 = 140
yy = y0
for r, row in enumerate(ROWS):
    for i, key in enumerate(row):
        x0 = 40 + ROW_OFF[r] + i * (CELL_W + GAP)
        d.rounded_rectangle([x0, yy, x0 + CELL_W, yy + ROW_H[r]], radius=16, outline="#666", width=3)
        d.text((x0 + 18, yy + 8), key.upper(), font=key_f, fill="black")
        cx, cy = x0 + 16, yy + 66
        line_h = LINE_H
        for m in key_mains.get(key, []):
            is_stroke = m in STROKES
            color = "#c00" if is_stroke else "black"
            # 预算宽度: 主根 + 附属
            group_w = MAIN_SIZE + 10 + (ATT_SIZE + 4) * len(attach.get(m, []))
            if cx + group_w > x0 + CELL_W - 12:
                cx = x0 + 16
                cy += line_h
            cx += draw_glyph(cx, cy, m, MAIN_SIZE, color)
            for a in attach.get(m, []):
                disp_a = "折²" if a == "6" else a
                if disp_a == "折²":
                    lf = ImageFont.truetype(MSYH, ATT_SIZE)
                    d.text((cx, cy + MAIN_SIZE - ATT_SIZE), disp_a, font=lf, fill="#aaa")
                    cx += d.textlength(disp_a, font=lf) + 6
                else:
                    cx += draw_glyph(cx, cy + MAIN_SIZE - ATT_SIZE - 2, a, ATT_SIZE, "#aaa")
            cx += 8
    yy += ROW_H[r] + GAP

d.text((40, H - 46), "生成: nightingale pipeline · 布局: 字词混合退火(200万步×6链) · 数据: 夜莺码v0.4键位布局.yaml", font=sub_f, fill="#999")
out = BASE / "releases/v0.4/夜莺码v0.4字根图.png"
img.save(out)
print(f"已输出 {out} ({W}x{H})")
# 自检: 每键主根数
for r in ROWS:
    print(" ".join(f"{k}:{len(key_mains.get(k,[]))}" for k in r))
