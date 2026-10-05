"""构建夜桜退火输入（libchai 格式）。

来源：
- 54 号冻结输入（data/frozen54/）：根组表、元素表结构、目标函数参数（t1 最终配置）、当量矩阵、target200 当量目标。
- 夜莺2.5 正式拆分与键位（data/baseline/）。
- 夜桜字音基准（data/inputs/夜桜字音基准.json）：新分读音频率。

改动：
1. 根组：戈 += 戈无点；止 += 正；天组 += 夭（2026-10-05）；鱼省 移除（2.5 无）；水火合组（锚定）；车(东)+西合组（锚定）；
   虫、𠀐 自 鸟／虫 组拆出为新组（与鸟组互斥，由目标函数约束）。
2. 元素：首末根按 2.5 拆分重映射到新根组；音码换自然码；频率 = 夜桜自然频率；按读音频率降序（读音即字）。
3. 分层：前 N = 前 N 字主读音 + 频率 ≥ 第 N 字的次要读音；写入各 tier 的 top。
4. 字词避重目标码：小鹤 → 自然码逐音节换算，权重不变。
5. target200 当量目标：按字重新对应新索引。

用法：python build/make_inputs.py [输出目录名]   默认 build/out/base
"""
import copy, json, os, sys, collections
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

F54 = ROOT / 'data/frozen54'
OUT = ROOT / 'build/out' / (sys.argv[1] if len(sys.argv) > 1 else 'base')
KEYS = 'abcdefghijklmnopqrstuvwxyz'


def load(p):
    return json.load(open(p, encoding='utf-8-sig'))


# ---------- 根组 ----------
groups = {f"G{g['序号']:03d}": list(g['根形']) for g in load(F54 / '当前完整根表.json')['根组']}
groups['G094'].append('戈无点')
groups['G104'].append('正')
groups['G065'].append('夭')                   # 2026-10-05 群友建议、作者同意：夭归并入天组（原拆为 撇＋大）
for _g, _rs in json.loads(os.environ.get('YZ_EXTRA_ROOTS', '{}')).items():   # 试算：追加归并根 {组: [根…]}
    groups[_g] += _rs
groups['G032'] = [r for r in groups['G032'] if r != '鱼省']
groups['G016'] += groups.pop('G127')          # 水 + 火（锚定同键）
groups['G088'] += groups.pop('G126')          # 车/东 + 西（锚定同键）
chong = ['虫', '𠀐']
groups['G020'] = [r for r in groups['G020'] if r not in chong]   # 鸟系
groups['G135'] = chong                                          # 虫系
MUTEX = [('G020', 'G135')]

root_key = load(ROOT / 'data/baseline/root_key.json')
splits = load(os.environ.get('YZ_SPLITS') or ROOT / 'data/baseline/splits.json')   # 试算可换拆分
g_of = {r: g for g, rs in groups.items() for r in rs}
missing = sorted(set(root_key) - set(g_of))
assert not missing, ('2.5 字根未归组', missing)
layout = {}
for g, rs in groups.items():
    ks = {root_key[r] for r in rs if r in root_key}
    assert len(ks) <= 1, ('组内键不一致', g, {r: root_key.get(r) for r in rs})
    layout[g] = ks.pop() if ks else None
assert all(layout.values()), [g for g, k in layout.items() if not k]

# ---------- 元素 ----------
E54 = yaml.safe_load(open(F54 / 'elements.yaml', encoding='utf-8'))
basis = {(r['字'], r['拼音']): r for r in load(ROOT / 'data/inputs/夜桜字音基准.json')}
fixed_short = {(e['词'], e['拼音']): e['简码长度'] for e in E54 if e.get('简码长度')}
FIX_PATH = ROOT / os.environ.get('YZ_FIX', 'data/inputs/2.5一二简固定.json')   # 3.0 起用 data/inputs/3.0一二简.json
USE_FIX25 = '"fix25": true' in (sys.argv[2] if len(sys.argv) > 2 else '')
if USE_FIX25:   # 作者 2026-09-30：固定夜莺2.5 全部一简、二简（码为本字音节前缀者）
    fixed_short = {(c, py): n for c, py, n in load(FIX_PATH)['fixed']}
