#!/usr/bin/env python3
"""生成夜莺 0.8.5 离线“按字根查字”工具。"""

from __future__ import annotations

import argparse
import base64
import json
import re
import zlib
from collections import defaultdict
from pathlib import Path

import yaml


STROKE_NAMES = {"横", "竖", "撇", "点", "折"}
DEFAULT_PRESENTATION_NAMES = {"卧人": "每字头", "印字旁": "印左边"}


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


def read_codes(path: Path) -> tuple[dict[str, list[tuple[str, int]]], list[str]]:
    by_code: dict[str, list[str]] = defaultdict(list)
    order: list[str] = []
    seen = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = raw.split("\t")
        if len(fields) != 2:
            raise SystemExit(f"非法单字码表行：{path}:{number}")
        char, code = fields
        by_code[code].append(char)
        if char not in seen:
            seen.add(char)
            order.append(char)
    result: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for code, chars in by_code.items():
        for rank, char in enumerate(chars, 1):
            result[char].append((code, rank))
    for rows in result.values():
        rows.sort(key=lambda row: (len(row[0]), row[0], row[1]))
    return result, order


def read_splits(paths: list[Path]) -> dict[str, list[str]]:
    result = {}
    for path in paths:
        for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            fields = raw.split("\t")
            if number == 1 and fields[0] in {"字", "汉字", "character"}:
                continue
            if len(fields) < 2:
                raise SystemExit(f"非法拆分表行：{path}:{number}")
            # 规范表使用“空格＋空格”分隔部件。
            value = fields[1].strip()
            parts = [part.strip() for part in re.split(r"\s*＋\s*", value) if part.strip()]
            old = result.get(fields[0])
            if old is not None and old != parts:
                raise SystemExit(f"拆分表冲突：{fields[0]}：{old} / {parts}（{path}:{number}）")
            result[fields[0]] = parts
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--splits", type=Path, required=True, action="append")
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--roots-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    codes, char_order = read_codes(args.single)
    splits = read_splits(args.splits)
    root_yaml = yaml.safe_load((args.roots_dir / "根集.yaml").read_text(encoding="utf-8"))
    presentation_names = dict(DEFAULT_PRESENTATION_NAMES)
    presentation_names.update({str(k): str(v) for k, v in (root_yaml.get("presentation_names") or {}).items()})

    def present(name: str) -> str:
        return presentation_names.get(str(name), str(name))
    rules = yaml.safe_load((args.roots_dir / "拆分规则.yaml").read_text(encoding="utf-8"))
    layout = yaml.safe_load(args.layout.read_text(encoding="utf-8"))
    mapping = {str(k): v for k, v in layout["form"]["mapping"].items()}
    repertoire = json.loads(zlib.decompress(
        (args.repo / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes()
    ))
    by_char = {chr(row["unicode"]): row for row in repertoire if row.get("unicode")}
    by_name = {str(row["name"]): chr(row["unicode"]) for row in repertoire if row.get("name") and row.get("unicode")}
    custom = {str(k): str(v) for k, v in (rules.get("custom_elements") or {}).items()}

    def resolve(name: str) -> str:
        return custom.get(name, by_name.get(name, name))

    root_items = []
    seen_root = set()
    roots_by_key: dict[str, list[str]] = defaultdict(list)
    for host, attached in root_yaml["roots"].items():
        host = str(host)
        key = trace_key(mapping, resolve(host))
        if not key:
            continue
        rows = [(host, "主根", host)] + [(str(x), "附属根", host) for x in (attached or [])]
        for name, role, owner in rows:
            identity = (key, name)
            if identity in seen_root:
                continue
            seen_root.add(identity)
            roots_by_key[key].append(name)
            root_items.append({"name": present(name), "formal_name": name, "key": key, "role": role, "host": present(owner), "glyph": resolve(name)})
    for host, children in (root_yaml.get("anchors") or {}).items():
        host = str(host)
        key = trace_key(mapping, resolve(host))
        if not key:
            continue
        for child in children or []:
            name = str(child)
            identity = (key, name)
            if identity in seen_root:
                continue
            seen_root.add(identity)
            roots_by_key[key].append(name)
            root_items.append({"name": present(name), "formal_name": name, "key": key, "role": "锚定根", "host": present(host), "glyph": resolve(name)})

    missing_splits = [char for char in char_order if char not in splits]
    if missing_splits:
        raise SystemExit(f"仍有{len(missing_splits)}个码表字没有规范拆分：{''.join(missing_splits[:30])}")

    index: dict[str, list[dict]] = {}
    for root in root_items:
        name, formal_name, glyph = root["name"], root["formal_name"], root["glyph"]
        rows = []
        for char in char_order:
            direct = formal_name in splits.get(char, []) or glyph in splits.get(char, [])
            if not direct:
                continue
            rows.append({
                "char": char,
                "codes": codes[char],
                "split": " ".join(present(part) for part in splits.get(char, [])),
            })
        index[f'{root["key"]}\0{name}'] = rows

    payload = json.dumps({"roots": root_items, "index": index}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    font = base64.b64encode(args.font.read_bytes()).decode()
    template_path = args.repo / "apps" / "v085" / "templates" / "component_lookup.html"
    html = template_path.read_text(encoding="utf-8")
    args.output.write_text(html.replace("__FONT__", font).replace("__DATA__", payload), encoding="utf-8")
    rendered = args.output.read_text(encoding="utf-8")
    embedded = rendered.split("const DATA=", 1)[1].split(",key=document", 1)[0].replace("<\\/", "</")
    if json.loads(embedded) != json.loads(json.dumps({"roots": root_items, "index": index}, ensure_ascii=False)):
        raise SystemExit("内嵌数据回读校验失败")
    print(f"roots={len(root_items)} indexed_rows={sum(map(len,index.values()))} output={args.output}")


if __name__ == "__main__":
    main()
