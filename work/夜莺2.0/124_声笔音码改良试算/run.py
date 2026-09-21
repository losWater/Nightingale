# -*- coding: utf-8 -*-
"""声笔音码改良试算（2026-09-16）：把它的第 3 码改成"声调×起笔"（25 键，可推），第 4 码换成一个可推的属性，比较各属性的重码。
结构：双拼（自然码）→ 二码字 = 该双拼字频最高者（照原方案）→ 三码 = 双拼 + 声调×起笔，取组内字频最高者 →
      四码 = 三码 + 属性 X，组内按字频排，第 2 位起算选重（原方案用排位填满，这里把排位留给第 5 码）。
属性 X：末笔 / 第二笔 / 第二笔×末笔 / 夜莺末根键 / 夜莺首根键 / 笔画数。笔画来自 Chai 字库展开，起笔分类照 GF0023（提归横、竖钩归竖、捺归点、其余钩折归折）。
数据：zip 里的 带调拼音/字频/双拼对照表（自然码列）；Chai repertoire；夜莺 拆分查询 D（首末根键）。"""
import io, sys, os, json, zlib, zipfile, re, collections, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = 'E:/夜莺2.0/work/夜莺2.0'
Z = zipfile.ZipFile('D:/nightingale/releases/v2.5/测试/音の根源码.zip'); names = {}
for i in Z.infolist():
    try: n = i.filename.encode('cp437').decode('gbk')
    except Exception: n = i.filename
    names[n] = i.filename
rd = lambda n: Z.read(names[n]).decode('utf-8-sig')
# 双拼（自然码）
sp = {}
for l in rd('tune/data/source/双拼方案对照表.txt').splitlines()[1:]:
    p = l.split('\t')
    if len(p) > 2: sp[p[0]] = p[2]
sp.setdefault('zhei', 'vz'); sp.setdefault('kei', 'kz')
# 字频与顺序
freq = {}; order = []
for l in rd('tune/data/source/字频.txt').splitlines():
    p = l.split('\t')
    if len(p) == 2 and p[0] not in freq: freq[p[0]] = int(p[1]); order.append(p[0])
# 带调拼音 → (音节, 调)
TONES = {'ā': ('a', 1), 'á': ('a', 2), 'ǎ': ('a', 3), 'à': ('a', 4), 'ō': ('o', 1), 'ó': ('o', 2), 'ǒ': ('o', 3), 'ò': ('o', 4), 'ē': ('e', 1), 'é': ('e', 2), 'ě': ('e', 3), 'è': ('e', 4),
         'ī': ('i', 1), 'í': ('i', 2), 'ǐ': ('i', 3), 'ì': ('i', 4), 'ū': ('u', 1), 'ú': ('u', 2), 'ǔ': ('u', 3), 'ù': ('u', 4), 'ǖ': ('v', 1), 'ǘ': ('v', 2), 'ǚ': ('v', 3), 'ǜ': ('v', 4), 'ü': ('v', 5), 'ḿ': ('m', 2), 'ń': ('n', 2), 'ň': ('n', 3), 'ǹ': ('n', 4)}
def parse(py):
    tone = 5; out = ''
    for ch in py:
        if ch in TONES: b, t = TONES[ch]; out += b; tone = t
        else: out += ch
    out = out.replace('ü', 'v')
    return out, tone
readings = collections.defaultdict(list)
for l in rd('tune/data/source/带调拼音.txt').splitlines():
    m = re.match(r'^(\S)\t（(.*)）', l)
    if not m: continue
    for py in m.group(2).split():
        syl, tone = parse(py)
        if syl in ('m', 'n', 'ng', 'hng'): continue
        if syl in sp: readings[m.group(1)].append((sp[syl], tone))
tab8105 = {l.split('	')[0] for l in rd('tune/output/单字码表.txt').splitlines() if '	' in l}
chars8105 = [c for c in order if c in readings and c in tab8105]
# Chai 字库 → 笔画序列
rows = json.loads(zlib.decompress(open('E:/夜莺2.0/repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate', 'rb').read()))
rep = {}
for r in rows:
    if r.get('unicode') is not None: rep[chr(r['unicode'])] = r
    if r.get('name'): rep.setdefault(r['name'], r)
def cls(feature):
    f = feature
    if f in ('横', '提'): return 1
    if f in ('竖', '竖钩'): return 2
    if f == '撇': return 3
    if f in ('点', '捺'): return 4
    return 5
import ast
def glyphs_of(r):
    g = r['glyphs']
    if isinstance(g, list): return g
    try: return ast.literal_eval(g)
    except Exception:
        try: return json.loads(g)
        except Exception: return []
def raw_strokes(ch, depth=0):
    """返回笔画 feature 名列表（未分类）"""
    r = rep.get(ch)
    if not r or depth > 12: return None
    gs = glyphs_of(r)
    if not gs: return None
    g = next((x for x in gs if 'G' in (x.get('tags') or [])), gs[0])
    t = g.get('type')
    if t == 'basic_component': return [s_['feature'] for s_ in g['strokes']]
    if t == 'derived_component':
        base = raw_strokes(g['source'], depth + 1)
        if base is None: return None
        out = []
        for s_ in g['strokes']:
            if not isinstance(s_, dict): continue
            if s_.get('feature') == 'reference':
                i = s_.get('index', 0)
                if isinstance(i, int) and 0 <= i < len(base): out.append(base[i])
            elif 'feature' in s_: out.append(s_['feature'])
        return out or base
    if t in ('compound', 'spliced_component'):
        out = []
        for op in g.get('operandList') or []:
            x = raw_strokes(op, depth + 1)
            if x is None: return None
            out += x
        return out
    return None
