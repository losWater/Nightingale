"""一条命令发布夜莺新版本。发新版只需：改 release/版本.json（版本、上一版、升级说明），写好 release/更新日志/夜莺<版本>.md。

第一段（默认，只在本地生成，不公开任何东西）：
  1. 单字表（build/rebuild_table.py：引擎输入→引擎→出表）＋ 字词表/综合表（release/make_ciku.py）
  2. 各平台码表（release/export_platforms.py）→ Nightingale-<版本>-tables-<日期>.zip
  3. 啾啾工具箱（release/make_toolbox.py）→ Nightingale-Toolbox-<版本>-<日期>.html
  4. Rime Mac 三包：搭台（release/stage_rime.py）→ 夜莺构建工具出包并验证 → 打包 → 发布验证
  5. 校验值
  6. 官网本地预览（release/make_website.py）
  全部放进 ~/Downloads/夜莺<版本>_发布附件/（官网预览在其中的“官网”）。

第二段（--publish，公开发布；作者确认后才跑）：
  7. 更新日志去掉“草稿”、写上发布日期并提交；Yozakura 打标签 v<版本>，同步到夜莺仓库 3.x 分支（work/夜莺3.0），推送
  8. GitHub 建发布页 v<版本>（正文 = 下载说明 + 更新日志），上传附件
  9. 触发 Windows 工作流（版本、日期作为输入），等它验证并上传 Windows 包
  10. 按发布页实际附件重新生成官网，推到 gh-pages；逐个检查线上下载链接
用法：.venv/bin/python release/publish.py [--publish] [--skip-table]
"""
import hashlib, json, re, shutil, subprocess, sys, time, urllib.parse, urllib.request, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'release'))
from config import C
from github_api import api

PY = str(ROOT / '.venv/bin/python')
REPO = 'losWater/Nightingale'
API = f'https://api.github.com/repos/{REPO}'
NG_BRANCH_CLONE = Path.home() / '.cache/yeying-ng'          # 夜莺仓库 3.x 分支的稀疏克隆
NG_BRANCH, NG_DIR = 'work/yeying30-nb46', 'work/夜莺3.0'
PAGES = Path.home() / '.cache/ng-pages'                      # gh-pages 克隆
SYNCED = Path.home() / '.cache/yeying-local/synced_commit'   # 已同步到夜莺分支的 Yozakura 提交
OUT = Path.home() / f'Downloads/{C.NAME}_发布附件'
SITE = OUT / '官网'
run = lambda *a, **k: subprocess.run([str(x) for x in a], check=True, **k)
quiet = dict(stdout=subprocess.DEVNULL)


def step(n, text): print(f'\n== {n}. {text}', flush=True)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def changelog_ready():
    """更新日志：去掉“草稿”行，标题下补发布日期（已有日期就更新为今天）。"""
    f = C.CHANGELOG
    assert f.exists(), f'缺更新日志 {f}'
    lines = [l for l in f.read_text(encoding='utf-8').split('\n') if not l.startswith('（草稿')]
    assert lines[0].startswith('# '), '更新日志第一行应为标题'
    body = lines[1:]
    while body and not body[0].strip(): body.pop(0)
    if body and re.fullmatch(r'20\d\d-\d\d-\d\d', body[0].strip()): body.pop(0)
    while body and not body[0].strip(): body.pop(0)
    f.write_text('\n'.join([lines[0], '', C.DATE, ''] + body), encoding='utf-8')
    assert len(body) > 3, '更新日志几乎是空的'


