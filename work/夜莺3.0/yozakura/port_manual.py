"""把夜莺的手动简码（data/inputs/手动调整.json，小鹤码）换算成夜桜（自然码 ZR27）的 yozakura/手动调整.json。
- 二简：同一读音的自然码音节；三简：该读音在夜桜表里的全码前三码；一简：同一读音的声母键（双拼两方案相同）。
- yozakura/手动调整.json 里“不照搬”列出的（码类、字）跳过（作者复核过的）。
- 自定义码（不按音码＋首根的码）无法自动换算：作者定好的夜桜码写在 yozakura/手动调整.json 的“自定义码”里（[夜桜码, 字, 说明（含对应的小鹤码）]），换算时原样保留；夜莺有、夜桜还没有的只报告。
- 每条三简报告：夜桜里这个码现在归谁（未套手动调整的表）、争码双方在小鹤/夜桜下的全码与当量、手感问题，便于按全码手感复核。
用法：.venv/bin/python yozakura/port_manual.py <未套手动调整的夜桜单字表>   # 由 yozakura/rebuild.py 调用
"""
import collections, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

SRC = ROOT / 'data/inputs/手动调整.json'
DST = ROOT / 'yozakura/手动调整.json'
M = json.load(open(ROOT / 'eval/box/combo.json'))
FIN = {}
for row in ('qwert', 'asdfg', 'zxcvb'):
    for i, k in enumerate(row): FIN[k] = ('L', [0, 1, 2, 3, 3][i])
for row in ('yuiop', 'hjkl;', 'nm,./'):
    for i, k in enumerate(row): FIN[k] = ('R', [3, 3, 2, 1, 0][i])


def feel(c):
    """全码当量与手感问题（测评站口径：大跨排、小跨排、小指干扰＝同手小指与无名指连按；另标同键三连）。"""
    if not c or len(c) != 4: return '—'
    eq = sum(M[c[i:i + 2]]['eq'] for i in range(3)); fl = []
    for i in range(3):
        p = c[i:i + 2]; a, b = p
        if M[p]['ms']: fl.append(p + '大跨')
        elif M[p]['ss']: fl.append(p + '小跨')
        if FIN[a][0] == FIN[b][0] and {FIN[a][1], FIN[b][1]} == {0, 1}: fl.append(p + '小指干扰')
    for i in range(2):                                   # 作者 2026-10-15：同键三连（如 cooo 的 ooo）击键快了很痛苦，当量看不出来
        if c[i] == c[i + 1] == c[i + 2]: fl.append(c[i] * 3 + '同键三连'); break
    return f"{c} {eq:.1f}" + (' ' + '、'.join(fl) if fl else '')


def load_table(p):
    codes, slot = collections.defaultdict(list), collections.defaultdict(list)
    for l in open(p, encoding='utf-8-sig'):
        x = l.rstrip('\n').split('\t')
        if len(x) >= 2 and len(x[0]) == 1:
            codes[x[0]].append(x[1]); slot[x[1]].append(x[0])
    return codes, slot


def main(base_table):
    src = json.load(open(SRC, encoding='utf-8'))
    old = json.load(open(DST, encoding='utf-8')) if DST.exists() else {}
    skip = {(x[1], len(x[0])) for x in old.get('不照搬', [])}
    readings = collections.defaultdict(set)
    for r in json.load(open(ROOT / 'data/inputs/夜桜字音基准.json', encoding='utf-8')):
        readings[r['字']].add(r['拼音'])
    zr_codes, zr_slot = load_table(base_table)
    xh_codes, _ = load_table(ROOT / 'release/tables/普通单字表.txt')
    full = lambda codes, ch, sy: next((c for c in codes[ch] if len(c) == 4 and c[:2] == sy), None)
    out = {'说明': '夜桜（自然码 ZR27）的手动一简/二简/三简：由 yozakura/port_manual.py 从夜莺 data/inputs/手动调整.json 逐条换算（同一读音，码换成自然码）。'
                 '“不照搬”是作者复核后夜桜不采用的条目，不参与出表、换算时跳过。出表时 YZ_MANUAL 指向本文件。',
           '一简': [], '二简': [], '三简': [], '不照搬': old.get('不照搬', []),
           '不照搬说明': '夜莺手动调整中经作者复核、夜桜不照搬的条目（记录在此，不参与出表）。',
           '自定义码': old.get('自定义码', []),
           '自定义码说明': '夜莺自定义码（不按音码＋首根）的夜桜对应码，人工换算，换算脚本原样保留；说明里注明对应的小鹤码。'}
    if old.get('先拆三简'): out['先拆三简'] = old['先拆三简']           # 夜桜按自己的码另算（先拆走之），原样保留
    report = []
    for kind in ('一简', '二简', '三简'):
        for code, ch, note in src.get(kind, []):
            if (ch, len(code)) in skip:
                report.append(f'跳过（不照搬）{kind} {code} {ch}'); continue
            n = len(code)
            pys = [p for p in readings[ch] if encode(p, 'xiaohe')[:min(n, 2)] == code[:min(n, 2)]]
            assert pys, (kind, code, ch)
            py = max(pys, key=lambda p: len([c for c in xh_codes[ch] if c[:2] == encode(p, 'xiaohe')]))
            sy = encode(py, 'ziranma')
            if n == 1:
                new = sy[0]
            elif n == 2:
                new = sy
            else:
                f = full(zr_codes, ch, sy); assert f, (code, ch, py)
                new = f[:3]
            out[kind].append([new, ch, f'自小鹤 {code} 换算（{py}）。原注：{note}'])
            if n == 3:
                rivals = [x for x in zr_slot.get(new, []) if x != ch]
                m = re.search(r'([^\s，、：；（）]+?)只留全码', note)
                names = list(dict.fromkeys(rivals + ([m.group(1)[-1]] if m else [])))
                line = f'三简 {code}→{new} {ch}：夜桜里该码原归 {"、".join(zr_slot.get(new, [])) or "空"}'
                for x in [ch] + names:
                    xs = [p for p in readings[x] if encode(p, 'ziranma') == sy]
                    p_ = xs[0] if xs else py
                    line += f'\n      {x}：小鹤全码 {feel(full(xh_codes, x, encode(p_, "xiaohe")))} ｜ 夜桜全码 {feel(full(zr_codes, x, sy))}'
                report.append(line)
            else:
                report.append(f'{kind} {code}→{new} {ch}：夜桜里该码原归 {"、".join(zr_slot.get(new, [])) or "空"}')
    done = {(x[1], m.group(1)) for x in out['自定义码'] for m in [re.search(r'小鹤 (\w+)', x[2])] if m}
    for code, ch, note in src.get('自定义码', []):
        if (ch, code) in done: report.append(f'自定义码 {code} {ch}：夜桜已有人工换算'); continue
        if '先拆走之' in note and '容错' not in note: continue      # 先拆走之的三码：夜桜按自己的码与同一规则另算
        report.append(f'⚠ 自定义码 {code} {ch} 无法自动换算，需作者定：{note}')
    json.dump(out, open(DST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n'.join(report))
    print(f"写入 {DST}：一简 {len(out['一简'])}、二简 {len(out['二简'])}、三简 {len(out['三简'])}、不照搬 {len(out['不照搬'])}")


if __name__ == '__main__':
    main(sys.argv[1])
