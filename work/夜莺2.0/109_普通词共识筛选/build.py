# -*- coding: utf-8 -*-
"""普通词共识筛选（2026-09-15 你裁定）：普通词库 = 四家方案词库（鲸凉鹤=91、简单鹤V9.3.0、魔然、虎码秃版）里至少三家收的词。
豁免：91/非规则词登记表 与 64/码位人工指定 中的词不参与筛选。补入：≥3家但 91 没有的二字词/四字及以上词，读音取自简单鹤（或魔然）的小鹤双拼码，
套 78 单字表的码；三字词属简词层不补。补入词排在该码位末尾，来由"共识补入"。词序其余保持 91（鲸凉鹤原序）。产物替代 91 作为 97/102 的输入。"""
import io, sys, os, json, collections, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); R = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/'
T = json.load(open(B + '/108_各家词库共识/共识表.json', encoding='utf-8'))['词']; cnt = {w: v['家数'] for w, v in T.items()}; srcs = {w: v['来源'] for w, v in T.items()}
reg = json.load(open(B + '/91_普通词表/非规则词登记表.json', encoding='utf-8-sig')); regw = {(e['词'] if isinstance(e, dict) else e) for v in reg['登记'].values() for e in v}
man = json.load(open(B + '/64_加入鲸凉鹤简词/码位人工指定.json', encoding='utf-8-sig')); manw = {t for ts in man.values() for t in ts if len(t) > 1}
rows = [l.rstrip('\r\n').split('\t') for l in open(B + '/91_普通词表/夜莺2.0普通词表_普通格式.txt', encoding='utf-8-sig') if l.strip()]
ok = lambda w: cnt.get(w, 0) >= 3 or w in regw or w in manw
keep = [r for r in rows if ok(r[0])]; drop = [r for r in rows if not ok(r[0])]
jdh = {}
for l in open(R + '简单鹤V9.3.0纯词库 (1).txt', encoding='utf-8-sig').read().splitlines():
    p = l.split('\t')
    if len(p) >= 2: jdh.setdefault(p[0], p[1])
mo = {}; body = False
for l in open(B + '/101_简词参考/魔然_moran_fixed_simp.dict.yaml', encoding='utf-8'):
    if l.strip() == '...': body = True; continue
    if body and l.strip() and not l.startswith('#'): p = l.rstrip('\n').split('\t'); mo.setdefault(p[0], p[1])
full = collections.defaultdict(list)
for l in open(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    p = l.strip().split('\t')
    if len(p) >= 2 and len(p[1]) == 4: full[p[0]].append(p[1])
def encode1(w, src):
    if len(w) == 2 and len(src) == 4:
        a = [c for c in full[w[0]] if c[:2] == src[:2]]; b = [c for c in full[w[1]] if c[:2] == src[2:4]]
        return (a[0][:2] + b[0][:2], '二字 AB+CD') if a and b else (None, '读音对不上（源码 %s）' % src)
    if len(w) >= 4 and len(src) == 4:
        chars = [w[0], w[1], w[2], w[-1]]
        return (src, '四字+ 前三首码+末字首码') if all(any(c[0] == x for c in full[ch]) for ch, x in zip(chars, src)) else (None, '首码对不上（源码 %s）' % src)
    return None, '长度/码长不符'
def own(w):   # 你 2026-09-15 指出：读音以我们自己的单字表为准；每个字只有一个读音（所有全码前两位相同）就直接编，不看别人
    if len(w) == 2:
        a = {c[:2] for c in full[w[0]]}; b = {c[:2] for c in full[w[1]]}
        return (a.pop() + b.pop(), '二字 AB+CD（自家读音）') if len(a) == 1 and len(b) == 1 else (None, None)
    chars = [w[0], w[1], w[2], w[-1]]; fs = [{c[0] for c in full[ch]} for ch in chars]
    return (''.join(f.pop() for f in fs), '四字+ 前三首码+末字首码（自家首码）') if all(len(f) == 1 for f in fs) else (None, None)
def encode(w):   # 自家读音唯一 → 直接编；含多音字 → 借简单鹤（再魔然）的小鹤双拼码定读音
    if len(w) == 3: return None, '三字词属简词层，不补'
    if not all(ch in full for ch in w): return None, '无源码或含8105外字'
    c, why = own(w)
    if c: return c, why
    why = '无源码或含8105外字'
    for src in [x for x in (jdh.get(w), mo.get(w)) if x]:
        c, why = encode1(w, src)
        if c: return c, why
    return None, why
ours = {r[0] for r in rows}
added = {}; failed = {}
for w in sorted(w for w, c in cnt.items() if c >= 3 and w not in ours):
    c, why = encode(w)
    if c: added[w] = c
    else: failed[w] = why
blocks = collections.OrderedDict()
for w, c in keep: blocks.setdefault(c, []).append(w)
for w, c in added.items(): blocks.setdefault(c, []).append(w)
# 2026-09-16 词无理码表（83）里的特设入口若不在表中则补入码位末尾（如 yeby=夜莺）
for _c, _w in json.load(open(B + '/83_单字表重放/词无理码表.json', encoding='utf-8-sig'))['条目'].items():
    if _w not in blocks.get(_c, []): blocks.setdefault(_c, []).append(_w)
out = '\r\n'.join('%s\t%s' % (w, c) for c in sorted(blocks) for w in blocks[c]) + '\r\n'
open(H + '/夜莺2.0普通词表_普通格式.txt', 'wb').write(out.encode('utf-8-sig'))
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '输入': '91/夜莺2.0普通词表_普通格式.txt', '共识表': '108/共识表.json', '口径': '四家里至少三家收；登记表与人工指定豁免；三字词不补',
       '91条目': len(rows), '保留': len(keep), '豁免保留': sum(1 for w, c in keep if cnt.get(w, 0) < 3), '去掉': len(drop), '去掉按家数': dict(collections.Counter(cnt.get(w, 0) for w, c in drop)),
       '补入': len(added), '补入按字数': dict(collections.Counter(min(len(w), 5) for w in added)), '补入失败': dict(collections.Counter(v.split('（')[0] for v in failed.values())),
       '条目': len(out.strip().split('\r\n')), '码位': len(blocks), 'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest(),
       '去掉明细': [{'词': w, '码': c, '家数': cnt.get(w, 0), '来源': srcs.get(w, [])} for w, c in drop],
       '补入明细': [{'词': w, '码': c, '来源': srcs.get(w, [])} for w, c in added.items()],
       '补入失败明细': {w: v for w, v in failed.items() if not v.startswith('三字词')}}
json.dump(rep, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('保留 %d（豁免 %d）+ 补入 %d = %d 条，码位 %d；去掉 %d；补入失败 %s' % (len(keep), rep['豁免保留'], len(added), rep['条目'], len(blocks), len(drop), rep['补入失败']))
print('读音对不上的二字词:', [w for w, v in failed.items() if v.startswith('读音')])
