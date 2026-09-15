# -*- coding: utf-8 -*-
"""组装 2.0 发布目录到仓库 D:/nightingale/releases/v2.0（照 v1.0 的五个分类），并准备 GitHub Release 附件。
大包（Rime 主力版 380MB 等）放 02_输入法挂接/rime/发布包/，只作本地留存，不入 git；上传到 GitHub Release 附件。
可重复运行：全量覆盖 releases/v2.0（保留 发布包/ 内容）。"""
import io, sys, os, json, shutil, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; U = W + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'; X = W + '/106_全平台导出'
R = 'D:/nightingale/releases/v2.0'; H = os.path.dirname(os.path.abspath(__file__))
DATE = '20260916'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
plan = {   # 目标相对路径 -> 源
 '01_正式码表/夜莺2.0字词表.txt': W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt',
 '01_正式码表/夜莺2.0字词表_码前.txt': W + '/113_扩展字入表/夜莺2.0最终表_码前格式.txt',
 '01_正式码表/夜莺2.0纯单字表.txt': W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt',
 '01_正式码表/夜莺2.0扩展字表.txt': W + '/112_扩展字继承/夜莺2.0扩展字表_普通格式.txt',
 '01_正式码表/夜莺2.0无理码表.json': W + '/83_单字表重放/无理码表.json',
 '01_正式码表/夜莺2.0词无理码表.json': W + '/83_单字表重放/词无理码表.json',
 '01_正式码表/夜莺2.0码位人工指定.json': W + '/64_加入鲸凉鹤简词/码位人工指定.json',
 '03_字根与拆分/夜莺2.0字根总表.html': O + '/字根总表.html',
 '03_字根与拆分/夜莺2.0字根键位表.txt': O + '/字根键位表.txt',
 '03_字根与拆分/夜莺2.0字根图.html': O + '/字根图.html',
 '03_字根与拆分/夜莺2.0字根图.png': O + '/夜莺2.0字根图.png',
 '03_字根与拆分/夜莺2.0完整拆分表.txt': O + '/完整拆分表.txt',
 '03_字根与拆分/夜莺2.0完整拆分表.html': O + '/完整拆分表.html',
 '03_字根与拆分/夜莺2.0扩展字拆分表.txt': W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt',
 '03_字根与拆分/夜莺2.0当前完整根表.md': W + '/07_当前完整根表/夜莺2.0当前完整根表.md',
 '03_字根与拆分/夜莺2.0当前完整根表.json': W + '/07_当前完整根表/夜莺2.0当前完整根表.json',
 '04_查询与练习/夜莺啾啾工具箱.html': U + '/夜莺啾啾工具箱.html',
 '04_查询与练习/夜莺2.0离线工具包.zip': U + '/夜莺2.0离线工具包.zip',
 '05_规则与裁决/码表概念与规则.md': W + '/码表概念与规则.md',
 '05_规则与裁决/评估规则.md': W + '/评估规则.md',
 '05_规则与裁决/当前任务树.md': W + '/当前任务树.md',
 '05_规则与裁决/会话概要_2026-09-14至16.md': W + '/会话概要_2026-09-14至16.md',
}
# 02：整个字词表与输入法目录 + Rime 轻量版目录
def add_tree(prefix, src):
    for dp, dn, fn in os.walk(src):
        for f in fn:
            p = os.path.join(dp, f); plan[prefix + os.path.relpath(p, src).replace('\\', '/')] = p