reserved = [e for e in E54 if e['拼音'] == 'reserved']

_W0 = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
SCHEME = _W0.get('scheme', 'ziranma')     # 双拼方案：ziranma（夜桜）/ xiaohe（实验：与夜莺2.5同双拼）
entries = []
for (c, py), r in basis.items():
    rs = splits[c]
    zr = encode(py, SCHEME)
    e = {'词': c, '拼音': py,
         '元素序列': [{'element': f'P_{zr[0]}', 'index': 0}, {'element': f'P_{zr[1]}', 'index': 0},
                   {'element': g_of[rs[0][0]], 'index': 0}, {'element': g_of[rs[-1][0]], 'index': 0}],
         '频率': max(0, round(r['自然频率'] * 1000))}
    if (c, py) in fixed_short:
        e['简码长度'] = fixed_short[(c, py)]
    entries.append(e)
entries.sort(key=lambda e: (-e['频率'], e['词'], e['拼音']))
entries += reserved                       # 固定二简简词占位，频率 0，置于末尾（同 54）
# 作者 2026-10-01：2.5 中凡没有单字二简的二码位，首选都是二字简词（今天 jt、这样 vy……），一律留给词。
N25 = Path.home() / 'Nightingale/夜莺2.5'
_single2 = {l.split('\t')[1].strip() for l in open(N25 / '产物/普通单字表.txt', encoding='utf-8-sig')
            if '\t' in l and len(l.split('\t')[0]) == 1 and len(l.split('\t')[1].strip()) == 2}
_word2 = {}
for l in open(N25 / '产物/综合字词表.txt', encoding='utf-8-sig'):
    p_ = l.rstrip('\n').split('\t')
    if len(p_) == 2 and len(p_[1]) == 2 and len(p_[0]) >= 2 and p_[1] not in _single2:
        _word2.setdefault(p_[1], p_[0])
# 嗯 en：口语补读的特殊二简（作者 2026-10-01），同样留出，出码表时按 2.5 给嗯
# 2026-10-02：3.0 起嗯补了 en 读音并列为正式二简，此时不再留给词
if ('嗯', 'en') not in fixed_short:
    _word2.setdefault('en', '嗯')
_have = {''.join(x['element'][2:] for x in e['元素序列']) for e in reserved}
for code, word in sorted(_word2.items()):
    if code not in _have:
        entries.append({'词': word, '拼音': 'reserved',
                        '元素序列': [{'element': f'P_{code[0]}', 'index': 0}, {'element': f'P_{code[1]}', 'index': 0}],
                        '频率': 0})
RESERVED2 = sorted(_word2)
index_of = collections.defaultdict(list)
for i, e in enumerate(entries):
    index_of[e['词']].append(i)

# ---------- 读音即字分层 ----------
char_total = collections.Counter()
for r in basis.values():
    char_total[r['字']] += r['自然频率']
char_order = [c for c, _ in char_total.most_common()]
main = {}
for (c, py), r in basis.items():
    if c not in main or r['自然频率'] > basis[(c, main[c])]['自然频率']:
        main[c] = py
pos = {(e['词'], e['拼音']): i for i, e in enumerate(entries)}


def tier_set(n):
    th = char_total[char_order[n - 1]]
    s = {pos[(c, main[c])] for c in char_order[:n]}
    s |= {pos[k] for k, r in basis.items() if r['自然频率'] >= th}
    return s


tiers = {}
for n in (300, 500, 1500, 1674, 3000, 3500, 3527, 6000):
    s = tier_set(n)
    prefix_gap = len(s - set(range(len(s))))
    tiers[n] = {'size': len(s), 'indices': sorted(s), '非前缀条目': prefix_gap}

# ---------- 配置 ----------
cfg = load(F54 / 't1_final_config.json')
cfg['info'] = {'name': f'夜桜 {OUT.name}', 'version': '2026-09-30'}
m = cfg['form']['mapping']
for k in list(m):
    if k.startswith('G'):
        del m[k]
for g, k in layout.items():
    m[g] = k
for k in KEYS:
    m[f'P_{k}'] = k
