"""Build Windows payloads from a hash-pinned, already released common payload.

Version and stamp are the only inputs: the Mac packages and their SHA-256 digests are read from the
GitHub release v<version> itself, and the V5 runtime directory name is read from the Mac package, so
nothing here needs editing for a new release.

Never writes installed input method data. Native Windows verification is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import os
import re
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, path, digest):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    if sha(path.read_bytes()) != digest:
        raise ValueError('SHA256 mismatch: ' + str(path))
    return path


def github_release(repo, tag):
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/tags/{tag}',
                                 headers={'Accept': 'application/vnd.github+json'})
    if os.environ.get('GH_TOKEN'):
        req.add_header('Authorization', 'Bearer ' + os.environ['GH_TOKEN'])
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def release_sources(repo, version):
    """The Mac packages attached to release v<version>, with GitHub's own SHA-256 digests."""
    assets = github_release(repo, f'v{version}')['assets']
    pattern = re.compile(rf'Nightingale-Rime-{re.escape(version)}-mac-(v5|shape|single)-\d{{8}}\.zip')
    sources = [dict(name=a['name'], size=a['size'], sha256=a['digest'].removeprefix('sha256:'), url=a['browser_download_url'])
               for a in assets if pattern.fullmatch(a['name'])]
    flavors = sorted(pattern.fullmatch(s['name']).group(1) for s in sources)
    assert flavors == ['shape', 'single', 'v5'], ('expected one Mac package per flavour on the release', flavors)
    return sorted(sources, key=lambda s: ['v5', 'shape', 'single'].index(pattern.fullmatch(s['name']).group(1)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default='losWater/Nightingale')
    p.add_argument('--upstream-repo', default='fcxxxz/rime-mohu')
    p.add_argument('--upstream-tag', default='latest', help='魔虎发布页标签；Windows 运行库取自当时该标签下的 flypy 包')
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--stamp', required=True, help='YYYYMMDD, used in file names and zip timestamps')
    args = p.parse_args()
    assert re.fullmatch(r'20\d{6}', args.stamp), args.stamp
    zip_time = (int(args.stamp[:4]), int(args.stamp[4:6]), int(args.stamp[6:]), 0, 0, 0)
    args.output.mkdir(parents=True, exist_ok=True)
    # 魔虎运行库直接取上游发布页当前的 flypy 包，用 GitHub 给出的 SHA-256 核对，并把来源写进 manifest
    up = github_release(args.upstream_repo, args.upstream_tag)
    upstream = next(a for a in up['assets'] if re.fullmatch(r'rime-mohu-flypy-[\w.-]+\.zip', a['name']) and 'mobile' not in a['name'])
    fetch(upstream['browser_download_url'], args.upstream, upstream['digest'].removeprefix('sha256:'))
    with zipfile.ZipFile(args.upstream) as z:
        runtime = {n.removeprefix('mohu/'): z.read(n) for n in z.namelist()
                   if n.startswith('mohu/runtime/') and n.endswith(('.dll', 'runtime-manifest.json', 'runtime-preload.txt'))}
    assert {Path(n).name for n in runtime} == {'libtigerengine.dll', 'lua54.dll', 'onnxruntime.dll',
                                             'libwinpthread-1.dll', 'runtime-manifest.json', 'runtime-preload.txt'}
    for name, data in runtime.items():
        if name.endswith('.dll'):
            pe = struct.unpack_from('<I', data, 0x3c)[0]
            assert data[:2] == b'MZ' and data[pe:pe + 4] == b'PE\0\0'
            assert struct.unpack_from('<H', data, pe + 4)[0] == 0x8664, name
    results = []
    for source in release_sources(args.repo, args.version):
        flavor = next(f for f in ('v5', 'shape', 'single') if f'-mac-{f}-' in source['name'])
        path = fetch(source.pop('url'), args.source_dir / source['name'], source['sha256'])
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            old = json.loads(z.read('manifest.json'))
            for name, digest in old['files'].items():
                assert sha(z.read(name)) == digest, name
            files = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
        schema = old['schema']
        # V5 运行库目录名取自 Mac 包本身（2.5 是 yeying25_v5/，3.0 起是 yeying_v5/），不写死
        homes = {n.split('/runtime/')[0] for n in files if '/runtime/' in n}
        assert flavor != 'v5' or len(homes) == 1, homes
        home = homes.pop() if homes else ''
        for name in list(files):
            if (name.endswith('.dylib') or name.startswith('squirrel.')
                    or name in ('manifest.json', 'v5-manifest.json', 'README.md', 'FEATURES.md', 'V5-README.md')):
                del files[name]
        if flavor == 'v5':
            files.update({home + '/' + n: data for n, data in runtime.items()})
        title = {'v5': 'V5 版（强烈推荐）', 'shape': '形码版', 'single': '形码单字版'}[flavor]
        files['weasel.custom.yaml.example'] = b'patch:\n  "style/horizontal": true\n'
        files['README.md'] = (f'# 夜莺 {args.version} · Windows {title}\n\n'
            '**只建议使用 V5 版本。V5 模型：强烈推荐。**\n\n'
            '平台：Windows x64，小狼毫 0.17.4 官方版。V5 原生库不支持 32 位或原生 ARM64 宿主。'
            '其他小狼毫版本的 Lua ABI 可能不同，不保证兼容。Mac 用户请下载独立 Mac 包。\n\n'
            '## 安装与升级\n\n'
            '1. 安装官方小狼毫 0.17.4：https://github.com/rime/weasel/releases/tag/0.17.4 。\n'
            '2. 从小狼毫菜单打开“用户文件夹”，先完整备份。退出小狼毫算法服务后再更新文件。\n'
            '3. 将包内 YAML 文件和 lua/ 合并复制到用户文件夹' + (f'；V5 还须复制整个 {home}/。' if home else '。') +
            '不要多套一层文件夹，不要将文件放进小狼毫程序目录，不替换程序的 rime.dll。\n'
            '4. 不覆盖自己的词库、钉选数据' + (f'、{home}/config/ 学习记录。' if home else '。') +
            f'参考 default.custom.yaml.example，把 `{schema}` 加入现有 patch/schema_list；'
            '首次安装且没有 default.custom.yaml 时，可复制示例并去掉 .example。\n'
            '5. 横排候选参考 weasel.custom.yaml.example，合并到已有 weasel.custom.yaml；不要整份覆盖自定义设置。\n'
            '6. 启动小狼毫并执行“重新部署”，Ctrl+` 切换到夜莺方案。更新 V5 DLL 后必须重启算法服务，'
            '仅重新部署不足以替换已加载的 DLL。\n\n'
            '## 功能与来源\n\n'
            'V5：固定码序＋本地整句模型；形码：四码、五码顶屏；形码单字：单字与夜莺快符、手动确认。'
            '保留对应 Mac 发布包的字词表、反查和 Lua 行为，只更换平台运行库、候选配置示例与安装说明。'
            '内部名称里的 mac 不表示 Windows 运行依赖 Mac。\n\n'
            '魔虎原作者 **fcxxxz**：https://github.com/fcxxxz/rime-mohu 。'
            'V5 模型、原生引擎及相关 Lua 为魔虎原作，不是夜莺原创。'
            '原作者声明、模型说明和 GPL v3 全文保留在 attribution/ 与 LICENSE-mohu。'
            '夜莺提供码表、词图与适配，源码在 https://github.com/losWater/Nightingale 。\n\n'
            '发布验证采用 Windows x64 的官方小狼毫引擎隔离部署及真实按键测试；'
            '不等于已人工遍历所有应用的图形界面。不要关闭系统安全防护；遇到拦截请核对官方来源和校验值。\n'
        ).encode('utf-8')
        manifest = dict(version=args.version, stamp=args.stamp, platform='windows-x64', schema=schema,
                        source_package=source, upstream_digest=upstream['digest'],
                        upstream=dict(repo=args.upstream_repo, tag=args.upstream_tag, name=upstream['name'],
                                      published_at=up.get('published_at')),
                        files={n: sha(b) for n, b in sorted(files.items())})
        files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
        name = f'Nightingale-Rime-{args.version}-windows-{flavor}-{args.stamp}.zip'
        target = args.output / name
        if target.exists():
            raise FileExistsError(target)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for n, b in sorted(files.items()):
                info = zipfile.ZipInfo(n, zip_time)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, b)
        with zipfile.ZipFile(target) as z:
            assert z.testzip() is None
            assert all(sha(z.read(n)) == digest for n, digest in manifest['files'].items())
            assert not any(n.endswith('.dylib') or n.startswith('squirrel.') for n in z.namelist())
        results.append(dict(name=name, label=f'夜莺 {title} · Windows x64 小狼毫',
                            sha256=sha(target.read_bytes()), size=target.stat().st_size))
        print('Packaged ' + name, flush=True)
    (args.output / 'assets.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / f'SHA256SUMS-windows-{args.stamp}.txt').write_text(
        ''.join(r['sha256'] + '  ' + r['name'] + '\n' for r in results), encoding='utf-8')


if __name__ == '__main__':
    main()
