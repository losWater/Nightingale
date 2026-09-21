# -*- coding: utf-8 -*-
"""把夜莺 2.0 最终表做成虎娘（Tigirl）码表目录（2026-09-16 你提议）。
虎娘码表格式（照 码表/虎码字词）：主表 X.dict.yaml（text/weight/code[/stem]，encoder 规则，import_tables）、X_ci.dict.yaml（四码及以上词）、
X_simp_ci.dict.yaml（简词）、*.拆分（字\\t拆分）、*.注释（候选注释）、快符.txt、常用符号.txt。同码候选按 weight 降序，
所以 weight = 1000000 − 该码位内的次序，保证与夜莺最终表顺序一致；一简字给 stem = 全码前两键（照虎码的写法）。"""
import io, sys, os, shutil, collections, datetime, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); OUT = H + '/夜莺2.0'
T = 'C:/Users/asus/AppData/Local/Tigirl/码表/虎码字词'
VER = datetime.date.today().strftime('%Y.%m.%d')
# 来源改为 106 的 Rime 固定词典：它已按最终表顺序合并了 40 条快符（如 a→啊/！、no→挪/の、xing→彳亍），同码按 weight 降序
rows = []
for l in open(W + '/106_全平台导出/Rime_主力版/yeying20_rime_fixed.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) == 3 and p[1] and p[2].isdigit(): rows.append((p[0], p[1], int(p[2])))
rows.sort(key=lambda r: (r[1], -r[2]))   # 同码按原权重降序，保持最终表次序
rows = [(t, c) for t, c, _ in rows]
CJK = lambda s: all('\u3400' <= ch <= '\u9fff' or '\U00020000' <= ch <= '\U0003134f' for ch in s)
pos = collections.Counter(); main = []; ci = []; simp = []
full_of = {}
for t, c in rows:
    if len(t) == 1 and len(c) == 4 and t not in full_of: full_of[t] = c
for t, c in rows:
    pos[c] += 1; w = 1000000 - pos[c]
    if len(t) == 1 or not CJK(t):   # 单字与快符（含 ——、……、：“ 这类多字符符号）进主表
        stem = full_of.get(t, '')[:2] if len(c) == 1 and full_of.get(t) else ''
        main.append((t, w, c, stem))
    elif len(c) >= 4: ci.append((t, w, c))
    else: simp.append((t, w, c))
os.makedirs(OUT, exist_ok=True)
head = lambda name, extra: 'name: %s\nversion: "%s"\nsort: by_weight\n%scolumns:\n  - text\n  - weight\n  - code\n  - stem\nencoder:\n  rules:\n    - length_equal: 2\n      formula: "AaAbBaBb"\n    - length_equal: 3\n      formula: "AaBaCa"\n    - length_in_range: [4, 99]\n      formula: "AaBaCaZa"\n' % (name, VER, extra)
def w(name, text): open(OUT + '/' + name, 'w', encoding='utf-8', newline='\n').write(text)
w('yeying20.dict.yaml', head('yeying20', '') + 'import_tables:\n  - yeying20_ci\n  - yeying20_simp_ci\n...\n\n' + ''.join('%s\t%d\t%s%s\n' % (t, wt, c, ('\t' + s) if s else '') for t, wt, c, s in main))
w('yeying20_ci.dict.yaml', head('yeying20_ci', 'use_preset_vocabulary: false\n') + '\n...\n\n' + ''.join('%s\t%d\t%s\n' % x for x in ci))
w('yeying20_simp_ci.dict.yaml', head('yeying20_simp_ci', 'use_preset_vocabulary: false\n') + '\n...\n\n' + ''.join('%s\t%d\t%s\n' % x for x in simp))
sp = [l.rstrip('\r\n').split('\t') for l in open(W + '/65_群友离线工具包/夜莺2.0离线工具包/完整拆分表.txt', encoding='utf-8-sig')][1:]
# 拆分栏不能含空格：虎娘按空白分列，「又 ＋ 寸」只会显示「又」（2026-09-20 实测）。
# 虎码自带的 虎码.拆分 十万行无一空格。夜莺有「变字头」这类多字根名，用间隔号分开而不是纯连写。
SEP = '·'
split_of = lambda s: SEP.join(s.split(' ＋ '))
w('夜莺.拆分', ''.join('%s\t%s\n' % (r[0], split_of(r[1])) for r in sp if len(r) >= 2))
assert not any(' ' in split_of(r[1]) or '　' in split_of(r[1]) for r in sp if len(r) >= 2), '拆分栏仍含空格'
for n in ('1拼音.注释', 'unicode.注释', '快符.txt', '常用符号.txt'): shutil.copy2(T + '/' + n, OUT + '/' + n)
w('说明.txt', '夜莺2.0 虎娘码表（%s）。由 work/夜莺2.0/123_虎娘导入/build.py 从 113 最终表生成：主表单字 %d 行、词 %d 行、简词 %d 行，拆分 %d 字。\n夜莺的 40 条快符已按最终表位置并入主表（a→啊/！ 等）；快符.txt/常用符号.txt/注释沿用虎娘自带文件（分号引导的符号与 /jc 加词等功能是虎娘的）。\n' % (VER, len(main), len(ci), len(simp), len(sp)))
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '主表': len(main), '词': len(ci), '简词': len(simp), '拆分': len(sp), '输出': OUT}
json.dump(rep, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(rep)
