#!/usr/bin/env python3
"""下载、校验并构建固定的 LCCC-base test 赛码语料。"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import urllib.request
from pathlib import Path


SOURCE_URL = "https://huggingface.co/datasets/silver/lccc/resolve/main/lccc_base_test.jsonl.gz"
SOURCE_SHA256 = "cf8757587bdb8f360cc94fc38baadf9e185bad65a26155527a8430c048676016"
EXPECTED_RECORDS = 10_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_if_needed(path: Path) -> None:
    if path.exists() and sha256(path) == SOURCE_SHA256:
        return
    temporary = path.with_suffix(path.suffix + ".part")
    if temporary.exists():
        temporary.unlink()
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "nightingale-corpus-builder/0.8"})
    with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)
    actual = sha256(temporary)
    if actual != SOURCE_SHA256:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"下载文件SHA-256不符：期望 {SOURCE_SHA256}，实际 {actual}")
    temporary.replace(path)


def extract_dialog(record: object, line_number: int) -> list[str]:
    # 当前固定下载文件的真实格式是一行一个字符串数组；数据集卡展示的是
    # {"dialog": [...]}。同时接受二者，但拒绝其它隐式结构。
    if isinstance(record, list):
        dialog = record
    elif isinstance(record, dict) and isinstance(record.get("dialog"), list):
        dialog = record["dialog"]
    else:
        raise ValueError(f"JSONL第{line_number}行既不是对话数组，也不含dialog数组")
    if not dialog or any(not isinstance(item, str) for item in dialog):
        raise ValueError(f"JSONL第{line_number}行dialog为空或含非字符串元素")
    return dialog


def build(source: Path, output: Path) -> dict[str, object]:
    dialogs: list[str] = []
    utterance_count = 0
    with gzip.open(source, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            dialog = extract_dialog(json.loads(line), line_number)
            cleaned = [re.sub(r"\s+", "", utterance) for utterance in dialog]
            if any(not utterance for utterance in cleaned):
                raise ValueError(f"JSONL第{line_number}行清洗后出现空话语")
            dialogs.append("\n".join(cleaned))
            utterance_count += len(cleaned)

    if len(dialogs) != EXPECTED_RECORDS:
        raise ValueError(f"记录数错误：期望 {EXPECTED_RECORDS}，实际 {len(dialogs)}")

    text = "\n\n".join(dialogs) + "\n"
    output.write_text(text, encoding="utf-8", newline="\n")
    return {
        "source_url": SOURCE_URL,
        "source_sha256": sha256(source),
        "records": len(dialogs),
        "utterances": utterance_count,
        "utf16_length": len(text.encode("utf-16-le")) // 2,
        "unicode_codepoints": len(text),
        "han_characters": len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text)),
        "output_sha256": sha256(output),
        "cleaning": "删除每句话语内部的全部Unicode空白；话语间一个LF，对话间两个LF；文件末尾一个LF",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / "lccc_base_test.jsonl.gz"
    output = output_dir / "lccc_base_test_clean.txt"
    report = output_dir / "构建报告.json"

    download_if_needed(source)
    result = build(source, output)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
