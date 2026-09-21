# -*- coding: utf-8 -*-
"""由 对比.py 的结果写 夜莺2.5更新日志（md + txt），放到 117_发布v2.0/ 供发布目录收录（2026-09-22）。"""
import io, sys, os, pickle, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
sys.path.insert(0, W + '/00_维护'); from 版本 import VER
R = pickle.load(open(H + '/对比结果.pkl', 'rb'))
WHY = {  # 错码修复的原因：按部件分（拆分订正后首根或末根变了）
    '農': '曲', '鄷': '曲', '庸': '庸', '慵': '庸', '镛': '庸', '墉': '庸', '鳙': '庸', '嘃': '庸', '嫞': '庸',
    '槦': '庸', '牅': '庸', '欫': '卸左', '脌': '年', '蓘': '衮', '剶': '彖', '劙': '彖', '椼': '衍', '葕': '衍',
    '餰': '衍', '珬': '戌'}
PART = {'曲': '囗＋横＋丨＋丨', '庸': '广＋肀＋用', '卸左': '卸左', '年': '𠂉＋横＋竖＋横＋竖', '衮': '衣＋八＋厶',
        '彖': '互中间＋豕', '衍': '行＋氵', '戌': '戊＋横'}
def cols(items, n=6, sep='　'):
    out = []
    for i in range(0, len(items), n): out.append(sep.join(items[i:i + n]))
    return out
L = []   # (级别, 文本)；级别 h1/h2/h3/p/li/code
def h(level, s): L.append(('h%d' % level, s))
def p(s): L.append(('p', s))
def li(s): L.append(('li', s))
def block(lines): L.append(('code', lines))
h(1, '夜莺 %s 更新日志' % VER)
p('对照基线：2026 年 9 月 17 日的夜莺 2.0 综合表（%d 条）→ 夜莺 %s 综合表（%d 条）。' % (R['old'], VER, R['new']))
p('条目 = 文字 + 编码。「字」为单字，「词」为码长四码及以上的多字词，「简词」为码长不足四码的多字词。')
p('Rime 方案名与个人词库不变，直接覆盖安装即可。Bime 码表文件夹改名为「夜莺%s」，需在 Bime 里重新选择一次。' % VER)
# 一
h(2, '一、错码修复（%d 字）' % len(R['fix']))
p('拆分订正后，这些字的首根或末根变了，全码随之更正。三简只看首根，均不受影响。')
by = collections.defaultdict(list)
for t, a, b in R['fix']: by[WHY.get(t, '其他')].append('%s %s→%s' % (t, a, b))
for part in ('曲', '庸', '卸左', '年', '衮', '彖', '衍', '戌', '其他'):
    if part not in by: continue
    h(3, '「%s」部件统一拆作 %s' % (part, PART.get(part, '')) if part in PART else '其他')
    block(cols(by[part], 4))
p('**常用字提醒**：庸、慵、镛、墉、鳙 的全码有变（如 庸 yscr → yscz），三简 ysc 等照旧。')
# 二
F = R['freq']
h(2, '二、调整频（%d 处）' % (sum(len(v) for v in F.values()) + len(R['jm'])))
for k in ('字', '词', '简词'):
    if k not in F and not (k == '字' and R['jm']): continue
    n = len(F.get(k, [])) + (len(R['jm']) if k == '字' else 0)
    h(3, '%s（%d）' % (k, n))
    if k == '字' and R['jm']:
        p('简码换人：')
        block(['%-4s %s → %s' % (c, '、'.join(a), '、'.join(b)) for c, a, b in R['jm']])
        p('让出简码的字都退回全码：什 ufkc、噢 保留二简 oo、哎 aitp。')
        p('码位内顺序：')
    block(['%-5s %s　→　%s' % (c, '、'.join(o), '、'.join(n)) for c, o, n in sorted(F.get(k, []))])
# 三
A = R['add']
h(2, '三、新增（%d 条）' % sum(len(v) for v in A.values() if v))
for k in ('字', '词', '简词'):
    v = A.get(k, [])
    h(3, '%s（%d）' % (k, len(v)))
    if not v: p('无。'); continue
    if k == '简词':
        p('二字简词：两字双拼首码。每个二码位最多保留 3 个候选（空格、分号、引号可选）。')
        g = collections.OrderedDict()
        for t, c in v: g.setdefault(c, []).append(t)
        block(['%-4s %s' % (c, '、'.join(ts)) for c, ts in g.items()])
    else:
        block(cols(['%s %s' % (c, t) for t, c in v], 5))
p('巨构 在原有 jvgz 之外新增 jugz，两码都能打。')
# 四
D = R['dele']
h(2, '四、删除（%d 条）' % sum(len(v) for k, v in D.items() if k != '符号'))
for k in ('字', '词', '简词'):
    v = D.get(k, [])
    h(3, '%s（%d）' % (k, len(v)))
    if not v: p('无。'); continue
    if k == '简词':
        p('二码位超过 3 个候选的，第 4 个起删去二码入口（这些词都另有四码全码，照样能打出）；另删 yo 上的「有时」「一时」。')
        g = collections.OrderedDict()
        for t, c in v: g.setdefault(c, []).append(t)
        block(['%-4s %s' % (c, '、'.join(ts)) for c, ts in g.items()])
    else:
        block(cols(['%s %s' % (c, t) for t, c in v], 5))
# 五
h(2, '五、其它调整')
S = D.get('符号', [])
h(3, 'o 引导符号区（删 %d 条）' % len(S))
p('删去逗号、句号、冒号、分号、引号，以及快符里已有的符号；假名区不变。')
block(cols(['%s %s' % (c, t) for t, c in S], 8))
h(3, '拆分显示')
li('含「曲」的字、「庸」族，以及彖、衍、戌、卸左、年、衮 等部件，拆分统一按既定规则；多数字只改拆分显示，编码不变。')
li('拆分提示（虎娘、Rime、工具箱）显示完整拆分，根之间用间隔号分开，如 对 → 又·寸。')
h(3, '其他')
li('虎娘新增「夜莺%s单字」纯单字练习码表（单字 + 快符，候选顺序与正式版一致）。' % VER.split('.')[0] if False else '虎娘新增「夜莺2.0单字」纯单字练习码表（单字 + 快符，候选顺序与正式版一致）。')
li('发布文件名带版本号：码表、挂接包、离线工具包均为「夜莺%s…」。' % VER)
# 输出
md = []; txt = []
for kd, s in L:
    if kd != 'li' and md and md[-1].startswith('- '): md.append(''); txt.append('')
    if kd == 'h1': md += ['# ' + s, '']; txt += [s, '=' * 40, '']
    elif kd == 'h2': md += ['## ' + s, '']; txt += [s, '-' * 40]
    elif kd == 'h3': md += ['### ' + s, '']; txt += ['【%s】' % s]
    elif kd == 'p': md += [s, '']; txt += [s.replace('**', ''), '']
    elif kd == 'li': md += ['- ' + s]; txt += ['・' + s]
    elif kd == 'code': md += ['```'] + s + ['```', '']; txt += ['  ' + x for x in s] + ['']
md.append(''); txt.append('')
OUT = W + '/117_发布v2.0'
open(OUT + '/夜莺%s更新日志.md' % VER, 'w', encoding='utf-8', newline='\n').write('\n'.join(md))
open(OUT + '/夜莺%s更新日志.txt' % VER, 'w', encoding='utf-8-sig', newline='\r\n').write('\n'.join(txt))
print('写出 夜莺%s更新日志.md / .txt，%d 行' % (VER, len(md)))
