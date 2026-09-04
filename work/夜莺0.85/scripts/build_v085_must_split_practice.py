#!/usr/bin/env python3
"""生成夜莺码 0.9 必拆字练习（离线单文件）。"""

from __future__ import annotations

import base64
import json
import random
import re
import zlib
from collections import defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.9"
ROOTS_DIR = ROOT / "夜莺B" / "work"
SPLITS_PATH = ROOT / "work" / "重开工程" / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
SINGLE_PATH = RELEASE / "01_正式码表" / "夜莺码v0.9单字版.txt"
LAYOUT_PATH = RELEASE / "01_正式码表" / "夜莺码v0.9键位布局.yaml"
FONT_PATH = ROOT / "data" / "jdhe" / "ChaiPUA.ttf"
REPERTOIRE_PATH = ROOT / "repos" / "webchai" / "packages" / "hanzi-chai" / "src" / "data" / "repertoire.json.deflate"
DICTIONARY_PATH = ROOT / "repos" / "webchai" / "packages" / "hanzi-chai" / "src" / "data" / "dictionary.txt"
OUTPUT_DIR = RELEASE / "04_查询与练习" / "必拆字"
OUTPUT_HTML = OUTPUT_DIR / "夜莺码v0.9必拆字练习.html"
OUTPUT_AUDIT = OUTPUT_DIR / "必拆字练习集.tsv"
PRESENTATION_NAMES = {"卧人": "每字头", "印字旁": "印左边"}
KEY_ORDER = {key: index for index, key in enumerate("qwertyuiopasdfghjklzxcvbnm")}


def trace_key(mapping: dict, element: str) -> str | None:
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


def load_resolver() -> tuple[dict[str, str], dict[str, str]]:
    rules = yaml.safe_load((ROOTS_DIR / "拆分规则.yaml").read_text(encoding="utf-8"))
    repertoire = json.loads(zlib.decompress(REPERTOIRE_PATH.read_bytes()))
    by_name = {str(row["name"]): chr(row["unicode"]) for row in repertoire if row.get("name") and row.get("unicode")}
    custom = {str(k): str(v) for k, v in (rules.get("custom_elements") or {}).items()}
    return by_name, custom


def resolve(name: str, by_name: dict[str, str], custom: dict[str, str]) -> str:
    return custom.get(name, by_name.get(name, name))


def read_codes() -> tuple[dict[str, list[str]], list[str]]:
    codes: dict[str, list[str]] = defaultdict(list)
    order: list[str] = []
    seen = set()
    for line in SINGLE_PATH.read_text(encoding="utf-8-sig").splitlines():
        if not line:
            continue
        char, code = line.split("\t")
        if code not in codes[char]:
            codes[char].append(code)
        if char not in seen:
            seen.add(char)
            order.append(char)
    return codes, order


def read_splits() -> dict[str, list[str]]:
    result = {}
    for number, line in enumerate(SPLITS_PATH.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split("\t")
        if number == 1 and fields[0] in {"字", "汉字", "character"}:
            continue
        if len(fields) < 2:
            continue
        result[fields[0]] = [part.strip() for part in re.split(r"\s*＋\s*", fields[1]) if part.strip()]
    return result


def tone_mark(reading: str) -> str:
    """把 Chai 的数字声调拼音转成便于阅读的声调符号。"""
    match = re.fullmatch(r"([a-züv:]+)([1-5])?", reading.strip().lower())
    if not match:
        return reading
    syllable = match.group(1).replace("u:", "ü").replace("v", "ü")
    tone = int(match.group(2) or "5")
    if tone == 5:
        return syllable
    vowels = "aeiouü"
    if not any(char in vowels for char in syllable):
        return syllable
    if "a" in syllable:
        index = syllable.index("a")
    elif "e" in syllable:
        index = syllable.index("e")
    elif "ou" in syllable:
        index = syllable.index("o")
    else:
        index = max(i for i, char in enumerate(syllable) if char in vowels)
    marks = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}
    return syllable[:index] + marks[syllable[index]][tone - 1] + syllable[index + 1:]


def read_pronunciations(charset: set[str]) -> dict[str, list[str]]:
    rows: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for order, raw in enumerate(DICTIONARY_PATH.read_text(encoding="utf-8-sig").splitlines()):
        fields = raw.split("\t")
        if len(fields) < 2 or fields[0] not in charset or not fields[1]:
            continue
        try:
            frequency = int(fields[2]) if len(fields) > 2 else 0
        except ValueError:
            frequency = 0
        rows[fields[0]].append((frequency, order, tone_mark(fields[1])))
    result = {}
    for char, values in rows.items():
        positive = [row for row in values if row[0] > 0] or values[:1]
        positive.sort(key=lambda row: (-row[0], row[1]))
        result[char] = list(dict.fromkeys(row[2] for row in positive))
    return result


