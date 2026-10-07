"""夜莺 3.0 字词表与综合表（第一版草稿）。
- 词：2.5 字词表的全部多字词条，词与词的顺序原样保留（词码只看双拼，与字根无关）；作者指定的调换见 data/inputs/3.0词序调整.json。
- 字：3.0 普通单字表（去掉符号表条目），字与字按 3.0 顺序。
- 特殊码：保留 莺 by、鹤 eh（自定义码），剧 jv、绪 xv（ü 容错）；ü 三码容错（予居欲狙羽郁巨，这些字没有三简）按 3.0 全码重新推导：ü 写 v + 全码第三码；
  依赖 2.5 字根的容错与 六 lqq 去掉。
- 同码排序（2.5 规则第五节、五之六，作者 2026-10-07 修订）：
  同码的字全部可让给首个词才让：词₁ → 字… → 其余词（最多一个词排到字前）；否则字在前。
  短码位（<4 码）：常用字不让（字的简码不让位）；其余字可让 ⇔ 简词频率 > 字频 × 16。
  全码位·二字词：字可让 ⇔ 该读音有简码，或 词频 > 字频 × 16。
  全码位·三字及以上词：常用字不让（2.5 规则 5a）；其余字可让 ⇔ 词频 > 字频 × 16。
  “常用字” = 通规字中该读音字频 ≥ 0.1/百万（YZ_PROTECT=freq，作者 2026-10-07 定，三码位与长词同一口径）。
  一简、二简一律不让；彩蛋码（莺 by、鹤 eh）固定首位；容错码一律排在词后。
  字频按读音、每百万；词频取虎码词库，查不到按 0.5。
- 综合表 = 字词表 + 符号表 + 快符（同夜莺 2.5 tools/maintenance/export.py）。
用法：.venv/bin/python release/make_ciku.py [输出目录]
"""
import collections, csv, json, math, re, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

N25 = Path.home() / 'Nightingale/夜莺2.5'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'release/tables'
RATIO, WORD_DEFAULT, FLOOR = 16, 0.5, 1e-3


