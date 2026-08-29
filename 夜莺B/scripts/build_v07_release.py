# -*- coding: utf-8 -*-
"""从夜莺B线程0定稿解生成夜莺0.7首批发布物。"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTCollection, TTFont
from short_code_overrides import apply_candidate_order, apply_overrides


HERE = Path(__file__).resolve().parent
BROOT = HERE.parent
BASE = BROOT.parent
DEFAULT_RUN = (BROOT / "work/final_protection_runs/"
               "hard_1500x15000_3500x5000_novel5000_20260825_074509/"
               "output-08-25+07_45_25/0")
STROKE_LABELS = {"1": "横", "2": "竖", "3": "撇", "4": "点", "5": "折"}
STROKE_NAMES = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}
ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def load_resolver():
    repertoire = json.loads(zlib.decompress(
        (BASE / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes()))
    by_name = {r.get("name"): chr(r["unicode"]) for r in repertoire
               if r.get("name") and r.get("unicode")}
    by_char = {chr(r["unicode"]): r for r in repertoire if r.get("unicode")}
    rules = yaml.safe_load((BROOT / "work/拆分规则.yaml").read_text(encoding="utf-8"))
    custom = {str(k): str(v) for k, v in rules.get("custom_elements", {}).items()}

    def resolve(value):
        text = STROKE_NAMES.get(str(value), str(value))
        return custom.get(text, by_name.get(text, text))

    custom_back = {v: k for k, v in custom.items()}

    def label(value):
        value = str(value)
        if value in STROKE_LABELS:
            return STROKE_LABELS[value]
        if value in custom_back:
            return custom_back[value]
        row = by_char.get(value)
        return str(row.get("name")) if row and row.get("name") else value

    return resolve, label


def trace_key(mapping, element):
    current, seen = str(element), set()
    while current not in seen:
        seen.add(current)
        value = mapping.get(current)
        if isinstance(value, str):
            return value
        if isinstance(value, dict) and value.get("element") is not None:
            current = str(value["element"])
            continue
        return None
    return None


def load_quick_symbols():
    result = defaultdict(list)
    path = BROOT / "work/快符.txt"
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        left, phrase = line.split("=", 1)
        code, position = left.rsplit(",", 1)
        result[code].append((int(position), phrase))
    return result


def insert_positioned(entries, additions):
    """按1基候选位插入，不覆盖已有候选，其余候选顺延。"""
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry[0]].append(entry[4])
    for code, rows in additions.items():
        for position, phrase in sorted(rows):
            if phrase in grouped[code]:
                continue
            target = max(0, min(position - 1, len(grouped[code])))
            grouped[code].insert(target, phrase)
    return [(code, phrase) for code in sorted(grouped) for phrase in grouped[code]]


def load_root_char_secondaries(rows):
    """为未出简的字根字生成 abx 二选；abxx 标准主码继续保留。"""
    manual = yaml.safe_load((BROOT / "work/简码资产.yaml").read_text(encoding="utf-8"))
    if not manual.get("root_char_three_secondary", False):
        return defaultdict(list)
    root_cfg = yaml.safe_load((BROOT / "work/根集.yaml").read_text(encoding="utf-8"))
    roots = set()
    for host, children in (root_cfg.get("roots") or {}).items():
        roots.add(str(host))
        roots.update(str(child) for child in (children or []))
    for host, children in (root_cfg.get("anchors") or {}).items():
        roots.add(str(host))
        roots.update(str(child) for child in (children or []))
    # 只有能作为独立汉字出现在码表中的单字符根才属于“字根字”。
    roots = {root for root in roots if len(root) == 1}
    additions = defaultdict(list)
    seen = set()
    for row in rows:
        char, full, short = row[0], row[1], row[3]
        if (
            char in roots
            and len(full) == 4
            and full[2] == full[3]
            and short == full
            and (full[:3], char) not in seen
        ):
            additions[full[:3]].append((2, char))
            seen.add((full[:3], char))
    return additions


def load_word_yield_three_secondaries(rows, manual):
    """为人工让出四码词位的单字补 abx 三码二选。"""
    wanted = {
        str(full): str(char)
        for full, char in (manual.get("word_yield_three_secondaries") or {}).items()
    }
    additions = defaultdict(list)
    found = set()
    for row in rows:
        char, full = str(row[0]), str(row[1])
        if wanted.get(full) == char and len(full) == 4:
            additions[full[:3]].append((2, char))
            found.add(full)
    missing = set(wanted) - found
    if missing:
        raise ValueError("词位让出补偿码未在四码表中找到：" + " ".join(sorted(missing)))
    return additions


def load_default_word_first_codes(rows, elements, manual):
    """找出低频单字应默认让给前排词组的四码位。"""
    policy = manual.get("default_word_first") or {}
    if not policy:
        return set()
    rank_from = int(policy["character_rank_from"])
    two_word_rank_top = int(policy["two_word_rank_top"])

    # 同一码若还存在阈值以内的常用字，不能被低频同码字连带拖后。
    code_min_rank = {}
    for item, row in zip(elements, rows):
        rank = int(item.get("排序序号", 10**12)) + 1
        code = str(row[1])
        code_min_rank[code] = min(rank, code_min_rank.get(code, rank))

    word_codes = set()
    path = BROOT / "work/lexicon/目标词库_四码位.tsv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            two_rank = int(row["two_top_rank"]) if row.get("two_top_rank") else None
            if two_rank is not None and two_rank <= two_word_rank_top:
                word_codes.add(str(row["code"]))
    return {
        code for code, rank in code_min_rank.items()
        if rank >= rank_from and code in word_codes
    }


def build_layout(solution_path, release):
    source = yaml.safe_load(solution_path.read_text(encoding="utf-8"))
    release_form = dict(source["form"])
    # Full optimizer configs carry the 170-root decision space.  A release
    # layout needs only the resolved mapping, not every candidate key.
    release_form.pop("mapping_space", None)
    layout = {
        "version": "0.7",
        "source": "夜莺B 0.7正式布局",
        "info": {
            "name": "夜莺码0.7",
            "author": "nightingale",
            "description": "小鹤双拼音码＋首末字根形码；夜莺B人工选根与终局退火线程0",
        },
        "form": release_form,
    }
    path = release / "夜莺码v0.7键位布局.yaml"
    path.write_text(yaml.safe_dump(layout, allow_unicode=True, sort_keys=False, width=10000),
                    encoding="utf-8")
    return layout


def build_table(code_path, elements_path, release):
    elements = yaml.safe_load(elements_path.read_text(encoding="utf-8"))
    rows = [line.split("\t") for line in code_path.read_text(encoding="utf-8").splitlines()]
    apply_overrides(rows)
    if len(elements) != len(rows):
        raise ValueError(f"code/elements 行数不一致：{len(rows)} != {len(elements)}")
    entries = []
    for serial, (item, row) in enumerate(zip(elements, rows)):
        char, full, short = row[0], row[1], row[3]
        if char != str(item["词"]):
            raise ValueError(f"code/elements 错位：{char} != {item['词']}")
        freq = int(item.get("频率", 0))
        if short != full:
            entries.append((short, 0, -freq, serial, char))
            entries.append((full, 1, -freq, serial, char))
        else:
            entries.append((full, 0, -freq, serial, char))
    manual = yaml.safe_load((BROOT / "work/简码资产.yaml").read_text(encoding="utf-8"))
    char_frequency = defaultdict(int)
    for item in elements:
        char_frequency[str(item["词"])] = max(char_frequency[str(item["词"])],
                                               int(item.get("频率", 0)))
    for code, char in manual.get("extra_codes", {}).items():
        entries.append((str(code), 0, -char_frequency[str(char)], len(entries), str(char)))
    # 同字同码去重；同码内：无简码字/简码优先，出简出全的全码后置。
    unique, seen = [], set()
    for entry in sorted(entries):
        ident = (entry[0], entry[4])
        if ident not in seen:
            seen.add(ident)
            unique.append(entry)
    unique = apply_candidate_order(unique)
    additions = load_quick_symbols()
    for code, positioned in load_root_char_secondaries(rows).items():
        additions[code].extend(positioned)
    for code, positioned in load_word_yield_three_secondaries(rows, manual).items():
        additions[code].extend(positioned)
    no_yield_rows = insert_positioned(unique, additions)
    no_yield_path = release / "夜莺码v0.7纯单版_不让位.txt"
    no_yield_path.write_text(
        "".join(f"{phrase}\t{code}\n" for code, phrase in no_yield_rows),
        encoding="utf-8", newline="\n"
    )
    plain_placeholders = {
        str(code): str(phrase)
        for code, phrase in (manual.get("plain_table_placeholders") or {}).items()
    }
    automatic_word_first = load_default_word_first_codes(rows, elements, manual)
    for code in automatic_word_first:
        plain_placeholders.setdefault(code, "①")
    for code, phrase in plain_placeholders.items():
        additions[code].append((1, phrase))
    pure_rows = insert_positioned(unique, additions)
    path = release / "夜莺码v0.7纯单版.txt"
    path.write_text("".join(f"{phrase}\t{code}\n" for code, phrase in pure_rows),
                    encoding="utf-8", newline="\n")
    sogou = release / "夜莺码v0.7纯单版搜狗短语.txt"
    quick_rows = load_quick_symbols()
    symbol_count = sum(len(rows) for code, rows in quick_rows.items() if len(code) == 1)
    shortcut_count = sum(len(rows) for code, rows in quick_rows.items() if len(code) > 1)
    lines = ["; 夜莺码 v0.7 纯单版 · 搜狗自定义短语挂接",
             f"; 小鹤双拼 + 首末字根 · 含{symbol_count}条一简次选快符及{shortcut_count}条快捷短语", ""]
    by_code = defaultdict(list)
    for code, phrase in pure_rows:
        # 普通纯单表靠可见符号占位；带序号的搜狗表直接使用候选序号，不收占位符。
        if plain_placeholders.get(code) == phrase:
            continue
        by_code[code].append(phrase)
    sogou_offsets = {
        str(code): int(offset)
        for code, offset in (manual.get("sogou_candidate_offsets") or {}).items()
    }
    for code in automatic_word_first:
        sogou_offsets[code] = max(1, sogou_offsets.get(code, 0))
    for code in sorted(by_code):
        offset = sogou_offsets.get(code, 0)
        lines.extend(f"{code},{position + offset}={phrase}"
                     for position, phrase in enumerate(by_code[code], 1))
    sogou.write_text("\r\n".join(lines) + "\r\n", encoding="utf-16", newline="")

    # 无简词综合版：收入精选六万二字词，但不加入简拼词。每个已裁决让位码
    # 最多只允许排名最高的一条词置于单字之前，其余同码词仍排在单字之后。
    words_by_code = defaultdict(list)
    lexicon_path = BROOT / "work/lexicon/二字词_精选60000.tsv"
    with lexicon_path.open(encoding="utf-8-sig", newline="") as handle:
        for rank, word_row in enumerate(csv.DictReader(handle, delimiter="\t"), 1):
            words_by_code[str(word_row["code"])].append((rank, str(word_row["word"])))
    chars_by_code = defaultdict(list)
    for code, phrase in no_yield_rows:
        chars_by_code[code].append(phrase)
    word_first_codes = set(sogou_offsets) | automatic_word_first
    word_first_overrides = {
        str(code): str(word)
        for code, word in (manual.get("word_first_overrides") or {}).items()
    }
    mixed_rows = []
    for code in sorted(set(chars_by_code) | set(words_by_code)):
        chars = chars_by_code.get(code, [])
        words = [word for _, word in words_by_code.get(code, [])]
        if code in word_first_codes and words:
            preferred = word_first_overrides.get(code)
            if preferred is not None:
                if preferred not in words:
                    raise ValueError(f"指定首选词不在精选二字词表：{code}={preferred}")
                words = [preferred] + [word for word in words if word != preferred]
            phrases = words[:1] + chars + words[1:]
        else:
            phrases = chars + words
        seen_phrases = set()
        for phrase in phrases:
            if phrase not in seen_phrases:
                seen_phrases.add(phrase)
                mixed_rows.append((code, phrase))
    mixed_path = release / "夜莺码v0.7字词版_无简词.txt"
    mixed_path.write_text(
        "".join(f"{phrase}\t{code}\n" for code, phrase in mixed_rows),
        encoding="utf-8", newline="\n"
    )
    return path, no_yield_path, mixed_path, unique, elements, rows


def root_catalog(layout, resolve):
    roots = yaml.safe_load((BROOT / "work/根集.yaml").read_text(encoding="utf-8"))
    mapping = {str(k): v for k, v in layout["form"]["mapping"].items()}
    mains, subsidiaries, anchors = defaultdict(list), defaultdict(list), defaultdict(list)
    for root, attached in roots["roots"].items():
        host = resolve(root)
        key = trace_key(mapping, host)
        if key:
            mains[key].append((str(root), host))
        for child in attached:
            subsidiaries[str(root)].append(str(child))
    for host, children in roots.get("anchors", {}).items():
        for child in children:
            anchors[str(host)].append(str(child))
    return mains, subsidiaries, anchors


def font_sources():
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simsunb.ttf"),
        Path("C:/Windows/Fonts/SimsunExtG.ttf"), BASE / "data/jdhe/ChaiPUA.ttf",
    ]
    result = []
    for path in candidates:
        if not path.exists():
            continue
        font = TTCollection(str(path)).fonts[0] if path.suffix.lower() == ".ttc" else TTFont(str(path))
        result.append((str(path), set(font.getBestCmap())))
    return result


def build_chart(layout, release, resolve, label):
    mains, subsidiaries, anchors = root_catalog(layout, resolve)
    sources, cache = font_sources(), {}

    def get_font(text, size):
        cp = ord(text[0]) if text else 0
        path = next((p for p, cmap in sources if cp in cmap), "C:/Windows/Fonts/msyh.ttc")
        cache.setdefault((path, size), ImageFont.truetype(path, size))
        return cache[(path, size)]

    cell_w, gap, row_offsets = 310, 14, (0, 70, 166)
    main_size, sub_size = 34, 18
    probe = Image.new("RGB", (10, 10), "white")
    probe_draw = ImageDraw.Draw(probe)

    def shown(text):
        return label(resolve(text)) if text not in STROKE_NAMES else text

    def text_width(text, size):
        font = get_font(text, size)
        return probe_draw.textlength(text, font=font)

    def group_layout(root):
        """返回主根及自动换行后的附属 token；每个主根独占一组。"""
        root_text = shown(root)
        main_width = text_width(root_text, main_size) + 9
        tokens = [(shown(x), "#999") for x in subsidiaries.get(root, [])]
        tokens += [(shown(x), "#3973ac") for x in anchors.get(root, [])]
        lines, current, used = [], [], main_width
        for text, color in tokens:
            width = text_width(text, sub_size) + 8
            if current and used + width > cell_w - 28:
                lines.append(current); current, used = [], 15
            current.append((text, color)); used += width
        if current or not lines:
            lines.append(current)
        height = max(45, 38 + (len(lines) - 1) * 23)
        return root_text, main_width, lines, height

    layouts = {key: [(root, group_layout(root)) for root, _ in mains.get(key, [])]
               for row in ROWS for key in row}
    def content_height(key):
        return sum(group[3] + 5 for _, group in layouts[key])
    row_heights = [82 + max(content_height(k) for k in row) for row in ROWS]
    width = 10 * (cell_w + gap) + 92
    height = 160 + sum(h + gap for h in row_heights) + 78
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 52)
    sub_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 23)
    key_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 38)
    draw.text((width // 2, 40), "夜莺码 v0.7 字根图", font=title_font, fill="black", anchor="mm")
    draw.text((width // 2, 93), "黑色＝主根　灰色＝附属形　蓝色＝锚定根　红色＝五大笔画根　音码＝小鹤双拼",
              font=sub_font, fill="#666", anchor="mm")

    yy = 138
    for row_index, row in enumerate(ROWS):
        for index, key in enumerate(row):
            x0 = 42 + row_offsets[row_index] + index * (cell_w + gap)
            draw.rounded_rectangle((x0, yy, x0 + cell_w, yy + row_heights[row_index]),
                                   radius=15, outline="#666", width=3)
            draw.text((x0 + 17, yy + 8), key.upper(), font=key_font, fill="black")
            cy = yy + 61
            for root, (root_text, main_width, extra_lines, group_height) in layouts[key]:
                main_font = get_font(root_text, main_size)
                draw.text((x0 + 15, cy), root_text, font=main_font,
                          fill="#c00000" if root in STROKE_NAMES else "#111")
                for line_index, tokens in enumerate(extra_lines):
                    cx = x0 + 15 + (main_width if line_index == 0 else 0)
                    ty = cy + 13 + line_index * 23
                    for text, color in tokens:
                        font = get_font(text, sub_size)
                        draw.text((cx, ty), text, font=font, fill=color)
                        cx += draw.textlength(text, font=font) + 8
                cy += group_height + 5
        yy += row_heights[row_index] + gap
    draw.text((42, height - 42), "夜莺0.7 · 夜莺B人工选根 · 终局退火线程0 · 2026-08-27",
              font=sub_font, fill="#999")
    path = release / "夜莺码v0.7字根图.png"
    image.save(path)
    return path


def load_splits(label):
    splits = {}
    path = BROOT / "work/analysis.tsv.splits.tsv"
    for line in path.read_text(encoding="utf-8").splitlines():
        char, sep, raw = line.partition("\t")
        if sep and char not in splits:
            splits[char] = " ".join(label(x) for x in raw.split())
    return splits


def font_base64():
    practice_source = Path("D:/mbpy/jdeV1/字根练习器.html")
    if practice_source.exists():
        text = practice_source.read_text(encoding="utf-8")
        match = re.search(r"url\(data:font/ttf;base64,([A-Za-z0-9+/=]+)\)", text)
        if match:
            return match.group(1), text
    font = (BASE / "data/jdhe/ChaiPUA.ttf").read_bytes()
    return base64.b64encode(font).decode(), None


def build_lookup(entries, release, label):
    by_code, by_char = defaultdict(list), defaultdict(list)
    for code, _, _, _, char in entries:
        by_code[code].append(char)
    for code, chars in by_code.items():
        for rank, char in enumerate(chars, 1):
            by_char[char].append((code, rank))
    splits = load_splits(label)
    data = {char: {"codes": sorted(codes, key=lambda x: (len(x[0]), x[0])),
                   "split": splits.get(char, "")}
            for char, codes in by_char.items()}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    font, _ = font_base64()
    html = """<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>夜莺码 v0.7 查码</title><style>
