from pathlib import Path
import json, re
from html import escape
ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / "assets"
RELEASE = ROOT / "releases/v0.9.1"

def build_root_practice(source: Path, target: Path):
    """Seed the built-in roots only when the learner has no saved deck."""
    text = source.read_text(encoding='utf-8')
    roots = (RELEASE / '04_查询与练习/夜莺码v0.9.1字根练习.txt').read_text(encoding='utf-8-sig')
    payload = json.dumps(roots, ensure_ascii=False).replace('<', r'\u003c')
    marker = '      await loadStoredData();'
    if text.count(marker) != 1:
        raise ValueError('Root practice initialization changed; check default import integration.')
    text = text.replace(marker, marker + f'''
      // Website default: retain existing decks and progress across reloads.
      if (!cards.length) {{
        await importFile(new File([{payload}], '夜莺1.0字根.txt', {{ type: 'text/plain' }}));
      }}''')
    text = text.replace('夜莺码 v0.9.1 字根练习器', '夜莺1.0 字根练习器')
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