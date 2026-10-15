"""夜莺官网（本地预览与发布用）：以夜莺仓库 apps/website 为底（作者的话取已发布的 gh-pages 版，素材目录不在稀疏检出里），换成当前版本。
版本、上一版、升级说明、维护记录链接都取 release/版本.json（release/config.py）；日期：发布页已建取发布日期，否则取今天。
- 首页：版本、方案数据（字根组数、选重、字词冲突）、下载区（按发布页 v<版本> 上实际的附件生成）、更新日志（站内 changelog.html）
- 性能页：release/compute_performance.py 现算（与 2.0 官网同口径；词频改用虎码词库）
- 工具页：release/make_toolbox.py 的工具箱单页；字根表由字根练习页内嵌的 roots 数据生成
- 更新日志：release/更新日志/ 里各版本的 md，新版本在前
每处替换都先核对原文存在，2.0/2.5 字样替换后不能残留（下载区的历史版本链接、升级说明除外）。
用法：python release/make_website.py [输出目录]   # 默认 ~/.cache/yeying-site；预览：python3 -m http.server 8765 --directory <输出目录>
"""
import json, re, shutil, subprocess, sys, tempfile
from html import escape
from pathlib import Path
import markdown
ROOT = Path(__file__).resolve().parent.parent
NG = Path.home() / 'Nightingale'; SRC = NG / 'apps/website'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.cache/yeying-site'
sys.path.insert(0, str(ROOT / 'release'))
from config import C
V = C.V
REL = 'https://github.com/losWater/Nightingale/releases'
import urllib.request, urllib.error
try:                                            # 发布页已建：日期与下载附件都以发布页为准；还没建（本地预览）：日期取今天，下载区显示“即将提供”
    with urllib.request.urlopen(f'https://api.github.com/repos/losWater/Nightingale/releases/tags/v{V}', timeout=60) as _r:
        _rel = json.load(_r)
except urllib.error.HTTPError as e:
    assert e.code == 404, e
    _rel = {'published_at': C.DATE, 'assets': []}
DATE = _rel['published_at'][:10]
STROKES = {'横', '竖', '撇', '折', '点'}


def rep(t, old, new, count=1):
    assert t.count(old) == count, (old[:50], t.count(old))
    return t.replace(old, new)


if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True)
tmp = Path(tempfile.mkdtemp())
subprocess.run([sys.executable, str(ROOT / 'release/make_toolbox.py'), str(tmp / 'tb')], check=True)
subprocess.run([sys.executable, str(ROOT / 'release/compute_performance.py'), str(ROOT / 'release/tables/字词表.txt'), f'{V}', DATE, str(OUT / 'performance-data.json')],
               check=True, stdout=subprocess.DEVNULL)
perf = json.load(open(OUT / 'performance-data.json', encoding='utf-8'))
row = {r['scope']: r for r in perf['rows']}
r15, r30, r60 = row['前1500字'], row['前3000字'], row['前6000字']
cf = perf['conflict']
meta = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
n_groups = len(meta['groups']); n_forms = sum(len(v) for v in meta['groups'].values())

for name in ('style.css', 'site.js', 'bird.svg', 'performance.css', 'performance.js', 'roots.css', 'roots.js', 'author.css'):
    shutil.copy2(SRC / name, OUT / name)
shutil.copytree(SRC / 'assets', OUT / 'assets')
(OUT / 'author.html').write_bytes(subprocess.run(['git', '-C', str(NG), 'show', 'origin/gh-pages:author.html'], check=True, capture_output=True).stdout)
(OUT / '.nojekyll').touch()

