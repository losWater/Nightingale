# -*- coding: utf-8 -*-
"""第 5 步：简词入表。97 字词表（字 + 普通词，四码位已跑让位规则）+ 102 二字简词 + 103 三字词三码 → 最终表四种格式。
裁定（2026-09-15，规则文档五之六）：简码位上字的简码不让位，字在首位、简词在字后；四码位一字不动。
自检：四码位与 97 逐条一致；每个简码位字都在词前；有字的简码位词 ≤2、无字 ≤3；简词条目与 102/103 逐条一致。"""
import io, sys, os, json, hashlib, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
def load(p):
    rows = []
    for line in open(p, encoding='utf-8-sig'):
        q = line.rstrip('\n').rstrip('\r').split('\t')
        if len(q) >= 2: rows.append((q[0], q[1]))
    return rows
base = load(B + '/97_字词合并/夜莺2.0字词表_普通格式.txt')
w2 = load(B + '/102_二字简词/夜莺2.0二字简词表_普通格式.txt')
w3 = load(B + '/103_三字词三码/夜莺2.0三字词三码表_普通格式.txt')
blocks = collections.OrderedDict()
for w, c in base: blocks.setdefault(c, []).append(w)
for w, c in w2 + w3:
    assert len(w) > 1 and len(c) < 4
    blocks.setdefault(c, []).append(w)   # 追加在字之后（97 的简码位只有字）
# 自检
bad = []
b97 = collections.OrderedDict()
for w, c in base: b97.setdefault(c, []).append(w)
for c, blk in blocks.items():
    if len(c) == 4:
        if blk != b97.get(c): bad.append(('四码位与97不一致', c))
    else:
        ch = [w for w in blk if len(w) == 1]; wd = [w for w in blk if len(w) > 1]
        if blk != ch + wd: bad.append(('字不在词前', c))
        if len(wd) > (2 if ch else 3): bad.append(('超出4.2上限', c))
assert not bad, bad[:10]
order = sorted(blocks)
def emit(c, w, i, f):
    return {'plain': w + '\t' + c, 'code1st': c + '\t' + w, 'shouxin': c + '=' + str(i) + ',' + w, 'sogou': c + ',' + str(i) + '=' + w}[f]
out = {}
for name, fmt, enc in (('夜莺2.0最终表_普通格式.txt', 'plain', 'utf-8-sig'), ('夜莺2.0最终表_码前格式.txt', 'code1st', 'utf-8-sig'),
                       ('夜莺2.0最终表_手心格式.txt', 'shouxin', 'utf-8-sig'), ('夜莺2.0最终表_搜狗.txt', 'sogou', 'utf-16')):
    lines = [emit(c, w, i + 1, fmt) for c in order for i, w in enumerate(blocks[c])]
    data = ('\r\n'.join(lines) + '\r\n').encode(enc)
    open(H + '/' + name, 'wb').write(data)
    out[name] = {'行数': len(lines), 'sha256': hashlib.sha256(data).hexdigest()}
    print('%-28s %d 行  %s' % (name, len(lines), out[name]['sha256'][:16]))
n1 = sum(len(w) == 1 for w, _ in base); n4 = sum(len(c) == 4 for _, c in base) - sum(len(w) == 1 and len(c) == 4 for w, c in base)
print('单字 %d + 普通词 %d + 二字简词 %d + 三字词三码 %d = %d；码位 %d；自检通过' % (n1, len(base) - n1, len(w2), len(w3), len(base) + len(w2) + len(w3), len(blocks)))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '输入': {'字词表': '97（普通词来自 109 共识筛选）', '二字简词': '102', '三字词三码': '103'},
           '单字': n1, '普通词': len(base) - n1, '二字简词': len(w2), '三字词三码': len(w3), '码位': len(blocks), '自检': '通过', '输出': out},
          open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
