#!/usr/bin/env python3
"""刷新0.8.5字根展示与发布清单输出哈希。"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.8.5"
TABLES = RELEASE / "01_正式码表"
ATTACHMENTS = RELEASE / "02_输入法挂接"
ROOTS = RELEASE / "03_字根与拆分"
TOOLS = RELEASE / "04_查询与练习"
MAINTENANCE = RELEASE / "05_维护与裁决"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root_table = ROOTS / "夜莺码v0.8.5字根表.html"
    text = root_table.read_text(encoding="utf-8")
    if not re.search(r'\["争字底","[^"]*"\],\["秉",""\]', text):
        text, count = re.subn(
            r'(\["争字底","[^"]*"\])',
            r'\1,["秉",""]', text, count=1,
        )
        if count != 1:
            raise SystemExit("字根表中未找到争字底锨定记录")
    text, count = re.subn(r',\["秉",""\](?=,\["皮","")', '', text, count=1)
    if count != 1 and text.count('["秉",""]') != 1:
        raise SystemExit("字根表中秉条目数异常")
    text = re.sub(r'(\["毛",")[^"]*("\])', r'\1\2', text, count=1)
    root_table.write_text(text, encoding="utf-8", newline="\n")

    practice = TOOLS / "夜莺码v0.8.5字根练习.txt"
    practice_text = practice.read_text(encoding="utf-8")
    practice_text, count = re.subn(r'^毛\tm\t.*$', '毛\tm\t', practice_text, count=1, flags=re.M)
    if count != 1:
        raise SystemExit("字根练习表中未找到毛根")
    practice.write_text(practice_text, encoding="utf-8", newline="\n")

    manifest_path = RELEASE / "发布清单.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    word_master = TABLES / "夜莺0.8.5字词表.txt"
    if word_master.is_file():
        word_rows = [line.split("\t", 1) for line in word_master.read_text(encoding="utf-8-sig").splitlines() if line]
        manifest["counts"]["reverse_lookup_codes"] = len({code for _text, code in word_rows})
        manifest["counts"]["reverse_lookup_entries"] = len(word_rows)
    manifest["outputs"] = {
        path.relative_to(RELEASE).as_posix(): sha256(path)
        for path in sorted(RELEASE.rglob("*"))
        if path.is_file()
        and path != manifest_path
        and "99_参考资料" not in path.relative_to(RELEASE).parts
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("字根表与发布清单已刷新")


if __name__ == "__main__":
    main()
