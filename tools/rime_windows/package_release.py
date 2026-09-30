"""Build Windows payloads from a hash-pinned, already released common payload.

Never writes installed input method data. Native Windows verification is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-manifest', type=Path, required=True)
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--stamp', required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    release = json.loads((REPO / 'assets/rime/mohu-release.json').read_text(encoding='utf-8'))
    upstream = next(a for a in release['assets'] if a['name'] == 'rime-mohu-flypy-latest.zip')
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
    for source in json.loads(args.source_manifest.read_text(encoding='utf-8')):
        flavor = next(f for f in ('v5', 'shape', 'single') if f'-mac-{f}-' in source['name'])
        path = fetch(f'https://github.com/losWater/Nightingale/releases/download/v{args.version}/' + source['name'],
                     args.source_dir / source['name'], source['sha256'])
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            old = json.loads(z.read('manifest.json'))
            for name, digest in old['files'].items():
                assert sha(z.read(name)) == digest, name
            files = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
        schema = old['schema']
        for name in list(files):
            if (name.endswith('.dylib') or name.startswith('squirrel.')
                    or name in ('manifest.json', 'v5-manifest.json', 'README.md', 'FEATURES.md', 'V5-README.md')):
                del files[name]
        if flavor == 'v5':
            files.update({'yeying25_v5/' + n: data for n, data in runtime.items()})
        title = {'v5': 'V5 版（强烈推荐）', 'shape': '形码版', 'single': '形码单字版'}[flavor]
        files['weasel.custom.yaml.example'] = b'patch:\n  "style/horizontal": true\n'
        files['README.md'] = (f'# 夜莺 {args.version} · Windows {title}\n\n'
            '**只建议使用 V5 版本。V5 模型：强烈推荐。**\n\n'
            '平台：Windows x64，小狼毫 0.17.4 官方版。V5 原生库不支持 32 位或原生 ARM64 宿主。'
            '其他小狼毫版本的 Lua ABI 可能不同，不保证兼容。Mac 用户请下载独立 Mac 包。\n\n'
            '## 安装与升级\n\n'
            '1. 安装官方小狼毫 0.17.4：https://github.com/rime/weasel/releases/tag/0.17.4 。\n'
            '2. 从小狼毫菜单打开“用户文件夹”，先完整备份。退出小狼毫算法服务后再更新文件。\n'
            '3. 将包内 YAML 文件和 lua/ 合并复制到用户文件夹；V5 还须复制整个 yeying25_v5/。'
            '不要多套一层文件夹，不要将文件放进小狼毫程序目录，不替换程序的 rime.dll。\n'
            '4. 不覆盖自己的词库、钉选数据、yeying25_v5/config/ 学习记录。'
            f'参考 default.custom.yaml.example，把 `{schema}` 加入现有 patch/schema_list；'
            '首次安装且没有 default.custom.yaml 时，可复制示例并去掉 .example。\n'
            '5. 横排候选参考 weasel.custom.yaml.example，合并到已有 weasel.custom.yaml；不要整份覆盖自定义设置。\n'
            '6. 启动小狼毫并执行“重新部署”，Ctrl+` 切换到夜莺方案。更新 V5 DLL 后必须重启算法服务，'
            '仅重新部署不足以替换已加载的 DLL。\n\n'
            '## 功能与来源\n\n'
            'V5：固定码序＋本地整句模型；形码：四码、五码顶屏；形码单字：单字与夜莺快符、手动确认。'
            '保留对应 Mac 发布包的字词表、反查和 Lua 行为，只更换平台运行库、候选配置示例与安装说明。'
            '内部 yeying25_mac 名称是兼容标识，不表示 Windows 运行依赖 Mac。\n\n'
            '魔虎原作者 **fcxxxz**：https://github.com/fcxxxz/rime-mohu 。'
            'V5 模型、原生引擎及相关 Lua 为魔虎原作，不是夜莺原创。'
            '原作者声明、模型说明和 GPL v3 全文保留在 attribution/ 与 LICENSE-mohu。'
            '夜莺提供码表、词图与适配，源码在 https://github.com/losWater/Nightingale 。\n\n'
            '发布验证采用 Windows x64 的官方小狼毫引擎隔离部署及真实按键测试；'
            '不等于已人工遍历所有应用的图形界面。不要关闭系统安全防护；遇到拦截请核对官方来源和校验值。\n'
        ).encode('utf-8')
        manifest = dict(version=args.version, stamp=args.stamp, platform='windows-x64', schema=schema,
                        source_package=source, upstream_digest=upstream['digest'],
                        files={n: sha(b) for n, b in sorted(files.items())})
        files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
        name = f'Nightingale-Rime-{args.version}-windows-{flavor}-{args.stamp}.zip'
        target = args.output / name
        if target.exists():
            raise FileExistsError(target)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for n, b in sorted(files.items()):
                info = zipfile.ZipInfo(n, (2026, 9, 30, 0, 0, 0))
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
