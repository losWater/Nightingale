"""辅助码对比：夜莺 / 简单鹤 / 魔然 / 魔虎，同一套字、读音、字频、词表，只换各方案自己的辅助码。
口径（作者 2026-10-17）：只统计“不加辅助码时不是首选”的字或词，逐个计数、不加权；加辅助码后成为首选的比例。
- 单字：同音节（拼音）分组，按读音字频排序；辅 1 键 / 2 键。
- 二字词：同双拼（两字音节）分组，按虎码词库词频排序；辅首字首根、辅末字首根、两字各一键、首字两键。
- 一个字有多个辅助码（如魔虎的容错码）时，打任何一个都能匹配；目标字按它的第一个（主）辅助码来打。
数据：夜莺 = 普通单字表全码后两位；简单鹤 = ~/Library/Rime/simple_crane.dict.yaml 四码后两位；
魔然 = rime-moran tools/data/moran_chai.txt；魔虎 = rime-mohu flypy 包 mohu_flypy.chars.dict.yaml（音节;辅助码）。
用法：.venv/bin/python eval/aux_compare.py
"""
import collections, json, sys, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode
AUX = Path.home() / '.cache/auxcmp'


def rd(p):
    return [l.rstrip('\n').split('\t') for l in open(p, encoding='utf-8-sig') if '\t' in l and not l.startswith('#')]


def table_after_dots(p):
    txt = Path(p).read_text(encoding='utf-8-sig')
    body = txt.split('\n...\n', 1)[1] if '\n...\n' in txt else txt
    return [l.split('\t') for l in body.splitlines() if '\t' in l and not l.startswith('#')]


# 各方案：(字, 小鹤音节) → [辅助码…]（主码在前）；魔然的辅助码与读音无关
def yeying():
    d = collections.defaultdict(list)
    for t, c in (r[:2] for r in rd(ROOT / 'release/tables/普通单字表.txt')):
        if len(t) == 1 and len(c) == 4 and c[2:] not in d[(t, c[:2])]: d[(t, c[:2])].append(c[2:])
    return d


def jdhe():
    d = collections.defaultdict(list)
    for r in table_after_dots(Path.home() / 'Library/Rime/simple_crane.dict.yaml'):
        t, c = r[0], r[1]
        if len(t) == 1 and len(c) == 4 and c.isalpha() and c[2:] not in d[(t, c[:2])]: d[(t, c[:2])].append(c[2:])
    return d


def mohu():
    d = collections.defaultdict(list)
    rows = sorted(table_after_dots(AUX / 'mohu_flypy.chars.dict.yaml'), key=lambda r: -float(r[2]) if len(r) > 2 and r[2].replace('.', '').isdigit() else 0)
    for r in rows:
        t, c = r[0], r[1]
        if len(t) == 1 and ';' in c:
            sy, a = c.split(';', 1)
            if len(a) == 2 and a not in d[(t, sy)]: d[(t, sy)].append(a)
    return d


def moran():
    d = collections.defaultdict(list)
    for r in rd(AUX / 'moran/tools/data/moran_chai.txt'):
        t, a = r[0], r[1]
        if len(t) == 1 and len(a) == 2 and a.isalpha() and a not in d[t]: d[t].append(a)
    return lambda ch, sy: d.get(ch, [])


SCHEMES = {'夜莺': yeying(), '简单鹤': jdhe(), '魔然': moran(), '魔虎': mohu()}
look = {k: (v if callable(v) else (lambda m: (lambda ch, sy: m.get((ch, sy), [])))(v)) for k, v in SCHEMES.items()}

# ---- 单字：通规 8105 各读音 ----
E = [e for e in yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader) if e['拼音'] != 'reserved']
lv = set()
for i in (1, 2, 3): lv |= {c for c in open(ROOT / f'data/inputs/通规分级/level-{i}.txt', encoding='utf-8').read().split() if len(c) == 1}
fr = collections.defaultdict(float)
for e in E:
    if e['词'] in lv: fr[(e['词'], encode(e['拼音'], 'xiaohe'))] += e['频率']
