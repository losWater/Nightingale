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


def build_practice(layout: dict, release: Path, roots_path: Path, template: Path, resolve, aliases):
    mains, subsidiaries, anchors = root_catalog(layout, roots_path, resolve, aliases)
    lines = []
    for keyboard_row in ROWS:
        for key in keyboard_row:
            for root in mains.get(key, []):
                hints = []
                if subsidiaries.get(root):
                    hints.append("附属: " + " ".join(subsidiaries[root]))
                if anchors.get(root):
                    hints.append("锚定同键: " + " ".join(anchors[root]))
                name = f"{root}(笔画)" if root in STROKE_NAMES else root
                lines.append(f"{name}\t{key}\t{'；'.join(hints)}")
    data_path = release / "夜莺码v0.8.5字根练习.txt"
    data_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    page = template.read_text(encoding="utf-8")
    page = page.replace("<title>元素重复练习器</title>", "<title>夜莺码 v0.8.5 字根练习器</title>")
    page = re.sub(r"简单鹤\s*V?1\.0", "夜莺码 v0.8.5", page, flags=re.I)
    page = page.replace("简单鹤V1.0", "夜莺码v0.8.5")
    page_path = release / "夜莺码v0.8.5字根练习器.html"
    page_path.write_text(page, encoding="utf-8")
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
        char: {"codes": sorted(codes, key=lambda item: (len(item[0]), item[0], item[1])), "split": splits.get(char, "")}
        for char, codes in by_char.items()
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    font = embedded_font(template, fallback_font)
    html = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>夜莺码 v0.8.5 拆分查询</title><style>