def build(skip_table):
    OUT.mkdir(parents=True, exist_ok=True)
    step(1, '码表')
    if not skip_table:
        run(PY, ROOT / 'build/rebuild_table.py')
    run(PY, ROOT / 'release/make_ciku.py', **quiet)
    step(2, '各平台码表')
    exp = OUT / f'{C.NAME}_字词表与输入法'
    shutil.rmtree(exp, ignore_errors=True)
    run(PY, ROOT / 'release/export_platforms.py', exp, **quiet)
    tables = OUT / f'Nightingale-{C.V}-tables-{C.STAMP}.zip'
    with zipfile.ZipFile(tables, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(exp.rglob('*')):
            if p.is_file() and p.name != '.DS_Store': z.write(p, p.relative_to(OUT))
    step(3, '啾啾工具箱')
    tb = OUT / f'{C.NAME}_工具箱'
    shutil.rmtree(tb, ignore_errors=True)
    run(PY, ROOT / 'release/make_toolbox.py', tb, **quiet)
    toolbox = OUT / f'Nightingale-Toolbox-{C.V}-{C.STAMP}.html'
    shutil.copy(tb / '夜莺啾啾工具箱.html', toolbox)
    step(4, 'Rime Mac 三包（构建、验证、打包、发布验证）')
    run(PY, ROOT / 'release/stage_rime.py', **quiet)
    log = open(C.STAGE / 'build.log', 'w')
    run(sys.executable, C.STAGE / 'tools/maintenance/build_mac.py', '--root', C.STAGE, '--verify', stdout=log, stderr=subprocess.STDOUT)
    pub = C.MAC_OUT / 'publication' / C.STAMP
    if pub.exists(): shutil.rmtree(pub)                       # 同一天重跑：旧的本地打包结果作废
    run(sys.executable, C.STAGE / 'tools/rime_mac/package_release.py', '--stamp', C.STAMP, cwd=C.STAGE,
        env=dict(__import__('os').environ, NIGHTINGALE_REPO=str(C.STAGE)), **quiet)
    run(sys.executable, C.STAGE / 'tools/rime_mac/verify_release.py', pub, cwd=C.STAGE)
    for p in pub.iterdir():
        if p.name.endswith('.zip') or p.name.startswith('SHA256SUMS'): shutil.copy(p, OUT / p.name)
    step(5, '校验值')
    (OUT / f'SHA256SUMS-tables-toolbox-{C.STAMP}.txt').write_text(
        ''.join(f'{sha(p)}  {p.name}\n' for p in (tables, toolbox)), encoding='utf-8')
    step(6, '官网本地预览')
    shutil.rmtree(SITE, ignore_errors=True)
    run(PY, ROOT / 'release/make_website.py', SITE, **quiet)
    print(f'\n第一段完成：{OUT}\n  官网预览：python3 -m http.server 8765 --directory "{SITE}"')
    for p in sorted(OUT.iterdir()):
        if p.is_file(): print(f'  {p.name}  {p.stat().st_size:,}')


def assets():
    return sorted(p for p in OUT.iterdir() if p.is_file() and re.match(r'(Nightingale-|SHA256SUMS-)', p.name))


def release_body():
    """发布页正文：下载说明（按附件生成）＋ 更新日志。"""
    D = f'https://github.com/{REPO}/releases/download/v{C.V}/'
    names = [p.name for p in assets()]
    flav = {'v5': ('Rime V5 版（强烈推荐）', '魔虎 V5 本地整句模型'), 'shape': ('Rime 形码版', '无模型，四码、五码顶屏'), 'single': ('Rime 形码单字版', '单字练习与夜莺快符')}
    lines = ['**只建议使用 V5 版本。V5 模型：强烈推荐。**', '', '## 下载', '']
    for k in ('v5', 'shape', 'single'):
        for n in names:
            if re.fullmatch(rf'Nightingale-Rime-{re.escape(C.V)}-mac-{k}-\d{{8}}\.zip', n):
                lines.append(f'- [Mac · {flav[k][0]}]({D}{n})：鼠须管，{flav[k][1]}')
    for n in names:
        if re.fullmatch(rf'Nightingale-{re.escape(C.V)}-tables-\d{{8}}\.zip', n): lines.append(f'- [手心 · 搜狗 · 冰凌 · Bime 码表]({D}{n})')
        if re.fullmatch(rf'Nightingale-Toolbox-{re.escape(C.V)}-\d{{8}}\.html', n): lines.append(f'- [啾啾工具箱 · 单文件]({D}{n})：拆分查询、部件反查、字根练习、字根表、字根图、完整拆分表')
    lines += ['', 'Windows 小狼毫包由工作流验证后补发到本页。Windows 与 Mac 包不能混装；升级前请备份个人词库。', '',
              re.sub(r'<[^>]+>', '', C.UPGRADE), '', '官网：https://loswater.github.io/Nightingale/', '',
              '魔虎原作者 [fcxxxz / rime-mohu](https://github.com/fcxxxz/rime-mohu)：V5 模型、原生引擎及相关 Lua 为魔虎原作，不是夜莺原创；'
              '原作者声明和许可证保留在包内 attribution/ 与 LICENSE-mohu。', '', '---', '']
    return '\n'.join(lines) + C.CHANGELOG.read_text(encoding='utf-8').split('\n', 1)[1]


def sync_branch():
    """把 Yozakura 自上次同步以来的提交，作为一个补丁放进夜莺仓库 3.x 分支（work/夜莺3.0），推送。返回分支提交号。"""
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    base = SYNCED.read_text().strip()
    if base != head:
        diff = subprocess.run(['git', '-C', str(ROOT), 'diff', '--binary', base, head], check=True, capture_output=True).stdout
        patch = NG_BRANCH_CLONE.parent / 'yeying-sync.diff'; patch.write_bytes(diff)
        run('git', '-C', NG_BRANCH_CLONE, 'pull', '-q', '--ff-only', 'origin', NG_BRANCH)
        run('git', '-C', NG_BRANCH_CLONE, 'apply', '--index', f'--directory={NG_DIR}', patch)
        run('git', '-C', NG_BRANCH_CLONE, 'commit', '-q', '-m', f'夜莺 {C.V}：同步 Yozakura {head[:7]}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
        run('git', '-C', NG_BRANCH_CLONE, 'push', '-q', 'origin', NG_BRANCH)
        patch.unlink(); SYNCED.write_text(head + '\n')
    return subprocess.run(['git', '-C', str(NG_BRANCH_CLONE), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()


def publish():
    assert assets(), '先跑第一段（不带 --publish）'
    changelog_ready()                                       # 去掉“草稿”、写上发布日期（发布时才做）
    run('git', '-C', ROOT, 'add', C.CHANGELOG)
    if subprocess.run(['git', '-C', str(ROOT), 'diff', '--cached', '--quiet']).returncode:
        run('git', '-C', ROOT, 'commit', '-q', '-m', f'夜莺 {C.V} 更新日志定稿（{C.DATE}）\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
    step(7, f'Yozakura 标签 v{C.V}，同步夜莺分支')
    run('git', '-C', ROOT, 'tag', '-a', f'v{C.V}', '-m', f'夜莺 {C.V} 发布（{C.DATE}）')
    run('git', '-C', ROOT, 'push', '-q', 'origin', 'HEAD', f'v{C.V}')
    target = sync_branch()
    step(8, f'发布页 v{C.V}')
    s, rel = api('GET', f'{API}/releases/tags/v{C.V}')
    if s == 404:
        s, rel = api('POST', f'{API}/releases', {'tag_name': f'v{C.V}', 'target_commitish': target, 'name': f'夜莺 {C.V}',
                                                 'body': release_body(), 'draft': False, 'prerelease': False, 'make_latest': 'true'})
        assert s == 201, (s, rel)
    have = {a['name'] for a in rel['assets']}
    for p in assets():
        if p.name in have: continue
        ct = 'text/plain' if p.suffix == '.txt' else 'text/html' if p.suffix == '.html' else 'application/zip'
        s, a = api('POST', f'https://uploads.github.com/repos/{REPO}/releases/{rel["id"]}/assets?name={urllib.parse.quote(p.name)}', p.read_bytes(), ct)
        assert s == 201 and a['size'] == p.stat().st_size, (p.name, s)
        print('  上传', p.name, flush=True)
    step(9, 'Windows 包（工作流）')
    since = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - 60))
    s, _ = api('POST', f'{API}/actions/workflows/rime-windows.yml/dispatches', {'ref': 'main', 'inputs': {'version': C.V, 'stamp': C.STAMP}})
    assert s == 204, s
    run_id = None
    for _ in range(120):
        time.sleep(20)
        s, r = api('GET', f'{API}/actions/workflows/rime-windows.yml/runs?event=workflow_dispatch&created=' + urllib.parse.quote('>=' + since))
        if r.get('workflow_runs'):
            w = r['workflow_runs'][0]; run_id = w['id']
            if w['status'] == 'completed':
                assert w['conclusion'] == 'success', f'Windows 工作流失败：{w["html_url"]}'
                break
    else:
        raise TimeoutError('Windows 工作流 40 分钟内没有完成')
    print('  Windows 工作流通过', run_id)
    s, rel = api('GET', f'{API}/releases/tags/v{C.V}')   # 发布页正文：“补发”换成 Windows 下载链接
    flav = {'v5': 'Rime V5 版（强烈推荐）', 'shape': 'Rime 形码版', 'single': 'Rime 形码单字版'}
    win = [f"- [Windows · {flav[k]}]({a['browser_download_url']})" for k in ('v5', 'shape', 'single') for a in rel['assets']
           if re.fullmatch(rf'Nightingale-Rime-{re.escape(C.V)}-windows-{k}-\d{{8}}\.zip', a['name'])]
    assert len(win) == 3, ('Windows 包不全', [a['name'] for a in rel['assets']])
    old = 'Windows 小狼毫包由工作流验证后补发到本页。'
    body = rel['body'].replace(old, '\n'.join(win) + '\n\nWindows 包面向 Windows x64 + 官方小狼毫 0.17.4；V5 不适用于 32 位或原生 ARM64 宿主。')
    if body != rel['body']: api('PATCH', f'{API}/releases/{rel["id"]}', {'body': body})
    step(10, '官网上线')
    shutil.rmtree(SITE, ignore_errors=True)
    run(PY, ROOT / 'release/make_website.py', SITE, **quiet)
    run('git', '-C', PAGES, 'pull', '-q', '--ff-only', 'origin', 'gh-pages')
    run('git', '-C', PAGES, 'rm', '-rq', '.')
    shutil.copytree(SITE, PAGES, dirs_exist_ok=True)
    run('git', '-C', PAGES, 'add', '-A', '.')
    run('git', '-C', PAGES, 'commit', '-q', '-m', f'site: 夜莺 {C.V}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
    run('git', '-C', PAGES, 'push', '-q', 'origin', 'gh-pages')
    s, rel = api('GET', f'{API}/releases/tags/v{C.V}')
    bad = []
    for a in rel['assets']:
        req = urllib.request.Request(a['browser_download_url'], headers={'Range': 'bytes=0-0'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: ok = r.status in (200, 206)
        except Exception: ok = False
        if not ok: bad.append(a['name'])
    assert not bad, ('下载不了', bad)
    print(f'\n已发布 夜莺 {C.V}：{rel["html_url"]}（{len(rel["assets"])} 个附件都能下载）；官网几分钟内更新。')


if __name__ == '__main__':
    if '--publish' in sys.argv:
        publish()
    else:
        build('--skip-table' in sys.argv)
