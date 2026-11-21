"""夜桜（夜莺 3.1 字根 + 自然码）官网分页：放在夜莺官网的 yozakura/ 下，与夜莺共用样式和明暗切换，配色换成樱色。
由 release/make_website.py 最后调用；也可单独跑：.venv/bin/python release/make_website_yozakura.py <夜莺官网输出目录>
- 版本、名称、形象取 yozakura/品牌.json（YZ_BRAND）；数据（字根组数、选重、字词冲突）现算，夜莺对照取同口径
- 下载区按 losWater/Yozakura 发布页 yozakura-v<版本> 上实际的附件生成；发布页还没建时显示“即将提供”
- 工具页：release/make_toolbox.py（YZ_BRAND）的夜桜单页与嘤嘤工具箱
- 与夜莺的差别：ZR27 相对 NB46 换键的根组（现算）
"""
import json, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.request
from html import escape
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / 'yozakura/品牌.json'
SITE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.cache/yeying-site'
OUT = SITE / 'yozakura'
PY = sys.executable
B = json.load(open(BRAND, encoding='utf-8'))
V, ID = B['版本'], B['标识']
NAME = B['名称'].removesuffix(V)                                  # 夜桜
REPO = 'losWater/Yozakura'
TAG = f'{ID}-v{V}'
REL = f'https://github.com/{REPO}/releases'
SRC = f'https://github.com/{REPO}/blob/main'
sys.path.insert(0, str(ROOT / 'release'))
from config import C as NG                                       # 夜莺（对照用；本进程不设 YZ_BRAND）
try:
    with urllib.request.urlopen(f'https://api.github.com/repos/{REPO}/releases/tags/{TAG}', timeout=60) as r:
        rel = json.load(r)
except urllib.error.HTTPError as e:
    assert e.code == 404, e
    rel = {'published_at': None, 'assets': []}
assets = {x['name']: x for x in rel['assets']}
DATE = (rel['published_at'] or '')[:10]


def perf(env, table, ver, out):
    subprocess.run([PY, str(ROOT / 'release/compute_performance.py'), str(table), ver, DATE or NG.DATE, str(out)],
                   env=env, check=True, stdout=subprocess.DEVNULL)
    d = json.load(open(out, encoding='utf-8'))
    return {r['scope']: r for r in d['rows']}, d['conflict']


if OUT.exists(): shutil.rmtree(OUT)
(OUT / 'tools').mkdir(parents=True)
tmp = Path(tempfile.mkdtemp())
yenv = dict(os.environ, YZ_BRAND=str(BRAND)); nenv = {k: v for k, v in os.environ.items() if k != 'YZ_BRAND'}
row, cf = perf(yenv, ROOT / 'yozakura' / B['字词表'], V, OUT / 'performance-data.json')
ng_table = NG.T('字词表.txt')                                    # 夜莺对照取已发布版（标签 v<版本>）的表，工作区里可能是下一版草稿
_tag = subprocess.run(['git', '-C', str(ROOT), 'show', f'v{NG.V}:{ng_table.relative_to(ROOT).as_posix()}'], capture_output=True)
if _tag.returncode == 0: ng_table = tmp / 'ng_字词表.txt'; ng_table.write_bytes(_tag.stdout)
nrow, ncf = perf(nenv, ng_table, NG.V, tmp / 'ng.json')
meta = json.load(open((ROOT / 'yozakura' / B['引擎输入']).resolve() / 'meta.json', encoding='utf-8'))
n_groups = len(meta['groups'])
zr = json.load(open(ROOT / 'yozakura' / B['布局'], encoding='utf-8'))
nb = json.load(open((ROOT / 'yozakura' / B['练习对照']['布局']).resolve(), encoding='utf-8'))
moved = sorted((g for g in meta['groups'] if zr[g] != nb[g]), key=lambda g: (nb[g], g))

# 形象：缩到 900 像素宽，减小页面体积
subprocess.run(['sips', '-Z', '900', str(ROOT / 'yozakura' / B['形象']), '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', '--out', str(OUT / 'yozakura-chibi.jpg')], check=True, stdout=subprocess.DEVNULL)

