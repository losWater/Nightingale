# -*- coding: utf-8 -*-
"""扩展字表（2026-09-16 你裁定）：只加新华字典（pwxcoo/chinese-xinhua）比 8105 多出的 7391 字，其中 1.0 扩展字有拆分的 7385 个；
拆分按 55/67 的规则从 1.0 继承到 2.0 根表（试算五）；全码 = 1.0 扩展字表的声码（小鹤双拼）+ 2.0 首根键 + 末根键；
简码：语料（BCC 四语料 + SUBTLEX）出现过的字，若其三简位在 110 最终表里没有字（可有简词）就给（二简位不动）；同一空位多个字争，语料次数高者得；每字至多一个简码。
产物：扩展字表（字\\t码，含简码行）、扩展字拆分表、报告。不改 8105 任何东西。"""
import io, sys, os, json, csv, collections, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
P5 = json.load(open(H + '/继承试算5.json', encoding='utf-8')); split = P5['拆分']; codes = P5['拟码']
# 2026-09-16 你裁定的 7 个无 1.0 拆分字（亪兙兡桛瓧瓰瓱）：拆分与声码来自 人工拆分.json，键从 58 拆分查询数据取（与试算五同源）
import re as _re
MAN = json.load(open(H + '/人工拆分.json', encoding='utf-8'))['字']
_s = open(W + '/58_拆分查询/夜莺2.0拆分查询.html', encoding='utf-8-sig').read(); _m = _re.search(r'\bconst D\s*=\s*', _s); _D = json.JSONDecoder().raw_decode(_s[_m.end():])[0]
_rk = {}
for _r in _D.values():
    for _g in _r['根']: _rk.setdefault(_g['根'], _g['键'])
for ch, v in MAN.items():
    parts = v['拆分'].split(' ＋ '); k1, k2 = _rk[parts[0]], _rk[parts[-1]]
    split[ch] = v['拆分']; codes[ch] = [v['声码'] + k1 + k2]
X = json.load(open(W + '/111_扩字_新华字典/候选字_初筛.json', encoding='utf-8')); want = list(X['多出']); trad = set(X['其中繁体旧字形'])
cnt = json.load(open(H + '/扩展字_语料次数.json', encoding='utf-8'))
order10 = {}
for i, l in enumerate(open('E:/夜莺2.0/releases/v1.0/01_正式码表/夜莺码v1.0扩展字表.tsv', encoding='utf-8-sig').read().splitlines()[1:]):
    p = l.split('\t')
    if len(p) >= 2: order10.setdefault(p[0], i)
blk = collections.OrderedDict()
for l in open(W + '/110_词序三家投票/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) >= 2: blk.setdefault(p[1], []).append(p[0])
haschar = lambda c: any(len(w) == 1 for w in blk.get(c, []))
chars = [ch for ch in want if ch in codes]; missing = [ch for ch in want if ch not in codes]
chars.sort(key=lambda ch: (-cnt.get(ch, 0), order10.get(ch, 10**9)))
taken = set(); short = {}; why = {}
for ch in chars:
    if cnt.get(ch, 0) <= 0: continue
    for c in codes[ch]:   # 拟码按字典序，第一条即 1.0 首条读音
        for s in (c[:3],):   # 2026-09-16 你裁定：只上三简位，二简不动
            if s in taken or haschar(s): continue
            short[ch] = s; why[ch] = '语料 %d 次，%s 位无字%s' % (cnt[ch], '二简' if len(s) == 2 else '三简', '（原有简词 %s）' % '、'.join(blk[s]) if s in blk else '（全空）'); taken.add(s); break
        if ch in short: break
rows = []
for ch in chars:
    if ch in short: rows.append((ch, short[ch]))
    for c in codes[ch]: rows.append((ch, c))
out = '\r\n'.join('%s\t%s' % (ch, c) for ch, c in rows) + '\r\n'
open(H + '/夜莺2.0扩展字表_普通格式.txt', 'wb').write(out.encode('utf-8-sig'))
sp = '汉字\t完整拆分\t首根\t末根\r\n' + ''.join('%s\t%s\t%s\t%s\r\n' % (ch, split[ch], split[ch].split(' ＋ ')[0], split[ch].split(' ＋ ')[-1]) for ch in chars)
open(H + '/夜莺2.0扩展字拆分表.txt', 'wb').write(sp.encode('utf-8-sig'))
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'), '口径': '新华字典多出且 1.0 有拆分的字；拆分继承规则见试算五；简码规则见文件头',
       '字数': len(chars), '繁体旧字形': sum(1 for ch in chars if ch in trad), '语料出现过': sum(1 for ch in chars if cnt.get(ch, 0) > 0), '条目': len(rows),
       '简码': len(short), '二简': sum(1 for s in short.values() if len(s) == 2), '三简': sum(1 for s in short.values() if len(s) == 3),
       '简码明细': {ch: {'码': short[ch], '来由': why[ch]} for ch in short}, '无1.0拆分未收': missing,
       '排序': '语料次数降序，无记录按 1.0 扩展字表原序', 'sha256': hashlib.sha256(out.encode('utf-8-sig')).hexdigest()}
json.dump(rep, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('扩展字 %d（繁体旧字形 %d，语料出现过 %d），条目 %d；简码 %d（二简 %d，三简 %d）；无 1.0 拆分未收 %s' % (len(chars), rep['繁体旧字形'], rep['语料出现过'], len(rows), len(short), rep['二简'], rep['三简'], missing))
print('简码样例:', [(ch, short[ch], why[ch][:30]) for ch in list(short)[:12]])