def strokes(ch):
    r = raw_strokes(ch)
    return [cls(f) for f in r] if r else None
# 夜莺首末根键
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
m = re.search(r'\bconst D\s*=\s*', q); D = json.JSONDecoder().raw_decode(q[m.end():])[0]
props = {}; miss = 0
for c in chars8105:
    s = strokes(c)
    if not s: miss += 1; continue
    d = D.get(c)
    props[c] = {'起笔': s[0], '末笔': s[-1], '第二笔': s[1] if len(s) > 1 else 0, '笔画数': len(s),
                '末根键': d['根'][-1]['键'] if d else '?', '首根键': d['根'][0]['键'] if d else '?'}
print('8105 字里有读音 %d，笔画展开失败 %d' % (len(chars8105), miss))
# 与原方案起笔核对（原表四码字第 4 码区 → 起笔）
STROKE_KEY = {k: i for i, keys in enumerate(['gfdsa', 'hjklm', 'trewq', 'yuiop', 'nbvcx'], 1) for k in keys}
tab = [l.split('\t') for l in rd('tune/output/单字码表.txt').splitlines() if '\t' in l]
agree = tot = 0
for t, c in tab:
    if len(c) >= 4 and t in props: tot += 1; agree += (STROKE_KEY[c[3]] == props[t]['起笔'])
print('起笔与原方案一致率 %d/%d = %.1f%%' % (agree, tot, agree / tot * 100))
bad = [(t, c, STROKE_KEY[c[3]], props[t]['起笔']) for t, c in tab if len(c) >= 4 and t in props and STROKE_KEY[c[3]] != props[t]['起笔']]
import collections as _c
print('不一致分布 原→我:', _c.Counter((a, b) for _, _, a, b in bad).most_common(8))
def feat(ch):
    r = rep.get(ch); gs = r['glyphs'] if isinstance(r['glyphs'], list) else json.loads(r['glyphs'].replace("'", '"'))
    g = next((x for x in gs if 'G' in (x.get('tags') or [])), gs[0]); return g.get('type'), (g.get('operandList') or g.get('source') or [s_.get('feature') for s_ in g.get('strokes', [])][:3])

# 模拟
rank = {c: i + 1 for i, c in enumerate(chars8105)}
by2 = collections.defaultdict(set)
for c in props:
    for spc, tone in readings[c]: by2[spc].add(c)
two = {spc: max(cs, key=lambda c: freq[c]) for spc, cs in by2.items()}
def simulate(X):
    groups = collections.defaultdict(list)   # (双拼, 调, 起笔, X) -> chars
    tri = collections.defaultdict(list)
    for c in props:
        for spc, tone in set(readings[c]):
            if two[spc] == c: continue
            tri[(spc, tone, props[c]['起笔'])].append(c)
    three = {}; sel = []
    for k, cs in tri.items():
        cs = sorted(set(cs), key=lambda c: -freq[c]); three[k] = cs[0]
        for c in cs[1:]: groups[k + (X(props[c]),)].append(c)
    dup = 0; wdup = collections.Counter(); maxg = 0; over = collections.Counter()
    for k, cs in groups.items():
        cs.sort(key=lambda c: -freq[c]); maxg = max(maxg, len(cs))
        for i, c in enumerate(cs):
            if i > 0:
                dup += 1
                for n in (1500, 3000, 6000):
                    if rank[c] <= n: wdup[n] += 1
            if i >= 25: over['需第六码'] += 1
    return {'四码组数': len(groups), '选重条目': dup, '前1500字选重': wdup[1500], '前3000字选重': wdup[3000], '前6000字选重': wdup[6000], '最大组': maxg, '超25需六码': over['需第六码']}
cands = {'末笔(5)': lambda p: p['末笔'], '第二笔(5)': lambda p: p['第二笔'], '第二笔×末笔(25)': lambda p: (p['第二笔'], p['末笔']),
         '夜莺末根键(26)': lambda p: p['末根键'], '夜莺首根键(26)': lambda p: p['首根键'], '笔画数(封顶25)': lambda p: min(p['笔画数'], 25),
         '末笔×笔画数段(25)': lambda p: (p['末笔'], min((p['笔画数'] - 1) // 3, 4)),
         '第二笔×笔画数段(25)': lambda p: (p['第二笔'], min((p['笔画数'] - 1) // 3, 4)),
         '末笔×末根键(≈130)': lambda p: (p['末笔'], p['末根键']),
         '原方案:纯排位': lambda p: 0}
res = {name: simulate(f) for name, f in cands.items()}
base_two = len(two); base_three = sum(1 for _ in set((spc, t, props[c]['起笔']) for c in props for spc, t in readings[c] if two[spc] != c))
lines = ['# 声笔音码改良试算：第 3 码 = 声调×起笔，第 4 码 = ?', '', '二码字 %d，三码字（每个 音节·调·起笔 组第一名）%d；其余进四码。选重 = 同一四码组里排第 2 位及以后的读音条目数。' % (base_two, base_three), '',
         '| 第 4 码属性 | 四码组数 | 选重条目 | 前1500字选重 | 前3000字选重 | 前6000字选重 | 最大组 | 需第六码 |', '|---|---|---|---|---|---|---|---|']
for name, r in res.items(): lines.append('| %s | %d | %d | %d | %d | %d | %d | %d |' % (name, r['四码组数'], r['选重条目'], r['前1500字选重'], r['前3000字选重'], r['前6000字选重'], r['最大组'], r['超25需六码']))
json.dump(res, open(H + '/结果.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(H + '/结果.md', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
