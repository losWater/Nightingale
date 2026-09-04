#!/usr/bin/env python3
"""把已校验的手心总挂接表无损拆成可独立勾选的模块。"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.9"
TABLES = RELEASE / "01_正式码表"
PALM = RELEASE / "02_输入法挂接" / "手心输入法"
OUTPUT = PALM / "模块化挂接正式版"


def read_plain(path: Path) -> list[tuple[str, str]]:
    return [tuple(line.split("\t")[:2]) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def read_palm(path: Path) -> list[tuple[str, int, str]]:
    result = []
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw:
            continue
        code, right = raw.split("=", 1)
        rank, text = right.split(",", 1)
        if not rank.isdigit():
            raise ValueError(f"{path}:{number}: 非法候选位")
        result.append((code, int(rank), text))
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source_path = PALM / "夜莺码v0.9电脑手心挂接.txt"
    source = read_palm(source_path)
    extension_chars = {r["字"] for r in read_tsv(TABLES / "夜莺码v0.9扩展字表.tsv")}
    single_pairs = set(read_plain(TABLES / "夜莺码v0.9单字版.txt"))
    core_single_pairs = {(char, code) for char, code in single_pairs if char not in extension_chars}
    short_pairs = {(r["词"], r["简码"]) for r in read_tsv(TABLES / "夜莺码v0.9简词表.tsv")}

    def is_short_word(text: str, code: str) -> bool:
        return len(text) > 1 and ((text, code) in short_pairs or len(code) < 4)
    quick = set()
    for raw in (ROOT / "symbo.txt").read_text(encoding="utf-8-sig").splitlines():
        left, text = raw.split("=", 1); code, rank = left.rsplit(",", 1)
        quick.add((text, code, int(rank)))
    ordinary_pairs = {
        (text, code) for text, code in read_plain(TABLES / "夜莺0.9字词表.txt")
        if len(text) > 1 and not is_short_word(text, code)
    }

    modules: dict[str, list[tuple[str, int, str]]] = {
        "01_夜莺0.9_核心单字.txt": [],
        "02_夜莺0.9_普通词.txt": [],
        "03_夜莺0.9_简词.txt": [],
        "04_夜莺0.9_快符.txt": [],
        "05_夜莺0.9_扩展字.txt": [],
    }
    unmatched = []
    for code, rank, text in source:
        if (text, code, rank) in quick:
            name = "04_夜莺0.9_快符.txt"
        elif text in extension_chars and len(text) == 1:
            name = "05_夜莺0.9_扩展字.txt"
        elif is_short_word(text, code):
            name = "03_夜莺0.9_简词.txt"
        elif len(text) == 1:
            name = "01_夜莺0.9_核心单字.txt"
        elif (text, code) in ordinary_pairs:
            name = "02_夜莺0.9_普通词.txt"
        else:
            unmatched.append((code, rank, text)); continue
        modules[name].append((code, rank, text))
    if unmatched:
        raise ValueError(f"无法归类的总表条目：{unmatched[:20]}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    reconstructed = []
    outputs = {}
    for name, rows in modules.items():
        path = OUTPUT / name
        path.write_bytes(("\n".join(f"{code}={rank},{text}" for code, rank, text in rows) + "\n").encode("utf-8"))
        reconstructed.extend(rows)
        outputs[name] = {"rows": len(rows), "sha256": sha256(path)}
    if Counter(reconstructed) != Counter(source):
        raise ValueError("模块重组后与总挂接表不一致")

    readme = """# 夜莺码0.9 手心模块化挂接

五个模块可同时勾选，候选位与原“电脑手心挂接”完全相同。

- 完整版：勾选 01—05 全部模块。
- 无二字词版：不勾选 02，勾选 01、03、04、05。普通词原有候选位依然保留为空位，供手心自带词库联想。
- 不需要繁体生僻字：可不勾选 05。
- 不需要简词或快符：可分别不勾选 03或04。

请勿同时勾选旧的整合挂接表，否则会导致重复候选。
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")
    manifest = {"source": str(source_path.relative_to(ROOT)), "source_rows": len(source),
                "source_sha256": sha256(source_path), "outputs": outputs, "reconstruction": "pass"}
    (OUTPUT / "模块化生成清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    release_manifest_path = RELEASE / "发布清单.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    for path in OUTPUT.iterdir():
        if path.is_file():
            name = path.relative_to(RELEASE).as_posix()
            release_manifest["outputs"][name] = sha256(path)
    release_manifest_path.write_text(json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_rows": len(source), "modules": {k: len(v) for k, v in modules.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