add_tree('02_输入法挂接/', X + '/夜莺2.0_字词表与输入法')
add_tree('02_输入法挂接/rime/Rime_轻量版/', X + '/Rime_轻量版')
add_tree('04_查询与练习/离线工具包/', O)   # 官网工具页从这里取
plan['夜莺2.0升级日志.md'] = H + '/夜莺2.0升级日志.md'
big = {   # 大包：本地 发布包/ + GitHub Release 附件
 f'Nightingale-2.0-tables-{DATE}.zip': X + '/夜莺2.0_字词表与输入法_含快符.zip',
 f'Nightingale-Rime-2.0-light-{DATE}.zip': X + '/夜莺2.0_Rime轻量版_含快符.zip',
 f'Nightingale-Rime-2.0-main-{DATE}.zip': X + '/夜莺2.0_Rime主力版_含快符.zip',
 f'Nightingale-Toolbox-2.0-{DATE}.html': U + '/夜莺啾啾工具箱.html',
 f'Nightingale-Toolbox-offline-2.0-{DATE}.zip': U + '/夜莺2.0离线工具包.zip',
}
# 清空重建（保留 发布包/）
if os.path.isdir(R):
    for n in os.listdir(R):
        p = R + '/' + n
        if n == '02_输入法挂接':
            for m in os.listdir(p):
                q = p + '/' + m
                if m == 'rime':
                    for k in os.listdir(q):
                        if k != '发布包': (shutil.rmtree if os.path.isdir(q + '/' + k) else os.remove)(q + '/' + k)
                else: (shutil.rmtree if os.path.isdir(q) else os.remove)(q)
        else: (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
manifest = {}
for rel, src in sorted(plan.items()):
    dst = R + '/' + rel; os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
    manifest[rel] = {'source': os.path.relpath(src, 'E:/夜莺2.0').replace('\\', '/'), 'sha256': sha(dst), 'bytes': os.path.getsize(dst)}
pk = R + '/02_输入法挂接/rime/发布包'; os.makedirs(pk, exist_ok=True)
assets = {}
for name, src in big.items():
    dst = pk + '/' + name; shutil.copy2(src, dst); assets[name] = {'sha256': sha(dst), 'bytes': os.path.getsize(dst)}
open(pk + f'/SHA256SUMS-{DATE}.txt', 'w', encoding='utf-8', newline='\n').write(''.join('%s  %s\n' % (v['sha256'], k) for k, v in assets.items()))
open(R + '/02_输入法挂接/rime/README.md', 'w', encoding='utf-8').write(f"""# Rime 挂接（夜莺2.0）

- `Rime_轻量版/`：轻量版全部文件（Rime 原生整句），解压即用，详见其中 使用说明.md。
- 主力版（含 V5 整句模型与 Windows 原生引擎，约 380MB）不入 git：见 GitHub Release v2.0 附件 `Nightingale-Rime-2.0-main-{DATE}.zip`；本地留存在 `发布包/`（已 gitignore）。
- 两版共有：Ctrl+数字 钉选、二字自动造词、Ctrl+Enter 主动造词、反引号双拼/波浪号全拼反查、F2 拆分提示、40 条快符。
- 校验：`发布包/SHA256SUMS-{DATE}.txt`。
""")
open(R + '/README.md', 'w', encoding='utf-8').write(f"""# 夜莺 2.0 发布目录（{DATE}）

音形码表：双拼（小鹤）+ 夜莺字根形码，四码定长；出简让全。8105 字 + 7391 扩展字（新华字典多出的字，含繁体旧字形），
普通词按四家方案共识筛选、词序三家投票，简词二字 952 条、三字三码 17282 条。最终表 155139 条。

- `01_正式码表/`：字词表（普通/码前）、纯单字表、扩展字表、无理码表、码位人工指定。
- `02_输入法挂接/`：手心（模块化）、搜狗挂接/五笔、冰凌、Bime、普通字词表；`rime/` 轻量版目录与主力版说明（主力包见 Release 附件）。
- `03_字根与拆分/`：字根总表/键位表/字根图、完整拆分表（15496 字）、当前完整根表。
- `04_查询与练习/`：啾啾工具箱单文件（拆分查询、部件反查、字根练习、字根图/表、完整拆分表）、离线工具包 zip 与展开的离线页面（官网工具页来源）。
- `夜莺2.0升级日志.md`：相对 1.0 的变化。
- `05_规则与裁决/`：码表概念与规则、评估规则、任务树与会话概要（全部裁定的来龙去脉）。
- 工作区脚本与逐批裁定在 `work/夜莺2.0/`（单字表可由 `83_单字表重放` 重放）。

校验值见 `发布清单.json`。
""")
json.dump({'version': '2.0', 'date': DATE, 'status': 'release', 'files': manifest, 'release_assets': assets,
           'final_table_entries': 155139, 'chars': 15496, 'note': '大包不入 git，见 GitHub Release v2.0 附件与本地 02_输入法挂接/rime/发布包/'},
          open(R + '/发布清单.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '目录': R, '文件数': len(manifest), '附件': assets},
          open(H + '/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tot = sum(v['bytes'] for v in manifest.values())
print('releases/v2.0：%d 个文件 %.1f MB（入 git）；发布包附件 %d 个 %.1f MB（不入 git）' % (len(manifest), tot / 1048576, len(assets), sum(v['bytes'] for v in assets.values()) / 1048576))
for k, v in assets.items(): print('  %7.1f MB  %s' % (v['bytes'] / 1048576, k))
