"""生成 Rime 反查数据（Lua 表，格式同夜莺 2.5 的 yeying25_mac_lookup_data）。
sounds[双拼] = {{字, 拆分, {该读音的码…（短的在前）}, 权重, 是否通规8105}, …}（常用读音按字频在前，扩展字在后）
pinyin[全拼] = 双拼
用法：python rime/make_lookup.py <普通单字表或整句码表> <输出 .lua> [有一简:1/0]
"""
import collections, json, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

table, out = Path(sys.argv[1]), Path(sys.argv[2])
use_one = (sys.argv[3] if len(sys.argv) > 3 else '1') == '1'
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
ONE = {(c, p): None for c, p, n in json.load(open(ROOT / 'data/inputs/3.0一二简.json', encoding='utf-8'))['fixed'] if n == 1}

codes = collections.defaultdict(list)
for l in open(table, encoding='utf-8-sig'):
    if l.startswith('#') or '\t' not in l: continue
    ch, c = l.rstrip('\n').split('\t')[:2]
    if len(ch) == 1 and c not in codes[ch]: codes[ch].append(c)

core = {e['词'] for e in E if e['拼音'] != 'reserved'}
rows = collections.defaultdict(list); seen = set()
for e in sorted((e for e in E if e['拼音'] != 'reserved'), key=lambda e: -e['频率']):
    ch, py = e['词'], e['拼音']
    try: sy = encode(py, 'xiaohe')
    except Exception: continue
    mine = [c for c in codes.get(ch, []) if c[:2] == sy and len(c) >= 2]
    if use_one and (ch, py) in ONE: mine = [c for c in codes[ch] if len(c) == 1] + mine
    if not mine or (ch, sy) in seen: continue
    seen.add((ch, sy))
    rows[sy].append((ch, sorted(mine, key=lambda c: (len(c), c)), 1))
for ch, cs in codes.items():                     # 扩展字（8105 以外）
    for sy in sorted({c[:2] for c in cs if len(c) >= 2}):
        if (ch, sy) not in seen:
            seen.add((ch, sy))
            rows[sy].append((ch, sorted((c for c in cs if c[:2] == sy), key=lambda c: (len(c), c)), 1 if ch in core else 0))

pinyin = {}
for py in json.load(open(ROOT / 'data/inputs/全音节映射.json', encoding='utf-8'))['小鹤']:
    try: pinyin[py] = encode(py, 'xiaohe')
    except Exception: pass


def lua(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


parts = []
for sy in sorted(rows):
    items = ','.join('{%s,%s,{%s},99999,%d}' % (lua(ch), lua(' ＋ '.join(p[0] for p in splits.get(ch, [])) or ch),
                                                  ','.join(lua(c) for c in cs), flag) for ch, cs, flag in rows[sy])
    parts.append(f'[{lua(sy)}]={{{items}}}')
pys = ','.join(f'[{lua(k)}]={lua(v)}' for k, v in sorted(pinyin.items()))
out.write_text('return {["sounds"]={' + ','.join(parts) + '},["pinyin"]={' + pys + '}}\n', encoding='utf-8')
print(out, '读音', len(rows), '条目', sum(len(v) for v in rows.values()), '全拼', len(pinyin))