# ---- 工具页 ----
subprocess.run([PY, str(ROOT / 'release/make_toolbox.py'), str(tmp / 'tb')], env=yenv, check=True, stdout=subprocess.DEVNULL)
HOME = ('<a href="../index.html" style="position:fixed;right:14px;bottom:14px;z-index:99;padding:8px 14px;border-radius:999px;background:#4a2a3c;'
        f'color:#f7eef2;text-decoration:none;font:15px/1 \'Microsoft YaHei\',sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.25)">← {NAME}首页</a>')
N = B['名称']
pages = {'split.html': f'单页/{N}_拆分查询.html', 'components.html': f'单页/{N}_部件反查.html', 'root-practice.html': f'单页/{N}_字根练习.html',
         'split-table.html': f'单页/{N}_完整拆分表.html', 'root-chart.html': f'单页/{N}_字根图.html', 'roots.html': f'单页/{N}_字根表.html',
         'toolbox.html': f'{B["工具箱名"]}.html'}
for target, src in pages.items():
    s = (tmp / 'tb' / src).read_text(encoding='utf-8-sig')
    s = s.replace('</body>', HOME + '</body>', 1) if '</body>' in s else s.replace('</html>', HOME + '</html>', 1)
    (OUT / 'tools' / target).write_text(s, encoding='utf-8')

# ---- 下载区 ----
pick = lambda pat: sorted(n for n in assets if re.fullmatch(pat, n))
dl = lambda f, title, sub: f'<a href="{assets[f]["browser_download_url"]}"><span>{title}<small>{sub}</small></span><b>↓</b></a>'
FLAVOR = {'v5': ('Rime V5 版（推荐）', '魔虎 V5 本地整句模型 · 自然码'), 'shape': ('Rime 形码版', '无模型 · 四码、五码顶屏'),
          'single': ('Rime 形码单字版', '单字练习')}
PLAT = {'mac': ('Mac', 'Apple Silicon', '鼠须管'), 'windows': ('Windows', '小狼毫 x64', '小狼毫')}


def platform(plat):
    name, v5host, host = PLAT[plat]
    zips = {re.search(rf'-{plat}-(v5|shape|single)-', n).group(1): n for n in pick(rf'Yozakura-Rime-{re.escape(V)}-{plat}-(v5|shape|single)-\d{{8}}\.zip')}
    if not zips:
        return f'<p>{name} 包即将提供，完成后会出现在发布页。</p>'
    links = ''.join(dl(zips[k], f'{name} · {FLAVOR[k][0]}', f'{v5host if k == "v5" else host} · {FLAVOR[k][1]}') for k in ('v5', 'shape', 'single') if k in zips)
    sums = pick(rf'SHA256SUMS-{plat}-\d{{8}}\.txt')
    return f'<div class="download-list">{links}</div>' + (f'<a class="quiet-link" href="{assets[sums[0]]["browser_download_url"]}">{name} 校验值 ↗</a>' if sums else '')


others = pick(rf'Yozakura-{re.escape(V)}-tables-\d{{8}}\.zip'), pick(rf'Yozakura-Toolbox-{re.escape(V)}-\d{{8}}\.html')
status = f'{NAME} {V} <span class="divider">/</span> ' + (f'{DATE} 发布' if DATE else '发布页准备中')
download = ('<section class="section download" id="download"><div><span class="eyebrow">MAKE IT YOURS</span><h2>把夜桜带到你的键盘。</h2>'
            '<p>选择你使用的系统，下载对应输入法包。</p>'
            f'<div class="version"><span class="status-dot"></span> {status}</div>'
            + (f'<a class="quiet-link" href="{REL}/tag/{TAG}">查看发布页与全部附件 ↗</a>' if DATE else '')
            + (f'<br><a class="quiet-link" href="changelog.html">{V} 更新日志 →</a>' if (ROOT / f'yozakura/更新日志/{NAME}{V}.md').exists() else '') + '</div><div>'
            '<p>请按操作系统下载，Windows 与 Mac 包不能混装。已经装了夜莺也没关系：夜桜的方案名和文件名都和夜莺分开，两个可以并存。</p>'
            '<h3>macOS · 鼠须管</h3><p>V5 限 Apple Silicon。</p>' + platform('mac') +
            '<h3>Windows · 小狼毫</h3>' + platform('windows') +
            '<h3>其他输入法与工具</h3>'
            + ('<div class="download-list">' + ''.join(dl(n, '各平台码表', f'{V} 字词表与手心、搜狗、冰凌等平台码表') for n in others[0])
               + ''.join(dl(n, f'{B["工具箱名"]} · 单文件', '拆分查询、部件反查、字根练习、字根表、字根图、完整拆分表') for n in others[1]) + '</div>'
               if others[0] or others[1] else '<p>码表与工具箱即将提供；工具可以先在上面的“查询与练习”里在线使用。</p>')
            + '<p>魔虎原作者 <a href="https://github.com/fcxxxz/rime-mohu">fcxxxz / rime-mohu</a>：V5 模型、原生引擎及相关 Lua 为魔虎原作。'
            '夜桜提供码表与适配；原作者声明和许可证保留在包内。</p></div></section>')

