# -*- coding: utf-8 -*-
"""把试验版装进本机小狼毫用户目录 D:/rime_data（可完全还原）。
会被覆盖的文件先原样备份到 D:/rime_data_魔虎试验前备份/（含旧模型，用移动不用复制）；新增了哪些文件记在 安装记录.json。
旧的 夜莺2.0主力 / 夜莺1.0主力 与魔虎新引擎共用同名文件（引擎、模型、三个 lua），试用期间从方案列表里暂时拿掉，还原后恢复。
用法：先退出小狼毫算法服务（脚本会自己停），python install_trial.py；还原：python install_trial.py --restore"""
import io, sys, os, json, shutil, subprocess, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); PKG = H + '/夜莺魔虎试验版'; R = 'D:/rime_data'; BK = 'D:/rime_data_魔虎试验前备份'; REC = BK + '/安装记录.json'
WEASEL = 'D:/Rime/weasel-0.17.4'
def server(stop):
    if stop: subprocess.run([WEASEL + '/WeaselServer.exe', '/q'], capture_output=True); time.sleep(2)
    else: subprocess.Popen(['cmd', '/c', 'start', '', WEASEL + '/WeaselServer.exe']); time.sleep(2); subprocess.Popen(['cmd', '/c', 'start', '', WEASEL + '/WeaselDeployer.exe', '/deploy'])
if '--restore' in sys.argv:
    rec = json.load(open(REC, encoding='utf-8')); server(True)
    for rel in rec['新增'] + rec['覆盖']:
        if os.path.isfile(R + '/' + rel): os.remove(R + '/' + rel)
    for rel in rec['覆盖']: os.makedirs(os.path.dirname(R + '/' + rel), exist_ok=True); shutil.move(BK + '/' + rel, R + '/' + rel)
    os.replace(REC, BK + '/安装记录_已还原.json'); server(False); print('已还原：删新增 %d，恢复 %d' % (len(rec['新增']), len(rec['覆盖']))); sys.exit()
assert not os.path.exists(REC), '已经装过了；要重装先 --restore'
server(True); new, over = [], []
files = [os.path.relpath(os.path.join(r, f), PKG).replace('\\', '/') for r, _, fs in os.walk(PKG) for f in fs if f != '生成清单.json'] + ['mohu/model/mohu-sentence-ngram-v5.bin']
for rel in files:
    src = H + '/upstream/model/mohu-sentence-ngram-v5.bin' if rel.endswith('.bin') else PKG + '/' + rel; dst = R + '/' + rel
    if rel == 'default.custom.yaml': continue
    if os.path.exists(dst): os.makedirs(os.path.dirname(BK + '/' + rel), exist_ok=True); shutil.move(dst, BK + '/' + rel); over.append(rel)
    else: new.append(rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
rel = 'default.custom.yaml'; os.makedirs(BK, exist_ok=True); shutil.copy2(R + '/' + rel, BK + '/' + rel); over.append(rel)
s = open(R + '/' + rel, encoding='utf-8').read()
s = s.replace('    - schema: yeying20_main\n', '    - schema: mohu_flypy        # 夜莺·魔虎 试验版\n').replace('    - schema: yeying_main\n', '')
open(R + '/' + rel, 'w', encoding='utf-8').write(s)
json.dump({'时间': time.strftime('%Y-%m-%d %H:%M:%S'), '新增': new, '覆盖': over}, open(REC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
server(False); print('已安装：新增 %d，覆盖（已备份）%d。部署完成后在方案选单里选「夜莺·魔虎」。' % (len(new), len(over)))
