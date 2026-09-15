"""Build the preview from website sources and the maintained 2.0 release tools.

2026-09-16 夜莺 2.0：构建来源改为 releases/v2.0。工具页取离线工具包（拆分查询、部件反查、字根练习、完整拆分表、字根图），
字根表由 2.0 字根总表 + 当前完整根表生成（130 组 / 404 根形），啾啾工具箱单文件一并发布。
"""
from pathlib import Path
import json
import shutil
import re
from html import escape
import markdown

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / '.tmp' / 'website-preview'
RELEASE = ROOT / 'releases' / 'v2.0'
TOOLS = RELEASE / '04_查询与练习'
STROKES = {'横', '竖', '撇', '折', '点'}

def load_root_groups():
    """2.0 根组：取字根练习页内嵌的 roots 数据（404 根形：根、键、组、例字，与练习/工具箱同一份定稿），
    按组名分组、保持出现顺序；主根 = 组名第一段对应的根形（如 点／氵／冫 → 点），找不到则取组内第一个。"""
    text = (TOOLS / '离线工具包/字根练习.html').read_text(encoding='utf-8-sig')
    m = re.search(r'\bconst roots\s*=\s*', text)
    if not m:
        raise ValueError('roots data not found in 字根练习.html')
    roots, _ = json.JSONDecoder().raw_decode(text[m.end():])
    groups = {}; order = []
    for r in roots:
        g = r['组']
        if g not in groups:
            groups[g] = {'键': r['键'], '根': []}; order.append(g)
        groups[g]['根'].append((r['根'], r.get('例字', '')))
    data = {k: [] for k in 'abcdefghijklmnopqrstuvwxyz'}
    for g in order:
        key = groups[g]['键']; roots_in = groups[g]['根']; names = [n for n, _ in roots_in]
        first = g.split('／')[0].strip()
        head = first if first in names else names[0]
        others = [n for n in names if n != head]
        label = head + ('(笔画)' if head in STROKES else '')
        data[key].append((label, '、'.join(others), g, dict(roots_in).get(head, '')))
    return data

def build_roots(target: Path):
    data = load_root_groups()
    if set(data) != set('abcdefghijklmnopqrstuvwxyz'):
        raise ValueError('Expected all 26 root keys')
    count = sum(len(roots) for roots in data.values())
    forms = sum(1 + (len(alias.split('、')) if alias else 0) for roots in data.values() for _, alias, _, _ in roots)
    sections = []
    for letters in ('qwertyuiop', 'asdfghjkl', 'zxcvbnm'):
        cards = []
        for key in letters:
            roots = data[key]
            items = []
            for root, alias, family, examples in roots:
                label = root.replace('(笔画)', '')
                item_class = 'root-item stroke-root' if '(笔画)' in root else 'root-item'
                items.append('<div class="' + item_class + '" title="' + escape(family + (' · 例字 ' + examples if examples else ''), quote=True) + '"><dt>' + escape(label) + '</dt><dd>' + escape(alias) + '</dd></div>')
            search = key + ' ' + ' '.join(root + ' ' + alias + ' ' + family + ' ' + examples for root, alias, family, examples in roots)
            cards.append('<article class="root-key" data-search="' + escape(search, quote=True) + '"><div class="key-head"><h2>' + key.upper() + '</h2><span>' + str(len(roots)) + ' 组</span></div><dl>' + ''.join(items) + '</dl></article>')
        sections.append('<div class="root-row">' + ''.join(cards) + '</div>')
    merged_rows = []
    for key in 'abcdefghijklmnopqrstuvwxyz':
        entries = []
        for root, alias, family, examples in data[key]:
            if alias:
                entries.append('<span><b>' + escape(root.replace('(笔画)', '')) + '</b>：' + escape(alias) + '</span>')
        merged_rows.append('<div class="merge-row"><b class="merge-letter">' + key + '</b><div>' + ('； '.join(entries) or '无附属根') + '</div></div>')
    template = (SOURCE / 'roots.html').read_text(encoding='utf-8')
    target.write_text(template.replace('<!-- ROOT_BOARD -->', ''.join(sections)).replace('<!-- MERGE_LIST -->', ''.join(merged_rows)).replace('{{ROOT_COUNT}}', str(count)).replace('{{FORM_COUNT}}', str(forms)), encoding='utf-8')
    return count, forms

HOME_LINK = '<a href="../index.html" style="position:fixed;right:14px;bottom:14px;z-index:99;padding:8px 14px;border-radius:999px;background:#243a3a;color:#f2f1eb;text-decoration:none;font:15px/1 \'Microsoft YaHei\',sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.25)">← 夜莺首页</a>'

def copy_tool(src: Path, target: Path):
    text = src.read_text(encoding='utf-8-sig')
    if '</body>' in text:
        text = text.replace('</body>', HOME_LINK + '</body>', 1)
    else:
        text = text.replace('</html>', HOME_LINK + '</html>', 1)
    target.write_text(text, encoding='utf-8')

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    article = markdown.Markdown(extensions=['toc'], extension_configs={'toc': {'baselevel': 2}})
    body = article.convert((ROOT / '素材' / '作者的话.md').read_text(encoding='utf-8-sig'))
    template = (SOURCE / 'author.html').read_text(encoding='utf-8')
    (OUT / 'author.html').write_text(template.replace('<!-- ARTICLE -->', body).replace('<!-- CONTENTS -->', article.toc), encoding='utf-8')
    shutil.copy2(SOURCE / 'author.css', OUT / 'author.css')
    shutil.copytree(SOURCE / 'assets', OUT / 'assets', dirs_exist_ok=True)
    for name in ('index.html', 'style.css', 'site.js', 'bird.svg', 'performance.html', 'performance.css', 'performance.js', 'performance-data.json', 'roots.css', 'roots.js'):
        shutil.copy2(SOURCE / name, OUT / name)
    for stale in ('word-conflict-data.json', 'word-conflict-method.md', 'performance-source.png'):
        (OUT / stale).unlink(missing_ok=True)
    (OUT / 'tools').mkdir(exist_ok=True)
    for stale in ('reverse.html', 'split-practice.html'):
        (OUT / 'tools' / stale).unlink(missing_ok=True)
    mappings = {
        'split.html': TOOLS / '离线工具包/拆分查询.html',
        'components.html': TOOLS / '离线工具包/部件反查.html',
        'root-practice.html': TOOLS / '离线工具包/字根练习.html',
        'split-table.html': TOOLS / '离线工具包/完整拆分表.html',
        'root-chart.html': TOOLS / '离线工具包/字根图.html',
        'toolbox.html': TOOLS / '夜莺啾啾工具箱.html',
    }
    for target, src in mappings.items():
        copy_tool(src, OUT / 'tools' / target)
    count, forms = build_roots(OUT / 'tools' / 'roots.html')
    (OUT / '.nojekyll').touch()
    print(OUT, '字根组', count, '根形', forms)

if __name__ == '__main__':
    main()
