"""Build the preview from website sources and the maintained release tools."""
from pathlib import Path
import json
import shutil
import re
from html import escape
import markdown

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / '.tmp' / 'website-preview'
RELEASE = ROOT / 'releases' / 'v1.0'

def build_root_practice(source: Path, target: Path):
    """Seed the built-in roots only when the learner has no saved deck."""
    text = source.read_text(encoding='utf-8')
    roots = (RELEASE / '04_查询与练习/夜莺码v1.0字根练习.txt').read_text(encoding='utf-8-sig')
    payload = json.dumps(roots, ensure_ascii=False).replace('<', r'\u003c')
    marker = '      await loadStoredData();'
    if text.count(marker) != 1:
        raise ValueError('Root practice initialization changed; check default import integration.')
    text = text.replace(marker, marker + f'''
      // Website default: retain existing decks and progress across reloads.
      if (!cards.length) {{
        await importFile(new File([{payload}], '夜莺1.0字根.txt', {{ type: 'text/plain' }}));
      }}''')
    text = text.replace('夜莺码 v1.0 字根练习器', '夜莺1.0 字根练习器')
    text = text.replace('if (shouldShowWelcome()) {',
                        "if (shouldShowWelcome() && currentFileName !== '夜莺1.0字根') {")
    target.write_text(text, encoding='utf-8')

def build_roots(source: Path, target: Path):
    """Render the maintained root data in the website theme."""
    text = source.read_text(encoding='utf-8')
    match = re.search(r'const DATA=(.*?);\s*const rows=', text, re.S)
    if not match:
        raise ValueError('Root table data marker changed')
    data = json.loads(match.group(1))
    if set(data) != set('abcdefghijklmnopqrstuvwxyz'):
        raise ValueError('Expected all 26 root keys')
    count = sum(len(roots) for roots in data.values())
    sections = []
    for letters in ('qwertyuiop', 'asdfghjkl', 'zxcvbnm'):
        cards = []
        for key in letters:
            roots = data[key]
            items = []
            for root, alias in roots:
                label = root.replace('(笔画)', '')
                parts = alias.split('；锚定同键: ')
                attached = parts[0]
                anchored = parts[1] if len(parts) > 1 else ''
                item_class = 'root-item stroke-root' if '(笔画)' in root else 'root-item'
                items.append('<div class="' + item_class + '"><dt>' + escape(label) + '</dt><dd>' + escape(attached) + ('<span class="anchor-note">锚定同键 · ' + escape(anchored) + '</span>' if anchored else '') + '</dd></div>')
            search = key + ' ' + ' '.join(root + ' ' + alias for root, alias in roots)
            cards.append('<article class="root-key" data-search="' + escape(search, quote=True) + '"><div class="key-head"><h2>' + key.upper() + '</h2><span>' + str(len(roots)) + ' 主根</span></div><dl>' + ''.join(items) + '</dl></article>')
        sections.append('<div class="root-row">' + ''.join(cards) + '</div>')
    merged_rows = []
    for key in 'abcdefghijklmnopqrstuvwxyz':
        entries = []
        for root, alias in data[key]:
            if alias:
                entries.append('<span><b>' + escape(root.replace('(笔画)', '')) + '</b>：' + escape(alias) + '</span>')
        merged_rows.append('<div class="merge-row"><b class="merge-letter">' + key + '</b><div>' + ('； '.join(entries) or '无附属根') + '</div></div>')
    template = (SOURCE / 'roots.html').read_text(encoding='utf-8')
    target.write_text(template.replace('<!-- ROOT_BOARD -->', ''.join(sections)).replace('<!-- MERGE_LIST -->', ''.join(merged_rows)).replace('{{ROOT_COUNT}}', str(count)), encoding='utf-8')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    article = markdown.Markdown(extensions=['toc'], extension_configs={'toc': {'baselevel': 2}})
    body = article.convert((ROOT / '素材' / '作者的话.md').read_text(encoding='utf-8-sig'))
    template = (SOURCE / 'author.html').read_text(encoding='utf-8')
    (OUT / 'author.html').write_text(template.replace('<!-- ARTICLE -->', body).replace('<!-- CONTENTS -->', article.toc), encoding='utf-8')
    shutil.copy2(SOURCE / 'author.css', OUT / 'author.css')
    shutil.copytree(SOURCE / 'assets', OUT / 'assets', dirs_exist_ok=True)
    for name in ('index.html', 'style.css', 'site.js', 'bird.svg', 'performance.html', 'performance.css', 'performance.js', 'performance-data.json', 'word-conflict-data.json', 'word-conflict-method.md', 'performance-source.png', 'roots.css', 'roots.js'):
        shutil.copy2(SOURCE / name, OUT / name)
    mappings = {
        'roots.html': '03_字根与拆分/夜莺码v1.0字根表.html',
        'root-practice.html': '04_查询与练习/夜莺码v1.0字根练习器.html',
        'split-practice.html': '04_查询与练习/必拆字/夜莺码v1.0必拆字练习.html',
        'split.html': '04_查询与练习/夜莺码v1.0拆分查询.html',
        'reverse.html': '04_查询与练习/夜莺码v1.0编码反查.html',
        'components.html': '04_查询与练习/夜莺码v1.0部件查字.html',
    }
    (OUT / 'tools').mkdir(exist_ok=True)
    for target, relative in mappings.items():
        if target == 'roots.html':
            shutil.copy2(RELEASE / relative, OUT / 'tools' / target)
        elif target == 'root-practice.html':
            shutil.copy2(RELEASE / relative, OUT / 'tools' / target)
        else:
            shutil.copy2(RELEASE / relative, OUT / 'tools' / target)
    links = {Path(relative).name: target for target, relative in mappings.items()}
    links.update({'工具导航.html': '../index.html#tools', 'bird.svg': '../bird.svg'})
    for page in (OUT / 'tools').glob('*.html'):
        text = page.read_text(encoding='utf-8')
        def rewrite(match):
            url = match.group(2)
            name = url.rsplit('/', 1)[-1]
            return match.group(1) + links.get(name, url) + match.group(3)
        text = re.sub(r'((?:href|src)=")([^"]+)(")', rewrite, text)
        page.write_text(text, encoding='utf-8')
    (OUT / '.nojekyll').touch()
    print(OUT)

if __name__ == '__main__':
    main()