def rd(p):
    return [tuple(l.rstrip('\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


W25 = rd(N25 / '主表/字词表.txt')
SYM = rd(N25 / '主表/符号表.txt'); SYMSET = set(SYM)
D30 = [r for r in rd(ROOT / 'release/tables/夜莺3.0_NB46_普通单字表.txt') if r not in SYMSET]

# ---- 频率 ----
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
tot = sum(e['频率'] for e in E if e['拼音'] != 'reserved')
rf = collections.Counter()
for e in E:
    if e['拼音'] == 'reserved': continue
    try: rf[(e['词'], encode(e['拼音'], 'xiaohe'))] += e['频率'] / tot * 1e6
    except Exception: pass
wt = {}
for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and not l.startswith('#') and p[1].isdigit() and len(p[0]) > 1:
        wt[p[0]] = max(wt.get(p[0], 0), int(p[1]))
wtot = sum(wt.values())
wfreq = lambda w: wt[w] / wtot * 1e6 if w in wt else None
ONE = {(c, encode(p, 'xiaohe')) for c, p, n in json.load(open(ROOT / 'data/inputs/3.0一二简.json', encoding='utf-8'))['fixed'] if n == 1}

# “不让位的字”口径（环境变量 YZ_PROTECT）：level12 = 通规一、二级字（默认）；freq = 通规 8105 中字频 ≥ 0.1/百万的读音
LEVEL = {}
for _n in (1, 2, 3):
    for _l in open(ROOT / f'data/inputs/通规分级/level-{_n}.txt', encoding='utf-8'):
        if _l.strip(): LEVEL[_l.strip()] = _n
import os
PROTECT = os.environ.get('YZ_PROTECT', 'freq')     # 作者 2026-10-07 定：三码位与长词都用 freq


def protected(ch, sy):
    if PROTECT == 'freq': return ch in LEVEL and rf.get((ch, sy), 0) >= 0.1
    return LEVEL.get(ch, 9) <= 2

# ---- 字 ----
chars = collections.defaultdict(list)
for t, c in D30: chars[c].append(t)
codes_of = collections.defaultdict(set)
for t, c in D30: codes_of[t].add(c)
special = []                                                    # (字, 码, 类型)
TOLERANCE = set()                                               # 容错码条目（一律排在词后）
CUSTOM = {('莺', 'by'), ('鹤', 'eh')}                            # 自定义码（彩蛋）固定在首位
for t, c, kind in [('莺', 'by', '自定义码'), ('鹤', 'eh', '自定义码'), ('剧', 'jv', '容错码'), ('绪', 'xv', '容错码')]:
    assert not chars.get(c), (c, chars.get(c))
    chars[c].append(t); special.append((t, c, kind))
    if kind == '容错码': TOLERANCE.add((t, c))
skipped = []
for t in '予居欲狙羽郁巨':
    full = sorted(c for c in codes_of[t] if len(c) == 4 and c[1] == 'u' and c[0] in 'jqxy')   # 2.5 做法：ü 写 v + 全码第三码
    if full and not chars.get(full[0][0] + 'v' + full[0][2]):
        c = full[0][0] + 'v' + full[0][2]; chars[c].append(t); special.append((t, c, '容错码')); TOLERANCE.add((t, c))
    else:
        skipped.append(t)

# ---- 词 ----
words = collections.defaultdict(list)
for t, c in W25:
    if len(t) > 1: words[c].append(t)
for c, w, before in json.load(open(ROOT / 'data/inputs/3.0词序调整.json', encoding='utf-8'))['提前']:   # 作者指定的词序调整
    ws = words[c]; assert w in ws and before in ws, (c, w, before)
    ws.remove(w); ws.insert(ws.index(before), w)


def has_short(ch, sy):
    return (ch, sy) in ONE or any(len(x) < 4 and x[:2] == sy for x in codes_of[ch])


def can_yield(ch, code, w):
    sy = code[:2]
    if len(code) == 4 and len(w) == 2 and has_short(ch, sy): return True, '有简码'
    if (ch, code) in TOLERANCE: return True, '容错码'
    if (ch, code) in CUSTOM: return False, '自定义码（彩蛋）'
    if len(code) <= 2: return False, '一二简不让'
    if (len(code) < 4 or len(w) > 2) and protected(ch, sy): return False, '常用字不让'
    cf = rf.get((ch, sy), 0); wf = wfreq(w)
    r = (wf if wf is not None else WORD_DEFAULT) / max(cf, FLOOR)
    return r > RATIO, f'{r:.1f}倍'


# ---- 合并 ----
table, log, overflow = [], [], []
for code in sorted(set(chars) | set(words)):
    C, W = chars.get(code, []), words.get(code, [])
    if len(code) < 4 and C and len(W) > 2: overflow.append((code, C, W))
    if not C or not W:
        order = C + W
    else:
        dec = [can_yield(ch, code, W[0]) for ch in C]
        if all(ok for ok, _ in dec):
            order = [W[0]] + C + W[1:]
        else:
            order = C + W
        log.append((code, C, W[0], dec, order[0]))
    table += [(t, code) for t in order]

OUT.mkdir(parents=True, exist_ok=True)
(OUT / '夜莺3.0_NB46_字词表.txt').write_text(''.join(f'{t}\t{c}\n' for t, c in table), encoding='utf-8')

# 综合表：字词表 + 符号 + 快符
groups = collections.defaultdict(list)
for t, c in table + SYM: groups[c].append(t)
for line in (N25 / '主表/快符.txt').read_text(encoding='utf-8-sig').splitlines():
    m = re.fullmatch(r'([a-z]+),(\d+)=(.+)', line)
    code, pos, text = m.group(1), int(m.group(2)), m.group(3)
    if text in groups[code]: groups[code].remove(text)
    assert 1 <= pos <= len(groups[code]) + 1, ('快符候选位超出范围', line)
    groups[code].insert(pos - 1, text)
combined = [(t, c) for c in sorted(groups) for t in groups[c] if not t.startswith('$ddcmd(')]
(OUT / '夜莺3.0_NB46_综合表.txt').write_text(''.join(f'{t}\t{c}\n' for t, c in combined), encoding='utf-8')
(OUT / '夜莺3.0_NB46_综合表_码前.txt').write_text(''.join(f'{c}\t{t}\n' for t, c in combined), encoding='utf-8')

# ---- 报告 ----
n_words = sum(len(v) for v in words.values()); n_out_words = sum(1 for t, c in table if len(t) > 1)
assert n_words == n_out_words, (n_words, n_out_words)
print('字词表', len(table), '条（字', sum(1 for t, c in table if len(t) == 1), '词', n_out_words, '）；综合表', len(combined), '条')
print('特殊码', special, '；未能推导的 ü 容错', ''.join(skipped))
print('短码位简词超上限', len(overflow), '；全码位字词同码按规则判定', len(log), '处，其中词占首选', sum(1 for x in log if len(x[4]) > 1))
json.dump({'特殊码': special, 'ü容错未推导': skipped, '超上限': overflow,
           '全码位判定': [(c, C, w, [list(d) for d in dec], first) for c, C, w, dec, first in log]},
          open(OUT / '夜莺3.0_NB46_字词表_说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
