# -*- coding: utf-8 -*-
"""查清 main_records 的口径：拿已知行数的正式版做对照（2026-09-20）。

纯单字版写入 21195 行，虎娘回报 main_records=20046，差 1149。
正式版主表已知 22883 行，用同样的 --update 走一遍，看它回报多少，
两边的差额比例一致就说明这是虎娘自己的计数口径，不是我们丢了数据。
--update 是 deploy_local.py 每次部署都做的常规操作。
"""
import io, sys, os, glob, subprocess, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root = os.environ['LOCALAPPDATA'] + '/Tigirl'
imp = sorted(glob.glob('C:/Program Files/Tigirl/versions/*/x64/Tigirl.Import.exe'), key=os.path.getmtime)[-1]

def rowcount(p):
    n = 0
    for l in open(p, encoding='utf-8'):
        q = l.rstrip('\n').split('\t')
        if len(q) >= 3 and q[1].isdigit(): n += 1
    return n

def imp_run(name, mode='--update'):
    d = os.path.join(root, '码表', name)
    p = subprocess.run([imp, mode, d, os.path.join(root, '拼音反查码表'), root, name, 'zh-CN'],
                       capture_output=True)
    return p.returncode, (p.stdout or b'').decode('utf-8', 'replace').strip(), \
           (p.stderr or b'').decode('utf-8', 'replace').strip()

for name, f in (('夜莺2.0', 'yeying20.dict.yaml'), ('夜莺2.0单字', 'yeying20_zi.dict.yaml')):
    path = os.path.join(root, '码表', name, f)
    n = rowcount(path)
    rc, out, err = imp_run(name)
    print('%-10s 主表写入 %6d 行   exit %d   %s%s' % (name, n, rc, out, ('  ERR:' + err) if err else ''))

# 分析纯单字版：按「每个字的第一行（最短码）+ 全码」这种可能的折叠口径数一数
rows = [tuple(l.rstrip('\n').split('\t')) for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8')]
per = collections.defaultdict(list)
for t, c in rows: per[t].append(c)
print('\n纯单字版行数的几种口径：')
print('  总行            %d' % len(rows))
print('  distinct 字     %d' % len(per))
print('  distinct 码位   %d' % len({c for _, c in rows}))
cnt = collections.Counter(len(v) for v in per.values())
print('  每字行数分布    %s' % dict(sorted(cnt.items())))
