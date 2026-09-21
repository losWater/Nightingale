# -*- coding: utf-8 -*-
"""把纯单字版装进本机虎娘，注册成独立码表「夜莺2.0单字」（2026-09-20）。

只碰自己这一个目录，不动正式版「夜莺2.0」，也不改 config.txt 的「当前码表」——
换不换由你在虎娘界面里点，脚本不替你切。
"""
import io, sys, os, glob, shutil, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
SRC = H + '/夜莺2.0单字'
NAME = '夜莺2.0单字'
root = os.environ['LOCALAPPDATA'] + '/Tigirl'
dst = root + '/码表/' + NAME
if not os.path.isdir(SRC): sys.exit('没有生成产物，先跑 build.py')
os.makedirs(dst, exist_ok=True)
n = 0
for f in glob.glob(SRC + '/*'):
    if os.path.isfile(f): shutil.copy2(f, dst); n += 1
print('拷入 %d 个文件 → %s' % (n, dst))
imps = sorted(glob.glob('C:/Program Files/Tigirl/versions/*/x64/Tigirl.Import.exe'), key=os.path.getmtime)
if not imps: sys.exit('未找到 Tigirl.Import.exe')
# --schema 建新方案，--update 更新已有；已注册过就走 update，免得覆盖掉用户词频
mode = '--update' if os.path.isdir(root + '/schemas/' + NAME) else '--schema'
print('导入方式：%s' % ('更新已有方案' if mode == '--update' else '新建方案'))
p = subprocess.run([imps[-1], mode, dst.replace('/', '\\'),
                    (root + '/拼音反查码表').replace('/', '\\'), root.replace('/', '\\'), NAME, 'zh-CN'],
                   capture_output=True)
out = (p.stdout or b'').decode('utf-8', 'replace').strip()
err = (p.stderr or b'').decode('utf-8', 'replace').strip()
print('tigirl import exit: %d' % p.returncode)
if out: print(out[-600:])
if err: print('stderr:', err[-400:])
sch = root + '/schemas/' + NAME
print('已注册方案目录：%s（%s）' % (sch, '存在' if os.path.isdir(sch) else '未生成'))
cur = [l for l in open(root + '/config.txt', encoding='utf-8-sig', errors='replace') if l.startswith('当前码表')]
print('虎娘当前码表：%s（没动它，要练习就在虎娘里切到「%s」）' % (cur[0].split('\t')[-1].strip() if cur else '?', NAME))
if p.returncode != 0: sys.exit(p.returncode)
