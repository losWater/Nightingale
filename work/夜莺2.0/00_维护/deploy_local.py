# -*- coding: utf-8 -*-
"""更新本机：小狼毫用户目录 D:/rime_data + 虎娘。只拷内容有变的文件，然后重新部署。
  ① 夜莺主力（127/Rime_夜莺主力，全是 yeying 名字的文件，不会覆盖别人的东西）+ 模型；方案列表里没有 yeying_flypy 就加到最前。
  ② 旧的 2.0 主力/轻量/形码（106/Rime_主力版 的 yeying20_* 文件），与 ① 互不冲突，继续保留。
引擎 dll 有变化时要先停算法服务才能替换，所以有变化就先停、拷完再起。"""
import io, sys, os, glob, shutil, hashlib, subprocess, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = 'D:/rime_data'; WEASEL = 'D:/Rime/weasel-0.17.4'
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); todo = []
PKG = W + '/127_魔虎基座试验/Rime_夜莺主力'
for root, _, fs in os.walk(PKG):
    for fn in fs:
        src = os.path.join(root, fn); rel = os.path.relpath(src, PKG).replace('\\', '/'); dst = D + '/' + rel
        if rel in ('default.custom.yaml', '生成清单.json'): continue
        if not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst) or h(src) != h(dst): todo.append((src, dst, '[主力] ' + rel))
model = W + '/127_魔虎基座试验/upstream/model/mohu-sentence-ngram-v5.bin'; mdst = D + '/yeying/model/mohu-sentence-ngram-v5.bin'
if not os.path.exists(mdst) or os.path.getsize(mdst) != os.path.getsize(model): todo.append((model, mdst, '[主力] 模型'))
S = W + '/106_全平台导出/Rime_主力版'
for f in glob.glob(S + '/yeying20_*.yaml') + glob.glob(S + '/lua/yeying20_*.lua') + glob.glob(S + '/mohu/data/yeying20*.txt'):
    rel = os.path.relpath(f, S).replace('\\', '/'); dst = D + '/' + rel
    if not os.path.exists(dst) or h(f) != h(dst): todo.append((f, dst, rel))
stop = any(d.lower().endswith('.dll') for _, d, _ in todo)
if stop: subprocess.run([WEASEL + '/WeaselServer.exe', '/q'], capture_output=True); time.sleep(2)
for src, dst, _ in todo: os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
c = D + '/default.custom.yaml'; s = open(c, encoding='utf-8').read()
if 'schema: yeying_flypy' not in s:
    shutil.copy2(c, c + '.bak-夜莺主力前'); s = s.replace('  schema_list:\n', '  schema_list:\n    - schema: yeying_flypy      # 夜莺主力\n', 1); open(c, 'w', encoding='utf-8').write(s); todo.append((c, c, 'default.custom.yaml 加入 yeying_flypy'))
print('rime changed:', ', '.join(t[2] for t in todo[:12]) + (' …共 %d 个' % len(todo) if len(todo) > 12 else '') or '无')
if stop:   # 完全脱钩启动：不继承本进程的输出管道，否则调用方的管道会一直等到算法服务退出（2026-09-17 export.py 因此卡住过）
    subprocess.Popen([WEASEL + '/WeaselServer.exe'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, creationflags=0x00000008 | 0x00000200); time.sleep(3)
subprocess.run(['cmd', '/c', 'start', '', '/wait', 'WeaselDeployer.exe', '/deploy'], cwd=WEASEL)
logs = sorted(glob.glob(os.environ['TEMP'] + '/rime.weasel/*.log'), key=os.path.getmtime)
last = [l for l in open(logs[-1], encoding='utf-8', errors='replace') if 'finished updating schemas' in l]; print(last[-1].strip()[-60:] if last else '未找到部署结果')
root = os.environ['LOCALAPPDATA'] + '/Tigirl'; dst = root + '/码表/夜莺2.0'
for f in glob.glob(W + '/123_虎娘导入/夜莺2.0/*'): shutil.copy2(f, dst)
imps = sorted(glob.glob('C:/Program Files/Tigirl/versions/*/x64/Tigirl.Import.exe'), key=os.path.getmtime)
p = subprocess.run([imps[-1], '--update', dst.replace('/', '\\'), (root + '/拼音反查码表').replace('/', '\\'), root.replace('/', '\\'), '夜莺2.0', 'zh-CN'], capture_output=True)
print('tigirl update exit: %d' % p.returncode)
