"""第三遍：汇总。每(体裁,字)：词内=词典计数；单字成词=总数×g2pW 抽样比例。六体裁等权相加。
输出 out/新频率.json 与 out/新旧对比.tsv（与 2.0 字音基准“频率”逐字比较份额）。"""
import json, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading'))
from annotate import READ, BASE

G = 'news wiki zhihu forum webnovel classic'.split()
P = {g: json.load(open(ROOT / f'reading/out/{g}.pass1.json', encoding='utf-8')) for g in G}

lab = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # [g][c][syl]
outside = collections.Counter()
val = collections.defaultdict(lambda: [0, 0])     # 词内对照 [一致, 总]
val_bad = collections.Counter()
TW = {('和', 'han'): 'he'}   # g2pW 台湾读音 → 大陆读音
for l in open(ROOT / 'reading/out/pass2.jsonl', encoding='utf-8'):
    j = json.loads(l)
    y = TW.get((j['c'], j['g2pw']), j['g2pw'])
    if j['k'] == 'single':
        if y in READ[j['c']]:
            lab[j['g']][j['c']][y] += 1
        elif y:
            outside[(j['c'], y)] += 1
    elif y and j['dict']:
        v = val[j['c']]; v[1] += 1
        if y == j['dict']:
            v[0] += 1
        else:
            val_bad[(j['c'], j['dict'], y)] += 1

old = collections.defaultdict(dict)
for r in BASE:
    old[r['字']][r['拼音']] = r['频率'] or 0

new = collections.defaultdict(collections.Counter)
source = collections.defaultdict(set)
incomplete = set()
for g in G:
    for c, d in P[g]['inword'].items():
        for syl, n in d.items():
            if not syl.startswith('?'):
                new[c][syl] += n
    for c, n in P[g]['single_n'].items():
        sample = lab[g][c]
        tot = sum(sample.values())
        if tot == 0:   # g2pW 未给出有效样本：单字部分按 03 旧比例分摊
            incomplete.add(c)
            ot = sum(old[c].values())
            sample = collections.Counter(old[c]) if ot else collections.Counter({min(READ[c]): 1})
            tot = sum(sample.values())
            source[c].add('单字回退03')
        for syl, k in sample.items():
            new[c][syl] += n * k / tot

rows = []
for c in new:
    if len(READ[c]) < 2:
        continue
    nt, ot = sum(new[c].values()), sum(old[c].values())
    if nt < 30:
        continue
    diff = max(abs(new[c][s] / nt - (old[c].get(s, 0) / ot if ot else 0)) for s in READ[c])
    v = val.get(c, [0, 0])
    rows.append((c, nt, diff, (v[1] - v[0]) / v[1] if v[1] >= 10 else None, {s: round(new[c][s] / nt, 3) for s in sorted(READ[c])},
                 {s: round(old[c].get(s, 0) / ot, 3) if ot else None for s in sorted(READ[c])}))
rows.sort(key=lambda r: -r[1])
with open(ROOT / 'reading/out/新旧对比.tsv', 'w', encoding='utf-8') as f:
    f.write('字\t语料出现\t最大份额差\t词内分歧率\t新份额\t旧份额(03)\n')
    for c, nt, d, vr, a, b in rows:
        f.write(f'{c}\t{nt:.0f}\t{d:.3f}\t{"" if vr is None else f"{vr:.2f}"}\t{json.dumps(a, ensure_ascii=False)}\t{json.dumps(b, ensure_ascii=False)}\n')
json.dump({c: dict(v) for c, v in new.items()}, open(ROOT / 'reading/out/新频率.json', 'w', encoding='utf-8'), ensure_ascii=False)

if __name__ == '__main__':
    agree = sum(v[0] for v in val.values()); tot = sum(v[1] for v in val.values())
    print(f'词内对照：g2pW 与词典一致 {agree}/{tot} = {agree / max(tot, 1):.1%}')
    print('不一致最多：', val_bad.most_common(12))
    print('g2pW 库外读音最多：', outside.most_common(12))
    print('尚无单字样本的字数', len(incomplete))
    print('\n高频多音字，差异≥10%：')
    for c, nt, d, vr, a, b in rows[:300]:
        if d >= 0.10 or (vr or 0) >= 0.2:
            print(f'  {c} 出现{nt:.0f} 差{d:.0%} 分歧{"-" if vr is None else f"{vr:.0%}"}  新{a}  旧{b}')
