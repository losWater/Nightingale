"""按夜莺 2.0 字根图的样式生成夜莺 3.0 字根图（静态 HTML）。
用法：python build/make_root_chart.py <布局json: {G组: 键}> <输出html> [标题]
根族名沿用 2.0 字根键位表；2.5/3.0 新增或合并的根组按成员拼名。换键的根组标注 2.5 原键。
"""
import json, sys, html, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path.home() / 'Nightingale/work/夜莺2.0/65_群友离线工具包/夜莺2.0离线工具包'
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
G, B = META['groups'], META['layout']
STROKES = {'横', '竖', '撇', '点', '折'}


def family_map():
    fam = {}
    for l in open(SRC / '字根键位表.txt', encoding='utf-8-sig').read().splitlines()[1:]:
        p = l.split('\t')
        if len(p) >= 3:
            fam[p[0]] = p[2]
    fam.setdefault('夭', fam.get('天'))          # 3.0 新增：夭归入天所在的根族（大／小）
    return fam


def nowrap(name):
    """根族名按"／"分段，每段不在中间断行（如"卧人"不能断成"卧/人"）。"""
    return '／'.join(f'<span style="white-space:nowrap">{html.escape(x)}</span>' for x in name.split('／'))


def main(layout_path, out, title='夜莺 3.0 · 字根图', clean=False):
    lay = json.load(open(layout_path, encoding='utf-8'))
    fam = family_map()
    tpl = open(SRC / '字根图.html', encoding='utf-8-sig').read()
    head = tpl[:tpl.find('<div class="root-page">')]
    script = tpl[tpl.find('<script>'):]
    items = collections.defaultdict(list)
    span = collections.defaultdict(set)              # 2.0 根族若已拆到多个根组，就不再沿用其名
    for g in G:
        for r in G[g]:
            span[fam.get(r, r)].add(g)
    for g in sorted(G):
        roots = G[g]
        names = [fam.get(r, r) if len(span[fam.get(r, r)]) == 1 else roots[0] for r in roots]
        fams = list(dict.fromkeys(names))
        name = '／'.join(fams)
        members = [r for r in roots if r not in fams]
        if len(fams) > 1:                      # 合并组：成员列全
            members = [r for r in roots if r != name]
        items[lay[g]].append((name, members, None if clean else (B[g] if B[g] != lay[g] else None), any(f in STROKES for f in fams), roots))
    e = html.escape
    rows = []
    for row in ('qwertyuiop', 'asdfghjkl', 'zxcvbnm'):
        cards = []
        for k in row:
            its = items[k]
            search = ' '.join([k] + [f'{n} {" ".join(rs)}' for n, _, _, _, rs in its])
            dl = ''.join(
                f'<div class="root-item {"stroke-root" if st else ""}"><dt>{nowrap(n)}{f"<sup class=moved>原{o.upper()}</sup>" if o else ""}</dt>'
                f'<dd>{e("、".join(m))}</dd></div>' for n, m, o, st, _ in its)
            cards.append(f'<section class="root-key" data-search="{e(search)}"><div class="key-head"><h2>{k.upper()}</h2></div><dl>{dl}</dl></section>')
        rows.append('<div class="root-row">' + ''.join(cards) + '</div>')
    merge = []
    for k in sorted(items):
        for n, m, o, st, rs in items[k]:
            merge.append(f'<div class="merge-row"><span class="merge-letter">{k.upper()}</span><div><b>{e(n)}</b>：{e("、".join(rs))}'
                         f'{f" <span class=moved>（2.5 在 {o.upper()}）</span>" if o else ""}</div></div>')
    n_moved = sum(1 for g in G if lay[g] != B[g])
    body = (f'<div class="root-page"><section class="root-intro"><div><h1>{e(title)}</h1>'
            + (f'<p>NB46 方案 · 根族分组显示 · 共 {len(G)} 组</p></div></section>' if clean else
               f'<p>NB46 方案 · 根族分组显示 · 共 {len(G)} 组，其中 {n_moved} 组相对 2.5 换键（标“原X”）</p></div></section>')
            + '<div class="root-controls"><label class="root-search"><span>查字根或键位</span><input id="root-search" placeholder="例如：木、赢字架、e"></label>'
            '<div class="root-options"><button id="compact-view" aria-pressed="true">紧凑键盘</button><button id="full-view" aria-pressed="false">展开归并根</button>'
            '<button id="print-roots">打印</button></div></div><div class="root-guide"><p>根族标题在键盘上显示，成员见下方归并字根表。</p>'
            '<span id="search-status">按 QWERTY 键位排列</span></div>'
            '<div id="root-board" class="root-board hide-alias">' + ''.join(rows) + '</div><p id="no-roots" hidden>没有匹配的根。</p>'
            '<section id="merge-list" class="merge-list"><div class="merge-heading"><h2>归并字根表</h2><p>同一根族的成员使用同键' + ('。' if clean else '；括号内为 2.5 的原键位。') + '</p></div>'
            '<div class="merge-columns">' + ''.join(merge) + '</div></section></div>')
    style = '<style>.moved{white-space:nowrap;font:600 10px/1 var(--sans,sans-serif);color:#b4532a;margin-left:4px;letter-spacing:0;vertical-align:super}.merge-row .moved{vertical-align:baseline;font-size:12px}</style>'
    head = head.replace('<title>夜莺2.0字根图</title>', f'<title>{e(title.replace(" · ", ""))}</title>')
    open(out, 'w', encoding='utf-8').write(head + style + body + script)
    print('输出', out, '换键', n_moved)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--clean']
    main(*a, clean='--clean' in sys.argv)
