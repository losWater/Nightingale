# -*- coding: utf-8 -*-
"""扩展字入表：110 最终表 + 112 扩展字表 → 本目录最终表四种格式。
规矩（2026-09-16 你裁定）：扩展字全码排在该码位现有字词之后（扩展字之间按 112 的顺序）；扩展字简码位：字排在该位所有简词之前，
简词按手册 4.2 上限裁到 2 个（被裁的记录在报告）；8105 的字、所有普通词的位置一律不动。自检：去掉扩展字后与 110 逐码位一致（除被裁简词）。"""
import io, sys, os, json, hashlib, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
def load(p):
    rows = []
    for l in open(p, encoding='utf-8-sig'):
        q = l.rstrip('\r\n').split('\t')
        if len(q) >= 2: rows.append((q[0], q[1]))
    return rows
base = load(B + '/110_词序三家投票/夜莺2.0最终表_普通格式.txt'); ext = load(B + '/112_扩展字继承/夜莺2.0扩展字表_普通格式.txt')
extset = {w for w, _ in ext}
blocks = collections.OrderedDict()
for w, c in base: blocks.setdefault(c, []).append(w)
dropped = []
for w, c in ext:
    blk = blocks.setdefault(c, [])
    if len(c) == 4: blk.append(w)
    else:
        assert not any(len(x) == 1 for x in blk), (c, blk)
        blk.insert(0, w)
        while sum(1 for x in blk if len(x) > 1) > 2:
            x = [y for y in blk if len(y) > 1][-1]; blk.remove(x); dropped.append({'码': c, '退出简词': x, '因': '扩展字 %s 占位，有字最多两词' % w})
b110 = collections.OrderedDict()
for w, c in base: b110.setdefault(c, []).append(w)
drop_set = {(d['码'], d['退出简词']) for d in dropped}
for c in b110:
    a = [w for w in b110[c] if (c, w) not in drop_set]; b = [w for w in blocks[c] if w not in extset]
    assert a == b, c
order = sorted(blocks)
def emit(c, w, i, f): return {'plain': w + '\t' + c, 'code1st': c + '\t' + w, 'shouxin': c + '=' + str(i) + ',' + w, 'sogou': c + ',' + str(i) + '=' + w}[f]
out = {}
for name, fmt, enc in (('夜莺2.0最终表_普通格式.txt', 'plain', 'utf-8-sig'), ('夜莺2.0最终表_码前格式.txt', 'code1st', 'utf-8-sig'), ('夜莺2.0最终表_手心格式.txt', 'shouxin', 'utf-8-sig'), ('夜莺2.0最终表_搜狗.txt', 'sogou', 'utf-16')):
    lines = [emit(c, w, i + 1, fmt) for c in order for i, w in enumerate(blocks[c])]
    data = ('\r\n'.join(lines) + '\r\n').encode(enc); open(H + '/' + name, 'wb').write(data); out[name] = {'行数': len(lines), 'sha256': hashlib.sha256(data).hexdigest()}
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '输入': {'最终表': '110', '扩展字表': '112'}, '110条目': len(base), '扩展字条目': len(ext), '条目': len(base) + len(ext) - len(dropped), '码位': len(blocks), '退出的简词': dropped, '输出': out}
json.dump(rep, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('110 %d + 扩展字 %d - 退出简词 %d = %d 条，码位 %d；自检通过' % (len(base), len(ext), len(dropped), rep['条目'], len(blocks)))
print('退出的简词:', [(d['码'], d['退出简词']) for d in dropped])
