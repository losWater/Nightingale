# -*- coding: utf-8 -*-
"""鲸凉鹤作者专属版（2026-09-17 你的口径）。

他的要求只有一条：**夜莺的单字保持原样**——单字落在 106 手心核心单字表指定的候选序号上，位置不变。
除此之外**他的词库一个字节都不动**：飞键、无理码、特设短语、简词、长码、词序，全部照抄；只把他词库里的单字条目换成夜莺的单字。
冲突时夜莺单字占住它的序号，他的词依次往后排（核心单字表的序号空位本来就是留给挂接词库填的，让位字从序号 2 起即为此设计）。

产物在 专属版/，手心格式（和他原文件同款：`码=序号,内容`，UTF-8 无 BOM，CRLF），另附普通格式与差异清单。可重复运行。"""
import io, sys, os, re, json, hashlib, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); OUT = H + '/专属版'; os.makedirs(OUT, exist_ok=True)
SRC = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
CORE = W + '/106_全平台导出/夜莺2.0_字词表与输入法/手心/模块化挂接/01_核心单字.txt'
AUX = W + '/106_全平台导出/夜莺2.0_字词表与输入法/手心/夜莺2.0_辅助码.txt'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
LINE = re.compile(r'([a-z]+)=(\d+),(.+)')
def rd(p):
    out = []
    for lineno, l in enumerate(open(p, encoding='utf-8-sig'), 1):
        m = LINE.fullmatch(l.strip())
        if m: out.append((m.group(1), int(m.group(2)), m.group(3), lineno))
    return out
# 1 夜莺单字：码 → {序号: 字}
core = collections.defaultdict(dict); core_n = 0
for c, i, t, _ in rd(CORE):
    assert i not in core[c], ('核心单字表序号重复', c, i); core[c][i] = t; core_n += 1
# 2 他的词：码 → [(原序号, 词)]，按他的原序号排；单字条目丢弃（由夜莺单字替代）
his = collections.defaultdict(list); dropped = []; his_n = 0
for c, i, t, lineno in rd(SRC):
    if len(t) == 1: dropped.append({'码': c, '序': i, '字': t, '行': lineno}); continue
    his[c].append((i, t)); his_n += 1
for c in his: his[c].sort()
# 3 合并：单字占住自己的序号，他的词按原顺序填剩下的位置
merged = {}; report = {'字词同码': 0, '留空位': 0, '空位码位': []}
for c in sorted(set(core) | set(his)):
    slots = dict(core.get(c, {})); pos = 1
    for _, w in his.get(c, []):
        while pos in slots: pos += 1
        slots[pos] = w; pos += 1
    if core.get(c) and his.get(c): report['字词同码'] += 1
    gaps = [i for i in range(1, max(slots) + 1) if i not in slots] if slots else []
    if gaps:
        report['留空位'] += len(gaps)
        if len(report['空位码位']) < 500: report['空位码位'].append({'码': c, '空位': gaps, '内容': ['%d=%s' % (i, slots[i]) for i in sorted(slots)]})
    merged[c] = slots
# 4 核验：单字序号与核心单字表逐条一致；他的词内容与相对顺序逐条一致
for c, d in core.items():
    for i, t in d.items(): assert merged[c].get(i) == t, ('单字位置变了', c, i, t, merged[c].get(i))
for c, ws in his.items():
    got = [merged[c][i] for i in sorted(merged[c]) if len(merged[c][i]) > 1 or (c in core and i not in core[c])]
    got = [merged[c][i] for i in sorted(merged[c]) if not (c in core and i in core[c])]
    assert got == [w for _, w in ws], ('词序变了', c, got[:5], [w for _, w in ws][:5])
lines = ['%s=%d,%s' % (c, i, t) for c in sorted(merged) for i, t in sorted(merged[c].items())]
open(OUT + '/夜莺2.0_鲸凉鹤专属_手心挂接.txt', 'wb').write(('\r\n'.join(lines) + '\r\n').encode('utf-8'))
flat = [(t, c) for c in sorted(merged) for _, t in sorted(merged[c].items())]      # 顺序 = 手心格式的码位与候选序，即本表的定稿次序
for name, fmt in (('普通', '%s\t%s'), ('码前', None)):
    body = '\r\n'.join((fmt % (t, c)) if fmt else ('%s\t%s' % (c, t)) for t, c in flat) + '\r\n'
    open(OUT + '/夜莺2.0_鲸凉鹤专属_%s.txt' % name, 'wb').write(body.encode('utf-8-sig'))      # 与夜莺正式版普通字词表同款：UTF-8 带 BOM、CRLF
