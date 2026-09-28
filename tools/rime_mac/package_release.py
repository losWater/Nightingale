"""Package clean build outputs for publication; never reads live Rime data or uploads."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from paths import ROOT, CODE, VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stamp', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'\d{8}', args.stamp):
        raise ValueError('stamp must be YYYYMMDD')
    out = ROOT/'publication'/args.stamp
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ROOT/'upstream/rime-mohu-flypy-latest.zip') as upstream:
        attribution = {'LICENSE-mohu': upstream.read('LICENSE'),
                       'attribution/MOHU-README.md': upstream.read('README.md'),
                       'attribution/MOHU-MODEL-README.md': upstream.read('mohu/model/README.md')}
    release = json.loads((ROOT/'upstream/mohu-release.json').read_text())
    attribution['attribution/MOHU-RELEASE.md'] = release['body'].encode()
    attribution['attribution/NOTICE.md'] = (
        '# 来源与原作者声明\n\n魔虎原作者：fcxxxz。V5 模型、原生引擎及相关 Lua 来自 '
        'https://github.com/fcxxxz/rime-mohu ，不是夜莺原创。\n'
        '上游发行采用 GPL v3；文件另有声明的遵照原声明，全文见 LICENSE-mohu。\n'
        '上游发布记录的构建提交为 f868b4a；对应源码：'
        'https://github.com/fcxxxz/rime-mohu/tree/f868b4a 。\n'
        '原始 README、模型说明和发布声明原样保留于本目录。\n'
        '夜莺修改包括夜莺码表/词图、私有命名空间、界面文案、候选混排和 Mac 适配，'
        '不将原模型或引擎算法宣称为夜莺原创。适配源码：'
        'https://github.com/losWater/Nightingale/tree/main/tools/rime_mac 。\n'
        '形码、形码单字包不包含魔虎模型或原生引擎。\n').encode()
    results = []
    for flavor, folder, schema, title in [
        ('v5', 'release-dual', 'yeying25_v5', 'V5 版（强烈推荐）'),
        ('shape', 'release-shape', 'yeying25_shape', '形码版'),
        ('single', 'release-single', 'yeying25_single', '形码单字版')]:
        files = {}
        for path in sorted((ROOT/folder).rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT/folder).as_posix()
            if rel in ('manifest.json', 'README.md', 'SINGLE-README.md', 'default.custom.yaml.example'):
                continue
            if flavor == 'v5' and ('yeying25_single' in rel or 'yeying25_shape' in rel):
                continue
            if any(x in rel for x in ('.userdb', 'snapshot', '/config/', '.log', '.DS_Store')):
                raise ValueError('Refuse personal/generated runtime data: '+rel)
            files[rel] = path.read_bytes()
        files.update(attribution)
        files['default.custom.yaml.example'] = ('patch:\n  schema_list:\n    - schema: '+schema+'\n').encode()
        original = (ROOT/folder/'README.md').read_text()
        files['FEATURES.md'] = original.encode()
        files['README.md'] = (f'# 夜莺 {VERSION} · {title}\n\n'
            '**只建议使用 V5 版本。V5 模型：强烈推荐。**\n\n'
            '本次发行针对 macOS 鼠须管。V5 引擎限 Apple Silicon；Windows、Intel Mac、手机未验证，不是通用安装包。\n\n'
            '## 安装与升级\n\n先通过鼠须管菜单打开用户文件夹，备份整个目录。'
            '将本包 YAML、lua/ 及（V5 包的）yeying25_v5/ 合并复制进去。'
            '不要删除或替换自己的用户词库、钉选数据和 yeying25_v5/config 学习数据。\n'
            f'参考 default.custom.yaml.example，将 `{schema}` 加入已有 patch/schema_list；'
            '已有其他输入方案的不要整份覆盖 default.custom.yaml。'
            'squirrel.custom.yaml.example 是横排候选补丁，同样只合并需要的设置。\n'
            '执行“重新部署”，然后切换到本包方案。V5 更新原生库后须完全退出并重启鼠须管。'
            '若系统隔离阻止动态库加载，先确认下载来自夜莺官方 Release，'
            '仅针对用户目录中本包的 yeying25_v5/runtime 解除隔离，不关闭全局系统保护。\n\n'
            '功能详情见 FEATURES.md；V5 的来源、模型说明另见 V5-README.md。'
            '各包只默认启用自己的一个方案。\n\n'
            '## 原作者与声明\n\n魔虎原作者 **fcxxxz**：https://github.com/fcxxxz/rime-mohu 。'
            'V5 模型、原生引擎及相关 Lua 为魔虎原作，不是夜莺原创。'
            '夜莺提供码表、词图与适配；上游声明和许可证完整保存在 attribution/ 与 LICENSE-mohu。\n').encode()
        manifest = {'version': VERSION, 'stamp': args.stamp, 'schema': schema,
                    'source': json.loads((ROOT.parent/'生成清单.json').read_text()),
                    'files': {n: hashlib.sha256(b).hexdigest() for n,b in files.items()}}
        files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode()
        name = f'Nightingale-Rime-{VERSION}-mac-{flavor}-{args.stamp}.zip'
        target = out/name
        if target.exists():
            raise FileExistsError(target)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for n,b in sorted(files.items()):
                archive.writestr(n,b)
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
            assert archive.read('LICENSE-mohu') == attribution['LICENSE-mohu']
            for n,digest in manifest['files'].items():
                assert hashlib.sha256(archive.read(n)).hexdigest() == digest
        results.append({'name': name, 'label': f'夜莺 {title} · macOS'+(' Apple Silicon' if flavor=='v5' else ''),
                        'size': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    (out/'assets.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    (out/f'SHA256SUMS-mac-{args.stamp}.txt').write_text(''.join(f'{r["sha256"]}  {r["name"]}\n' for r in results))
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
