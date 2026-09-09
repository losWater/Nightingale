"""Prepare a local 1.0 candidate from maintained sources; never publish."""
from pathlib import Path
import codecs
import hashlib
import json
import re
import runpy
import zipfile
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'releases/v0.9.1'
OUT = ROOT / 'releases/v1.0'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rename(text):
    return text.replace('0.9.1', '1.0')

def prepare():
    OUT.mkdir(exist_ok=True)
    website = runpy.run_path(str(ROOT / 'pipelines/v1/offline_tools.py'))
    rendered_roots = ROOT / '.tmp/release-tools/roots.html'
    rendered_roots.parent.mkdir(parents=True, exist_ok=True)
    website['build_roots'](SOURCE / '03_字根与拆分/夜莺码v0.9.1字根表.html', rendered_roots)
    provenance = {}
    skipped = []
    for source in sorted(SOURCE.rglob('*')):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE)
        name = relative.as_posix()
        skip = (name.startswith('99_') or '旧版备份' in name or '模块化挂接实验' in name
                or '冰虎' in name or source.suffix.lower() in {'.png', '.pdf', '.zip'}
                or relative.name in {'发布清单.json', 'README.md'} and len(relative.parts) == 1
                or relative.name == '夜莺码v0.9.1更新日志.txt')
        if skip:
            skipped.append(name)
            continue
        target = OUT / rename(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        # Tables and audit records retain their original bytes and historical references.
        if source.suffix == '.html' or source.name == 'README.md' or source.suffix == '.yaml' or source.suffix == '.json' and relative.parts[0] == '02_输入法挂接':
            raw = rename(raw.decode('utf-8-sig')).encode('utf-8')
        elif '冰凌词库' in source.name:
            raw = rename(raw.decode('utf-16')).encode('utf-16')
        target.write_bytes(raw)
        provenance[target.relative_to(OUT).as_posix()] = {'source': source.relative_to(ROOT).as_posix(), 'sha256': sha(source)}

    # The latest roots are standalone, with both views and embedded styles/scripts.
    path = OUT / '03_字根与拆分/夜莺码v1.0字根表.html'
    html = rendered_roots.read_text(encoding='utf-8-sig')
    for name in ('style.css', 'roots.css'):
        css = (ROOT / 'pipelines/v1/assets' / name).read_text(encoding='utf-8-sig')
        html = html.replace(f'<link rel="stylesheet" href="../{name}">', '<style>' + css + '</style>')
    for name in ('site.js', 'roots.js'):
        js = (ROOT / 'pipelines/v1/assets' / name).read_text(encoding='utf-8-sig')
        html = html.replace(f'<script src="../{name}" defer></script>', '')
        html = html.replace('</body>', '<script>' + js + '</script></body>')
    html = re.sub(r'<link rel="icon"[^>]*>', '', html)
    html = html.replace('../bird.svg', '../04_查询与练习/bird.svg')
    html = html.replace('../index.html', '../04_查询与练习/工具导航.html')
    html = html.replace('<a href="../performance.html">性能</a>', '')
    html = html.replace('href="root-practice.html"', 'href="../04_查询与练习/夜莺码v1.0字根练习器.html"')
    html = html.replace('href="split.html"', 'href="../04_查询与练习/夜莺码v1.0拆分查询.html"')
    path.write_text(html, encoding='utf-8')
    tools = OUT / '04_查询与练习'
    (tools / 'bird.svg').write_bytes((ROOT / 'pipelines/v1/assets/bird.svg').read_bytes())
    website['build_root_practice'](SOURCE / '04_查询与练习/夜莺码v0.9.1字根练习器.html', tools / '夜莺码v1.0字根练习器.html')
    practice = tools / '夜莺码v1.0字根练习器.html'
    practice.write_text(rename(practice.read_text(encoding='utf-8')), encoding='utf-8')
    links = [('字根表（两种展示）','../03_字根与拆分/夜莺码v1.0字根表.html'),('字根练习','夜莺码v1.0字根练习器.html'),('拆分查询','夜莺码v1.0拆分查询.html'),('编码反查','夜莺码v1.0编码反查.html'),('部件查字','夜莺码v1.0部件查字.html'),('必拆字练习','必拆字/夜莺码v1.0必拆字练习.html')]
    (tools / '工具导航.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>夜莺1.0 离线工具</title><style>body{max-width:800px;margin:50px auto;padding:24px;background:#101c29;color:#fafcf5;font:16px/2 sans-serif}a{color:#acd7bf;display:block;padding:14px;border-bottom:1px solid #2a3a45}</style><h1>夜莺1.0 · 离线工具</h1><p>打开即用，无需网站。</p>' + ''.join(f'<a href="{url}">{label} →</a>' for label,url in links) + '</html>',encoding='utf-8')
    draft = (ROOT / 'docs/releases/夜莺1.0升级日志_草稿.txt').read_text(encoding='utf-8')
    (OUT / '夜莺1.0升级日志.txt').write_text(draft,encoding='utf-8')
    (OUT / 'README.md').write_text('''# 夜莺1.0

基于小鹤双拼的音形方案。乱序字根，拆分直观，常用字无重，常用字词避重。

本包汇总0.9.1发布后的维护，截至实战第88条。本包为1.0正式版码表与离线资料。网站暂不发布。

## 使用

- `01_正式码表`：单字主表、字词主表、码前镜像、简词、扩展字、布局及特殊码记录。
- `02_输入法挂接`：搜狗、手心、冰凌导入文件。按对应目录README操作；手心整合版与模块版二选一，避免重复启用。
- `03_字根与拆分`：新版离线字根表、拆分表和字架说明。字根表可切换主根版/归并版并打印；五笔画用金色标示。旧版PNG/PDF未混入此包。
- `04_查询与练习/工具导航.html`：双击打开离线工具。字根练习首次默认导入174条字根，已有数据和进度继续保留。
- `05_维护与裁决`：完整维护历史；历史条目包含撤销和覆盖，请以后续裁决为准。

## 升级前

先备份个人用户词库、输入法配置和自定义短语；导入本包时停用旧夜莺表，避免同码重复。详细变化见`夜莺1.0升级日志.txt`。

本次统一包内当前文件名及工具标题为1.0。历史记录里的旧版本、源路径与校验值保留，便于追溯。网站仍为独立本地预览，未打包为已上线服务。

如需继续维护，请在仓库修改真源并重新执行`python pipelines/v1/prepare.py`；当前真源仍在维护目录，勿直接修改本发布副本。
''',encoding='utf-8')
    # Old sample-file paragraphs no longer describe the clean package.
    for folder in ('冰凌输入法','手心输入法','搜狗输入法'):
        p = OUT / '02_输入法挂接' / folder / 'README.md'
        if p.exists():
            text = p.read_text(encoding='utf-8')
            text = '\n'.join(line for line in text.splitlines() if '冰虎' not in line and '模块化挂接实验' not in line and '旧版备份' not in line)
            p.write_text(text+'\n',encoding='utf-8')
    single = OUT / '01_正式码表/夜莺码v1.0单字版.txt'
    combined = OUT / '01_正式码表/夜莺1.0字词表.txt'
    assert single.read_bytes() == (SOURCE / '01_正式码表/夜莺码v0.9.1单字版.txt').read_bytes()
    assert combined.read_bytes() == (SOURCE / '01_正式码表/夜莺0.9.1字词表.txt').read_bytes()
    rows = [line.split('\t') for line in combined.read_text(encoding='utf-8-sig').splitlines()]
    by_code = {}
    for word,code in rows: by_code.setdefault(code,[]).append(word)
    expected = {'iy':'纯','qu':'取','quw':'区','que':'曲','quea':'曲','quwy':'鸲','dky':'顶','yre':'圆','llzi':'量子','mcdk':'锚定','vja':'战','vj':'站','wj':'完','ts':'通','tsw':'同','mcxs':'茅'}
    for code,word in expected.items(): assert by_code[code][0] == word, (code,word)
    assert by_code['mcdk'][:2] == ['锚定','铆钉']
    assert len(rows) == len({tuple(row) for row in rows})
    mirror = [line.split('\t') for line in (OUT / '01_正式码表/夜莺1.0字词表_码前.txt').read_text(encoding='utf-8-sig').splitlines()]
    assert mirror == [[code,word] for word,code in rows]
    palm = OUT / '02_输入法挂接/手心输入法'
    module_dir = palm / '模块化挂接正式版'
    total = (palm / '夜莺码v1.0电脑手心挂接.txt').read_text(encoding='utf-8-sig').splitlines()
    module_rows = []
    manifest = {'source':'../夜莺码v1.0电脑手心挂接.txt','source_rows':len(total),'source_sha256':sha(palm/'夜莺码v1.0电脑手心挂接.txt'),'outputs':{}}
    for p in sorted(module_dir.glob('*.txt')):
        content = p.read_text(encoding='utf-8-sig').splitlines(); module_rows.extend(content)
        manifest['outputs'][p.name] = {'rows':len(content),'sha256':sha(p)}
    assert Counter(module_rows) == Counter(total)
    (module_dir / '模块化生成清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Validate local HTML links; external and internal anchors are deliberately excluded.
    for p in OUT.rglob('*.html'):
        for url in re.findall(r'(?:href|src)="([^"<>]+)"',p.read_text(encoding='utf-8')):
            if url.startswith(('#','http:','https:','data:','javascript:')) or '$' in url: continue
            target = (p.parent / url.split('#')[0].split('?')[0]).resolve()
            assert target.exists(), (p,url)
    (OUT / '准备检查.md').write_text('''# 1.0发布检查

- 2026-09-09本轮准备已运行仓库门禁，81项测试通过；后续修改应重新运行。
- 单字与综合主表逐字节保持维护真源内容，候选不因改版本号变化。
- 综合表无重复字词码对；码前镜像逐行对应。
- 已核对17个最终裁决码位及锚定/铆钉次序。
- 手心五模块合计与完整挂接表无损一致。
- 离线HTML本地链接存在，新版字根图与练习数据随包提供。
- 字根旧PDF/PNG、旧挂接备份、实验样例及外部参考库排除，原文件仍留在仓库。
- 性能截图属于提供的单字评测结果，未作为本次最终码表重新跑出的数据。
- 用户已确认发布1.0码表与离线资料；网站不在本次发布范围。
''',encoding='utf-8')
    hashes = {p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != '发布清单.json'}
    manifest = {'version':'1.0','status':'release','maintenance_through':88,'counts':{'single_entries':len(single.read_text(encoding='utf-8-sig').splitlines()),'combined_entries':len(rows)},'source_files':provenance,'excluded_from_package':skipped,'outputs':hashes}
    (OUT / '发布清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive = ROOT / 'releases/夜莺1.0.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,'夜莺1.0/'+p.relative_to(OUT).as_posix())
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    (archive.with_suffix('.sha256')).write_text(sha(archive)+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps({'files':len(hashes)+1,'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)},ensure_ascii=False))

if __name__ == '__main__':
    prepare()

