"""生成夜桜字音基准：整字总频沿用 2.0（自然频率之和），多音字各读音份额换为语料实测。

口径（2026-09-30，第二版）：
- 对全部多音字出现位置均匀抽样（sample_all.py），每处取 g2pW 上下文读音（label_samples.py）。
- g2pW 偏台湾读音：REJECT 中的读音一律改用 pypinyin 整句读音（大陆词典）。
- 文白异读（COLLOQ）：g2pW 给出白读音时，仅当 jieba 判为单字成词才采用，否则改用 pypinyin；
  被改掉的白读另计“口语频率”，退火权重另设（默认 0.5）。
- 著：只用现代体裁（名著中 著=着 的旧用法）。
- 作者/审校裁定（OVERRIDE）优先于实测份额。
- 语料出现 <30 次的字保留 2.0 份额。音码改为自然码。"""
import json, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading')); sys.path.insert(0, str(ROOT / 'lib'))
from annotate import READ, BASE
from shuangpin import encode

G = 'news wiki zhihu forum webnovel classic'.split()
MODERN_ONLY = {'著'}
MIN_OCC = 30
REJECT = {('和', 'han'), ('劲', 'jing'), ('塞', 'se'), ('咋', 'ze'), ('靓', 'jing'), ('攒', 'cuan'),
          ('缉', 'qi'), ('垃', 'le'), ('圾', 'se')}
# 血、熟 不列入：g2pW 在 血液/熟悉 等词内也标白读（台湾读音），会虚增口语频率。单字成词的白读已计入正式份额。
COLLOQ = {'薄': 'bao', '剥': 'bao', '削': 'xiao', '露': 'lou', '嚼': 'jiao',
          '壳': 'qiao', '落': 'lao', '色': 'shai'}
OVERRIDE_PATH = ROOT / 'reading/审校裁定.json'   # {字: {音节: 份额}}
OVERRIDE = {k: v for k, v in json.load(open(OVERRIDE_PATH, encoding='utf-8')).items()
            if not k.startswith('_')} if OVERRIDE_PATH.exists() else {}


def final_reading(j):
    """返回 (采用读音, 被改掉的白读或None)"""
    c, g, p = j['c'], j['g2pw'], j['py']
    if g not in READ[c]:
        return (p if p in READ[c] else None), None
    if (c, g) in REJECT:
        return (p if p in READ[c] else None), None
    if COLLOQ.get(c) == g and not j['single']:
        return (p if p in READ[c] else g), (g if p in READ[c] and p != g else None)
    return g, None


n = collections.defaultdict(collections.Counter)
for g in G:
    for c, k in json.load(open(ROOT / f'reading/out/{g}.sample.json', encoding='utf-8'))['n'].items():
        n[g][c] = k

lab = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
colloq = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
stat = collections.defaultdict(collections.Counter)      # 字 -> {'n','diff_py','low_conf'}
for l in open(ROOT / 'reading/out/labels.jsonl', encoding='utf-8'):
    j = json.loads(l)
    r, lost = final_reading(j)
    if r is None:
        continue
    lab[j['g']][j['c']][r] += 1
    if lost:
        colloq[j['g']][j['c']][lost] += 1
    st = stat[j['c']]
    st['n'] += 1
    st['diff_py'] += (j['py'] in READ[j['c']] and j['py'] != r)
    st['low_conf'] += (j['conf'] is not None and j['conf'] < 0.8)

est = collections.defaultdict(collections.Counter)
est_colloq = collections.defaultdict(collections.Counter)
occ = collections.Counter()
for g in G:
    for c, k in n[g].items():
        if c in MODERN_ONLY and g == 'classic':
            continue
        smp = lab[g][c]
        t = sum(smp.values())
        if not t:
            continue
        occ[c] += k
        for r, m in smp.items():
            est[c][r] += k * m / t
        for r, m in colloq[g][c].items():
            est_colloq[c][r] += k * m / t

old_total = collections.Counter()
for r in BASE:
    old_total[r['字']] += r['自然频率'] or 0

out, log = [], collections.Counter()
for r in BASE:
    c, s = r['字'], r['拼音']
    total = old_total[c]
    row = dict(字=c, 拼音=s, 音码=encode(s, 'ziranma'), 小鹤音码=r['音码'], 旧自然频率=r['自然频率'])
    if len(READ[c]) < 2:
        row.update(自然频率=r['自然频率'], 来源='单音字')
    elif c in OVERRIDE:
        row.update(自然频率=total * OVERRIDE[c].get(s, 0), 来源='审校裁定'); log['审校裁定'] += 1
    elif occ[c] < MIN_OCC:
        row.update(自然频率=r['自然频率'], 来源='语料不足沿用2.0'); log['语料不足'] += 1
    else:
        e = sum(est[c].values())
        row.update(自然频率=total * est[c][s] / e, 来源='语料实测'); log['语料实测'] += 1
        if est_colloq[c][s]:
            row['口语频率'] = total * est_colloq[c][s] / e
            log['口语异读'] += 1
    st = stat[c]
    if st['n']:
        row['样本'] = st['n']
        row['与pypinyin分歧'] = round(st['diff_py'] / st['n'], 3)
        row['低置信'] = round(st['low_conf'] / st['n'], 3)
    out.append(row)

if __name__ == '__main__':
    json.dump(out, open(ROOT / 'data/inputs/夜桜字音基准.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('条目', len(out), dict(log))
