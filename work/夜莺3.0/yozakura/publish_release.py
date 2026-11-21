"""夜桜发布页：在 losWater/Yozakura 建（或补）yozakura-v<版本> 发布页，上传 ~/Downloads/<名称>_发布附件 里还没传的附件。
标签需已推送（发布页挂在标签名上）。正文按附件生成：下载说明、与夜莺的关系、官网链接。可重复跑：已有的发布页只补附件、更新正文。
用法：.venv/bin/python yozakura/publish_release.py
"""
import json, re, sys, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'release'))
from github_api import api

B = json.load(open(ROOT / 'yozakura/品牌.json', encoding='utf-8'))
V, ID, NAME = B['版本'], B['标识'], B['名称']
REPO = 'losWater/Yozakura'; API = f'https://api.github.com/repos/{REPO}'; TAG = f'{ID}-v{V}'
SRC = Path.home() / f'Downloads/{NAME}_发布附件'
files = sorted(p for p in SRC.iterdir() if p.suffix in ('.zip', '.txt', '.html'))
assert files, f'{SRC} 里没有附件'
D = f'https://github.com/{REPO}/releases/download/{TAG}/'
flav = {'v5': ('Rime V5 版（推荐）', '魔虎 V5 本地整句模型，自然码'), 'shape': ('Rime 形码版', '无模型，四码、五码顶屏'), 'single': ('Rime 形码单字版', '单字练习')}
lines = [f'夜桜 {V}：夜莺的字根与拆分，配自然码双拼。', '', '## 下载', '']
for k in ('v5', 'shape', 'single'):
    for p in files:
        if re.fullmatch(rf'Yozakura-Rime-{re.escape(V)}-mac-{k}-\d{{8}}\.zip', p.name):
            lines.append(f'- [Mac · {flav[k][0]}]({D}{p.name})：鼠须管，{flav[k][1]}')
for p in files:
    if re.fullmatch(rf'Yozakura-{re.escape(V)}-tables-\d{{8}}\.zip', p.name): lines.append(f'- [字词表与各平台码表]({D}{p.name})')
    if re.fullmatch(rf'Yozakura-Toolbox-{re.escape(V)}-\d{{8}}\.html', p.name): lines.append(f'- [{B["工具箱名"]} · 单文件]({D}{p.name})：拆分查询、部件反查、字根练习、字根表、字根图、完整拆分表')
lines += ['', 'Windows 小狼毫包即将提供。解压后放进 Rime 用户目录、重新部署即可使用；方案名与文件名都和夜莺分开，可与夜莺并存。', '',
          '官网：https://loswater.github.io/Nightingale/yozakura/ · 设计与维护记录：'
          f'https://github.com/{REPO}/blob/main/docs/夜桜自然码.md', '',
          '魔虎原作者 [fcxxxz / rime-mohu](https://github.com/fcxxxz/rime-mohu)：V5 模型、原生引擎及相关 Lua 为魔虎原作；原作者声明和许可证保留在包内。']
LOG = ROOT / f'yozakura/更新日志/{NAME}.md'                # 本版更新日志（去掉标题、草稿行与注释）接在正文后面
if LOG.exists():
    log = [l for l in LOG.read_text(encoding='utf-8').split('\n')[1:] if not l.startswith('（草稿') and not l.startswith('<!--')]
    lines += ['', '---', '', '# 更新日志', ''] + log
body = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n'

s, rel = api('GET', f'{API}/releases/tags/{TAG}')
if s == 404:
    s, rel = api('POST', f'{API}/releases', {'tag_name': TAG, 'name': f'夜桜 {V}', 'body': body, 'draft': False, 'prerelease': False, 'make_latest': 'true'})
    assert s == 201, (s, rel)
    print('已建发布页', rel['html_url'])
elif rel['body'] != body:
    s, rel = api('PATCH', f'{API}/releases/{rel["id"]}', {'body': body}); assert s == 200, (s, rel)
local = {p.name for p in files}
for a in rel['assets']:                                  # 本地附件已换成新版（日期变了）：发布页上的旧附件撤下
    if a['name'] not in local:
        s, _ = api('DELETE', f'{API}/releases/assets/{a["id"]}'); assert s == 204, (a['name'], s)
        print('  撤下', a['name'], flush=True)
have = {a['name'] for a in rel['assets']}
for p in files:
    if p.name in have: continue
    ct = 'text/plain' if p.suffix == '.txt' else 'text/html' if p.suffix == '.html' else 'application/zip'
    s, a = api('POST', f'https://uploads.github.com/repos/{REPO}/releases/{rel["id"]}/assets?name={urllib.parse.quote(p.name)}', p.read_bytes(), ct)
    assert s == 201 and a['size'] == p.stat().st_size, (p.name, s)
    print('  上传', p.name, flush=True)
s, rel = api('GET', f'{API}/releases/tags/{TAG}')
print(rel['html_url'], '附件', len(rel['assets']), '个')
