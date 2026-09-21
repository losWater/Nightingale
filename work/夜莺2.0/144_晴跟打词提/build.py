# -*- coding: utf-8 -*-
"""给「晴跟打 Pro」（TypeSunnyPro）生成夜莺的词提文件，两份（2026-09-22）：
  含次选：词库里有的都列，候选在第几位写第几位。
  仅首选：多字词只列能在首选打出的，不在首选的词不列，跟打器会拆成单字；单字和符号照常全列。
格式照它自带的 小鹤/虎码 词提：每行「字词<TAB>打法」，一个字词一行，写最快的打法：
    纯字母   首选且码长为 4，打满自动上屏（按用户四码定长的打法，四码首选不加空格）
    _        首选但码没打满，按空格上屏
    数字 N   第 N 个候选，按数字键选
来源：发布目录的综合表（字词表 + 符号 + 快符，码位内顺序即候选顺序）。
每个字词在它所有的码里挑按键最少的；按键数 = 字母数 +（四码首选 0，否则 1）。同样少时取码短的。
输出到本目录，并复制一份到晴跟打的 UserResources/词提/。
"""
import io, sys, os, shutil, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
sys.path.insert(0, W + '/00_维护'); from 版本 import VER, RELEASE_DIR
SRC = RELEASE_DIR + '/01_正式码表/夜莺%s综合表.txt' % VER
DST_APP = 'D:/TypeSunnyPro-20260623.1820-windows/UserResources/词提'
slot = collections.defaultdict(list)
for l in open(SRC, encoding='utf-8-sig'):
    f = l.rstrip('\r\n').split('\t')
    if len(f) >= 2 and f[0] and f[1]: slot[f[1]].append(f[0])
def ways(first_only_words):
    """每个字词挑按键最少的打法；first_only_words=True 时，多字词只从首选打法里挑，没有首选打法的词不列（跟打器会拆成单字）。"""
    best = {}
    for c, ts in slot.items():
        if len(c) > 4: continue                     # 晴跟打词提限定最多四码；只能靠长码打的词就不列，拆成单字
        for i, t in enumerate(ts, 1):
            if i > 9: continue                       # 数字键只到 9
            is_word = len(t) > 1 and all(0x3400 <= ord(ch) <= 0x9fff or ord(ch) > 0xffff for ch in t)
            if first_only_words and is_word and i != 1: continue
            way = c if (i == 1 and len(c) == 4) else c + ('_' if i == 1 else str(i))
            key = (len(c) + (0 if way == c else 1), len(c), c)
            if t not in best or key < best[t][0]: best[t] = (key, way)
    return best
order = [t for c in slot for t in slot[c]]
old_file = DST_APP + '/夜莺%s.txt' % VER                 # 上一版只有一份，换成下面两份
if os.path.exists(old_file): os.remove(old_file)
for tag, fo in (('含次选', False), ('仅首选', True)):
    best = ways(fo); seen = set(); out = []
    for t in order:
        if t in seen or t not in best or chr(9) in t or chr(10) in t: continue
        seen.add(t); out.append(t + chr(9) + best[t][1])
    name = '夜莺%s_%s.txt' % (VER, tag)
    open(H + '/' + name, 'w', encoding='utf-8-sig', newline=chr(13) + chr(10)).write(chr(10).join(out) + chr(10))
    tail = collections.Counter(('数字' if w[-1].isdigit() else '_' if w[-1] == '_' else '纯字母') for _, w in best.values())
    print('%s：%d 条（%s）' % (name, len(out), '，'.join('%s %d' % kv for kv in tail.most_common())))
    print('   ' + '  '.join('%s %s' % (t, best[t][1] if t in best else '（不列）') for t in ('哪里', '那里', '想起了', '伸', '什', '机器', '几起', '！')))
    if os.path.isdir(DST_APP): shutil.copy2(H + '/' + name, DST_APP + '/' + name)
print('已放到 %s' % DST_APP)
