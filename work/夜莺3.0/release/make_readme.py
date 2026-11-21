"""夜莺仓库首页 README（GitHub 上看到的）：版本、下载、安装说明按发布页 v<版本> 的实际附件生成，与官网同步。
魔虎原作者声明、学习与查询两节原样保留（从现有 README 里取）。
用法：.venv/bin/python release/make_readme.py [README 路径]   # 默认 ~/Nightingale/README.md；release/publish.py --publish 最后一步会调用
"""
import json, re, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'release'))
from config import C

REPO = 'losWater/Nightingale'
SITE = 'https://loswater.github.io/Nightingale/'
path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'Nightingale/README.md'
old = path.read_text(encoding='utf-8')
with urllib.request.urlopen(f'https://api.github.com/repos/{REPO}/releases/tags/v{C.V}', timeout=60) as r:
    rel = json.load(r)
assets = {a['name']: a['browser_download_url'] for a in rel['assets']}
date = rel['published_at'][:10]


def keep(title):
    """取现有 README 中“## 标题”整节（到下一个 ## 为止）。"""
    m = re.search(rf'^## {re.escape(title)}\n.*?(?=^## |\Z)', old, flags=re.S | re.M)
    assert m, f'README 里没有“{title}”一节'
    return m.group(0).rstrip('\n')


def find(pat):
    return next((n for n in assets if re.fullmatch(pat, n)), None)


FLAVOR = [('v5', '**V5 版（强烈推荐）**', '本地整句模型，保留夜莺固定码序'),
          ('shape', '形码版', '无模型，最大四码、五码顶屏'),
          ('single', '形码单字版', '单字与夜莺快符，手动确认上屏')]
V = re.escape(C.V)


def platform(plat, title, note):
    rows = [f'| {label} | [下载]({assets[n]})：{desc} |' for k, label, desc in FLAVOR
            if (n := find(rf'Nightingale-Rime-{V}-{plat}-{k}-\d{{8}}\.zip'))]
    if not rows:
        return f'### {title}\n\n即将提供，完成后会出现在[发布页](https://github.com/{REPO}/releases/tag/v{C.V})。\n'
    sums = find(rf'SHA256SUMS-{plat}-\d{{8}}\.txt')
    extra = f'\n[校验值]({assets[sums]})' + (f' · [引擎验证报告]({assets["windows-verification.json"]})' if plat == 'windows' and 'windows-verification.json' in assets else '') if sums else ''
    return f'### {title}\n\n{note}\n\n| 版本 | 下载与用途 |\n|---|---|\n' + '\n'.join(rows) + '\n' + extra + '\n'


others = []
if (n := find(rf'Nightingale-{V}-tables-\d{{8}}\.zip')): others.append(f'- [手心 · 搜狗 · 冰凌 · Bime 等平台码表]({assets[n]})')
if (n := find(rf'Nightingale-Toolbox-{V}-\d{{8}}\.html')): others.append(f'- [啾啾工具箱 · 单文件]({assets[n]})：拆分查询、部件反查、字根练习、字根表、字根图、完整拆分表，离线可用')
upgrade = re.sub(r'<a href="([^"]+)">([^<]+)</a>', lambda m: f'[{m.group(2)}]({SITE}{m.group(1)})', C.UPGRADE)
text = f'''# 夜莺码

夜莺是一套基于小鹤双拼的音形输入方案：双拼音码＋首末字根，常用字可用简码。

当前正式版本为 **{C.V}**（{date}）。[官网]({SITE}) · [发布页与全部附件](https://github.com/{REPO}/releases/tag/v{C.V}) · [更新日志]({SITE}changelog.html)

## Rime 下载

**只建议使用 V5 版本。V5 模型：强烈推荐。** 形码和形码单字版仅供需要固定码表输入或单字练习的用户选择。Windows 和 Mac 各有三个独立包，请按操作系统下载，不能混装。

{platform('windows', 'Windows · 小狼毫', '面向 **Windows x64 + 官方小狼毫 0.17.4**，已在官方引擎上实际部署并按键验证。V5 不支持 32 位或原生 ARM64 宿主。')}
{platform('mac', 'Mac · 鼠须管', 'V5 原生引擎仅适用于 **Apple Silicon**；Mac 包不能用于 Windows 或手机。')}
**安装**：把整个包解压到 Rime 用户文件夹（同名文件覆盖），点“重新部署”，用 Ctrl+` 切换到夜莺方案。包里的 default.custom.yaml 已列好夜莺的三个方案，装几个包、先后顺序都不影响；它会替换原有的 default.custom.yaml，如果还用着别的方案，部署后把它们加回方案列表。安装前建议备份用户文件夹；V5 更换原生库后须重启小狼毫算法服务或鼠须管。

{upgrade}

### 其他输入法与工具

{chr(10).join(others)}

{keep('魔虎原作者与声明')}

{keep('学习与查询')}

## 维护

3.x 的码表、拆分与发布工具在 [work/yeying30-nb46](https://github.com/{REPO}/tree/work/yeying30-nb46/work/夜莺3.0) 分支的 work/夜莺3.0 目录维护；发布流程见其中的 release/发布流程.md。[维护架构](MAINTENANCE.md) 与 [夜莺2.5](夜莺2.5/README.md) 目录保留供追溯。
'''
path.write_text(re.sub(r'\n{3,}', '\n\n', text), encoding='utf-8')
print(path, '已更新为', C.V)
