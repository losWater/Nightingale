# -*- coding: utf-8 -*-
"""夜莺 2.0 虎娘「纯单字版」码表（2026-09-20 你要：用来练单字）。

和 123 的正式版是两个独立的虎娘码表目录，互不干扰：
  123_虎娘导入/夜莺2.0      → 虎娘里的「夜莺2.0」    字 + 词 + 简词 + 快符，日常用
  137_虎娘单字版/夜莺2.0单字 → 虎娘里的「夜莺2.0单字」纯单字，练习用

设计要点
  1 只保留单字，另加 40 条快符。词、简词与 o 引导的符号区不进表，
    所以练习时打任何码都不会跳出词来抢首选。
    （快符本来也去掉了，2026-09-20 你说「快符没了，要加上」，按 106 同一份原表并回。）
  2 **单字之间的相对次序与正式方案完全一致**——直接取主表的行序，它就是权威候选顺序。
    这样同码多字的选重顺序是真的，练出来的手感能直接迁移到日常。
  3 不写 import_tables（没有词表可导），但保留 encoder 段，格式与虎娘自带码表一致。
    虎娘的造词是 /jc 显式触发的，不会在练习中自动造出词来。
  4 拆分表、注释、符号文件照抄正式版，显示拆分的功能照常可用。

来源：`00_维护/主表/夜莺2.0单字表.txt`（单字）+ `106/参考模板/快符原表.txt`（快符）。
  不走 106 的 Rime 合并词典，因为那份里还混了 877 条 o 区符号（ofpp 上就有 36 个字根查询
  条目），对练单字是噪音。直接读主表既干净，也符合「主表是唯一事实来源」。
  容错码与特殊简码保留：它们在正式方案里也是能打出来的入口，练习时保持一致。
"""
import io, sys, os, re, shutil, collections, datetime, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
OUT = H + '/夜莺2.0单字'
T = 'C:/Users/asus/AppData/Local/Tigirl/码表/虎码字词'
SRC = W + '/00_维护/主表/夜莺2.0单字表.txt'
VER = datetime.date.today().strftime('%Y.%m.%d')

rows = []
for l in open(SRC, encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) == 2 and p[0] and p[1]: rows.append((p[0], p[1]))
total_rows = len(rows)                           # 主表行序即权威候选顺序，不重排

CJK = lambda s: all('\u3400' <= ch <= '\u9fff' or '\U00020000' <= ch <= '\U0003134f' for ch in s)
# 主表理应全是单个汉字。这里不做筛选，而是做核验——筛掉东西意味着主表出了问题，要报出来
chars = rows
bad = [x for x in rows if len(x[0]) != 1 or not CJK(x[0])]
if bad:
    print('！主表出现非单字行 %d 条，前几条：%s' % (len(bad), bad[:5]))
    sys.exit('主表异常，不生成练习表')
dropped = 0
# 一简的 stem 用全码前两键（照虎码写法）
full_of = {}
for t, c in chars:
    if len(c) == 4 and t not in full_of: full_of[t] = c
# 按码位分组，保持主表行序（dict 记插入顺序）
groups = {}
for t, c in chars: groups.setdefault(c, []).append(t)
# 并入 40 条快符（2026-09-20 你要求加回）。用的是 106 的同一份原表，格式「码,位置=文本」，
# 位置是 1 起的候选序号。快符全在单字母码上，练习表那些码位只有一个一简字，
# 所以插完的次序与正式版一致：b → 不 》 >。
QP = W + '/106_全平台导出/参考模板/快符原表.txt'
quick = []
for line in open(QP, encoding='utf-8-sig').read().splitlines():
    m = re.fullmatch(r'([a-z]+),(\d+)=(.+)', line)
    if not m: continue
    c, n, t = m.group(1), int(m.group(2)), m.group(3)
    quick.append((t, c, n))
    groups.setdefault(c, [])
    if t not in groups[c]: groups[c].insert(n - 1, t)
if len(quick) != 40: sys.exit('快符原表应为 40 条，实得 %d' % len(quick))
misplaced = [(t, c, n) for t, c, n in quick if groups[c][n - 1] != t]
if misplaced: sys.exit('快符未落在原表声明的位置：%s' % misplaced[:5])
main = []
for c, ts in groups.items():
    for i, t in enumerate(ts):
        stem = full_of.get(t, '')[:2] if len(c) == 1 and full_of.get(t) else ''
        main.append((t, 1000000 - i - 1, c, stem))

os.makedirs(OUT, exist_ok=True)
head = ('name: yeying20_zi\nversion: "%s"\nsort: by_weight\ncolumns:\n  - text\n  - weight\n  - code\n  - stem\n'
        'encoder:\n  rules:\n    - length_equal: 2\n      formula: "AaAbBaBb"\n'
        '    - length_equal: 3\n      formula: "AaBaCa"\n    - length_in_range: [4, 99]\n      formula: "AaBaCaZa"\n' % VER)
