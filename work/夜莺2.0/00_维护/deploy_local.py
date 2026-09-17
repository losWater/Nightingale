# -*- coding: utf-8 -*-
"""更新本机：小狼毫用户目录 D:/rime_data（只拷内容有变的夜莺 2.0 文件，然后重新部署）+ 虎娘码表更新。"""
import io, sys, os, glob, shutil, hashlib, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = W + '/106_全平台导出/Rime_主力版'; D = 'D:/rime_data'
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); changed = []
for f in glob.glob(S + '/yeying20_*.yaml') + glob.glob(S + '/lua/*.lua') + glob.glob(S + '/mohu/data/yeying20*.txt'):
    rel = os.path.relpath(f, S); dst = os.path.join(D, rel)
    if not os.path.exists(dst) or h(f) != h(dst): shutil.copy2(f, dst); changed.append(rel)
print('rime changed:', ', '.join(changed) or '无')
subprocess.run(['cmd', '/c', 'start', '', '/wait', 'WeaselDeployer.exe', '/deploy'], cwd='D:/Rime/weasel-0.17.4')
logs = sorted(glob.glob(os.environ['TEMP'] + '/rime.weasel/*.log'), key=os.path.getmtime)
last = [l for l in open(logs[-1], encoding='utf-8', errors='replace') if 'finished updating schemas' in l]; print(last[-1].strip()[-60:] if last else '未找到部署结果')
root = os.environ['LOCALAPPDATA'] + '/Tigirl'; dst = root + '/码表/夜莺2.0'
for f in glob.glob(W + '/123_虎娘导入/夜莺2.0/*'): shutil.copy2(f, dst)
imps = sorted(glob.glob('C:/Program Files/Tigirl/versions/*/x64/Tigirl.Import.exe'), key=os.path.getmtime)
p = subprocess.run([imps[-1], '--update', dst.replace('/', '\\'), (root + '/拼音反查码表').replace('/', '\\'), root.replace('/', '\\'), '夜莺2.0', 'zh-CN'], capture_output=True)
print('tigirl update exit: %d' % p.returncode)
