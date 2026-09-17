# -*- coding: utf-8 -*-
"""根因修复（2026-09-17 你指出：发现与原则不符要查根因、排除代码层隐患）。
现象：补音字进表后，97 的字词让位规则不认识"补音字"，按普通字处理，17 个码位里补音字排到词前面，几处还顶掉首选词。
      第二十三批当时"撞位排最后"只是碰巧没撞词，规则从未落到代码里。我先用 15 条人工指定盖住，这是绕开不是修复。
修复：① 新建登记表 83_单字表重放/补音表.json（全码 → 补音字）；② 97 增加规则 5b：登记的补音字让位给该码位全部词，字与字之间的次序不动；
      ③ 撤掉那 15 条人工指定；④ 规则写进 码表概念与规则.md。可重复运行。"""
import io, sys, os, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
# ① 登记表：第二十三批 10 字 + 第二十七批 裳 + 第二十八批 74 条
reg = {}
for fn in ('29_第二十三批_补标准读音.json', '33_第二十七批_实战反馈第二批.json', '34_第二十八批_补音.json'):
    for o in json.load(open(W + '/83_单字表重放/裁定/' + fn, encoding='utf-8'))['操作']:
        if o['op'] == '加' and len(o['码']) == 4: reg.setdefault(o['码'], []).append(o['字'])
json.dump({'说明': '补音字登记表：后补的少数读音/俗读，只为"打得出来"。97 规则 5b：这些字在所登记的全码位上让位给全部词（排在最后一个词之后），字与字的次序仍按单字表。新补音时在此登记。', '条目': reg},
          open(W + '/83_单字表重放/补音表.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# ② 97 规则 5b
p = W + '/97_字词合并/build.py'; s = open(p, encoding='utf-8').read()
if '补音表.json' not in s:
    a = "# 人工指定：按 码位人工指定.json 的顺序把指定项置前\n"; assert s.count(a) == 1
    s = s.replace(a, "# 规则 5b（2026-09-17）：登记在 83/补音表.json 的补音字，让位给该码位全部词；字与字的次序不动；人工指定的码位不动\n"
                     "buyin = json.load(open(B + '/83_单字表重放/补音表.json', encoding='utf-8'))['条目']; buyin_applied = 0\n"
                     "for c, cs in buyin.items():\n    blk = blocks.get(c, [])\n    if c in man or not any(len(w) > 1 for w in blk): continue\n"
                     "    last = max(i for i, w in enumerate(blk) if len(w) > 1); mv = [w for w in blk[:last] if w in cs]\n"
                     "    if mv: blocks[c] = [w for w in blk[:last + 1] if w not in mv] + mv + blk[last + 1:]; buyin_applied += 1\n" + a)
    a2 = "print('\\n合并后码位 %d；"; assert s.count(a2) == 1
    s = s.replace(a2, "print('补音字让位生效 %d 个码位' % buyin_applied)\n" + a2)
    bk = H + '/实装前备份/97_字词合并/build.py'; os.makedirs(os.path.dirname(bk), exist_ok=True); shutil.copy2(p, bk); open(p, 'w', encoding='utf-8').write(s)
# ③ 撤人工指定
f = H + '/人工次序.json'
if os.path.exists(f):
    order = json.load(open(f, encoding='utf-8')); pm = W + '/64_加入鲸凉鹤简词/码位人工指定.json'; man = json.load(open(pm, encoding='utf-8-sig'))
    for c, o in order.items():
        if man.get(c) == o: del man[c]
    json.dump(man, open(pm, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(f, H + '/人工次序_已撤销.json'); print('人工指定撤 %d 条，现 %d 条' % (len(order), len(man)))
# ④ 规则文档
p = W + '/码表概念与规则.md'; s = open(p, encoding='utf-8').read()
if '5b.' not in s:
    a = '6. 人工指定（`64/码位人工指定.json`）的码位不动。'; assert s.count(a) == 1
    s = s.replace(a, '5b. 【裁定 2026-09-17】**补音字**（后补的少数读音、俗读，登记在 `83_单字表重放/补音表.json`）在所登记的全码位上**让位给该码位全部词**，不论词长、不论该字有无简码；字与字之间仍按单字表次序（含出简让全）。理由：补音只为"打得出来"，不应动任何既有首选。三简位空着的可给三简（同日裁定）。新补音必须登记，否则 97 会按普通字处理（2026-09-17 曾因此顶掉 17 个码位的词，见 `130/rootfix.py`）。\n' + a)
    open(p, 'w', encoding='utf-8').write(s)
print('补音表 %d 个码位' % len(reg))