# ---- 首页 ----
t = (SRC / 'index.html').read_text(encoding='utf-8')
t = rep(t, 'content="夜莺 2.5，', f'content="夜莺 {V}，')
t = rep(t, '</span> 夜莺 2.5 · 正式发布</div>', f'</span> 夜莺 {V} · 正式发布</div>')
t = rep(t, '<p>130 组字根，由退火与人工裁定共同定下键位。', f'<p>{n_groups} 组字根，由退火与人工裁定共同定下键位。')
t = rep(t, '前 1500 字选重为 0，前 6000 字加权选重率 0.017%。', f'前 1500 字选重为 {r15["选重"]}，前 6000 字加权选重率 {r60["选重加权%"]:.3f}%。')
t = rep(t, '高频字词全码冲突 55 对降到 0。', f'高频字词全码冲突 {cf["全部单字全码"]} 对降到 {cf["剔除有简码的字"]}。')
t = rep(t, '<p>按 2.5 最终表与多来源字频重算：每字取主读音最短入口，前 1500 字选重为 0，前 3000 字合计 7，前 6000 字合计 171、按字频加权选重率 0.017%。'
           '字词冲突取字频前 1500 的字与词频前 10000 的四码词，全码同码 55 对，剔除有简码的字后为 0。</p>',
        f'<p>按 {V} 字词表与多来源字频重算：每字取主读音最短入口，前 1500 字选重为 {r15["选重"]}，前 3000 字合计 {r30["选重"]}，'
        f'前 6000 字合计 {r60["选重"]}、按字频加权选重率 {r60["选重加权%"]:.3f}%。字词冲突取字频前 1500 的字与虎码词库词频前 10000 的多字词，'
        f'全码同码 {cf["全部单字全码"]} 对，剔除有简码的字后为 {cf["剔除有简码的字"]}。</p>')
t = rep(t, '<p>归并组与全部根形两种模式，答错原题重学。</p>', f'<p>归并组与全部根形，可以只练 {V} 改动过的根，答错原题重学。</p>')
a = t.index('<section class="section download" id="download">'); b = t.index('</section>', a) + len('</section>')
# 下载区按发布页上实际的附件生成：文件名、日期、有哪些平台都从发布页读，不写死
assets = {x['name']: x for x in _rel['assets']}
pick = lambda pat: sorted(n for n in assets if re.fullmatch(pat, n))
FLAVOR = {'v5': ('Rime V5 版（强烈推荐）', '魔虎 V5 本地整句模型'), 'shape': ('Rime 形码版', '无模型 · 四码、五码顶屏'),
          'single': ('Rime 形码单字版', '单字练习与夜莺快符')}
PLAT = {'mac': ('Mac', 'Apple Silicon' , '鼠须管'), 'windows': ('Windows', '小狼毫 x64', '小狼毫')}
dl = lambda f, title, sub: f'<a href="{assets[f]["browser_download_url"]}"><span>{title}<small>{sub}</small></span><b>↓</b></a>'


def platform(plat):
    name, v5host, host = PLAT[plat]
    zips = {re.search(rf'-{plat}-(v5|shape|single)-', n).group(1): n for n in pick(rf'Nightingale-Rime-{re.escape(V)}-{plat}-(v5|shape|single)-\d{{8}}\.zip')}
    if not zips:
        return f'<p>{name} {V} 包即将提供，完成后会出现在发布页。</p>'
    links = ''.join(dl(zips[k], f'{name} · {FLAVOR[k][0]}', f'{v5host if k == "v5" else host} · {FLAVOR[k][1]}') for k in ('v5', 'shape', 'single') if k in zips)
    sums = pick(rf'SHA256SUMS-{plat}-\d{{8}}\.txt')
    return f'<div class="download-list">{links}</div>' + (f'<a class="quiet-link" href="{assets[sums[0]]["browser_download_url"]}">{name} 校验值 ↗</a>' if sums else '')


