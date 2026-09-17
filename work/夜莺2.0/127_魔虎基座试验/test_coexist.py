# -*- coding: utf-8 -*-
"""共存验证：把魔虎原版整包和夜莺主力装进同一个独立目录 E:/ymt_both，先查两包有没有同名文件，再分别用两个方案实跑。"""
import io, sys, os, shutil, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); A = H + '/upstream/pkg'; B = H + '/Rime_夜莺主力'; T = 'E:/ymt_both'; M = H + '/upstream/model/mohu-sentence-ngram-v5.bin'
ls = lambda r: {os.path.relpath(os.path.join(d, f), r).replace('\\', '/') for d, _, fs in os.walk(r) for f in fs}
same = sorted((ls(A) & ls(B)) - {'生成清单.json'}); print('两包同名文件：', same or '无')
if os.path.isdir(T): shutil.rmtree(T)          # 本脚本自己的测试目录
shutil.copytree(A, T);
for d, _, fs in os.walk(B):
    o = os.path.join(T, os.path.relpath(d, B)); os.makedirs(o, exist_ok=True)
    for f in fs:
        if f not in ('生成清单.json', 'default.custom.yaml'): shutil.copy2(os.path.join(d, f), os.path.join(o, f))
os.link(M, T + '/mohu/model/mohu-sentence-ngram-v5.bin'); os.link(M, T + '/yeying/model/mohu-sentence-ngram-v5.bin')
open(T + '/default.custom.yaml', 'w', encoding='utf-8').write('patch:\n  schema_list:\n    - schema: mohu_flypy\n    - schema: yeying_flypy\n')
cases = ['nihc', 'wwts', 'by', 'jxl', 'woxihrni', 'jbtmtmqibucoxliuqusjbu']
for i, schema in enumerate(('mohu_flypy', 'yeying_flypy')):
    p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', T, schema] + (['maintenance'] if i == 0 else []), input=('\n'.join(cases) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3000)
    print('==', schema, '退出码', p.returncode)
    for l in p.stdout.decode('utf-8').splitlines(): f = l.split('\t'); print('  %-24s %s' % (f[0], ' / '.join(f[3:7])))
