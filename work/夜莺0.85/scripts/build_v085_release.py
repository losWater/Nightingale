#!/usr/bin/env python3
"""Build the audited Nightingale 0.8.5 release and offline learning tools."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import sys
import zlib
from collections import OrderedDict, defaultdict
from pathlib import Path

import yaml


ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
STROKE_LABELS = {"1": "横", "2": "竖", "3": "撇", "4": "点", "5": "折"}
STROKE_NAMES = {value: key for key, value in STROKE_LABELS.items()}
PRESENTATION_NAMES = {"卧人": "每字头", "印字旁": "印左边"}
TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "apps" / "v085" / "templates"


def present_name(value: str) -> str:
    return PRESENTATION_NAMES.get(str(value), str(value))


def present_split(value: str) -> str:
    return " ＋ ".join(present_name(part.strip()) for part in re.split(r"\s*＋\s*", value))


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def copy_exact(source: Path, target: Path) -> None:
    shutil.copyfile(source, target)
    if sha256(source) != sha256(target):
        raise SystemExit(f"copy hash mismatch: {source} -> {target}")


def write_code_first(source: Path, target: Path) -> None:
    source_rows = []
    for line_number, raw in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = raw.split("\t")
        if len(fields) != 2:
            raise SystemExit(f"invalid single table row {source}:{line_number}")
        char, code = fields
        if len(char) != 1 or not (1 <= len(code) <= 4 and code.isascii() and code.isalpha() and code.islower()):
            raise SystemExit(f"invalid single char/code {source}:{line_number}")
        source_rows.append((char, code))
    target.write_text("".join(f"{code}\t{char}\n" for char, code in source_rows), encoding="utf-8")
    verify = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        code, char = raw.split("\t")
        verify.append((char, code))
    if verify != source_rows:
        raise SystemExit(f"code-first round-trip mismatch: {target}")


def load_resolver(repo: Path, roots_dir: Path):
    repertoire = json.loads(
        zlib.decompress((repo / "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate").read_bytes())
    )
    by_name = {row.get("name"): chr(row["unicode"]) for row in repertoire if row.get("name") and row.get("unicode")}
    by_char = {chr(row["unicode"]): row for row in repertoire if row.get("unicode")}
    rules = yaml.safe_load((roots_dir / "拆分规则.yaml").read_text(encoding="utf-8"))
    custom = {str(key): str(value) for key, value in rules.get("custom_elements", {}).items()}
    custom_back = {value: key for key, value in custom.items()}

    def resolve(value: str) -> str:
        text = STROKE_NAMES.get(str(value), str(value))
        return custom.get(text, by_name.get(text, text))

    def label(value: str) -> str:
        value = str(value)
        if value in STROKE_LABELS:
            return STROKE_LABELS[value]
        if value in custom_back:
            return custom_back[value]
        row = by_char.get(value)
        return str(row.get("name")) if row and row.get("name") else value

    return resolve, label


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


def build_layout(config_path: Path, release: Path) -> tuple[dict, Path]:
    source = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    release_form = dict(source["form"])
    release_form.pop("mapping_space", None)
    layout = {
        "version": "0.8.5",
        "source": "夜莺0.8.5 G8C12正式布局",
        "info": {
            "name": "夜莺码0.8.5",
            "author": "nightingale",
            "description": "小鹤双拼音码＋首末字根形码；G8C12手感与三码率优化布局",
        },
        "form": release_form,
    }
    target = release / "夜莺码v0.8.5键位布局.yaml"
    target.write_text(yaml.safe_dump(layout, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    return layout, target


def load_presentation_aliases(path: Path) -> dict[str, list[str]]:
    source = yaml.safe_load(path.read_text(encoding="utf-8"))
    aliases: dict[str, list[str]] = defaultdict(list)
    for row in source.get("accepted_implicit_equivalences", []):
        layer = row.get("presentation_layer") or {}
        if row.get("status") == "accepted_with_presentation_alias" and layer.get("root_trainer"):
            expected = row.get("expected_final_split") or []
            if len(expected) == 1:
                aliases[str(expected[0])].append(str(row["glyph"]))
    return aliases


def root_catalog(layout: dict, roots_path: Path, resolve, presentation_aliases: dict[str, list[str]]):
    roots = yaml.safe_load(roots_path.read_text(encoding="utf-8"))
    mapping = {str(key): value for key, value in layout["form"]["mapping"].items()}
    mains: dict[str, list[str]] = defaultdict(list)
    subsidiaries: dict[str, list[str]] = defaultdict(list)
    anchors: dict[str, list[str]] = defaultdict(list)
    for root, attached in roots["roots"].items():
        root = str(root)
        key = trace_key(mapping, resolve(root))
        if key:
            mains[key].append(root)
        subsidiaries[root].extend(str(item) for item in (attached or []))
    for host, children in (roots.get("anchors") or {}).items():
        anchors[str(host)].extend(str(item) for item in (children or []))
    for host, aliases in presentation_aliases.items():
        subsidiaries[host].extend(alias for alias in aliases if alias not in subsidiaries[host])
    return mains, subsidiaries, anchors


def build_practice(layout: dict, release: Path, roots_path: Path, resolve, aliases):
    mains, subsidiaries, anchors = root_catalog(layout, roots_path, resolve, aliases)
    lines = []
    for keyboard_row in ROWS:
        for key in keyboard_row:
            for root in mains.get(key, []):
                hints = []
                if subsidiaries.get(root):
                    hints.append("附属: " + " ".join(present_name(item) for item in subsidiaries[root]))
                if anchors.get(root):
                    hints.append("锚定同键: " + " ".join(present_name(item) for item in anchors[root]))
                name = f"{root}(笔画)" if root in STROKE_NAMES else present_name(root)
                if root == "囗":
                    name = "囗-[（框）]-"
                lines.append(f"{name}\t{key}\t{'；'.join(hints)}")
    data_path = release / "夜莺码v0.8.5字根练习.txt"
    data_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    page_template = TEMPLATE_DIR / "root_practice.html"
    page_path = release / "夜莺码v0.8.5字根练习器.html"
    # 练习器模板中保留了历史发布页的原始换行；按字节复制可避免无意义的整页变更。
    page_path.write_bytes(page_template.read_bytes())
    if not any(line.startswith("子\t") and "孑" in line for line in lines):
        raise SystemExit("presentation alias 孑 was not attached to 子 in practice data")
    return data_path, page_path, len(lines)


def read_single_table(path: Path):
    by_code: OrderedDict[str, list[str]] = OrderedDict()
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, 1):
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 2:
                raise SystemExit(f"invalid single table row {line_number}")
            char, code = parts
            by_code.setdefault(code, []).append(char)
    by_char: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for code, chars in by_code.items():
        for index, char in enumerate(chars, 1):
            by_char[char].append((code, index))
    return by_char


def read_splits(path: Path) -> dict[str, str]:
    splits = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, 1):
            parts = raw.rstrip("\r\n").split("\t")
            if line_number == 1 and parts[0] in {"字", "character"}:
                continue
            if len(parts) < 2:
                raise SystemExit(f"invalid split row {line_number}")
            splits.setdefault(parts[0], parts[1])
    return splits


def embedded_font(template: Path, fallback: Path) -> str:
    text = template.read_text(encoding="utf-8")
    match = re.search(r"url\(data:font/ttf;base64,([A-Za-z0-9+/=]+)\)", text)
    if match:
        return match.group(1)
    return base64.b64encode(fallback.read_bytes()).decode()


def build_lookup(single_path: Path, split_path: Path, release: Path, template: Path, fallback_font: Path):
    by_char = read_single_table(single_path)
    splits = read_splits(split_path)
    data = {
        char: {"codes": sorted(codes, key=lambda item: (len(item[0]), item[0], item[1])), "split": present_split(splits.get(char, "")) if splits.get(char) else ""}
        for char, codes in by_char.items()
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    font = embedded_font(template, fallback_font)
    html = (TEMPLATE_DIR / "split_lookup.html").read_text(encoding="utf-8")
    target = release / "夜莺码v0.8.5拆分查询.html"
    target.write_text(html.replace("__FONT__", font).replace("__DATA__", blob), encoding="utf-8")
    return target, len(data), sum(1 for char in data if char in splits)


def build_reverse_lookup(combined_path: Path, target: Path) -> tuple[int, int]:
    by_code: OrderedDict[str, list[str]] = OrderedDict()
    entry_count = 0
    for line_number, raw in enumerate(combined_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = raw.split("\t")
        if len(fields) != 2:
            raise SystemExit(f"invalid combined row {combined_path}:{line_number}")
        text, code = fields
        if not text or not (1 <= len(code) <= 4 and code.isascii() and code.isalpha() and code.islower()):
            raise SystemExit(f"invalid combined entry {combined_path}:{line_number}")
        by_code.setdefault(code, []).append(text)
        entry_count += 1
    if not by_code:
        raise SystemExit(f"empty combined table: {combined_path}")
    data = json.dumps(by_code, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (TEMPLATE_DIR / "reverse_lookup.html").read_text(encoding="utf-8")
    target.write_text(html.replace("__DATA__", data), encoding="utf-8")
    # Validate the exact embedded payload before accepting the page.
    rendered = target.read_text(encoding="utf-8")
    marker_a, marker_b = "const DATA=", ";const q="
    embedded = rendered.split(marker_a, 1)[1].split(marker_b, 1)[0].replace("<\\/", "</")
    verify = json.loads(embedded)
    if verify != by_code or sum(len(items) for items in verify.values()) != entry_count:
        raise SystemExit("reverse lookup embedded data mismatch")
    return len(by_code), entry_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--single-sogou", type=Path, required=True)
    parser.add_argument("--single-sogou-quick", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--combined-sogou", type=Path, required=True)
    parser.add_argument("--combined-sogou-quick", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--roots-dir", type=Path, required=True)
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--presentation", type=Path, required=True)
    parser.add_argument(
        "--practice-template", type=Path,
        help="已废弃的兼容参数；现在固定使用apps/v085/templates/root_practice.html",
    )
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--single-decisions", type=Path, required=True)
    parser.add_argument("--irrational", type=Path, required=True)
    args = parser.parse_args()
    if args.release.exists():
        raise SystemExit(f"release directory already exists: {args.release}")
    args.release.mkdir(parents=True)
    tables = args.release / "01_正式码表"
    sogou = args.release / "02_输入法挂接" / "搜狗输入法"
    roots_and_splits = args.release / "03_字根与拆分"
    tools = args.release / "04_查询与练习"
    maintenance = args.release / "05_维护与裁决"
    for directory in (tables, sogou, roots_and_splits, tools, maintenance):
        directory.mkdir(parents=True)

    inputs = [args.single, args.single_sogou, args.single_sogou_quick,
              args.combined, args.combined_sogou, args.combined_sogou_quick,
              args.config, args.splits, args.presentation, args.decisions, args.single_decisions, args.irrational]
    input_hashes = {str(path.resolve()): sha256(path) for path in inputs}
    copy_exact(args.single, tables / "夜莺码v0.8.5单字版.txt")
    copies = [
        (args.single_sogou, "夜莺码v0.8.5无二字词版_搜狗.txt"),
        (args.single_sogou_quick, "夜莺码v0.8.5无二字词版_搜狗_含快符.txt"),
        (args.combined, "夜莺0.8.5字词表.txt"),
        (args.combined_sogou, "夜莺码v0.8.5挂接字词版_搜狗词库.txt"),
        (args.combined_sogou_quick, "夜莺码v0.8.5挂接字词版_搜狗词库_含快符.txt"),
        (args.decisions, "夜莺码v0.8.5字词裁决.tsv"),
        (args.single_decisions, "夜莺码v0.8.5单字裁决.tsv"),
        (args.irrational, "夜莺码v0.8.5无理码表.tsv"),
    ]
    for source, name in copies:
        if "搜狗" in name:
            destination = sogou / name
        elif "裁决" in name:
            destination = maintenance / name
        else:
            destination = tables / name
        copy_exact(source, destination)

    layout, layout_path = build_layout(args.config, tables)
    resolve, _ = load_resolver(args.repo, args.roots_dir)
    aliases = load_presentation_aliases(args.presentation)
    practice_data, practice_page, root_count = build_practice(
        layout, tools, args.roots_dir / "根集.yaml", resolve, aliases
    )
    lookup, char_count, split_count = build_lookup(
        args.single, args.splits, tools, TEMPLATE_DIR / "root_practice.html", args.repo / "data/jdhe/ChaiPUA.ttf"
    )
    reverse_code_count, reverse_entry_count = build_reverse_lookup(
        args.combined, tools / "夜莺码v0.8.5编码反查.html"
    )

    notes = args.release / "README.md"
    notes.write_text(
        "# 夜莺码 0.8.5\n\n"
        "本版采用G8C12布局，默认发布挂接字词版；当前综合版不含简词。\n\n"
        "- 搜狗词库版只写单字，并保留词让出的候选序号空位；\n"
        "- 单字搜狗版与挂接搜狗词库版均提供`含快符`变体，额外加入39条既有快符；\n"
        "- 字根练习器配套读取同目录练习TXT；\n"
        "- 拆分查询页离线内嵌正式单字码与8105规范拆分；\n"
        "- 编码反查页离线内嵌最终G，可按精确码或前缀查看全部单字、词与候选位；\n"
        "- 展示层中“孑”作为“子”根提示，不改变正式拆分或Chai根集。\n",
        encoding="utf-8",
    )

    outputs = sorted(path for path in args.release.rglob("*") if path.is_file())
    manifest = {
        "schema_version": 1,
        "version": "0.8.5",
        "status": "pass",
        "inputs": input_hashes,
        "counts": {"practice_roots": root_count, "lookup_chars": char_count, "lookup_chars_with_split": split_count,
                   "reverse_lookup_codes": reverse_code_count, "reverse_lookup_entries": reverse_entry_count},
        "outputs": {path.relative_to(args.release).as_posix(): sha256(path) for path in outputs},
    }
    manifest_path = args.release / "发布清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
