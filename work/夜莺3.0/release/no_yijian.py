"""无一简试验：从普通单字表去掉一简，两种补法，并用实打语料比较。
A 只删一简：一简字退回全码；全码前三码空着的补三码。
B 一简升二简：一简字占自己双拼的二码首位；原占位的二简字让出二码（有三码的留三码，没有的若三码空就补，否则只剩全码）；
  一简字自己的三码空着也补上（同二简补三码）。
C 同 B，但让位字的三码若被字频更低的读音占着，就抢过来（被抢的退回全码）。
用法：.venv/bin/python release/no_yijian.py <普通单字表> <输出目录>
"""
import collections, json, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib')); sys.path.insert(0, str(ROOT / 'eval'))
from shuangpin import encode
from real_typing import run
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=L)
FR = {(e['词'], e['拼音']): e['频率'] for e in E if e['拼音'] != 'reserved'}
TOT = sum(FR.values())
ONE = [(c, p) for c, p, n in json.load(open(ROOT / 'data/inputs/3.0一二简.json', encoding='utf-8'))['fixed'] if n == 1]
src, outdir = Path(sys.argv[1]), Path(sys.argv[2])
outdir.mkdir(parents=True, exist_ok=True)


def load():
    slots = collections.OrderedDict()
    for l in open(src, encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2:
            slots.setdefault(p[1], []).append(p[0])
    return slots


def full_of(slots, ch, sy):
    return next((c for c in sorted(slots) if len(c) == 4 and c[:2] == sy and ch in slots[c]), None)


def save(slots, name):
    path = outdir / f'{name}_普通单字表.txt'
    with open(path, 'w', encoding='utf-8') as f:
        for code in sorted(slots):
            for ch in slots[code]:
                f.write(f'{ch}\t{code}\n')
    return path


def variant_a():
    s = load(); log = []
    for ch, py in ONE:
        sy = encode(py, 'xiaohe')
        s[sy[0]].remove(ch)
        full = full_of(s, ch, sy)
        if full and not s.get(full[:3]):
            s[full[:3]] = [ch]; log.append((ch, '三码 ' + full[:3]))
        else:
            log.append((ch, '全码 ' + full))
    for k in [k for k, v in s.items() if not v]: del s[k]
    return s, log


def rfreq(ch, sy):
    return max((f for (c, p), f in FR.items() if c == ch and encode(p, 'xiaohe') == sy), default=0)


def variant_b(grab=False):
    s = load(); log = []
    for ch, py in ONE:
        sy = encode(py, 'xiaohe')
        s[sy[0]].remove(ch)
        old = [h for h in s.get(sy, []) if h != ch]
        s[sy] = [ch]
        for h in old:                              # 让位的二简字
            hp = next((p for (c, p) in FR if c == h and encode(p, 'xiaohe') == sy), None)
            hf = full_of(s, h, sy)
            if hf and h in s.get(hf[:3], []):
                where = '三码 ' + hf[:3] + '（已有）'
            elif hf and not s.get(hf[:3]):
                s[hf[:3]] = [h]; where = '三码 ' + hf[:3] + '（补）'
            elif grab and hf and all(rfreq(o, sy) < rfreq(h, sy) for o in s[hf[:3]]):
                where = '三码 ' + hf[:3] + '（抢' + ''.join(s[hf[:3]]) + '的）'; s[hf[:3]] = [h]
            else:
                where = '全码 ' + (hf or '?') + ('（三码被' + ''.join(s.get(hf[:3], [])) + '占）' if hf else '')
            log.append((h, hp, f'让出 {sy} → {where}', FR.get((h, hp), 0) / TOT))
        full = full_of(s, ch, sy)
        if full and not s.get(full[:3]):
            s[full[:3]] = [ch]
    for k in [k for k, v in s.items() if not v]: del s[k]
    return s, log


base = run(str(src), 'xiaohe')
A, la = variant_a(); pa = save(A, 'A只删一简')
B, lb = variant_b(); pb = save(B, 'B一简升二简')
C, lc = variant_b(True); pc = save(C, 'C升二简且抢三码')
ra, rb, rc = run(str(pa), 'xiaohe'), run(str(pb), 'xiaohe'), run(str(pc), 'xiaohe')
keys = ['一简%', '二简%', '三码%', '四码%', '字均键数', '键均当量', '字均当量', '选重%', '小指干扰%', '同指大跨排%']
print('\t'.join(['指标', '现行', 'A只删一简', 'B一简升二简', 'C升二简且抢三码']))
for k in keys:
    print('\t'.join([k] + [f'{r[k]:.4f}' if isinstance(r[k], float) else str(r[k]) for r in (base, ra, rb, rc)]))
print('\nA：', '；'.join(f'{c} {w}' for c, w in la))
print('\nB 让位的二简字：')
for h, p, w, f in sorted(lb, key=lambda x: -x[3]):
    print(f'  {h} {p} {100 * f:.3f}%  {w}')
print('\nC 与 B 不同的：')
for (h, p, w, f), (_, _, w2, _) in zip(lb, lc):
    if w != w2: print(f'  {h} {p} {100 * f:.3f}%  {w2}')
# 前1500 档四码（门禁 ≤125）：该读音没有 <4 的码
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
T1500 = META['tier_indices']['1500']


def four(slots):
    has = collections.defaultdict(set)
    for code, chs in slots.items():
        for ch in chs: has[ch].add(code)
    n = 0
    for i in T1500:
        ch, py = E[i]['词'], E[i]['拼音']; sy = encode(py, 'xiaohe')
        if not any(len(c) < 4 and (c[:2] == sy or ((ch, py) in ONE and len(c) == 1)) for c in has[ch]): n += 1
    return n


print('\n前1500四码：现行', four(load()), 'A', four(A), 'B', four(B), 'C', four(C))
json.dump({'现行': base, 'A': ra, 'B': rb, 'C': rc, 'A明细': la, 'B明细': lb, 'C明细': lc}, open(outdir / '对比.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
