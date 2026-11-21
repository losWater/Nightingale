"""定制词库：在用户自己的魔然固定码表里，把单字换成夜桜的单字，其余（词、占位符、码、顺序、表头）一律不动（作者 2026-10-15：他可能有飞键，不改他的码）。
- 删去原表里的单字条目（汉字单字；②③④ 等占位符号保留）；
- 夜桜单字（yozakura/tables/字词表.txt 里的单字，含 ü 码、彩蛋码）按夜桜同码顺序放入，与他的条目同码时按夜桜字词让位规则（release/make_ciku.py）：
  一二码位字在前；三码位词频超过字频 1000 倍才让；四码位字有更短的码或词频超过字频 16 倍才让；
  字全部可让时：他的第一个词 → 夜桜的字 → 他其余条目（原顺序）；否则字在前。他的条目之间顺序始终不变；
- 第三列 stem 填该字该读音的四码全码（魔然造词按 stem 取码）。
用法：.venv/bin/python yozakura/定制/make_custom.py <他的 moran_fixed_simp.dict.yaml> [输出]
"""
import collections, json, sys, unicodedata
import yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
src = Path(sys.argv[1]); out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / 'Downloads/夜桜定制_moran_fixed_simp.dict.yaml'
head, body = src.read_text(encoding='utf-8').split('\n...\n', 1)
is_char = lambda t: len(t) == 1 and unicodedata.category(t) == 'Lo'          # 汉字单字；①②③④ 是 No，保留

ours = collections.defaultdict(list); full = collections.defaultdict(list)
for l in open(ROOT / 'yozakura/tables/字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')[:2]
    if len(t) == 1:
        ours[c].append(t)
        if len(c) == 4: full[t].append(c)


# 字频（读音、每百万，夜桜引擎输入）与词频（虎码词库，每百万；查不到按 0.5），同 make_ciku
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode
E = yaml.load(open(ROOT / 'build/out/zr31/elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
tot = sum(e['频率'] for e in E if e['拼音'] != 'reserved'); rf = collections.Counter()
for e in E:
    if e['拼音'] != 'reserved': rf[(e['词'], encode(e['拼音'], 'ziranma'))] += e['频率'] / tot * 1e6
wt = {}
for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and not l.startswith('#') and p[1].isdigit() and len(p[0]) > 1: wt[p[0]] = max(wt.get(p[0], 0), int(p[1]))
wtot = sum(wt.values())
wfreq = lambda w: wt[w] / wtot * 1e6 if w in wt else 0.5
allcodes = collections.defaultdict(list)
for c, ts in ours.items():
    for t in ts: allcodes[t].append(c)


def can_yield(ch, code, w):
    if len(code) <= 2 or is_char(w) or not any('\u3400' <= x <= '\u9fff' for x in w): return False
    cf = max(rf.get((ch, code[:2]), 0), 0.01 if len(code) == 3 else 1e-3)
    if len(code) == 3: return wfreq(w) / cf > 1000
    if any(len(x) < 4 and x[:2] == code[:2] for x in allcodes[ch]): return True
    return wfreq(w) / cf > 16


def stem(t, c):
    cands = [f for f in full[t] if f[:len(c)] == c[:2] or (len(c) == 1 and f[0] == c)] or full[t]
    return cands[0] if cands else ''


lines = body.split('\n')
theirs = collections.defaultdict(list)        # 码 → [(行, 是否单字)]
order, other, dropped = [], [], 0
for l in lines:
    x = l.split('\t')
    if l.strip() and not l.startswith('#') and len(x) >= 2:
        if is_char(x[0]): dropped += 1; continue
        if x[1] not in theirs: order.append(x[1])
        theirs[x[1]].append(l)
    else:
        other.append(l)                        # 注释、空行（放在词库段之前，保持原样）
codes = sorted(set(theirs) | set(ours), key=lambda c: (order.index(c) if c in theirs else 10 ** 9, c))
pos = {c: i for i, c in enumerate(order)}
codes = order + sorted(set(ours) - set(theirs))
moved = collections.Counter(); yielded = collections.Counter(); out_lines = []
for c in codes:
    mine = [f'{t}\t{c}\t{stem(t, c)}' if stem(t, c) not in ('', c) else f'{t}\t{c}' for t in ours.get(c, [])]
    rest = theirs.get(c, [])
    if mine and rest:
        w = rest[0].split('\t')[0]
        if all(can_yield(t, c, w) for t in ours[c]):
            out_lines += rest[:1] + mine + rest[1:]; yielded[len(c)] += 1; continue
        moved[len(c)] += 1
    out_lines += mine + rest
first = [l for l in other if l.strip()]
out.write_text(head + '\n...\n' + '\n'.join(other) + '\n' + '\n'.join(out_lines) + '\n', encoding='utf-8')
print(f'输出 {out}：去掉他的单字 {dropped} 条，放入夜桜单字 {sum(len(v) for v in ours.values())} 条；他的其他条目 {sum(len(v) for v in theirs.values())} 条原样保留')
print('同码位：字在前', dict(sorted(moved.items())), '；字让他的第一个词', dict(sorted(yielded.items())))