plats = [PLAT[p_][0] for p_ in ('windows', 'mac') if pick(rf'Nightingale-Rime-{re.escape(V)}-{p_}-.*\.zip')]
others = pick(rf'Nightingale-{re.escape(V)}-tables-\d{{8}}\.zip'), pick(rf'Nightingale-Toolbox-{re.escape(V)}-\d{{8}}\.html')
download = ('<section class="section download" id="download"><div><span class="eyebrow">MAKE IT YOURS</span><h2>把夜莺带到你的键盘。</h2>'
            '<p>选择你使用的系统，下载对应输入法包。</p>'
            f'<div class="version"><span class="status-dot"></span> 夜莺 {V} <span class="divider">/</span> {DATE} · {" / ".join(plats)} Rime 三版本</div>'
            f'<a class="quiet-link" href="{REL}/tag/v{V}">查看发布页与全部附件 ↗</a>'
            + ''.join(f'<a class="quiet-link" href="{REL}/tag/v{h}">历史版本：{h} 发布页 ↗</a>' for h in dict.fromkeys([C.PREV] + C.HISTORY)) + '</div><div>'
            '<p><strong>只建议使用 V5 版本。V5 模型：强烈推荐。</strong></p>'
            '<p>请按操作系统下载，Windows 与 Mac 包不能混装。升级前备份个人词库。</p>'
            f'<p>{C.UPGRADE}</p>'
            '<h3>Windows · 小狼毫</h3><p>Windows x64 · 官方小狼毫 0.17.4；V5 不适用于 32 位或原生 ARM64 宿主。</p>' + platform('windows') +
            '<h3>macOS · 鼠须管</h3><p>V5 限 Apple Silicon；Intel Mac 不在本次 V5 支持范围。</p>' + platform('mac') +
            '<h3>其他输入法与工具</h3><div class="download-list">'
            + ''.join(dl(n, '手心 · 搜狗 · 冰凌 · Bime', f'{V} 各平台码表与说明，不是 Windows Rime 包') for n in others[0])
            + ''.join(dl(n, '啾啾工具箱 · 单文件', '拆分查询、部件反查、字根练习、字根表、字根图、完整拆分表') for n in others[1]) + '</div>'
            '<p>魔虎原作者 <a href="https://github.com/fcxxxz/rime-mohu">fcxxxz / rime-mohu</a>：V5 模型、原生引擎及相关 Lua 为魔虎原作，不是夜莺原创。'
            '夜莺提供码表、词图与适配；原作者声明和许可证保留在包内 attribution/ 与 LICENSE-mohu。</p></div></section>')
t = t[:a] + download + t[b:]
t = rep(t, 'href="https://github.com/losWater/Nightingale/blob/main/releases/v2.5/夜莺2.5更新日志.md"', 'href="changelog.html"')
t = rep(t, 'href="https://github.com/losWater/Nightingale/blob/main/releases/v2.5/05_规则与裁决/当前任务树.md"', f'href="{C.RECORD}"')
rest = re.sub(r'releases/(tag|download)/v(2\.5|1\.0)[^"]*', '', t)
rest = rest.replace('releases/v2.5/05_规则与裁决/码表概念与规则.md', '')      # 编码规则没变，仍指向 2.5 的规则文档
rest = rest.replace(C.UPGRADE, '')
for h in [C.PREV] + C.HISTORY: rest = rest.replace(f'历史版本：{h} 发布页', '')
assert not re.search(r'2\.[05]', rest), re.findall(r'.{30}2\.[05].{10}', rest)
(OUT / 'index.html').write_text(t, encoding='utf-8')

# ---- 性能页 ----
t = (SRC / 'performance.html').read_text(encoding='utf-8')
t = rep(t, 'content="夜莺 2.0 单字性能与字词避重：码长分布、选重、键位负担与字词冲突，全部按 2.0 最终表重算。"',
        f'content="夜莺 {V} 单字性能与字词避重：码长分布、选重、键位负担与字词冲突，全部按 {V} 字词表重算。"')
t = rep(t, '<title>性能 · 夜莺2.0</title>', f'<title>性能 · 夜莺{V}</title>')
t = rep(t, '<span class="eyebrow">夜莺 2.0 / 性能</span>', f'<span class="eyebrow">夜莺 {V} / 性能</span>')
t = rep(t, '这里的数据全部按 2.0 最终表、多来源字频与统一当量表重算', f'这里的数据全部按 {V} 字词表、多来源字频与统一当量表重算')
# 上一版同口径的字词冲突（取 git 标签 v<上一版> 的字词表；3.0 标签里还是旧文件名）
for _p in ('release/tables/字词表.txt', 'release/tables/夜莺3.0_NB46_字词表.txt'):
    _r = subprocess.run(['git', '-C', str(ROOT), 'show', f'v{C.PREV}:{_p}'], capture_output=True)
    if _r.returncode == 0: (tmp / 'prev.txt').write_bytes(_r.stdout); break
