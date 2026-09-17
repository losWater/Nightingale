# -*- coding: utf-8 -*-
"""一次性改 build_release.py（2026-09-17 你要求：主力版换成魔虎基座的「夜莺主力」；发布包用中文名，一眼看出功能）。
GitHub 会把中文附件文件名变成 default.zip（实测），所以：本地 发布包/ 里用中文文件名（传群文件用）；Release 上文件名保持原英文（官网下载链接不变），中文写在附件显示名里。"""
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = os.path.dirname(os.path.abspath(__file__)) + '/build_release.py'; s = open(p, encoding='utf-8').read()
def rep(old, new):
    global s; assert s.count(old) == 1, old[:50]; s = s.replace(old, new)
rep(" f'Nightingale-2.0-tables-{DATE}.zip': X + '/夜莺2.0_字词表与输入法_含快符.zip',\n f'Nightingale-Rime-2.0-light-{DATE}.zip': X + '/夜莺2.0_Rime轻量版_含快符.zip',\n f'Nightingale-Rime-2.0-main-{DATE}.zip': X + '/夜莺2.0_Rime主力版_含快符.zip',\n"
    " f'Nightingale-Rime-2.0-mobile-{DATE}.zip': X + '/夜莺2.0_Rime手机版_万象模型_含快符.zip',\n f'Nightingale-Toolbox-2.0-{DATE}.html': U + '/夜莺啾啾工具箱.html',\n f'Nightingale-Toolbox-offline-2.0-{DATE}.zip': U + '/夜莺2.0离线工具包.zip',\n}",
    " # Release 上的英文文件名: (来源, 本地中文文件名, Release 上的中文显示名)\n"
    " f'Nightingale-Rime-2.0-main-{DATE}.zip': (W + '/127_魔虎基座试验/夜莺2.0_Rime主力版.zip', '夜莺2.0_Rime主力版_整句含模型_电脑用.zip', '夜莺主力 · Rime 主力版（整句，含魔虎 V5 模型，电脑用）'),\n"
    " f'Nightingale-Rime-2.0-light-{DATE}.zip': (X + '/夜莺2.0_Rime轻量版_含快符.zip', '夜莺2.0_Rime轻量版_无模型_小体积.zip', 'Rime 轻量版（Rime 原生整句，无模型，体积小）'),\n"
    " f'Nightingale-Rime-2.0-mobile-{DATE}.zip': (X + '/夜莺2.0_Rime手机版_万象模型_含快符.zip', '夜莺2.0_Rime手机版_同文与仓_万象模型.zip', 'Rime 手机版（同文／仓输入法，万象语法模型）'),\n"
    " f'Nightingale-2.0-tables-{DATE}.zip': (X + '/夜莺2.0_字词表与输入法_含快符.zip', '夜莺2.0_码表与挂接包_手心搜狗冰凌Bime.zip', '码表与挂接包（手心、搜狗、冰凌、Bime、纯码表）'),\n"
    " f'Nightingale-Toolbox-2.0-{DATE}.html': (U + '/夜莺啾啾工具箱.html', '夜莺啾啾工具箱_拆分查询与字根练习.html', '啾啾工具箱（单个网页：拆分查询、部件反查、字根练习）'),\n"
    " f'Nightingale-Toolbox-offline-2.0-{DATE}.zip': (U + '/夜莺2.0离线工具包.zip', '夜莺2.0_离线工具包.zip', '离线工具包（工具箱各页面的离线版）'),\n}")
rep("assets = {}\nfor name, src in big.items():\n    dst = pk + '/' + name; shutil.copy2(src, dst); assets[name] = {'sha256': sha(dst), 'bytes': os.path.getsize(dst)}\n"
    "open(pk + f'/SHA256SUMS-{DATE}.txt', 'w', encoding='utf-8', newline='\\n').write(''.join('%s  %s\\n' % (v['sha256'], k) for k, v in assets.items()))\n",
    "assets = {}\n# 只清理上次由本脚本放进 发布包/ 的文件（记在 发布清单.json 的 release_assets 里，含旧的英文名文件）\n"
    "try: old_assets = json.load(open(R + '/发布清单.json', encoding='utf-8'))['release_assets']\nexcept Exception: old_assets = {}\n"
    "for k, v in old_assets.items():\n    for fn in (k, v.get('本地文件名', '')):\n        if fn and os.path.isfile(pk + '/' + fn): os.remove(pk + '/' + fn)\n"
    "for name, (src, cn, label) in big.items():\n    dst = pk + '/' + cn; shutil.copy2(src, dst); assets[name] = {'本地文件名': cn, '显示名': label, 'sha256': sha(dst), 'bytes': os.path.getsize(dst)}\n"
    "open(pk + '/校验值SHA256.txt', 'w', encoding='utf-8', newline='\\n').write(''.join('%s  %s  （Release 上叫 %s）\\n' % (v['sha256'], v['本地文件名'], k) for k, v in assets.items()))\n")
rep("- 主力版（含 V5 整句模型与 Windows 原生引擎，约 380MB）不入 git：见 GitHub Release v2.0 附件 `Nightingale-Rime-2.0-main-{DATE}.zip`；本地留存在 `发布包/`（已 gitignore）。",
    "- 主力版「夜莺主力」（夜莺码表与词库 + 魔虎 rime-mohu 的功能层、原生整句引擎与 V5 模型，GPL v3，约 480MB）不入 git：见 GitHub Release v2.0 附件 `Nightingale-Rime-2.0-main-{DATE}.zip`；本地留存在 `发布包/`（已 gitignore，中文文件名）。")
rep("- 两版共有：Ctrl+数字 钉选、二字自动造词、Ctrl+Enter 主动造词、反引号双拼/波浪号全拼反查、F2 拆分提示、40 条快符。", "- 轻量版与手机版：Ctrl+数字 钉选、二字自动造词、Ctrl+Enter 主动造词；主力版用魔虎自带的置顶与加词。三版共有：反引号双拼/波浪号全拼反查、F2、40 条快符。")
rep("- 校验：`发布包/SHA256SUMS-{DATE}.txt`。", "- 校验：`发布包/校验值SHA256.txt`。")
open(p, 'w', encoding='utf-8').write(s); print('ok')