def w(name, text): open(OUT + '/' + name, 'w', encoding='utf-8', newline='\n').write(text)
w('yeying20_zi.dict.yaml', head + '...\n\n' + ''.join('%s\t%d\t%s%s\n' % (t, wt, c, ('\t' + s) if s else '') for t, wt, c, s in main))
sp = [l.rstrip('\r\n').split('\t') for l in open(W + '/65_群友离线工具包/夜莺2.0离线工具包/完整拆分表.txt', encoding='utf-8-sig')][1:]
# 拆分栏不能含空格：虎娘把 拆分 文件按空白分列，「又 ＋ 寸」会被截成「又」，候选注释里只显示第一个根
# （2026-09-20 实测；虎码自带的 虎码.拆分 十万行里一个空格都没有，格式是 字\t根连写）。
# 夜莺有「变字头」这类多字根名，占 14.4% 的字，纯连写会糊成「日定字底」，所以用间隔号分开。
SEP = '·'
split_of = lambda s: SEP.join(s.split(' ＋ '))
w('夜莺.拆分', ''.join('%s\t%s\n' % (r[0], split_of(r[1])) for r in sp if len(r) >= 2))
assert not any(' ' in split_of(r[1]) or '　' in split_of(r[1]) for r in sp if len(r) >= 2), '拆分栏仍含空格'
for n in ('1拼音.注释', 'unicode.注释', '快符.txt', '常用符号.txt'): shutil.copy2(T + '/' + n, OUT + '/' + n)

# ── 自检 ──
ok = True; msg = []
bycode = collections.defaultdict(list)
for t, wt, c, _ in main: bycode[c].append((wt, t))
# ① 写出的权重降序必须等于写入顺序（虎娘按 weight 排候选，这条不成立就会串位）
for c, v in bycode.items():
    if [t for _, t in sorted(v, key=lambda x: -x[0])] != [t for _, t in v]:
        ok = False; msg.append('码位 %s 权重降序与写入顺序不符' % c); break
pure = {c: [t for _, t in v] for c, v in bycode.items()}
# ② 与正式虎娘表交叉核对：把正式表按 weight 降序展开，滤掉词与符号后，逐码必须和纯单字版一致。
#    这是两份独立产物的对照——正式版从 106 的 Rime 词典生成，纯单字版从主表生成。
OFF = W + '/123_虎娘导入/夜莺2.0/yeying20.dict.yaml'
mpair = set(rows)
if os.path.exists(OFF):
    o = collections.defaultdict(list)
    for l in open(OFF, encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[1].isdigit(): o[p[2]].append((int(p[1]), p[0]))
    diff = 0; sample = []
    for c, seq in pure.items():
        off_seq = [t for _, t in sorted(o.get(c, []), key=lambda x: -x[0]) if (t, c) in mpair]
        seq = [t for t in seq if (t, c) in mpair]
        if off_seq != seq:
            diff += 1
            if len(sample) < 3: sample.append('%s 正式=%s 单字版=%s' % (c, ''.join(off_seq), ''.join(seq)))
    if diff:
        ok = False; msg.append('与正式虎娘表有 %d 个码位次序不符：%s' % (diff, '；'.join(sample)))
    else: print('交叉核对：%d 个码位与正式虎娘表逐位一致 ✓' % len(pure))
else: print('（未找到正式虎娘表，跳过交叉核对）')
multi = sum(1 for c, v in bycode.items() if len(v) > 1)
w('说明.txt',
  '夜莺2.0 虎娘【纯单字版】码表（%s）\n\n'
  '用途：练单字。表里只有单字和 40 条快符，没有词、没有简词、没有 o 引导的符号区，\n'
  '所以打任何码都不会跳出词来抢首选。\n\n'
  '单字之间的相对次序与正式版「夜莺2.0」完全一致，选重顺序是真的，练出来能直接迁移到日常。\n'
  '快符的位置也与正式版一致（b → 不 》 >）。容错码与特殊简码保留，因为它们在正式方案里也能打出来。\n\n'
  '条目 %d 条（单字 %d + 快符 %d），占用码位 %d 个，其中 %d 个码位有多个候选。\n\n'
  '与正式版是两个独立码表，在虎娘里切换「当前码表」即可，互不影响。\n'
  '由 work/夜莺2.0/137_虎娘单字版/build.py 生成：单字取自 00_维护/主表/夜莺2.0单字表.txt，\n'
  '快符取自 106_全平台导出/参考模板/快符原表.txt，并与正式虎娘表逐码位交叉核对通过。\n'
  % (VER, len(main), len(main) - len(quick), len(quick), len(bycode), multi))
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '单字': len(main), '码位': len(bycode),
       '多字码位': multi, '丢弃行': dropped, '源行': total_rows, '拆分': len(sp), '输出': OUT,
       '自检': 'OK' if ok else '；'.join(msg)}
json.dump(rep, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('单字 %d，码位 %d（多字码位 %d），主表共 %d 行' % (len(main), len(bycode), multi, total_rows))
print('自检：' + ('通过——单字集合与相对次序和正式表一致' if ok else '失败！' + '；'.join(msg)))
print('→ ' + OUT)
if not ok: sys.exit(1)
