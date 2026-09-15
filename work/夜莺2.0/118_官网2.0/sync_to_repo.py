# -*- coding: utf-8 -*-
"""把官网 2.0 源文件同步到仓库 D:/nightingale/apps/website/（site/ 下的页面、脚本、说明 + 重算的 performance-data.json），
并删掉 1.0 遗留、不再随站发布的文件。然后由仓库内 apps/website/build.py 构建到 .tmp/website-preview。"""
import io, sys, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); S = H + '/site'; D = 'D:/nightingale/apps/website'
copied = []
for n in os.listdir(S):
    shutil.copy2(S + '/' + n, D + '/' + n); copied.append(n)
shutil.copy2(H + '/performance-data.json', D + '/performance-data.json'); copied.append('performance-data.json')
removed = []
for n in ('word-conflict-data.json', 'word-conflict-method.md', 'performance-source.png'):
    p = D + '/' + n
    if os.path.exists(p): os.remove(p); removed.append(n)
print('同步 %d 个文件：%s；删除 %s' % (len(copied), '、'.join(sorted(copied)), '、'.join(removed) or '无'))