subprocess.run([sys.executable, str(ROOT / 'release/compute_performance.py'), str(tmp / 'prev.txt'), C.PREV, DATE, str(tmp / 'prev.json')], check=True, stdout=subprocess.DEVNULL)
pcf = json.load(open(tmp / 'prev.json', encoding='utf-8'))['conflict']
t = rep(t, '2026-09-16 重算 · 单字取主读音最短入口', f'{DATE} 重算 · 单字取主读音最短入口')
t = rep(t, '<span id="conflict-full">55</span> 对 → <span id="conflict-left">0</span> 对',
        f'<span id="conflict-full">{cf["全部单字全码"]}</span> 对 → <span id="conflict-left">{cf["剔除有简码的字"]}</span> 对')
t = rep(t, '<p>夜莺2.0单字 × 2.0 普通词表（四家共识）<br>', f'<p>夜莺{V}单字 × 虎码词库词频<br>')
t = rep(t, '<b id="conflict-full-bar">55 对</b>', f'<b id="conflict-full-bar">{cf["全部单字全码"]} 对</b>')
t = rep(t, '前 1500 字里没有简码的字只有 126 个。', f'前 1500 字里没有简码的字只有 {cf["前1500字中无简码的字数"]} 个。')
n_rows = sum(1 for l in open(ROOT / 'release/tables/字词表.txt', encoding='utf-8-sig') if '\t' in l)
t = rep(t, '<p>2026-09-16 按 2.0 最终表（155139 条）重算。字取字频前 1500（32 多来源字频）的全部四码全码；词取 08 综合排名前 10000 的四码词；同码即计一对。'
           '剔除有简码的字后再算一次。与 1.0 页面口径相同，词表换为 2.0 的四家共识普通词表。</p>',
        f'<p>{DATE} 按 {V} 字词表（{n_rows} 条）重算。字取字频前 1500（32 多来源字频）的全部四码全码；词取虎码词库词频前 10000 的多字词；同码即计一对。'
        f'剔除有简码的字后再算一次。口径与 2.0 页面相同，只是词频改用虎码词库（2.0 用的综合词频不在仓库里）；同一口径下 {C.PREV} 为 {pcf["全部单字全码"]} 对 → {pcf["剔除有简码的字"]} 对。</p>')
script = f'{C.SOURCE}/release/compute_performance.py'
t = rep(t, 'https://github.com/losWater/Nightingale/blob/main/work/夜莺2.0/118_官网2.0/compute_performance.py', script, 2)
t = rep(t, '<p>以下数据按 2.0 最终表重算，与上述字词冲突分别统计。</p>', f'<p>以下数据按 {V} 字词表重算，与上述字词冲突分别统计。</p>')
t = rep(t, '<strong>0</strong><h2>前1500字选重</h2>', f'<strong>{r15["选重"]}</strong><h2>前1500字选重</h2>')
t = rep(t, '<strong>0.017<small>%</small></strong>', f'<strong>{r60["选重加权%"]:.3f}<small>%</small></strong>')
t = rep(t, '<strong>3.21</strong><h2>前6000字加权键长</h2>', f'<strong>{r60["加权键长"]:.2f}</strong><h2>前6000字加权键长</h2>')
t = rep(t, '<h3>前1500字：357 → 0</h3><p>前 1500 字里有 357 个字的全码不在首选',
        f'<h3>前1500字：{r15["全码重"]} → {r15["选重"]}</h3><p>前 1500 字里有 {r15["全码重"]} 个字的全码不在首选')