# ---- 更新日志页 changelog.html：yozakura/更新日志/夜桜<版本>.md 各版，新版在前；套夜莺官网“作者的话”页的版式，配色同本页 ----
LOGS = sorted((ROOT / 'yozakura/更新日志').glob(f'{NAME}*.md'), key=lambda f: [int(x) for x in f.stem.removeprefix(NAME).split('.')], reverse=True)
yz_log = f'<a href="changelog.html">{NAME}更新日志 <span>→</span></a>' if LOGS else ''
THEME = ':root{--bg:#1c1520;--panel:#261c2b;--text:#f1e9ee;--muted:#b4a3ad;--line:#3d2f40;--accent:#f2b6cc;--button:#f0bfd2;--ink:#3a1d2b;--moon:#f3dbe5}' \
        ':root[data-theme=light]{--bg:#faf3f5;--panel:#f3e6eb;--text:#3b2433;--muted:#7a5d6b;--line:#e6d2da;--accent:#a8466e;--button:#a8466e;--ink:#fff;--moon:#f2d6e0}'
if LOGS:
    import markdown
    md = markdown.Markdown(extensions=['toc', 'tables'], extension_configs={'toc': {'baselevel': 2}})
    parts = []
    for f in LOGS:
        lines = [l for l in f.read_text(encoding='utf-8').split('\n') if not l.startswith('（草稿') and not l.startswith('<!--')]
        lines[0] = '# ' + lines[0].lstrip('# ').replace(' 更新日志', '')
        parts.append('\n'.join(lines))
    body = md.convert('\n\n'.join(parts))
    _a = subprocess.run(['git', '-C', str(Path.home() / 'Nightingale'), 'show', 'origin/gh-pages:author.html'], capture_output=True)
    t = _a.stdout.decode('utf-8') if _a.returncode == 0 else (SITE / 'author.html').read_text(encoding='utf-8')
    for a, b in (('href="style.css"', 'href="../style.css"'), ('href="author.css"', 'href="../author.css"'), ('src="site.js"', 'src="../site.js"'), ('href="bird.svg"', 'href="../bird.svg"')):
        assert a in t, a; t = t.replace(a, b)
    t = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{NAME}各版本更新日志，最新为 {V}。">', t)
    t = re.sub(r'<title>[^<]*</title>', f'<title>更新日志 · {NAME}{V}</title>', t)
    t = re.sub(r'<header class="header">.*?</header>', f'<header class="header"><a class="brand" href="index.html">{NAME}<span>YOZAKURA</span></a><nav aria-label="主导航">'
               f'<a href="index.html">首页</a><a href="index.html#download">下载</a><a href="../index.html">夜莺 ↗</a></nav>'
               '<div class="header-end"><button id="theme" type="button" aria-label="切换至浅色模式">☼</button></div></header>', t, count=1, flags=re.S)
    t = re.sub(r'<header class="article-heading">.*?</header>', f'<header class="article-heading"><p class="eyebrow">{NAME}</p><h1>更新日志</h1>'
               f'<p>最新：{V}' + (f'（{DATE}）' if DATE else '') + '</p></header>', t, flags=re.S)
    t = re.sub(r'(<nav aria-label="文章目录">).*?(</nav>)', lambda m_: m_.group(1) + md.toc + m_.group(2), t, flags=re.S)
    t = re.sub(r'(<article class="article-body" id="article">).*?(<p class="article-return">)', lambda m_: m_.group(1) + body + m_.group(2), t, flags=re.S)
    t = re.sub(r'<p class="article-return">.*?</p>', '<p class="article-return"><a href="index.html#download">← 返回夜桜首页</a></p>', t, flags=re.S)
    t = re.sub(r'<footer>.*?</footer>', f'<footer><a class="brand" href="index.html">{NAME}<span>YOZAKURA</span></a><p class="community">欢迎加入qq群聊交流：<strong>1121088815</strong></p></footer>', t, flags=re.S)
    t = t.replace('</head>', f'<style>{THEME}::selection{{background:#c9739a}}.article-body table{{border-collapse:collapse;margin:1em 0}}'
                  '.article-body th,.article-body td{border:1px solid var(--line);padding:6px 12px;text-align:center}</style></head>', 1)
    assert '夜莺</span>' not in t and 'NIGHTINGALE' not in t, '更新日志页残留夜莺页眉'
    (OUT / 'changelog.html').write_text(t, encoding='utf-8')

