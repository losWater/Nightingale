"""字词撞码（作者 2026-10-01 标准）：只算二字词（虎码秃版词库，按词频排序）。
“按实际打”：读音若有一二三简（码长<4 且非全码），不算撞；只有必须打全码的读音，其全码等于某词码才算撞。
规则：①前1500字 × 前1万词 = 0（硬）；②前1500字 × 前3万词 尽量低；③前3500字 × 前1万词 尽量低。
词码 = 两字音节双拼（pypinyin 按词组定音）。"""
import json, sys, collections
from pathlib import Path
import warnings; warnings.filterwarnings('ignore')
from pypinyin import lazy_pinyin
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

def top_words(scheme, n_max=30000):
    ws = []
    for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2 and not l.startswith('#') and p[1].isdigit() and len(p[0]) == 2:
            ws.append((int(p[1]), p[0]))
    ws.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for w, word in ws:
        if word in seen: continue
        seen.add(word)
        py = lazy_pinyin(word, errors=lambda t: ['?'] * len(t))
        try:
            code = encode(py[0], scheme) + encode(py[1], scheme)
        except Exception:
            continue
        out.append((word, code))
        if len(out) >= n_max: break
    return out

def clashes(typed4, words, n_words, idx):
    """typed4: {读音序号: 必须打全码时的全码}；返回 [(字读音序号, 词)]"""
    by = collections.defaultdict(list)
    for word, code in words[:n_words]:
        by[code].append(word)
    return [(i, by[typed4[i]]) for i in idx if i in typed4 and typed4[i] in by]