def root_catalog() -> list[dict]:
    root_yaml = yaml.safe_load((ROOTS_DIR / "根集.yaml").read_text(encoding="utf-8"))
    presentation = dict(PRESENTATION_NAMES)
    presentation.update({str(k): str(v) for k, v in (root_yaml.get("presentation_names") or {}).items()})
    layout = yaml.safe_load(LAYOUT_PATH.read_text(encoding="utf-8"))
    mapping = {str(k): v for k, v in layout["form"]["mapping"].items()}
    by_name, custom = load_resolver()
    items, seen = [], set()

    def add(name: str, role: str, host: str) -> None:
        glyph = resolve(name, by_name, custom)
        key = trace_key(mapping, glyph)
        identity = (key, name)
        if not key or identity in seen:
            return
        seen.add(identity)
        items.append({"name": name, "display": presentation.get(name, name), "glyph": glyph,
                      "key": key, "role": role, "host": host})

    for host, attached in root_yaml["roots"].items():
        host = str(host)
        add(host, "主根", host)
        for name in attached or []:
            add(str(name), "附属根", host)
    for host, children in (root_yaml.get("anchors") or {}).items():
        for name in children or []:
            add(str(name), "锚定根", str(host))
    items.sort(key=lambda row: (KEY_ORDER.get(row["key"], 99), 0 if row["role"] == "主根" else 1))
    return items


def build_questions() -> tuple[list[dict], list[dict]]:
    codes, char_order = read_codes()
    splits = read_splits()
    roots = root_catalog()
    root_yaml = yaml.safe_load((ROOTS_DIR / "根集.yaml").read_text(encoding="utf-8"))
    presentation = dict(PRESENTATION_NAMES)
    presentation.update({str(k): str(v) for k, v in (root_yaml.get("presentation_names") or {}).items()})
    pronunciations = read_pronunciations(set(char_order))
    rank = {char: index for index, char in enumerate(char_order)}
    usable_chars = [char for char in char_order if char in splits and any(len(code) == 4 for code in codes[char])]

    candidates: dict[tuple[int, str], list[str]] = {}
    for index, root in enumerate(roots):
        names = {root["name"], root["glyph"]}
        candidates[(index, "首")] = [char for char in usable_chars if splits[char] and splits[char][0] in names]
        candidates[(index, "末")] = [char for char in usable_chars if splits[char] and splits[char][-1] in names]

    slots = [slot for slot, chars in candidates.items() if chars]
    slots.sort(key=lambda slot: (len(candidates[slot]), KEY_ORDER.get(roots[slot[0]]["key"], 99), slot[0], slot[1]))
    char_to_slot: dict[str, tuple[int, str]] = {}
    slot_to_char: dict[tuple[int, str], str] = {}

    def augment(slot: tuple[int, str], visited: set[str]) -> bool:
        ordered = sorted(candidates[slot], key=lambda char: (rank[char], char))
        for char in ordered:
            if char in visited:
                continue
            visited.add(char)
            other = char_to_slot.get(char)
            if other is None or augment(other, visited):
                char_to_slot[char] = slot
                slot_to_char[slot] = char
                return True
        return False

    for slot in slots:
        augment(slot, set())

    questions, audit = [], []
    for root_index, root in enumerate(roots):
        for side in ("首", "末"):
            slot = (root_index, side)
            char = slot_to_char.get(slot)
            if not char:
                continue
            full_codes = [code for code in codes[char] if len(code) == 4]
            shortest_length = min(map(len, codes[char]))
            short_codes = [code for code in codes[char] if len(code) == shortest_length]
            split = splits[char]
            display_split = [presentation.get(part, part) for part in split]
            question = {
                "char": char,
                "full": full_codes,
                "short": short_codes,
                "split": display_split,
                "pinyin": pronunciations.get(char, []),
            }
            questions.append(question)
            audit.append({**root, "side": side, "char": char, "split": " ＋ ".join(display_split),
                          "pinyin": " / ".join(pronunciations.get(char, [])),
                          "full": " ".join(full_codes), "short": " ".join(short_codes),
                          "candidate_count": len(candidates[slot])})
    # 以“一个字根的首、末两题”为最小单位固定乱序：同根题相邻，字根组之间乱序。
    # 用户不能从字根表或键盘顺序反推当前根；重复构建同一版本仍得到相同结果。
    paired = list(zip(questions, audit))
    groups: list[list[tuple[dict, dict]]] = []
    for pair in paired:
        identity = (pair[1]["key"], pair[1]["name"])
        if not groups or (groups[-1][0][1]["key"], groups[-1][0][1]["name"]) != identity:
            groups.append([])
        groups[-1].append(pair)
    random.Random("nightingale-v0.9-must-split-root-groups-v2").shuffle(groups)
    paired = [pair for group in groups for pair in group]
    questions = [question for question, _row in paired]
    audit = [{"sequence": index, **row} for index, (_question, row) in enumerate(paired, 1)]
    return questions, audit


def build_html(questions: list[dict]) -> str:
    payload = json.dumps(questions, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    font = base64.b64encode(FONT_PATH.read_bytes()).decode()
    template_path = ROOT / "apps" / "v085" / "templates" / "must_split_practice.html"
    template = template_path.read_text(encoding="utf-8")
    return template.replace("__FONT__", font).replace("__DATA__", payload)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    questions, audit = build_questions()
    OUTPUT_HTML.write_text(build_html(questions), encoding="utf-8")
    columns = ["sequence", "key", "display", "name", "role", "host", "side", "char", "pinyin", "split", "full", "short", "candidate_count"]
    lines = ["\t".join(columns)] + ["\t".join(str(row[column]) for column in columns) for row in audit]
    OUTPUT_AUDIT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"questions={len(questions)} roots={len({(r['key'],r['name']) for r in audit})} output={OUTPUT_HTML}")


if __name__ == "__main__":
    main()