# ---- 与夜莺对比 ----
groups = meta['groups']
chips = ''.join(f'<li><b>{escape(groups[g][0])}</b><small>{escape("、".join(groups[g][1:4]))}{"…" if len(groups[g]) > 4 else ""}</small>'
                f'<span>{nb[g].upper()} → <em>{zr[g].upper()}</em></span></li>' for g in moved)
cmp_rows = ''
for label, f in [('前 1500 字选重', lambda r, c: r['前1500字']['选重']), ('前 3000 字选重', lambda r, c: r['前3000字']['选重']),
                 ('前 6000 字加权选重率', lambda r, c: f"{r['前6000字']['选重加权%']:.3f}%"), ('前 6000 字加权键长', lambda r, c: f"{r['前6000字']['加权键长']:.2f}"),
                 ('前 1500 字无简码的字', lambda r, c: c['前1500字中无简码的字数']),
                 ('字词全码同码 → 剔除有简码的字', lambda r, c: f"{c['全部单字全码']} → {c['剔除有简码的字']}")]:
    cmp_rows += f'<tr><th scope="row">{label}</th><td>{f(row, cf)}</td><td>{f(nrow, ncf)}</td></tr>'

r15, r60 = row['前1500字'], row['前6000字']
html = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{NAME} {V}，夜莺的自然码版：夜莺的字根与拆分，配自然码双拼。">
  <meta name="theme-color" content="#1c1520">
  <title>{NAME} · 夜莺的自然码版</title>
  <link rel="icon" href="../bird.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../style.css">
  <style>
    :root{{--bg:#1c1520;--panel:#261c2b;--text:#f1e9ee;--muted:#b4a3ad;--line:#3d2f40;--accent:#f2b6cc;--button:#f0bfd2;--ink:#3a1d2b;--moon:#f3dbe5}}
    :root[data-theme=light]{{--bg:#faf3f5;--panel:#f3e6eb;--text:#3b2433;--muted:#7a5d6b;--line:#e6d2da;--accent:#a8466e;--button:#a8466e;--ink:#fff;--moon:#f2d6e0}}
    ::selection{{background:#c9739a}}
    .character-frame{{background:#fff;border-color:#e8b9cb88}}
    .character-art figcaption small{{color:#d58aa8}}
    .moved{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}}
    .moved li{{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--panel);display:flex;flex-direction:column;gap:2px}}
    .moved b{{font-family:var(--serif);font-size:20px;font-weight:500}}.moved small{{color:var(--muted);font-size:11px;min-height:1.6em}}
    .moved span{{font:12px var(--sans);letter-spacing:1px;color:var(--muted)}}.moved em{{font-style:normal;color:var(--accent);font-weight:600}}
    .compare{{width:100%;border-collapse:collapse;font-size:14px;margin:6px 0 10px}}
    .compare th,.compare td{{padding:10px 8px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}}
    .compare th[scope=row]{{text-align:left;font-weight:400;color:var(--muted)}}.compare thead th{{font-weight:600}}
    .compare td:nth-child(2){{color:var(--accent);font-weight:600}}
    .sibling{{display:inline-block;margin-top:14px;font-size:12px;color:var(--muted)}}.sibling:hover{{color:var(--accent)}}
  </style>
  <script src="../site.js" defer></script>
</head>
<body>
  <a class="skip" href="#main">跳到正文</a>
  <header class="header"><a class="brand" href="#">{NAME}<span>YOZAKURA</span></a>
    <nav aria-label="主导航"><a href="#learn">开始学习</a><a href="#tools">查询与练习</a><a href="#diff">与夜莺的区别</a><a href="#download">下载</a>{'<a href="changelog.html">更新日志</a>' if LOGS else ''}<a href="../index.html">夜莺 ↗</a></nav>
    <div class="header-end"><a href="https://github.com/{REPO}" class="github">GitHub ↗</a><button id="theme" type="button" aria-label="切换至浅色模式" title="切换明暗模式">☼</button></div>
  </header>
  <main id="main">
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy"><div class="eyebrow"><span class="status-dot"></span> {NAME} {V} · 夜莺的自然码版</div>
        <h1 id="hero-title">{NAME}<span>同一套字根，<br>换一种双拼。</span></h1>
        <p class="intro">夜莺的字根与拆分 · 自然码双拼</p>
        <p class="principles">乱序字根 <i>·</i> 拆分直观 <i>·</i> 常用字无重 <i>·</i> 常用字词避重</p>
        <div class="actions"><a class="button primary" href="#learn">开始学习 <span>→</span></a><a class="button secondary" href="#download">下载码表 <span>↓</span></a></div>
        {f'<a class="quiet-link" href="changelog.html">{V} 更新了什么？看更新日志 →</a><br>' if LOGS else ''}<a class="quiet-link" href="tools/split.html">已经在用了？查一个字的拆分 ↗</a><br>
        <a class="sibling" href="../index.html">用小鹤双拼？请看夜莺 ↗</a>
      </div>
      <figure class="hero-art character-art">
        <div class="character-frame"><img src="yozakura-chibi.jpg" alt="Q版夜桜：深紫长发、樱花和服，捧着发光的“桜”字键帽，周围飘着樱花花瓣" width="900" height="900" fetchpriority="high"></div>
        <figcaption>夜色里，樱花落在指尖。<small>YOZAKURA · 夜桜</small></figcaption>
      </figure>
    </section>
    <section class="features" aria-label="方案特点">
      <article><span class="feature-number">01 / 同源</span><h2>与夜莺同根</h2><p>字根、归并、拆分与夜莺相同，<br>夜莺改动时夜桜同步更新。</p></article>
      <article><span class="feature-number">02 / 双拼</span><h2>自然码音码</h2><p>音码用自然码双拼。<br>为配合自然码，{len(moved)} 组字根换了键。</p></article>
      <article><span class="feature-number">03 / 单字</span><h2>常用字无重</h2><p>前 1500 字选重为 {r15["选重"]}，<br>前 6000 字加权选重率 {r60["选重加权%"]:.3f}%。</p></article>
      <article><span class="feature-number">04 / 字词</span><h2>常用字词避重</h2><p>有简码的字在全码位让给词。<br>高频字词全码冲突 {cf["全部单字全码"]} 对降到 {cf["剔除有简码的字"]}。</p></article>
    </section>
    <section class="section learn" id="learn">
      <div class="section-heading"><div><span class="eyebrow">GET STARTED</span><h2>从读音出发，用字形落笔。</h2></div><p>会自然码双拼，就有了熟悉的起点。<br>接下来，认识字根，练习拆分。</p></div>
      <div class="learn-layout"><div class="formula"><span class="tiny-label">单字全码 · 四键成字</span><div class="keys"><kbd>a</kbd><kbd>b</kbd><span>＋</span><kbd>x</kbd><kbd>y</kbd></div><div class="key-labels"><span>自然码音码</span><span>首根</span><span>末根</span></div><p>先取读音，再取规范拆分的首、末字根。<br>常用字还可以使用一至三简；二字词取两字双拼，三字词取三字首码。规则与夜莺相同，只是音码换成自然码。</p><a href="{SRC}/docs/夜桜自然码.md">阅读夜桜的设计记录 ↗</a></div>
        <div class="steps"><div class="practice-companion"><img src="yozakura-chibi.jpg" alt="Q版夜桜捧着桜字键帽" width="900" height="900" loading="lazy"><p>从一个字根开始，<br>慢慢熟悉每一个键位。</p></div><a href="tools/roots.html"><span>01</span><div><h3>认识字根</h3><p>查看键位分布，找到每个字根的位置。</p></div><b>↗</b></a><a href="tools/root-practice.html"><span>02</span><div><h3>练熟键位</h3><p>字根练习按题数间隔复习；夜莺用户可以只练换了键的根。</p></div><b>↗</b></a><a href="tools/split.html"><span>03</span><div><h3>开始拆字</h3><p>遇到不会拆的字随时查询，看拆分与可用编码。</p></div><b>↗</b></a></div></div>
      <details class="scope"><summary>“常用字无重”的统计口径</summary><p>与夜莺官网同一口径，按 {NAME} {V} 字词表与多来源字频重算：每字取主读音最短入口，前 1500 字选重为 {r15["选重"]}，前 3000 字合计 {row["前3000字"]["选重"]}，前 6000 字合计 {r60["选重"]}、按字频加权选重率 {r60["选重加权%"]:.3f}%。字词冲突取字频前 1500 的字与虎码词库词频前 10000 的多字词，全码同码 {cf["全部单字全码"]} 对，剔除有简码的字后为 {cf["剔除有简码的字"]}。</p></details>
    </section>
    <section class="section" id="tools"><div class="section-heading"><div><span class="eyebrow">YOUR TOOLBOX</span><h2>遇到一个字，就来这里。</h2></div><p>查询与练习，随时打开。<br>都在浏览器本地运行，不需要联网。</p></div>
      <div class="tool-grid"><a class="tool-card" href="tools/split.html"><span class="tool-glyph">拆</span><h3>拆分查询 <b>↗</b></h3><p>查汉字的规范拆分与全部编码，也可以输入编码查候选。</p></a><a class="tool-card" href="tools/components.html"><span class="tool-glyph">根</span><h3>部件反查 <b>↗</b></h3><p>从熟悉的部件出发，按首根、末根找到目标字。</p></a><a class="tool-card" href="tools/root-chart.html"><span class="tool-glyph">图</span><h3>字根图 <b>↗</b></h3><p>整张键盘上的字根分布，适合打印或放在手边。</p></a><a class="tool-card" href="tools/toolbox.html"><span class="tool-glyph">箱</span><h3>{B["工具箱名"]} <b>↗</b></h3><p>以上全部合在一个页面里，含完整拆分表，可下载离线用。</p></a></div>
    </section>
    <section class="section" id="diff"><div class="section-heading"><div><span class="eyebrow">FROM NIGHTINGALE</span><h2>从夜莺过来，只要记住这些。</h2></div><p>拆分、简码规则都不变。<br>{len(moved)} 组字根换了键，其余 {n_groups - len(moved)} 组与夜莺相同。</p></div>
      <ul class="moved">{chips}</ul>
      <div class="section-heading" style="margin-top:46px"><div><h2 style="font-size:22px">与夜莺 {NG.V} 同口径对比</h2></div><p>两边都按各自的正式字词表重算。</p></div>
      <table class="compare"><thead><tr><th></th><th scope="col">{NAME} {V}</th><th scope="col">夜莺 {NG.V}</th></tr></thead><tbody>{cmp_rows}</tbody></table>
      <p style="font-size:13px;color:var(--muted)">夜莺手动定的简码，夜桜按同一读音换算成自然码照搬；个别经作者复核不照搬的，记录在设计记录里。</p>
    </section>
    {download}
    <section class="section updates" id="updates"><div><img class="update-portrait" src="yozakura-chibi.jpg" alt="夜桜头像" width="900" height="900" loading="lazy"><span class="eyebrow">GROWING WITH NIGHTINGALE</span><h2>夜莺每进一步，夜桜也跟上一步。</h2><p>夜桜的字根和拆分取自夜莺，夜莺调整后夜桜一条命令重建。<br>用自然码打字的反馈，同样欢迎。</p></div><div class="update-links"><a href="{SRC}/docs/夜桜自然码.md">设计与维护记录 <span>↗</span></a>{yz_log}<a href="../changelog.html">夜莺更新日志 <span>↗</span></a><a href="https://github.com/{REPO}/issues">反馈一个问题 <span>↗</span></a></div></section>
  </main>
  <footer><a class="brand" href="#">{NAME}<span>YOZAKURA</span></a><p class="community">欢迎加入qq群聊交流：<strong>1121088815</strong></p><a href="https://github.com/{REPO}">在 GitHub 上一起完善 ↗</a></footer>
</body>
</html>
'''
(OUT / 'index.html').write_text(html, encoding='utf-8')
shutil.rmtree(tmp)
print(OUT, f'；换键 {len(moved)} 组；前1500选重', r15['选重'], '前6000加权', r60['选重加权%'], '；冲突', cf['全部单字全码'], '→', cf['剔除有简码的字'],
      '；发布页', '已建' if DATE else '未建（下载区显示即将提供）')