t = rep(t, '<h3>前3000字：7 个选重</h3><p>前 1500 字为 0，1501–3000 字区间为 7。前 6000 字合计 171，',
        f'<h3>前3000字：{r30["选重"]} 个选重</h3><p>前 1500 字为 {r15["选重"]}，1501–3000 字区间为 {row["1501–3000"]["选重"]}。前 6000 字合计 {r60["选重"]}，')
t = rep(t, '<h3>171 字 ≠ 0.017% 的字</h3><p>171 / 6000 约为 2.85%，这是字数占比；0.017% 是按字频加权的选重率',
        f'<h3>{r60["选重"]} 字 ≠ {r60["选重加权%"]:.3f}% 的字</h3><p>{r60["选重"]} / 6000 约为 {r60["选重"] / 60:.2f}%，这是字数占比；{r60["选重加权%"]:.3f}% 是按字频加权的选重率')
t = rep(t, '<caption>夜莺 2.0 单字性能 · 2026-09-16 重算</caption>', f'<caption>夜莺 {V} 单字性能 · {DATE} 重算</caption>')
t = rep(t, '<p>字表：2.0 最终表（含扩展字', f'<p>字表：{V} 字词表（含扩展字')
assert not re.search(r'2\.[05]', t.replace('2.5 为', '').replace('与 2.0 页面', '').replace('（2.0 用的', '')), re.findall(r'.{30}2\.[05].{10}', t)
(OUT / 'performance.html').write_text(t, encoding='utf-8')

# ---- 工具页 ----
HOME_LINK = ('<a href="../index.html" style="position:fixed;right:14px;bottom:14px;z-index:99;padding:8px 14px;border-radius:999px;background:#243a3a;'
             'color:#f2f1eb;text-decoration:none;font:15px/1 \'Microsoft YaHei\',sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.25)">← 夜莺首页</a>')
(OUT / 'tools').mkdir()
pages = {'split.html': f'单页/{C.NAME}_拆分查询.html', 'components.html': f'单页/{C.NAME}_部件反查.html', 'root-practice.html': f'单页/{C.NAME}_字根练习.html',
         'split-table.html': f'单页/{C.NAME}_完整拆分表.html', 'root-chart.html': f'单页/{C.NAME}_字根图.html', 'toolbox.html': '夜莺啾啾工具箱.html'}
for target, src in pages.items():
    s = (tmp / 'tb' / src).read_text(encoding='utf-8-sig')
    s = s.replace('</body>', HOME_LINK + '</body>', 1) if '</body>' in s else s.replace('</html>', HOME_LINK + '</html>', 1)
    (OUT / 'tools' / target).write_text(s, encoding='utf-8')

# ---- 字根表（同 apps/website/build.py，按 (组, 键) 分组：3.0 鸟／虫 拆在两个键）----
s = (tmp / f'tb/单页/{C.NAME}_字根练习.html').read_text(encoding='utf-8')
m = re.search(r'\bconst roots\s*=\s*', s); roots, _ = json.JSONDecoder().raw_decode(s[m.end():])
groups, order = {}, []
for r in roots:
    g = (r['组'], r['键'])
    if g not in groups: groups[g] = []; order.append(g)
    groups[g].append((r['根'], r.get('例字', '')))
data = {k: [] for k in 'abcdefghijklmnopqrstuvwxyz'}
for g in order:
    names = [n for n, _ in groups[g]]
    first = g[0].split('／')[0].strip()
    head = first if first in names else names[0]
    others = [n for n in names if n != head]
    data[g[1]].append((head + ('(笔画)' if head in STROKES else ''), '、'.join(others), g[0], dict(groups[g]).get(head, '')))
