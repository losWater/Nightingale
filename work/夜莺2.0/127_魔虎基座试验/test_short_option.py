# -*- coding: utf-8 -*-
"""验证"简词进整句"选项：在独立目录 E:/ymt 里套用启用方法里的 patch，重新部署，比较开关前后同一批输入的首选；测完还原。"""
import io, sys, os, re, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
T = 'E:/ymt'; H = os.path.dirname(os.path.abspath(__file__)); C = T + '/yeying_flypy.custom.yaml'
cases = ['uqlwobuvidc', 'jxlwomfquiifj', 'dddajx', 'nihc', 'wwts', 'woxihrni']
def run():
    p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', T, 'yeying_flypy', 'maintenance'], input=('\n'.join(cases) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900)
    assert p.returncode == 0, p.stderr[-600:]; return {l.split('\t')[0]: l.rstrip('\n').split('\t')[3:6] for l in p.stdout.decode('utf-8').splitlines()}
off = run()
txt = open(H + '/Rime_夜莺主力/简词进整句_启用方法.txt', encoding='utf-8').read(); open(C, 'w', encoding='utf-8').write(txt[txt.index('patch:'):])
try: on = run()
finally: os.remove(C)
for c in cases: print('%-16s 关: %s\n%-16s 开: %s' % (c, ' / '.join(off[c]), '', ' / '.join(on[c])))
run(); print('已还原为默认（关）')
