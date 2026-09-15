# -*- coding: utf-8 -*-
"""第 2 步产物：纯普通词表（只有词，无字，无简词）+ 非规则词登记表。
来源：今日处理完的词层（62 无简词表，含 85–90 的全部裁定）。62/64 此后仅作输入材料。
分类：可推导=普通词；不可推导者按类登记（叠词写法/声母s→u/口音替换/o前缀数字/含符号或字母/码长超四/自定义短语/其他）。"""
import io, sys, os, json, hashlib, collections, datetime, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
NUM = set('零〇一二三四五六七八九十百千万亿两廿卅')
custom = json.load(open(B + '/83_单字表重放/词无理码表.json', encoding='utf-8'))['条目']   # 码->词
SRC = B + '/62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt'
order = collections.OrderedDict(); chars = collections.defaultdict(set)
for line in open(SRC, encoding='utf-8-sig'):
    p = line.rstrip('\n').rstrip('\r').split('\t')
    if len(p) < 2: continue
    w, c = p[0], p[1]
    if len(w) == 1 and c.isalpha(): chars[w].add(c)
    if len(w) > 1: order.setdefault(c, []).append(w)
AB = collections.defaultdict(set); A = collections.defaultdict(set)
for w, cs in chars.items():
    for c in cs:
        if len(c) >= 4 and c not in TOL: AB[w].add(c[:2]); A[w].add(c[0])

def derive(word):
    n = len(word)
    if any(ch not in AB for ch in word): return None
    if n == 2: return {a + b for a in AB[word[0]] for b in AB[word[1]]}
    if n == 3: return {a + b + c for a in A[word[0]] for b in A[word[1]] for c in AB[word[2]]}
    return {a + b + c + d for a in A[word[0]] for b in A[word[1]] for c in A[word[2]] for d in A[word[-1]]}

def posmap(word):
    n = len(word)
    if n == 2: return {0: (word[0], 0), 1: (word[0], 1), 2: (word[1], 0), 3: (word[1], 1)}
    if n == 3: return {0: (word[0], 0), 1: (word[1], 0), 2: (word[2], 0), 3: (word[2], 1)}
    return {0: (word[0], 0), 1: (word[1], 0), 2: (word[2], 0), 3: (word[-1], 0)}

def classify(w, c):
    if custom.get(c) == w: return '自定义短语'
    if not c.isalpha(): return '非字母码'
    if len(c) < 4: return '简词(不应出现)'
    if len(c) > 4: return '码长超四'
    d = derive(w)
    if d is None: return '含符号字母或8105外字'
    if c in d: return None
    if len(w) == 4 and w[0] == w[1] and w[2] == w[3]: return '叠词写法(字1AB+字3AB)'
    if c.startswith('o') and all(ch in NUM for ch in w): return 'o前缀数字词'
    h, x = min(((sum(a != b for a, b in zip(c, y)), y) for y in d))
    pm = posmap(w); diffs = [(i, c[i], x[i]) for i in range(4) if c[i] != x[i]]
    if all(a == 's' and b == 'u' for _, a, b in diffs): return '声母s写作u'
    if all(pm[i][1] == 0 for i, _, _ in diffs): return '声母口音替换'
    if all(pm[i][1] == 1 for i, _, _ in diffs): return '韵母口音替换'
    return '其他不合规则'

rows = []; reg = collections.defaultdict(list); stat = collections.Counter()
for c, ws in order.items():
    for i, w in enumerate(ws):
        k = classify(w, c)
        rows.append((c, w, i + 1))
        if k is None: stat['普通词'] += 1
        else: stat[k] += 1; reg[k].append({'词': w, '码': c, '候选位': i + 1})
out = '\r\n'.join('%s\t%s' % (w, c) for c, w, i in rows) + '\r\n'
open(H + '/夜莺2.0普通词表_普通格式.txt', 'wb').write(out.encode('utf-8-sig'))
out2 = '\r\n'.join('%s\t%s' % (c, w) for c, w, i in rows) + '\r\n'
open(H + '/夜莺2.0普通词表_码前格式.txt', 'wb').write(out2.encode('utf-8-sig'))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '来源': SRC.replace(B + '/', ''),
           '说明': '不按规则但按用户裁定保留的词，按类登记；自定义短语见 83/词无理码表.json',
           '统计': dict(stat), '登记': reg},
          open(H + '/非规则词登记表.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '词条': len(rows), '码位': len(order),
           '统计': dict(stat),
           'sha256': {f: hashlib.sha256(open(H + '/' + f, 'rb').read()).hexdigest() for f in ('夜莺2.0普通词表_普通格式.txt', '夜莺2.0普通词表_码前格式.txt')}},
          open(H + '/生成说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('普通词表：%d 词条，%d 码位' % (len(rows), len(order)))
for k, v in sorted(stat.items(), key=lambda x: -x[1]): print('   %-22s %6d' % (k, v))
print('登记表条目：%d' % sum(len(v) for v in reg.values()))