_mc = float((json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}).get('move_cost', 0))
# 换键代价（作者 2026-10-01）：留在夜莺2.5 原键得 0，换到其他键得 move_cost（经引擎正则化计入目标）
cfg['generated_mapping_space'] = {g: [{'value': k, 'score': 0.0 if k == layout[g] else _mc} for k in KEYS] for g in groups}
cfg['optimization']['objective']['regularization_strength'] = 1.0
cfg['generated_mapping_space'].update({f'P_{k}': [{'value': k, 'score': 0.0}] for k in KEYS})
obj = cfg['optimization']['objective']
for part in ('characters_full', 'characters_short'):
    for t in obj[part]['tiers']:
        t['top'] = tiers[t['top']]['size']
for t in obj['character_word_collision']['character_tiers']:
    t['top'] = tiers[t['top']]['size']

# 字词避重目标：小鹤 → 自然码
xh2py = {}
for (c, py), r in basis.items():
    xh2py.setdefault(r['小鹤音码'], set()).add(py)
xh2zr = {}
for xh, pys in xh2py.items():
    zs = {encode(p, SCHEME) for p in pys}
    assert len(zs) == 1, (xh, pys)
    xh2zr[xh] = zs.pop()
old_targets = obj['character_word_collision']['targets']
new_targets, unmapped = {}, 0
for code, v in old_targets.items():
    a, b = code[:2], code[2:]
    if a in xh2zr and b in xh2zr:
        new_targets[xh2zr[a] + xh2zr[b]] = v
    else:
        unmapped += 1
assert len(new_targets) == len(old_targets) - unmapped
obj['character_word_collision']['targets'] = new_targets
_W = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
if 'cross' in _W:   # 字词避重权重（2.0 为 0.1）
    obj['character_word_collision']['weight'] = float(_W['cross'])

# target200：按字重新对应
t200 = load(F54 / 'targets.json')
for t in t200:
    t['indices'] = [i for i in index_of[t['character']] if entries[i]['拼音'] != 'reserved']

