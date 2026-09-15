# -*- coding: utf-8 -*-
"""词序三家投票（2026-09-15 你裁定）：四码位上的词按简单鹤、魔然、虎码三家投票排序——每家把我们这组词里它排得最靠前的那个投为首选
（简单鹤=手心挂接候选位，魔然=同码文件先后，虎码=作者词频；分不出的不投）；两家以上一致就采用；逐位投：定下一位后拿掉它再投下一位；
无多数则剩余保持鲸凉鹤原序（待定，留清单）。字的位置不动，人工指定的码位不动。输入 104 最终表，输出本目录最终表四种格式，106 改从这里取。"""
import io, sys, os, re, json, collections, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
R = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/'; D = 'D:/夜莺码论文实验/data/tiger_tu_pkg/虎码秃版 小狼毫（Win）/'
jpos = {}
for l in open(R + '简单鹤V9.3.0电脑手心挂接.txt', encoding='utf-16').read().splitlines():
    m = re.fullmatch(r'([a-z]+)=(\d+),(.+)', l.strip())
    if m and len(m[3]) > 1: jpos[m[3]] = min(jpos.get(m[3], 99), int(m[2]))
mpos = {}; body = False; grp = collections.defaultdict(list)
for l in open(B + '/101_简词参考/魔然_moran_fixed_simp.dict.yaml', encoding='utf-8'):
    if l.strip() == '...': body = True; continue
    if body and l.strip() and not l.startswith('#'):
        p = l.rstrip('\n').split('\t')
        if len(p[0]) > 1: grp[p[1]].append(p[0])
for c, ws in grp.items():
    for i, w in enumerate(ws, 1): mpos[w] = min(mpos.get(w, 99), i)
tw = {}; body = False
for l in open(D + 'tigress_ci.dict.yaml', encoding='utf-8'):
    if l.strip() == '...': body = True; continue
    if body and l.strip() and not l.startswith('#'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2 and p[1].isdigit(): tw[p[0]] = max(tw.get(p[0], 0), int(p[1]))
SCORERS = [('简单鹤', lambda w: jpos.get(w)), ('魔然', lambda w: mpos.get(w)), ('虎码', lambda w: -tw[w] if w in tw else None)]
def vote(words):
    v = {}
    for name, score in SCORERS:
        sc = [(score(w), w) for w in words if score(w) is not None]
        if not sc: continue
        best = min(s for s, _ in sc); top = [w for s, w in sc if s == best]
        if len(top) == 1: v[name] = top[0]
    return v
def order(words):
    rest = list(words); out = []; log = []
    while len(rest) > 1:
        v = vote(rest); tally = collections.Counter(v.values())
        if tally and tally.most_common(1)[0][1] >= 2:
            w = tally.most_common(1)[0][0]; out.append(w); rest.remove(w); log.append({'位': len(out), '词': w, '投票': v})
        else:
            log.append({'位': len(out) + 1, '待定': list(rest), '投票': v}); break
    return out + rest, log
blocks = collections.OrderedDict()
for l in open(B + '/104_简词入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) >= 2: blocks.setdefault(p[1], []).append(p[0])
man = json.load(open(B + '/64_加入鲸凉鹤简词/码位人工指定.json', encoding='utf-8-sig'))
changed = []; pending = []; nvote = 0
for c, blk in blocks.items():
    if len(c) != 4 or c in man: continue
    slots = [i for i, w in enumerate(blk) if len(w) > 1]; words = [blk[i] for i in slots]
    if len(words) < 2: continue
    new, log = order(words); nvote += 1
    if new != words:
        for i, w in zip(slots, new): blk[i] = w
        changed.append({'码': c, '原序': words, '新序': new, '投票': log})
    if any('待定' in x for x in log): pending.append({'码': c, '新序': new, '投票': log})
order_codes = sorted(blocks)
def emit(c, w, i, f): return {'plain': w + '\t' + c, 'code1st': c + '\t' + w, 'shouxin': c + '=' + str(i) + ',' + w, 'sogou': c + ',' + str(i) + '=' + w}[f]
out = {}
for name, fmt, enc in (('夜莺2.0最终表_普通格式.txt', 'plain', 'utf-8-sig'), ('夜莺2.0最终表_码前格式.txt', 'code1st', 'utf-8-sig'), ('夜莺2.0最终表_手心格式.txt', 'shouxin', 'utf-8-sig'), ('夜莺2.0最终表_搜狗.txt', 'sogou', 'utf-16')):
    lines = [emit(c, w, i + 1, fmt) for c in order_codes for i, w in enumerate(blocks[c])]
    data = ('\r\n'.join(lines) + '\r\n').encode(enc); open(H + '/' + name, 'wb').write(data); out[name] = {'行数': len(lines), 'sha256': hashlib.sha256(data).hexdigest()}
# 自检：与 104 比，每个码位字位置相同、词集合相同；人工指定码位逐条相同
b104 = collections.OrderedDict()
for l in open(B + '/104_简词入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t'); b104.setdefault(p[1], []).append(p[0])
for c in b104:
    a, b = b104[c], blocks[c]
    assert [i for i, w in enumerate(a) if len(w) == 1] == [i for i, w in enumerate(b) if len(w) == 1] and all(x == y for x, y in zip(a, b) if len(x) == 1), c
    assert sorted(a) == sorted(b), c
    if c in man or len(c) != 4: assert a == b, c
firsts = sum(1 for x in changed if x['原序'][0] != x['新序'][0])
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '输入': '104/夜莺2.0最终表_普通格式.txt', '投票码位': nvote, '次序有变的码位': len(changed), '首选有变的码位': firsts, '待定码位': len(pending), '输出': out, '变化明细': changed, '待定明细': pending}
json.dump(rep, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('投票码位 %d；次序有变 %d（首选有变 %d）；待定 %d；自检通过' % (nvote, len(changed), firsts, len(pending)))
