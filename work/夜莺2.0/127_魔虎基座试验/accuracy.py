# -*- coding: utf-8 -*-
"""整句首选准确率：试验版（魔虎新引擎+TCSKNM04 模型）对 现主力版（旧引擎+TCSKNM02）。
语料：LCCC 日常对话测试集，抽 6~14 字的纯汉字句 300 句（固定随机种子）；拼音用 pypinyin 按句注音，转小鹤双拼，纯双拼连打、不加辅码。"""
import io, sys, os, re, random, subprocess, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pypinyin import lazy_pinyin
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); N = 300
FIN = {'iu': 'q', 'ei': 'w', 'e': 'e', 'uan': 'r', 'ue': 't', 've': 't', 'un': 'y', 'u': 'u', 'i': 'i', 'uo': 'o', 'o': 'o', 'ie': 'p', 'a': 'a', 'ong': 's', 'iong': 's', 'ai': 'd', 'en': 'f', 'eng': 'g',
       'ang': 'h', 'an': 'j', 'uai': 'k', 'ing': 'k', 'iang': 'l', 'uang': 'l', 'ou': 'z', 'ia': 'x', 'ua': 'x', 'ao': 'c', 'ui': 'v', 'v': 'v', 'in': 'b', 'iao': 'n', 'ian': 'm', 'er': 'r', 'vn': 'y', 'van': 'r'}
def flypy(py):
    py = py.replace('ü', 'v')
    if py in ('a', 'o', 'e'): return py * 2
    if py in ('ai', 'an', 'ao', 'ei', 'en', 'er', 'ou'): return py
    if py == 'ang': return 'ah'
    if py == 'eng': return 'eg'
    for a, b in (('zh', 'v'), ('ch', 'i'), ('sh', 'u')):
        if py.startswith(a): return b + FIN[py[2:]]
    ini, fin = py[0], py[1:]
    if ini in 'jqxy' and fin in ('u', 'ue', 'uan', 'un'): fin = {'u': 'u', 'ue': 've', 'uan': 'van', 'un': 'vn'}[fin]; return ini + {'u': 'u', 've': 't', 'van': 'r', 'vn': 'y'}[fin]
    return ini + FIN[fin]
han = re.compile(r'^[\u4e00-\u9fff]{6,14}$'); pool = []
for l in open('D:/nightingale/work/重开工程/07_赛码语料/LCCC_base_test/lccc_base_test_clean.txt', encoding='utf-8'):
    for s in re.split(r'[，。！？、,.!?\s~…]+', l.strip()):
        if han.match(s): pool.append(s)
pool = sorted(set(pool)); random.Random(20260917).shuffle(pool); S = []
for s in pool:
    try: code = ''.join(flypy(p) for p in lazy_pinyin(s))
    except KeyError: continue
    if len(code) == 2 * len(s): S.append((s, code))
    if len(S) == N: break
def run(user, schema):
    p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', user, schema], input=('\n'.join(c for _, c in S) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3000)
    assert p.returncode == 0, (user, p.returncode, p.stderr[-500:]); tail = p.stderr.decode('utf-8', 'replace').strip().splitlines()[-2:]
    return [l.split('\t') for l in p.stdout.decode('utf-8').splitlines()], tail
new, tn = run('E:/ymt', 'yeying_flypy')
subprocess.run(['subst', 'Y:', '/D'], capture_output=True); subprocess.run(['subst', 'Y:', (W + '/106_全平台导出/engine-check-final/main').replace('/', '\\')], check=True)
try: old, to = run('Y:/', 'yeying20_main')
finally: subprocess.run(['subst', 'Y:', '/D'])
def chars(a, b): return sum(x == y for x, y in zip(a, b)) if len(a) == len(b) else 0
tot = sum(len(s) for s, _ in S); rep = []; A = B = ca = cb = 0
for (s, c), n, o in zip(S, new, old):
    A += n[3] == s; B += o[3] == s; ca += chars(n[3], s); cb += chars(o[3], s)
    if (n[3] == s) != (o[3] == s): rep.append('%s  %s\n   试验版 %s\n   现主力 %s' % ('试验版胜' if n[3] == s else '现主力胜', s, n[3], o[3]))
out = ['句数 %d，总字数 %d' % (len(S), tot), '整句首选全对：试验版 %d（%.1f%%），现主力 %d（%.1f%%）' % (A, A / len(S) * 100, B, B / len(S) * 100),
       '逐字正确率：试验版 %.2f%%，现主力 %.2f%%' % (ca / tot * 100, cb / tot * 100), '试验版 ' + ' | '.join(tn), '现主力 ' + ' | '.join(to), '', '两边结果不同的句子：'] + rep
open(H + '/整句准确率对照.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n'); print('\n'.join(out[:5])); print('不同的句子 %d 条，试验版胜 %d' % (len(rep), sum(r.startswith('试验版胜') for r in rep)))