OUT.mkdir(parents=True, exist_ok=True)
yaml.safe_dump(entries, open(OUT / 'elements.yaml', 'w', encoding='utf-8'), allow_unicode=True, sort_keys=False)
json.dump(cfg, open(OUT / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(t200, open(OUT / 'targets.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in ('matrix.json', 'equivalence.txt', 'distribution.txt'):
    (OUT / f).write_bytes((F54 / f).read_bytes())
json.dump({'groups': groups, 'layout': layout, 'mutex': MUTEX,
           'tiers': {n: {k: v for k, v in t.items() if k != 'indices'} for n, t in tiers.items()},
           'tier_indices': {n: t['indices'] for n, t in tiers.items()}},
          open(OUT / 'meta.json', 'w', encoding='utf-8'), ensure_ascii=False)
# ---------- 夜桜附加目标项配置 ----------
W = {'move_cost': 0, 'clash': False, 'shape_cost': 0, 'scheme': 'ziranma', 'eq_shape': False, 'eq_bins': False, 'cross': 0.1, 'fix25': False, 'eff1500': 0.0, 'eff3500': 0.0, 'excl1500': 5.0, 'excl3500': 1.0, 'overload': 1.0, 'rank_gate': 50.0, 'eq23': 0.0, 'eq34': 0.0,
     'mutex': 1000.0, 'alpha': 4.0}
W.update(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
n_real = sum(1 for e in entries if e['拼音'] != 'reserved')
sig_id = {}
signature = [sig_id.setdefault(tuple(x['element'] for x in e['元素序列']), len(sig_id)) for e in entries[:n_real]]
M = load(F54 / 'matrix.json')
diff = {k: sum(M.get(a + k, 1.3) for a in KEYS) / 26 for k in KEYS}
share = {k: (1 / diff[k]) ** W['alpha'] for k in KEYS}
share = {k: v / sum(share.values()) for k, v in share.items()}
yz = {'n': n_real, 'signature': signature, 'frequency': [float(e['频率']) for e in entries[:n_real]],
      'exclusive': [{'indices': tiers[1500]['indices'], 'weight': W['excl1500']},
                    {'indices': tiers[3500]['indices'], 'weight': W['excl3500']},
                    {'indices': tiers[1500]['indices'], 'weight': W['eff1500'], 'effective': True, 'actual': W.get('eff_actual', True)},
                    {'indices': tiers[3500]['indices'], 'weight': W['eff3500'], 'effective': True, 'actual': W.get('eff_actual', True),
                     'allow': W.get('eff3500_allow', 0)}],
      'target_share': share, 'overload_weight': W['overload'],
      'rank_gate': {'p': 21}, 'rank_gate_weight': W['rank_gate'],
      'eq23_weight': W['eq23'], 'eq34_weight': W['eq34'],
      'mutex': [{'a': pos[('虫', 'chong')], 'b': pos[('鸟', 'niao')], 'position': 2, 'weight': W['mutex']}],
      'matrix': str(OUT / 'matrix.json')}
if W.get('clash'):   # 字词撞码（作者 2026-10-01）：①前1500×前1万 硬；②前1500×前3万 软；③前3500×前1万 软
    sys.path.insert(0, str(ROOT / 'eval'))
    from word_clash import top_words
    tw = [c for _, c in top_words(SCHEME, 30000)]
    yz['word_clash'] = [
        {'chars': tiers[1500]['indices'], 'words': tw[:10000], 'weight': W.get('clash_hard', 200.0)},
        {'chars': tiers[1500]['indices'], 'words': tw[:30000], 'weight': W.get('clash_1500_3w', 5.0)},
        {'chars': tiers[3500]['indices'], 'words': tw[:10000], 'weight': W.get('clash_3500_1w', 2.0),
         'allow': W.get('clash3_allow', 0)}]
if W.get('shape_cost'):   # 形码成本（作者 2026-10-01）
    fixed_idx = {i for i, e in enumerate(entries[:n_real]) if e.get('简码长度')}
    t1500, t6000 = set(tiers[1500]['indices']), set(tiers[6000]['indices'])
    yz['shape'] = {'top': sorted(t1500 - fixed_idx),
                   'rest': [i for i in range(n_real) if i not in t1500 and i not in fixed_idx],
                   'top_share': W.get('top_share', 0.5), 'weight': W['shape_cost'],
                   'four_idx': sorted(t1500), 'four_max': W.get('four_max', 120),
                   'san_idx': sorted(t6000 - fixed_idx), 'san_min': W.get('san_min', 3600),
                   'gate_weight': W.get('shape_gate', 200.0), 'san_weight': W.get('san_weight', 1.0),
                   'p_cap': W.get('p_cap', 0.04), 'p_weight': W.get('p_weight', 0.0)}
if W.get('eq_shape'):   # 第二原则：形码管得到的读音（排除固定一二简），档内按字频加权
    fixed_idx = {i for i, e in enumerate(entries[:n_real]) if e.get('简码长度')}
    yz['eq_bins'] = [{'indices': [i for i in range(n_real) if i not in fixed_idx], 'weight': 1.0, 'weighted': True}]
elif W.get('eq_bins'):   # 分档不加权当量：排除固定一二简读音
    fixed_idx = {i for i, e in enumerate(entries[:n_real]) if e.get('简码长度')}
    edges = [(0, 300, 30), (300, 500, 20), (500, 1500, 25), (1500, 3000, 15), (3000, 6000, 10), (6000, None, 5)]
    prev, bins = set(), []
    for lo, hi, wt in edges:
        cur = set(tiers[hi]['indices']) if hi else set(range(n_real))
        band = sorted((cur - prev) - fixed_idx)
        bins.append({'indices': band, 'weight': wt})
        prev = cur
    yz['eq_bins'] = bins
json.dump(yz, open(OUT / 'yozakura.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(W, open(OUT / 'weights.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('留给词的二码位', len(RESERVED2), ' '.join(RESERVED2))
print('根组', len(groups), '元素条目', len(entries), '字词避重目标', len(new_targets), '未换算', unmapped)
print('分层（读音身份数 / 非前缀条目）', {n: (t['size'], t['非前缀条目']) for n, t in tiers.items()})
print('输出', OUT)
