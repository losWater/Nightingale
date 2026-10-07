"""导出可视化调根工具的数据（与 construct/model.py 同口径）。"""
import json, sys, os, glob
import numpy as np
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../neighborhood'))
import model as MD, forces as FO
import engine_eval as E

out_path = sys.argv[1]
G = MD.G; N = MD.N
flags = np.zeros(N, int)
T300 = np.zeros(N, bool); T300[MD.META['tier_indices']['300']] = True
T500 = np.zeros(N, bool); T500[MD.META['tier_indices']['500']] = True
ONE = np.array([e.get('简码长度') == 1 for e in FO.E[:N]])
for bit, arr in enumerate([MD.t1521, MD.t3571, MD.TOP, MD.REST, MD.FOUR, MD.SANI, MD.fixed, T300, T500, ONE]):
    flags |= arr.astype(int) << bit
R = [[E_['词'], E_['拼音'], FO.syl[i], int(MD.G1[i]), int(MD.G2[i]), float(MD.fr[i]), int(flags[i])] for i, E_ in enumerate(FO.E[:N])]
words = {}
for x in FO.WD:
    words.setdefault(x['码'], []).append([x['词'], x['排名']])
c = {x['moved']: x['layout'] for x in json.load(open(MD.ROOT / 'neighborhood/curve.json'))}
w65 = {x['moved']: x['layout'] for x in json.load(open(MD.ROOT / 'neighborhood/w65.json'))}
pr = json.load(open(MD.ROOT / 'construct/prefs_syllable.json', encoding='utf-8'))
layouts = {'喜好第一名': pr['layout'], 'NB46': c[46], 'W55': w65[55], '2.5': MD.B, '退火冠军': E.champion()}
data = {
    'groups': [{'id': g, 'roots': MD.META['groups'][g], 'b25': MD.B[g]} for g in G],
    'readings': R,
    'words': words,
    'flag': {f: MD.FLAG[f].round(4).tolist() for f in ('eq', 'ms', 'pd')},
    'cal': MD.CAL,
    'score': {k: list(v) for k, v in MD.SCORE.items()},
    'low': MD.LOW,
    'mutex': [int(MD.GB), int(MD.GC)],
    'layouts': layouts,
    'prefs': {g: pr['prefs'][g]['排名'] for g in G},
}
# 扩展字与符号表（与 build/make_plain_table.py 同规则：2.5 单字表中 8105 以外、正式全码的字；符号沿用 2.5 原码）
from pathlib import Path as _P
N25 = _P.home() / 'Nightingale/夜莺2.5'
splits = json.load(open(MD.ROOT / 'data/baseline/splits.json', encoding='utf-8'))
old_keys = json.load(open(MD.ROOT / 'data/baseline/root_key.json', encoding='utf-8'))
splits25 = json.load(open(MD.ROOT / 'data/baseline/splits_2.5.json', encoding='utf-8'))   # 核对扩展字的 2.5 码用
g_of = {r: g for g, rs in MD.META['groups'].items() for r in rs}
GI = {g: i for i, g in enumerate(G)}
core = {e['词'] for e in FO.E[:N]}
sys.path.insert(0, str(MD.ROOT / 'lib'))
from shuangpin import encode as _enc
VALID = {_enc(py, 'xiaohe') for py in json.load(open(MD.ROOT / 'data/inputs/全音节映射.json', encoding='utf-8'))['小鹤']}
ext = []
for l in open(N25 / '主表/单字表.txt', encoding='utf-8-sig'):
    p_ = l.rstrip('\n').split('\t')
    if len(p_) < 2 or len(p_[0]) != 1 or p_[0] in core or len(p_[1]) != 4 or p_[0] not in splits:
        continue
    rs = splits[p_[0]]
    if p_[1][:2] not in VALID:
        continue
    rs25 = splits25.get(p_[0], rs)
    if p_[1][2:] != old_keys[rs25[0][0]] + old_keys[rs25[-1][0]]:
        continue
    ext.append([p_[0], p_[1][:2], GI[g_of[rs[0][0]]], GI[g_of[rs[-1][0]]]])
data['ext'] = ext
data['sym'] = [l.rstrip('\n').split('\t')[:2] for l in open(N25 / '主表/符号表.txt', encoding='utf-8-sig') if len(l.rstrip('\n').split('\t')) >= 2]
data['oneTwo'] = [e.get('简码长度') or 0 for e in FO.E[:N]]
# 形码盒子字频序（按字，码圈惯例）；不在盒子字表里的记 0
_box = {}
for _l in open(MD.ROOT / 'eval/box/默认字频.txt', encoding='utf-8'):
    _p = _l.rstrip('\n').split('\t')
    if len(_p) >= 2 and _p[0] not in _box: _box[_p[0]] = len(_box) + 1
data['boxRank'] = [_box.get(e['词'], 0) for e in FO.E[:N]]
json.dump(data, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
# 供 JS 核对的参考值
ref = {}
for n, l in layouts.items():
    F, S, m = MD.score(l)
    ref[n] = {'S': S, 'pen': int(m['pen']), '形码成本': m['形码成本'], '三简': m['三简'], '四码': m['四码'], 'p占比': m['p占比'],
              '撞码': [int(x) for x in m['撞码']], '1521重': int(m['1521重']), '3571重': int(m['3571重']),
              '小指干扰%': m['小指干扰%'], '同指大跨排%': m['同指大跨排%'], '键均当量': m['键均当量'], '换键根组': int(m['换键根组'])}
json.dump(ref, open(out_path.replace('.json', '_ref.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('读音', N, '词码', len(words), '大小', os.path.getsize(out_path) // 1024, 'KB')