@font-face{font-family:Chai;src:url(data:font/ttf;base64,__FONT__)}:root{--bg:#f5f6f8;--card:#fff;--fg:#191c20;--muted:#707680;--accent:#6d3be7;--chip:#f0eaff;--line:#e2e5e9}@media(prefers-color-scheme:dark){:root{--bg:#111419;--card:#1a1e25;--fg:#eceef1;--muted:#9ba1aa;--accent:#b69cff;--chip:#302650;--line:#2c323b}}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:Chai,\"Microsoft YaHei\",sans-serif;display:flex;justify-content:center;padding:8vh 16px}.wrap{width:min(620px,100%)}h1{font-size:22px;margin:0 0 5px}.sub{color:var(--muted);font-size:13px;margin-bottom:18px}input{width:100%;font:inherit;font-size:22px;padding:13px 16px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--fg);outline:0}.list{display:grid;gap:11px;margin-top:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}.char{font-size:35px;margin-right:12px}.split{color:var(--muted)}.split b{color:var(--accent);font-size:18px}.codes{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}.chip{background:var(--chip);color:var(--accent);border-radius:8px;padding:4px 9px;font:17px Consolas,monospace}.chip small{color:var(--muted);font:12px Chai,sans-serif;margin-left:5px}</style></head><body><main class=\"wrap\"><h1>夜莺码 v0.7 查码</h1><div class=\"sub\">纯单字码表 · 输入一个或多个汉字，查看简码、全码、候选位与正式拆分</div><input id=\"q\" autofocus placeholder=\"输入汉字……\"><div id=\"out\" class=\"list\"></div></main><script>const DATA=__DATA__;const q=document.querySelector('#q'),out=document.querySelector('#out');function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}function render(){out.innerHTML='';for(const ch of [...q.value].filter(x=>/\\S/.test(x)).slice(0,30)){const d=DATA[ch],card=document.createElement('section');card.className='card';if(!d){card.innerHTML=`<span class=char>${esc(ch)}</span><span class=split>不在码表中</span>`}else{const chips=d.codes.map(([c,r])=>`<span class=chip>${c}<small>${r===1?'首选':'第'+r+'候选'}</small></span>`).join('');card.innerHTML=`<span class=char>${esc(ch)}</span>${d.split?`<span class=split>拆分 <b>${esc(d.split)}</b></span>`:''}<div class=codes>${chips}</div>`}out.append(card)}}q.addEventListener('input',render)</script></body></html>"""
    html = html.replace("__FONT__", font).replace("__DATA__", blob)
    path = release / "夜莺码查码.html"
    path.write_text(html, encoding="utf-8")
    return path, len(data)


def build_practice(layout, release, resolve):
    mains, subsidiaries, anchors = root_catalog(layout, resolve)
    lines = []
    for row in ROWS:
        for key in row:
            for root, _ in mains.get(key, []):
                hints = []
                if subsidiaries.get(root):
                    hints.append("附属: " + " ".join(subsidiaries[root]))
                if anchors.get(root):
                    hints.append("锚定同键: " + " ".join(anchors[root]))
                name = f"{root}(笔画)" if root in STROKE_NAMES else root
                lines.append(f"{name}\t{key}\t{'；'.join(hints)}")
    data_path = release / "夜莺码字根练习.txt"
    data_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _, template = font_base64()
    if template is None:
        raise FileNotFoundError("未找到 D:/mbpy/jdeV1/字根练习器.html")
    page = re.sub(r"简单鹤\s*V?1\.0", "夜莺码 v0.7", template, flags=re.I)
    page = page.replace("简单鹤V1.0", "夜莺码v0.7")
    page_path = release / "夜莺码字根练习器.html"
    page_path.write_text(page, encoding="utf-8")
    return data_path, page_path, len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--release", type=Path, default=BASE / "releases/v0.7")
    ap.add_argument("--config", type=Path,
                    help="最终布局配置；默认依次取 run/config.yaml、run/solution-0.yaml")
    ap.add_argument("--elements", type=Path, default=BROOT / "work/analysis_elements.yaml",
                    help="与 run/code.txt 逐行对应的元素资产")
    args = ap.parse_args()
    args.release.mkdir(parents=True, exist_ok=True)
    resolve, label = load_resolver()
    config = args.config or (args.run / "config.yaml")
    if not config.exists():
        config = args.run / "solution-0.yaml"
    layout = build_layout(config, args.release)
    table, no_yield_table, mixed_table, entries, _, _ = build_table(
        args.run / "code.txt", args.elements, args.release
    )
    chart = build_chart(layout, args.release, resolve, label)
    lookup, char_count = build_lookup(entries, args.release, label)
    practice, practice_page, root_count = build_practice(layout, args.release, resolve)
    table_count = sum(1 for _ in table.open(encoding="utf-8"))
    print(f"纯单版：{table}（{table_count} 条）")
    no_yield_count = sum(1 for _ in no_yield_table.open(encoding="utf-8"))
    print(f"不让位纯单版：{no_yield_table}（{no_yield_count} 条）")
    mixed_count = sum(1 for _ in mixed_table.open(encoding="utf-8"))
    print(f"无简词字词版：{mixed_table}（{mixed_count} 条）")
    print(f"字根图：{chart}")
    print(f"查码页：{lookup}（{char_count} 字）")
    print(f"字根练习：{practice} / {practice_page}（{root_count} 主根）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
