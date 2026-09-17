# -*- coding: utf-8 -*-
"""更新本机：小狼毫用户目录 D:/rime_data（只拷内容有变的文件，然后重新部署）+ 虎娘码表更新。
魔虎试验版装着的时候（D:/rime_data_魔虎试验前备份/安装记录.json 存在）：旧主力版与试验版同名的文件一律不拷（否则会盖掉试验版的新脚本/引擎），
并改为把 127 试验包里有变的文件同步过去；新出现的文件记进安装记录，保证 --restore 能还原干净。"""
import io, sys, os, glob, json, shutil, hashlib, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = W + '/106_全平台导出/Rime_主力版'; D = 'D:/rime_data'
REC = 'D:/rime_data_魔虎试验前备份/安装记录.json'; rec = json.load(open(REC, encoding='utf-8')) if os.path.exists(REC) else None
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); changed = []
owned = set(rec['新增'] + rec['覆盖']) if rec else set()
for f in glob.glob(S + '/yeying20_*.yaml') + glob.glob(S + '/lua/*.lua') + glob.glob(S + '/mohu/data/yeying20*.txt'):
    rel = os.path.relpath(f, S).replace('\\', '/'); dst = D + '/' + rel
    if rel in owned: continue
    if not os.path.exists(dst) or h(f) != h(dst): shutil.copy2(f, dst); changed.append(rel)
if rec:
    PKG = W + '/127_魔虎基座试验/夜莺魔虎试验版'; added = False
    for root, _, fs in os.walk(PKG):
        for fn in fs:
            rel = os.path.relpath(os.path.join(root, fn), PKG).replace('\\', '/'); dst = D + '/' + rel
            if rel in ('default.custom.yaml', '生成清单.json'): continue
            if not os.path.exists(dst):
                rec['新增'].append(rel); added = True
            elif h(os.path.join(root, fn)) == h(dst): continue
            elif rel not in owned: continue                     # 不是试验版装进去的同名文件，不碰
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(os.path.join(root, fn), dst); changed.append('[试验版] ' + rel)
    if added: json.dump(rec, open(REC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('rime changed:', ', '.join(changed) or '无')
subprocess.run(['cmd', '/c', 'start', '', '/wait', 'WeaselDeployer.exe', '/deploy'], cwd='D:/Rime/weasel-0.17.4')
logs = sorted(glob.glob(os.environ['TEMP'] + '/rime.weasel/*.log'), key=os.path.getmtime)
last = [l for l in open(logs[-1], encoding='utf-8', errors='replace') if 'finished updating schemas' in l]; print(last[-1].strip()[-60:] if last else '未找到部署结果')
root = os.environ['LOCALAPPDATA'] + '/Tigirl'; dst = root + '/码表/夜莺2.0'
for f in glob.glob(W + '/123_虎娘导入/夜莺2.0/*'): shutil.copy2(f, dst)
imps = sorted(glob.glob('C:/Program Files/Tigirl/versions/*/x64/Tigirl.Import.exe'), key=os.path.getmtime)
p = subprocess.run([imps[-1], '--update', dst.replace('/', '\\'), (root + '/拼音反查码表').replace('/', '\\'), root.replace('/', '\\'), '夜莺2.0', 'zh-CN'], capture_output=True)
print('tigirl update exit: %d' % p.returncode)
