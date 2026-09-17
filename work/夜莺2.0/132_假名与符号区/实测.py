# -*- coding: utf-8 -*-
"""用小狼毫引擎实打 o 区：假名、日语标点、罗马数字、圆圈数字、声调、ot/of 符号，以及确认没有污染整句与原有字词。"""
import io, sys, os, shutil, subprocess, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
PKG = W + '/106_全平台导出/Rime_轻量版'; T = 'E:/ysym'
if os.path.isdir(T): shutil.rmtree(T)      # 本脚本自己的测试目录
shutil.copytree(PKG, T)
shutil.copy2(W + '/127_魔虎基座试验/upstream/pkg/default.yaml', T + '/default.yaml')
CASES = [('ora', '平假名 あ'), ('orki', '拗音挂 き 后'), ('ortu', '促音挂 つ 后'), ('orno', 'の'), ('orp', '长音符'),
         ('oba', '片假名 ア'), ('obki', '片假名拗音'), ('obsi', 'シ'), ('obp', '片假名长音'),
         ('orb', '日语标点'), ('old', '罗马大写'), ('olx', '罗马小写'), ('oxu', '圆圈数字'),
         ('opa', 'a 四声'), ('ope', 'e 四声加 ê'), ('opv', 'ü 四声'), ('otc', '℃'), ('oti', '×÷✗'), ('ofhb', '货币组'), ('ofjt', '箭头组'),
         ('ofdw', '单位组：夜莺原有的在前'), ('o', '夜莺 o 一简仍是哦'), ('oo', '仍是噢'), ('ou', '仍是欧'), ('ox', '仍是偶像'), ('ord', '仍是偶然的'),
         ('woxihrni', '整句没被污染'), ('nihc', '你好'), ('wwts', '胃痛在前')]
p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', T, 'yeying20_light', 'maintenance'],
                   input=('\n'.join(c for c, _ in CASES) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1200)
assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-800:]
res = {l.split('\t')[0]: l.rstrip('\n').split('\t')[3:] for l in p.stdout.decode('utf-8').splitlines()}
for c, note in CASES:
    print('%-10s %-22s %s' % (c, note, '  '.join(res.get(c, [])[:9])))