sections = []
for letters in ('qwertyuiop', 'asdfghjkl', 'zxcvbnm'):
    cards = []
    for key in letters:
        items = []
        for root, alias, family, ex in data[key]:
            cls = 'root-item stroke-root' if '(笔画)' in root else 'root-item'
            items.append(f'<div class="{cls}" title="{escape(family + (" · 例字 " + ex if ex else ""), quote=True)}"><dt>{escape(root.replace("(笔画)", ""))}</dt><dd>{escape(alias)}</dd></div>')
        search = key + ' ' + ' '.join(f'{r} {a} {f} {e}' for r, a, f, e in data[key])
        cards.append(f'<article class="root-key" data-search="{escape(search, quote=True)}"><div class="key-head"><h2>{key.upper()}</h2><span>{len(data[key])} 组</span></div><dl>{"".join(items)}</dl></article>')
    sections.append('<div class="root-row">' + ''.join(cards) + '</div>')
merged = []
for key in 'abcdefghijklmnopqrstuvwxyz':
    entries = [f'<span><b>{escape(r.replace("(笔画)", ""))}</b>：{escape(a)}</span>' for r, a, f, e in data[key] if a]
    merged.append(f'<div class="merge-row"><b class="merge-letter">{key}</b><div>{"； ".join(entries) or "无附属根"}</div></div>')
t = (SRC / 'roots.html').read_text(encoding='utf-8')
t = rep(t, '<title>字根表 · 夜莺2.0</title>', f'<title>字根表 · 夜莺{V}</title>')
t = rep(t, '<span class="eyebrow">夜莺 2.0 / 字根表</span>', f'<span class="eyebrow">夜莺 {V} / 字根表</span>')
t = rep(t, '<p>夜莺2.0 · 字根表</p>', f'<p>夜莺{V} · 字根表</p>')
assert sum(len(r) for r in groups.values()) == n_forms
t = t.replace('<!-- ROOT_BOARD -->', ''.join(sections)).replace('<!-- MERGE_LIST -->', ''.join(merged)).replace('{{ROOT_COUNT}}', str(n_groups)).replace('{{FORM_COUNT}}', str(n_forms))
(OUT / 'tools/roots.html').write_text(t, encoding='utf-8')

# ---- 更新日志 ----
md = markdown.Markdown(extensions=['toc', 'tables'], extension_configs={'toc': {'baselevel': 2}})
parts = []                                                  # 各版本更新日志，新版本在前；每版一级标题降为二级
for f in C.CHANGELOGS:
    lines = f.read_text(encoding='utf-8').split('\n')
    lines[0] = '# ' + lines[0].lstrip('# ').replace(' 更新日志', '')
    parts.append('\n'.join(l for l in lines if not l.startswith('（草稿')))
body = md.convert('\n\n'.join(parts))
t = (OUT / 'author.html').read_text(encoding='utf-8')
t = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="夜莺各版本更新日志，最新为 {V}。">', t)
t = re.sub(r'<title>[^<]*</title>', f'<title>更新日志 · 夜莺{V}</title>', t)
t = re.sub(r'<header class="article-heading">.*?</header>', f'<header class="article-heading"><p class="eyebrow">夜莺</p><h1>更新日志</h1>'
           f'<p>最新：{V}（{DATE}）</p></header>', t, flags=re.S)
t = re.sub(r'(<nav aria-label="文章目录">).*?(</nav>)', lambda m_: m_.group(1) + md.toc + m_.group(2), t, flags=re.S)
t = re.sub(r'(<article class="article-body" id="article">).*?(<p class="article-return">)', lambda m_: m_.group(1) + body + m_.group(2), t, flags=re.S)
t = t.replace('<a href="index.html#author">作者的话</a>', '<a href="index.html#updates">更新日志</a>').replace('href="index.html#author">← 返回首页', 'href="index.html#updates">← 返回首页')
t = t.replace('</head>', '<style>.article-body table{border-collapse:collapse;margin:1em 0}.article-body th,.article-body td{border:1px solid var(--line,#ccc);padding:6px 12px;text-align:center}</style></head>', 1)
(OUT / 'changelog.html').write_text(t, encoding='utf-8')
shutil.rmtree(tmp)
print(OUT, '；字根组', n_groups, '根形', n_forms, '；前1500选重', r15['选重'], '前6000加权', r60['选重加权%'], '；冲突', cf['全部单字全码'], '→', cf['剔除有简码的字'])
