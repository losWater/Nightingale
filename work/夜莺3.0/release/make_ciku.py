"""夜莺 3.0 字词表与综合表（第一版草稿）。
- 词：2.5 字词表的全部多字词条，词与词的顺序原样保留（词码只看双拼，与字根无关）；作者指定的调换见 data/inputs/词序调整.json。
- 字：3.0 普通单字表（去掉符号表条目），字与字按 3.0 顺序。
- 特殊码：保留 莺 by、鹤 eh（自定义码），剧 jv、绪 xv（ü 容错）；ü 三码容错（予居欲狙羽郁巨，这些字没有三简）按 3.0 全码重新推导：ü 写 v + 全码第三码；
  依赖 2.5 字根的容错与 六 lqq 去掉。
- 同码排序（2.5 规则第五节、五之六，作者 2026-10-07 修订）：
  同码的字全部可让给首个词才让：词₁ → 字… → 其余词（最多一个词排到字前）；否则字在前。
  短码位（<4 码）：字一律在前，简词排在字后（作者 2026-10-07：字重要，简码是给字的，简词是送的）。
  全码位·二字词：字可让 ⇔ 该读音有简码，或 词频 > 字频 × 16。
  全码位·三字及以上词：常用字不让（2.5 规则 5a）；其余字可让 ⇔ 词频 > 字频 × 16。
  长词里的“常用字” = 通规字中该读音字频 ≥ 0.1/百万（YZ_PROTECT=freq，作者 2026-10-07 定）。
  彩蛋码（莺 by、鹤 eh）固定首位；容错码一律排在词后。
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
sys.path.insert(0, str(ROOT / 'release'))
from config import C
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else C.TABLES
RATIO, WORD_DEFAULT, FLOOR = 16, 0.5, 1e-3


def rd(p):
    return [tuple(l.rstrip('\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


W25 = rd(N25 / '主表/字词表.txt')
SYM = rd(N25 / '主表/符号表.txt'); SYMSET = set(SYM)
D30 = [r for r in rd(C.T('普通单字表.txt')) if r not in SYMSET]

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
ONE = {(c, encode(p, 'xiaohe')) for c, p, n in json.load(open(ROOT / 'data/inputs/一二简.json', encoding='utf-8'))['fixed'] if n == 1}

# “不让位的字”口径（环境变量 YZ_PROTECT）：level12 = 通规一、二级字（默认）；freq = 通规 8105 中字频 ≥ 0.1/百万的读音
LEVEL = {}
for _n in (1, 2, 3):
    for _l in open(ROOT / f'data/inputs/通规分级/level-{_n}.txt', encoding='utf-8'):
        if _l.strip(): LEVEL[_l.strip()] = _n
import os
PROTECT = os.environ.get('YZ_PROTECT', 'freq')     # 作者 2026-10-07 定：三码位与长词都用 freq
SHORT_RATIO = float(os.environ.get('YZ_SHORT_RATIO', '1000'))   # 三码位：词频超过字频这么多倍才让词在前（作者 2026-10-08 定 1000）
PROTECT_MIN = float(os.environ.get('YZ_PROTECT_MIN', '0.1'))   # 读音字频门槛（每百万），低于它的通规字读音才按公式让位


def protected(ch, sy):
    if PROTECT == 'freq': return ch in LEVEL and rf.get((ch, sy), 0) >= PROTECT_MIN
    return LEVEL.get(ch, 9) <= 2

# ---- 字 ----
chars = collections.defaultdict(list)
for t, c in D30: chars[c].append(t)
codes_of = collections.defaultdict(set)
for t, c in D30: codes_of[t].add(c)
special = []                                                    # (字, 码, 类型)
TOLERANCE = set()                                               # 容错码条目（一律排在词后；ü 单字码不算，见下）
CUSTOM = {('莺', 'by'), ('鹤', 'eh')}                            # 自定义码（彩蛋）固定在首位
# ü 单字码（作者 2026-10-15）：jv 剧、jvb 居这些是正式打法（居 jubt 难按），不是容错，和彩蛋码一样算自定义码、固定字在首位（夜莺构建工具只认 全码/简码/容错码/自定义码/全码词/简词）
for t, c, kind in [('莺', 'by', '自定义码'), ('鹤', 'eh', '自定义码'), ('剧', 'jv', '自定义码'), ('绪', 'xv', '自定义码')]:
    assert not chars.get(c), (c, chars.get(c))
    chars[c].append(t); special.append((t, c, kind))
    CUSTOM.add((t, c))
skipped = []
for t in '予居欲狙羽郁巨':
    full = sorted(c for c in codes_of[t] if len(c) == 4 and c[1] == 'u' and c[0] in 'jqxy')   # 2.5 做法：ü 写 v + 全码第三码
    if full and not chars.get(full[0][0] + 'v' + full[0][2]):
        c = full[0][0] + 'v' + full[0][2]; chars[c].append(t); special.append((t, c, '自定义码')); CUSTOM.add((t, c))
    else:
        skipped.append(t)

# ---- 词 ----
words = collections.defaultdict(list)
for t, c in W25:
    if len(t) > 1: words[c].append(t)
ORDER = json.load(open(ROOT / 'data/inputs/词序调整.json', encoding='utf-8'))
for c, w, _ in ORDER.get('新增词', []):                                   # 作者新增的词（码按作者给的），排在该码原有的词后面
    assert w not in words[c], (c, w); words[c].append(w)
for c, w, before in ORDER['提前']:   # 作者指定的词序调整
    ws = words[c]; assert w in ws and before in ws, (c, w, before)
    ws.remove(w); ws.insert(ws.index(before), w)


KEEP = {(ch, c) for c, ch, _ in json.load(open(ROOT / 'data/inputs/词序调整.json', encoding='utf-8')).get('字不让', [])}   # 作者逐个指定不让位的字

# ü 容错词（作者 2026-10-08）：虎码词频前 TOL_TOP 的二字词，第一字 ju/qu/xu 可写 jv/qv/xv，第二字只有 ju 可写 jv；
# 新码上排在原有长词前面（长词让），与单字的冲突按二字词的让位规则（字有简码或词频超过字频 16 倍才让）。
TOL_TOP = int(os.environ.get('YZ_TOL_TOP', '20000'))
two_rank = {w: i for i, w in enumerate(sorted((w for w in wt if len(w) == 2), key=lambda w: -wt[w]), 1)}
tol_words = collections.defaultdict(list)
for t, c in sorted(((t, c) for t, c in W25 if len(t) == 2 and len(c) == 4 and two_rank.get(t, 10**9) <= TOL_TOP), key=lambda x: two_rank[x[0]]):
    heads = [c[:2]] + ([c[0] + 'v'] if c[0] in 'jqx' and c[1] == 'u' else [])
    tails = [c[2:]] + (['jv'] if c[2:] == 'ju' else [])
    for v in (h + s for h in heads for s in tails):
        if v != c and t not in tol_words[v]: tol_words[v].append(t)
for v, ts in tol_words.items():
    assert not any(len(w) == 2 for w in words.get(v, [])), (v, words.get(v))
    words[v] = ts + words.get(v, [])


def has_short(ch, sy):
    return (ch, sy) in ONE or any(len(x) < 4 and x[:2] == sy for x in codes_of[ch])


def can_yield(ch, code, w):
    sy = code[:2]
    if len(code) == 4 and len(w) == 2 and has_short(ch, sy): return True, '有简码'
    if (ch, code) in TOLERANCE: return True, '容错码'
    if (ch, code) in CUSTOM: return False, '自定义码 / ü码'
    if (ch, code) in KEEP: return False, '作者指定不让'
    if len(code) == 3:                                  # 作者 2026-10-08：三码位只在词频超过字频 SHORT_RATIO 倍时让给简词（生僻字占的空三简）
        r = (wfreq(w) or WORD_DEFAULT) / max(rf.get((ch, sy), 0), 0.01)   # 字频下限 0.01/百万（与作者看的统计同口径）
        if r > SHORT_RATIO: return True, f'三码位{r:.0f}倍'
    if len(code) <= 3: return False, '简码不让'          # 作者 2026-10-07：字重要，一二三简都是给字的，简词是送的
    if (len(code) < 4 or len(w) > 2) and protected(ch, sy): return False, '常用字不让'
    cf = rf.get((ch, sy), 0); wf = wfreq(w)
    r = (wf if wf is not None else WORD_DEFAULT) / max(cf, FLOOR)
    return r > RATIO, f'{r:.1f}倍'


# ---- 合并 ----
PINS = {c: ts for c, ts, _ in ORDER.get('钉选', [])}
if os.environ.get('YZ_PERSONAL'):                       # 作者个人调整里的钉选（只在本机个人版生效）
    PINS.update({c: ts for c, ts, _ in json.load(open(os.environ['YZ_PERSONAL'], encoding='utf-8')).get('钉选', [])})
table, log, overflow = [], [], []
for code in sorted(set(chars) | set(words)):
    C, W = chars.get(code, []), words.get(code, [])
    if len(code) < 4 and C and len(W) > 2: overflow.append((code, C, W))
    if not C or not W:
        order = C + W
    else:
        dec = [can_yield(ch, code, W[0]) for ch in C]
        if all(ok for ok, _ in dec):
            k = 1                                       # ü 容错词：字对几个容错词都该让，就排在它们全部后面
            while code in tol_words and k < len(W) and W[k] in tol_words[code] and all(can_yield(ch, code, W[k])[0] for ch in C): k += 1
            order = W[:k] + C + W[k:]
        else:
            order = C + W
        log.append((code, C, W[0], dec, order[0]))
    if code in PINS:                                    # 作者钉选：指定的几项按顺序排最前，其余原序
        assert all(x in order for x in PINS[code]), (code, PINS[code], order)
        order = PINS[code] + [x for x in order if x not in PINS[code]]
    table += [(t, code) for t in order]

OUT.mkdir(parents=True, exist_ok=True)
(OUT / '字词表.txt').write_text(''.join(f'{t}\t{c}\n' for t, c in table), encoding='utf-8')

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
(OUT / '综合表.txt').write_text(''.join(f'{t}\t{c}\n' for t, c in combined), encoding='utf-8')
(OUT / '综合表_码前.txt').write_text(''.join(f'{c}\t{t}\n' for t, c in combined), encoding='utf-8')

# ---- 报告 ----
n_words = sum(len(v) for v in words.values()); n_out_words = sum(1 for t, c in table if len(t) > 1)
assert n_words == n_out_words, (n_words, n_out_words)
print('字词表', len(table), '条（字', sum(1 for t, c in table if len(t) == 1), '词', n_out_words, '）；综合表', len(combined), '条')
print('特殊码', special, '；未能推导的 ü 容错', ''.join(skipped), '；ü 容错词', sum(len(v) for v in tol_words.values()), '条（', len(tol_words), '码）')
print('短码位简词超上限', len(overflow), '；全码位字词同码按规则判定', len(log), '处，其中词占首选', sum(1 for x in log if len(x[4]) > 1))
json.dump({'特殊码': special, 'ü容错未推导': skipped, 'ü容错词': {v: ts for v, ts in sorted(tol_words.items())}, '超上限': overflow,
           '全码位判定': [(c, C, w, [list(d) for d in dec], first) for c, C, w, dec, first in log]},
          open(OUT / '字词表_说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