chars = sorted(((f, ch, sy) for (ch, sy), f in fr.items()), reverse=True)


def first_rank(cands, target):
    """cands: [(freq, item)] 已匹配的候选；目标是否第一。"""
    return max(cands)[1] == target if cands else False


def char_eval(scheme, n, k):
    L = look[scheme]
    by_sy = collections.defaultdict(list)
    for f, ch, sy in chars: by_sy[sy].append((f, ch))
    top = chars[:n] if n else chars
    need = [(f, ch, sy) for f, ch, sy in top if max(by_sy[sy])[1] != ch]
    ok = miss = 0
    for f, ch, sy in need:
        aux = L(ch, sy)
        if not aux: miss += 1; continue
        typed = aux[0][:k]
        cands = [(ff, cc) for ff, cc in by_sy[sy] if any(a[:k] == typed for a in L(cc, sy))]
        ok += first_rank(cands, ch)
    return len(need), ok, miss


# ---- 二字词 ----
wf = {}
for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and p[1].isdigit() and len(p[0]) == 2: wf[p[0]] = max(wf.get(p[0], 0), int(p[1]))
info = json.load(open(ROOT / 'release/tables/字词表_说明.json', encoding='utf-8'))
ucodes = set(info.get('ü容错词', {}))
words = sorted({(wf[t], t, c) for t, c in (r[:2] for r in rd(ROOT / 'release/tables/字词表.txt'))
                if len(t) == 2 and len(c) == 4 and c not in ucodes and wf.get(t, 0) > 0}, reverse=True)
WMODES = {'辅首字首根': lambda a, b: a[:1], '辅末字首根': lambda a, b: b[:1], '两字各一键': lambda a, b: a[:1] + b[:1], '首字两键': lambda a, b: a[:2]}


def word_eval(scheme, n, mode):
    L, key = look[scheme], WMODES[mode]
    by = collections.defaultdict(list)
    for f, w, c in words: by[c].append((f, w))
    top = words[:n] if n else words
    need = [(f, w, c) for f, w, c in top if max(by[c])[1] != w]
    ok = miss = 0
    for f, w, c in need:
        a, b = L(w[0], c[:2]), L(w[1], c[2:])
        if not a or not b: miss += 1; continue
        typed = key(a[0], b[0])
        cands = []
        for ff, ww in by[c]:
            aa, bb = L(ww[0], c[:2]), L(ww[1], c[2:])
            if any(key(x, y) == typed for x in aa or [''] for y in bb or ['']): cands.append((ff, ww))
        ok += first_rank(cands, w)
    return len(need), ok, miss


if __name__ == '__main__':
    print('【单字】不加辅助码就不是首选的字里，加辅助码后成为首选的比例（逐个计数）')
    for n, name in ((1500, '前1500字'), (3000, '前3000字'), (6000, '前6000字')):
        for k in (1, 2):
            row = []
            for s in SCHEMES:
                need, ok, miss = char_eval(s, n, k)
                row.append(f'{s} {ok / need * 100:5.1f}%' + (f'(缺{miss})' if miss else ''))
            print(f'  {name} 辅{k}键（需辅 {need} 字）：' + '  '.join(row))
    print('【二字词】不加辅助码就不是首选的词里，加辅助码后成为首选的比例（逐个计数）')
    for n, name in ((10000, '前1万词'), (30000, '前3万词')):
        for mode in WMODES:
            row = []
            for s in SCHEMES:
                need, ok, miss = word_eval(s, n, mode)
                row.append(f'{s} {ok / need * 100:5.1f}%' + (f'(缺{miss})' if miss else ''))
            print(f'  {name} {mode}（需辅 {need} 词）：' + '  '.join(row))
