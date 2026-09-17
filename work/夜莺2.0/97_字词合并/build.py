# -*- coding: utf-8 -*-
"""第 3 步：单字表（78）+ 普通词表（91）→ 合并 → 跑字词让位规则（码表概念与规则.md 第五节 1–5a，含 84 逐条例外、人工指定）→ 四种格式。
验证：与 62（第 2 步输入，已跑过同一规则）逐码位比对，应一致。"""
import io, sys, os, json, hashlib, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
H = os.path.dirname(os.path.abspath(__file__))
TOL = {'jv', 'jvb', 'jvn', 'jvo', 'xv', 'yvl', 'yvz', 'yvc', 'yvo', 'eh'}
EXC = {'xmic', 'xime', 'vatk', 'xkyb', 'bcpg', 'jiyt'}
rank = {e['字']: e['字频'] for e in json.load(open(B + '/59_单字当量排行/单字当量排行.json', encoding='utf-8'))}
man = json.load(open(B + '/64_加入鲸凉鹤简词/码位人工指定.json', encoding='utf-8-sig'))

def load(p):
    rows = []
    for line in open(p, encoding='utf-8-sig'):
        q = line.rstrip('\n').rstrip('\r').split('\t')
        if len(q) >= 2: rows.append((q[0], q[1]))
    return rows

chars = load(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt')
words = load(B + '/109_普通词共识筛选/夜莺2.0普通词表_普通格式.txt')   # 2026-09-15 换源：共识筛选后的普通词表
codes = collections.defaultdict(set)
for w, c in chars: codes[w].add(c)
hasS = lambda w: any(len(c) < 4 and c not in TOL for c in codes[w])

blocks = collections.OrderedDict()
for w, c in chars: blocks.setdefault(c, []).append(w)
for w, c in words: blocks.setdefault(c, []).append(w)

def target(F, blk):
    ch = [w for w in blk if len(w) == 1]; wd = [w for w in blk if len(w) > 1]
    if not ch or not wd or len(F) != 4 or F in man or F in EXC: return blk
    ok = len(wd[0]) == 2 and all(hasS(w) or rank.get(w, 99999) > 5000 for w in ch)
    return (wd[:1] + ch + wd[1:]) if ok else ch + wd

adj = 0
for c in list(blocks):
    t = target(c, blocks[c])
    if t != blocks[c]: blocks[c] = t; adj += 1
# 规则 5b（2026-09-17）：登记在 83/补音表.json 的补音字，让位给该码位全部词；字与字的次序不动；人工指定的码位不动
buyin = json.load(open(B + '/83_单字表重放/补音表.json', encoding='utf-8'))['条目']; buyin_applied = 0
for c, cs in buyin.items():
    blk = blocks.get(c, [])
    if c in man or not any(len(w) > 1 for w in blk): continue
    last = max(i for i, w in enumerate(blk) if len(w) > 1)
    # 只有"后面到最后一个词之间不再有别的单字"的补音字才后移——越过别的字会打乱单字表次序（juwt：桔不得越过橘；114 有此断言）
    mv = [w for i, w in enumerate(blk[:last]) if w in cs and all(len(x) > 1 or x in cs for x in blk[i + 1:last])]
    if mv: blocks[c] = [w for w in blk[:last + 1] if w not in mv] + mv + blk[last + 1:]; buyin_applied += 1
# 人工指定：按 码位人工指定.json 的顺序把指定项置前
manual_applied = 0
for c, seq in man.items():
    if c in blocks:
        rest = [w for w in blocks[c] if w not in seq]
        newo = [w for w in seq if w in blocks[c]] + rest
        if newo != blocks[c]: blocks[c] = newo; manual_applied += 1

order = sorted(blocks)
def emit(c, w, i, f):
    return {'plain': w + '\t' + c, 'code1st': c + '\t' + w, 'shouxin': c + '=' + str(i) + ',' + w, 'sogou': c + ',' + str(i) + '=' + w}[f]
out = {}
for name, fmt, enc in (('夜莺2.0字词表_普通格式.txt', 'plain', 'utf-8-sig'), ('夜莺2.0字词表_码前格式.txt', 'code1st', 'utf-8-sig'),
                       ('夜莺2.0字词表_手心格式.txt', 'shouxin', 'utf-8-sig'), ('夜莺2.0字词表_搜狗.txt', 'sogou', 'utf-16')):
    lines = [emit(c, w, i + 1, fmt) for c in order for i, w in enumerate(blocks[c])]
    data = ('\r\n'.join(lines) + '\r\n').encode(enc)
    open(H + '/' + name, 'wb').write(data)
    out[name] = {'行数': len(lines), 'sha256': hashlib.sha256(data).hexdigest()}
    print('%-30s %d 行  %s' % (name, len(lines), out[name]['sha256'][:16]))

# 验证：与 62 比对
o62 = collections.OrderedDict()
for w, c in load(B + '/62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt'): o62.setdefault(c, []).append(w)
diff = [c for c in set(blocks) | set(o62) if blocks.get(c) != o62.get(c)]
print('补音字让位生效 %d 个码位' % buyin_applied)
print('\n合并后码位 %d；规则调整了 %d 个码位；人工指定生效 %d 个码位' % (len(blocks), adj, manual_applied))
print('与 62 比对：不一致码位 %d' % len(diff))
for c in sorted(diff)[:10]: print('   %-5s 合并[%s]  62[%s]' % (c, '、'.join(blocks.get(c, [])[:5]), '、'.join(o62.get(c, [])[:5])))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '输入': {'单字表': '78/夜莺2.0纯单字表_普通格式.txt', '普通词表': '91/夜莺2.0普通词表_普通格式.txt'},
           '单字条目': len(chars), '词条目': len(words), '码位': len(blocks), '规则调整码位': adj, '人工指定生效': manual_applied,
           '与62不一致码位': len(diff), '不一致样例': sorted(diff)[:50], '输出': out},
          open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