@font-face{font-family:Chai;src:url(data:font/ttf;base64,__FONT__)}:root{--bg:#f5f6f8;--card:#fff;--fg:#191c20;--muted:#707680;--accent:#6d3be7;--chip:#f0eaff;--line:#e2e5e9}@media(prefers-color-scheme:dark){:root{--bg:#111419;--card:#1a1e25;--fg:#eceef1;--muted:#9ba1aa;--accent:#b69cff;--chip:#302650;--line:#2c323b}}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:Chai,"Microsoft YaHei",sans-serif;display:flex;justify-content:center;padding:8vh 16px}.wrap{width:min(680px,100%)}h1{font-size:22px;margin:0 0 5px}.sub{color:var(--muted);font-size:13px;margin-bottom:18px}input{width:100%;font:inherit;font-size:22px;padding:13px 16px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--fg);outline:0}.list{display:grid;gap:11px;margin-top:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}.char{font-size:35px;margin-right:12px}.split{color:var(--muted)}.split b{color:var(--accent);font-size:18px}.codes{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}.chip{background:var(--chip);color:var(--accent);border-radius:8px;padding:4px 9px;font:17px Consolas,monospace}.chip small{color:var(--muted);font:12px Chai,sans-serif;margin-left:5px}</style></head><body><main class="wrap"><h1>夜莺码 v0.8.5 拆分查询</h1><div class="sub">正式单字接口 C v5 · 输入汉字查看简码、全码、候选位与8105规范拆分</div><input id="q" autofocus placeholder="输入汉字……"><div id="out" class="list"></div></main><script>const DATA=__DATA__;const q=document.querySelector('#q'),out=document.querySelector('#out');function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}function render(){out.innerHTML='';for(const ch of [...q.value].filter(x=>/\S/.test(x)).slice(0,50)){const d=DATA[ch],card=document.createElement('section');card.className='card';if(!d){card.innerHTML=`<span class=char>${esc(ch)}</span><span class=split>不在码表中</span>`}else{const chips=d.codes.map(([c,r])=>`<span class=chip>${c}<small>${r===1?'首选':'第'+r+'候选'}</small></span>`).join('');card.innerHTML=`<span class=char>${esc(ch)}</span>${d.split?`<span class=split>拆分 <b>${esc(d.split)}</b></span>`:'<span class=split>暂无规范拆分</span>'}<div class=codes>${chips}</div>`}out.append(card)}}q.addEventListener('input',render)</script></body></html>"""
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
    html = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>夜莺码 v0.8.5 编码反查</title><style>
:root{--bg:#f5f6f8;--card:#fff;--fg:#191c20;--muted:#707680;--accent:#6d3be7;--chip:#f0eaff;--line:#e2e5e9}@media(prefers-color-scheme:dark){:root{--bg:#111419;--card:#1a1e25;--fg:#eceef1;--muted:#9ba1aa;--accent:#b69cff;--chip:#302650;--line:#2c323b}}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:"Microsoft YaHei",sans-serif;display:flex;justify-content:center;padding:8vh 16px}.wrap{width:min(760px,100%)}h1{font-size:22px;margin:0 0 5px}.sub,.empty{color:var(--muted);font-size:13px}.sub{margin-bottom:18px}input{width:100%;font:22px Consolas,monospace;padding:13px 16px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--fg);outline:0}.section{margin-top:18px}.section h2{font-size:15px;margin:0 0 9px;color:var(--muted)}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 15px;margin:8px 0}.code{color:var(--accent);font:19px Consolas,monospace;margin-right:10px}.count{color:var(--muted);font-size:12px}.items{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.item{background:var(--chip);border-radius:8px;padding:5px 9px;font-size:18px}.item small{color:var(--muted);font-size:11px;margin-left:5px}.word{font-size:16px}.prefix{max-height:55vh;overflow:auto}.hidden{display:none}</style></head><body><main class="wrap"><h1>夜莺码 v0.8.5 编码反查</h1><div class="sub">数据来自正式挂接字词接口G · 精确码显示完整候选 · 前缀最多展示200个码位</div><input id="q" maxlength="4" autofocus autocomplete="off" spellcheck="false" placeholder="输入编码，例如 jix"><section id="exact" class="section"></section><section id="family" class="section prefix"></section></main><script>const DATA=__DATA__;const q=document.querySelector('#q'),exact=document.querySelector('#exact'),family=document.querySelector('#family');function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}function card(code,items){return `<div class=card><span class=code>${code}</span><span class=count>${items.length}项</span><div class=items>${items.map((x,i)=>`<span class="item ${[...x].length>1?'word':''}">${esc(x)}<small>${[...x].length===1?'字':'词'} · ${i+1}</small></span>`).join('')}</div></div>`}function render(){const v=q.value.toLowerCase().replace(/[^a-z]/g,'').slice(0,4);if(q.value!==v)q.value=v;if(!v){exact.innerHTML='';family.innerHTML='';return}const hit=DATA[v];exact.innerHTML=`<h2>精确匹配</h2>${hit?card(v,hit):'<div class=empty>这个码没有候选。</div>'}`;const codes=Object.keys(DATA).filter(x=>x.startsWith(v)&&x!==v).slice(0,200);family.innerHTML=`<h2>前缀家族（${codes.length}${codes.length===200?'＋':''}个码位）</h2>${codes.length?codes.map(x=>card(x,DATA[x])).join(''):'<div class=empty>没有更长的同前缀码。</div>'}`}q.addEventListener('input',render)</script></body></html>'''
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
    parser.add_argument("--practice-template", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--single-decisions", type=Path, required=True)
    parser.add_argument("--irrational", type=Path, required=True)
    args = parser.parse_args()
    if args.release.exists():
        raise SystemExit(f"release directory already exists: {args.release}")
    args.release.mkdir(parents=True)

    inputs = [args.single, args.single_sogou, args.single_sogou_quick,
              args.combined, args.combined_sogou, args.combined_sogou_quick,
              args.config, args.splits, args.presentation, args.decisions, args.single_decisions, args.irrational]
    input_hashes = {str(path.resolve()): sha256(path) for path in inputs}
    copy_exact(args.single, args.release / "夜莺码v0.8.5单字版.txt")
    copies = [
        (args.single_sogou, "夜莺码v0.8.5单字版_搜狗.txt"),
        (args.single_sogou_quick, "夜莺码v0.8.5单字版_搜狗_含快符.txt"),
        (args.combined, "夜莺码v0.8.5挂接字词版_无简词.txt"),
        (args.combined_sogou, "夜莺码v0.8.5挂接字词版_搜狗词库.txt"),
        (args.combined_sogou_quick, "夜莺码v0.8.5挂接字词版_搜狗词库_含快符.txt"),
        (args.decisions, "夜莺码v0.8.5字词裁决.tsv"),
        (args.single_decisions, "夜莺码v0.8.5单字裁决.tsv"),
        (args.irrational, "夜莺码v0.8.5无理码表.tsv"),
    ]
    for source, name in copies:
        copy_exact(source, args.release / name)

    layout, layout_path = build_layout(args.config, args.release)
    resolve, _ = load_resolver(args.repo, args.roots_dir)
    aliases = load_presentation_aliases(args.presentation)
    practice_data, practice_page, root_count = build_practice(
        layout, args.release, args.roots_dir / "根集.yaml", args.practice_template, resolve, aliases
    )
    lookup, char_count, split_count = build_lookup(
        args.single, args.splits, args.release, args.practice_template, args.repo / "data/jdhe/ChaiPUA.ttf"
    )
    reverse_code_count, reverse_entry_count = build_reverse_lookup(
        args.combined, args.release / "夜莺码v0.8.5编码反查.html"
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

    outputs = sorted(path for path in args.release.iterdir() if path.is_file())
    manifest = {
        "schema_version": 1,
        "version": "0.8.5",
        "status": "pass",
        "inputs": input_hashes,
        "counts": {"practice_roots": root_count, "lookup_chars": char_count, "lookup_chars_with_split": split_count,
                   "reverse_lookup_codes": reverse_code_count, "reverse_lookup_entries": reverse_entry_count},
        "outputs": {path.name: sha256(path) for path in outputs},
    }
    manifest_path = args.release / "发布清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