old = OUT + '/夜莺2.0_鲸凉鹤专属_普通格式.txt'
if os.path.exists(old): os.remove(old)      # 本脚本早先版本的文件名
import shutil; shutil.copy2(AUX, OUT + '/夜莺2.0_辅助码.txt')
json.dump(dropped, open(OUT + '/被替换掉的原单字条目.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(report['空位码位'], open(OUT + '/序号留空的码位.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
readme = f"""# 夜莺 2.0 · 鲸凉鹤专属版（{datetime.date.today().strftime('%Y-%m-%d')}）

给鲸凉鹤作者的挂接码表：**夜莺的单字 + 你自己原封不动的词库**。

## 这版做了什么

- **单字全部换成夜莺 2.0 的**，而且落在夜莺核心单字表指定的候选位上，和夜莺正式版逐条一致（{core_n} 条，{len(core)} 个码位）。
  夜莺的"出简让全""字词让位"都体现在这些序号里：让位的字从第 2 位起，空出来的第 1 位就是留给你的词的。
- **你的词库一个字节都没动**：编码、词、先后顺序全部照抄（{his_n} 条，{len(his)} 个码位）。飞键没还原，无理码没改，特设短语和长码都在，简词也都在。
- 你原来词库里的单字条目（{len(dropped)} 条）被夜莺单字替换掉了，清单见 `被替换掉的原单字条目.json`。

## 同一个码上字和词怎么排

夜莺单字占住它在核心单字表里的序号，你的词按原顺序填剩下的位置。例如 `wwts`：夜莺是 2=喂、4=喴，你的词就落在 1、3 和 5 往后。
字词同码的码位共 {report['字词同码']} 个。有 {report['留空位']} 个序号没人填（你的词不够填满夜莺留的空位），清单见 `序号留空的码位.json`，手心会自动紧凑显示，不影响使用。

## 文件

- `夜莺2.0_鲸凉鹤专属_手心挂接.txt`：手心格式（`码=序号,内容`），和你原来的文件同款，UTF-8 无 BOM、CRLF，直接替换即可。共 {len(lines)} 条。
- `夜莺2.0_鲸凉鹤专属_普通.txt`：同样内容的"文字<Tab>编码"版，给别的输入法用；顺序就是手心格式的候选次序。
- `夜莺2.0_鲸凉鹤专属_码前.txt`："编码<Tab>文字"版，内容与顺序同上。
  这两个文件与夜莺正式版的普通字词表同款：UTF-8 带 BOM、CRLF。
- `夜莺2.0_辅助码.txt`：夜莺的辅助码（每个字全码的后两键 = 首根键 + 末根键），{sum(1 for _ in open(AUX, encoding='utf-8-sig'))} 字。

## 来源

- 你的词库：`鲸凉鹤1.1手心挂接.txt`
- 夜莺单字：夜莺 2.0 核心单字表（8105 通用规范汉字 + 7391 扩展字）
- 生成：`work/夜莺2.0/131_鲸凉鹤专属版/build.py`
"""
open(OUT + '/README.md', 'w', encoding='utf-8', newline='\n').write(readme)
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '夜莺单字条目': core_n, '他的词条目': his_n, '被替换的原单字条目': len(dropped),
           '合并后条目': len(lines), '码位': len(merged), '字词同码码位': report['字词同码'], '留空序号': report['留空位'],
           '来源': {'词库': SRC, '词库sha256': sha(SRC), '核心单字表': CORE, '核心单字表sha256': sha(CORE)}}, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('夜莺单字 %d 条 + 他的词 %d 条 = %d 条，%d 个码位；替换掉他的原单字 %d 条；字词同码 %d 个码位；留空序号 %d 个' % (core_n, his_n, len(lines), len(merged), len(dropped), report['字词同码'], report['留空位']))
