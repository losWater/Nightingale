# -*- coding: utf-8 -*-
"""把官网 2.0 源文件同步到仓库 D:/nightingale/apps/website/（site/ 下的页面、脚本、说明 + 重算的 performance-data.json），
并删掉 1.0 遗留、不再随站发布的文件。然后由仓库内 apps/website/build.py 构建到 .tmp/website-preview。"""
import json, io, sys, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(H) + '/00_维护'); from 版本 import VER, TAG, RELEASE_DIR; RDATE = json.load(open(RELEASE_DIR + '/发布清单.json', encoding='utf-8'))['date']; S = H + '/site'; D = 'D:/nightingale/apps/website'
copied = []
for n in os.listdir(S):
    if n.endswith(('.html', '.py', '.md', '.js', '.css')):
        _t = open(S + '/' + n, encoding='utf-8').read()
        open(D + '/' + n, 'w', encoding='utf-8', newline='').write(_t.replace('{{VER}}', VER).replace('{{TAG}}', TAG).replace('{{DATE}}', RDATE))
    else: shutil.copy2(S + '/' + n, D + '/' + n)
    copied.append(n)
shutil.copy2(H + '/performance-data.json', D + '/performance-data.json'); copied.append('performance-data.json')
removed = []
for n in ('word-conflict-data.json', 'word-conflict-method.md', 'performance-source.png'):
    p = D + '/' + n
    if os.path.exists(p): os.remove(p); removed.append(n)
print('同步 %d 个文件：%s；删除 %s' % (len(copied), '、'.join(sorted(copied)), '、'.join(removed) or '无'))
