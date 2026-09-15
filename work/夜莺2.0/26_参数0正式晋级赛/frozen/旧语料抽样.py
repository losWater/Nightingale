# -*- coding: utf-8 -*-
"""从多源原始语料抽取句子并按句长均分抽样。

规则（按群友规格）：
  - 以。！？；换行切句，取句内汉字串计长；
  - 只保留汉字长度1—30的句子；
  - 避生僻字：全部汉字须在通用规范汉字表8105内；
  - 各长度桶均分抽样，桶内跨来源轮转，保证体裁混合；
  - 固定随机种子，可复现。

输出TSV：length  source  sentence(原句)  hanzi(仅汉字串)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import zipfile
from collections import defaultdict
from pathlib import Path

HAN = re.compile(r"[一-鿿]")
SPLIT = re.compile(r"[。！？；!?\n\r]+")
# 含字母数字的句子多为混排/代码/公式，直接放弃
ALNUM = re.compile(r"[A-Za-z0-9]")


def sentences_from_text(text: str):
    for raw in SPLIT.split(text):
        raw = raw.strip()
        if not raw or ALNUM.search(raw):
            continue
        hanzi = "".join(HAN.findall(raw))
        if 1 <= len(hanzi) <= 30:
            yield raw, hanzi


def iter_wiki(path: Path, limit: int):
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = obj.get("completion") or obj.get("text") or ""
            for pair in sentences_from_text(text):
                yield pair
                n += 1
                if n >= limit:
                    return


TAG = re.compile(r"<[^>]+>")


def iter_media_zip(path: Path, limit: int):
    """传媒库：单个超大JSONL（title/content，正文含HTML标签），流式逐行。"""
    n = 0
    with zipfile.ZipFile(path) as z:
        info = max(z.infolist(), key=lambda i: i.file_size)
        with z.open(info) as f:
            buf = b""
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                buf += chunk
                *lines, buf = buf.split(b"\n")
                for raw_line in lines:
                    try:
                        obj = json.loads(raw_line.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        continue
                    text = TAG.sub("", f"{obj.get('title', '')}。{obj.get('content', '')}")
                    for pair in sentences_from_text(text):
                        yield pair
                        n += 1
                        if n >= limit:
                            return


def iter_lccc_zip(path: Path, limit: int):
    """LCCC为超大JSON（对话字符串嵌套列表），流式扫描引号串，词间空格去除。"""
    utt_re = re.compile(r'"((?:[^"\\]|\\.)*)"')
    n = 0
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".json"):
                continue
            with z.open(name) as f:
                tail = ""
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    text = tail + chunk.decode("utf-8", errors="replace")
                    last = text.rfind('"')
                    body, tail = text[:last], text[last:]
                    for m in utt_re.finditer(body):
                        for pair in sentences_from_text(m.group(1).replace(" ", "")):
                            yield pair
                            n += 1
                            if n >= limit:
                                return
            return  # 单个json已足够


def iter_parquet(path: Path, limit: int):
    import pyarrow.parquet as pq
    n = 0
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=2000):
        col = None
        for cand in ("text", "content", "completion"):
            if cand in batch.schema.names:
                col = batch.column(cand)
                break
        if col is None:
            return
        for v in col:
            for pair in sentences_from_text(str(v)):
                yield pair
                n += 1
                if n >= limit:
                    return


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw_dir", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--per-bucket", type=int, default=334, help="每个句长桶抽样数")
    ap.add_argument("--per-source-cap", type=int, default=400000, help="每源最多抽取候选句数")
    ap.add_argument("--charset", type=Path, required=True, help="8105字表，一行一字")
    ap.add_argument("--seed", type=int, default=20260830)
    args = ap.parse_args()

    charset = set(args.charset.read_text(encoding="utf-8").split())
    sources = {
        "百科": (iter_wiki, args.raw_dir / "wikipedia-cn.jsonl"),
        "传媒": (iter_media_zip, args.raw_dir / "传媒领域语料库.zip"),
        "对话": (iter_lccc_zip, args.raw_dir / "LCCC-large.zip"),
        "网文": (iter_parquet, args.raw_dir / "fineweb_skypile_00000.parquet"),
    }
    rng = random.Random(args.seed)
    buckets: dict[tuple[int, str], list] = defaultdict(list)
    for tag, (fn, path) in sources.items():
        if not path.exists():
            print(f"跳过缺失来源: {tag} {path}")
            continue
        count = 0
        seen = set()
        for raw, hanzi in fn(path, args.per_source_cap):
            if hanzi in seen or any(c not in charset for c in hanzi):
                continue
            seen.add(hanzi)
            # 蓄水池按桶抽样，每桶每源最多per_bucket条候选
            key = (len(hanzi), tag)
            pool = buckets[key]
            count += 1
            if len(pool) < args.per_bucket:
                pool.append((raw, hanzi))
            else:
                j = rng.randrange(count)
                if j < args.per_bucket:
                    pool[j] = (raw, hanzi)
        print(f"{tag}: 有效候选句 {count:,}")

    tags = [t for t in sources if any((l, t) in buckets for l in range(1, 31))]
    rows = []
    for length in range(1, 31):
        picked = []
        pools = {t: list(buckets.get((length, t), [])) for t in tags}
        for t in tags:
            rng.shuffle(pools[t])
        # 轮转各来源取句，直到该桶抽满
        while len(picked) < args.per_bucket and any(pools.values()):
            for t in tags:
                if pools[t] and len(picked) < args.per_bucket:
                    raw, hanzi = pools[t].pop()
                    picked.append((length, t, raw, hanzi))
        rows.extend(picked)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        f.write("length\tsource\tsentence\thanzi\n")
        for length, tag, raw, hanzi in rows:
            f.write(f"{length}\t{tag}\t{raw}\t{hanzi}\n")
    from collections import Counter
    dist = Counter(r[0] for r in rows)
    srcdist = Counter(r[1] for r in rows)
    print(f"总句数 {len(rows):,}")
    print("句长分布:", dict(sorted(dist.items())))
    print("来源分布:", dict(srcdist))


if __name__ == "__main__":
    main()
