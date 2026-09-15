# -*- coding: utf-8 -*-
"""用方案的真实挂接码表（手心“码=位,候选”格式）在语料上模拟打字，统计码长。

打法规则（按群友规格）：
  - 贪心最长词优先分词（词典即码表内全部纯汉字多字候选）；
  - 词候选位≤3：直接取（码长+1键上屏/选重）；
  - 二字词候选位>3且允许辅助码时：按目标词任一字的首根辅一码，
    辅后位≤3则取（4码+辅1+1键）；辅首/辅尾取更优者；
  - 仍取不到则整词放弃，退回拆单；
  - 单字取候选位≤3的最短码（码长+1键）；>3选时用全码翻页（码长+2键）。

码长＝总击键数÷总汉字数。标点不计。输出整体与分体裁统计及打法构成。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HANWORD = re.compile(r"^[一-鿿]+$")
XINXIN = re.compile(r"^([a-z;,./']+)=(\d+),(.+)$")   # 手心：码=位,候选
SOGOU = re.compile(r"^([a-z;,./']+),(\d+)=(.+)$")    # 搜狗：码,位=候选


def decode_any(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def load_table(path: Path, fmt: str = "xinxin"):
    """fmt: xinxin|sogou|plain。plain为“候选\\t码”，同码按行序定候选位。"""
    code_cands: dict[str, list[tuple[int, str]]] = defaultdict(list)
    word_codes: dict[str, list[tuple[str, int]]] = defaultdict(list)
    seen_per_code: Counter = Counter()
    for line in decode_any(path).splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "---")):
            continue
        if fmt == "plain":
            row = line.split()
            if len(row) < 2:
                continue
            cand, code = row[0], row[1]
            if not code.isascii() or code.isdigit():
                continue
            seen_per_code[code] += 1
            pos = seen_per_code[code]
        else:
            m = (XINXIN if fmt == "xinxin" else SOGOU).match(line)
            if not m:
                continue
            code, pos, cand = m.group(1), int(m.group(2)), m.group(3)
        code_cands[code].append((pos, cand))
        if HANWORD.fullmatch(cand):
            word_codes[cand].append((code, pos))
    for cands in code_cands.values():
        cands.sort()
    return code_cands, word_codes


def load_aux(path: Path, index: int):
    aux = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        r = line.split()
        if len(r) >= 2 and len(r[0]) == 1 and len(r[1]) > index:
            aux.setdefault(r[0], r[1][index])
    return aux


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("table", type=Path, help="手心挂接码表（码=位,候选）")
    ap.add_argument("corpus", type=Path, help="语料TSV（length source sentence hanzi）")
    ap.add_argument("output", type=Path)
    ap.add_argument("--aux-table", type=Path, help="单字全码表，用于辅助码模拟")
    ap.add_argument("--aux-index", type=int, default=2)
    ap.add_argument("--max-word", type=int, default=8)
    ap.add_argument("--no-aux", action="store_true", help="关闭辅助码模拟")
    ap.add_argument("--format", choices=["xinxin", "sogou", "plain"], default="xinxin")
    args = ap.parse_args()

    code_cands, word_codes = load_table(args.table, args.format)
    aux = load_aux(args.aux_table, args.aux_index) if args.aux_table and not args.no_aux else {}

    def word_cost(word: str):
        """返回 (击键数, 方式, 候选位)；取不到返回None。"""
        best = None
        for code, pos in word_codes.get(word, ()):
            if pos <= 3:
                c = len(code) + 1
                if best is None or (c, pos) < (best[0], best[2]):
                    best = (c, "简词" if len(code) < 2 * min(len(word), 2) else "打词", pos)
        if best:
            return best
        if aux and len(word) == 2:
            # 全码4码的候选里做辅助码筛选
            for code, pos in word_codes.get(word, ()):
                if len(code) != 4:
                    continue
                for side in (0, 1):
                    k = aux.get(word[side])
                    if k is None:
                        continue
                    kept = [w for _, w in code_cands[code]
                            if HANWORD.fullmatch(w) and len(w) == 2
                            and (aux.get(w[0]) == k or aux.get(w[1]) == k)]
                    if word in kept and kept.index(word) + 1 <= 3:
                        return (6, "辅助码", kept.index(word) + 1)
        return None

    def char_cost(ch: str):
        """返回 (击键数, 候选位)；取不到返回None。"""
        best = None
        for code, pos in word_codes.get(ch, ()):
            if pos <= 3:
                c = len(code) + 1
                if best is None or (c, pos) < best:
                    best = (c, pos)
        if best is not None:
            return best
        full = [(code, pos) for code, pos in word_codes.get(ch, ()) if len(code) >= 4]
        if full:
            return (len(full[0][0]) + 2, 4)  # 翻页选重，记为4+
        return None

    stats = Counter()
    pos_stats = defaultdict(Counter)          # 打法 -> 候选位分布（按上屏次数）
    units_total = 0
    keys_total = chars_total = 0
    by_source = defaultdict(lambda: [0, 0])   # keys, chars
    by_length = defaultdict(lambda: [0, 0])
    skipped = 0
    for line in args.corpus.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        length, source, _, text = int(parts[0]), parts[1], parts[2], parts[3]
        if any(char_cost(c) is None for c in text):
            skipped += 1
            continue
        i, keys = 0, 0
        while i < len(text):
            done = False
            for size in range(min(args.max_word, len(text) - i), 1, -1):
                seg = text[i:i + size]
                got = word_cost(seg)
                if got:
                    keys += got[0]
                    stats[got[1]] += size
                    pos_stats[got[1]][got[2]] += 1
                    units_total += 1
                    i += size
                    done = True
                    break
            if not done:
                ck, cpos = char_cost(text[i])
                keys += ck
                stats["拆单"] += 1
                pos_stats["拆单"][cpos] += 1
                units_total += 1
                i += 1
        keys_total += keys
        chars_total += len(text)
        by_source[source][0] += keys
        by_source[source][1] += len(text)
        by_length[length][0] += keys
        by_length[length][1] += len(text)

    all_pos = Counter()
    for c in pos_stats.values():
        all_pos.update(c)
    reselect_units = sum(v for p, v in all_pos.items() if p > 1)

    report = {
        "table": str(args.table.resolve()),
        "corpus": str(args.corpus.resolve()),
        "aux_enabled": bool(aux),
        "sentences_skipped_missing_char": skipped,
        "总汉字数": chars_total,
        "总击键数": keys_total,
        "码长": keys_total / chars_total if chars_total else 0,
        "打法构成_按字数": dict(stats),
        "打法构成_占比": {k: v / chars_total for k, v in stats.items()},
        "上屏单位数": units_total,
        "选重": {
            "首选率": all_pos.get(1, 0) / units_total if units_total else 0,
            "候选位分布": {str(p): v / units_total for p, v in sorted(all_pos.items())},
            "选重率_非首选上屏占比": reselect_units / units_total if units_total else 0,
            "每百字选重次数": reselect_units / chars_total * 100 if chars_total else 0,
            "分打法候选位": {m: {str(p): v for p, v in sorted(c.items())}
                             for m, c in sorted(pos_stats.items())},
        },
        "分体裁码长": {s: k / c for s, (k, c) in sorted(by_source.items())},
        "分句长码长": {l: k / c for l, (k, c) in sorted(by_length.items())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "分句长码长"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
