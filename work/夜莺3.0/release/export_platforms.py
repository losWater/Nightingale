"""夜莺 3.0 各平台文本码表导出（格式照夜莺 2.0 106_全平台导出/build.py 的文本部分；Rime 包另做）。
输入：单字表（3.0 普通单字表去掉符号）、字词表（release/make_ciku.py）、符号表与快符（夜莺 2.5 主表，原样沿用）、拆分（data/baseline/splits.json）。
输出：普通字词表（有简词/无简词/综合表/普通单字表/快符）、手心（模块化挂接、辅助码）、搜狗挂接、搜狗五笔、冰凌五笔、Bime、说明与核验。
用法：python release/export_platforms.py [输出目录]
"""
import collections, datetime, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
N25 = Path.home() / 'Nightingale/夜莺2.5'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'Downloads/夜莺3.0_字词表与输入法'
NAME, VER = '夜莺3.0', '3.0|' + datetime.date.today().strftime('%y%m%d')


def write(p, s, enc='utf-8-sig'):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s, encoding=enc, newline='')


def rd(p):
    return [tuple(l.rstrip('\r\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


SRC = ROOT / 'release/tables/夜莺3.0_NB46_字词表.txt'
rows = rd(SRC)
assert len(rows) == len(set(rows))
symbols = rd(N25 / '主表/符号表.txt'); symbolset = set(symbols)
single = [r for r in rd(ROOT / 'release/tables/夜莺3.0_NB46_普通单字表.txt') if r not in symbolset]
special = {(t, c) for t, c in rows if len(t) == 1} - set(single)          # 彩蛋码、容错码只在字词表里
single_all = single + sorted(special, key=lambda r: r[1])
assert {(t, c) for t, c in rows if len(t) == 1} == set(single_all)


def short(t, c):
    # 标点不算字：说道：“ 仍是二字简词
    return len(c) < 4 and len(t) > 1 and (sum('㐀' <= x <= '鿿' for x in t) < 4 or t.startswith('$ddcmd('))


def table(rr, reverse):
    return ''.join(f'{c}\t{t}\r\n' if reverse else f'{t}\t{c}\r\n' for t, c in rr)


no_short = [(t, c) for t, c in rows if not short(t, c)]
for label, rr in [('有简词', rows), ('无简词', no_short)]:
    for rev in (False, True):
        write(OUT / '普通字词表' / f'{NAME}_{label}_{"码前" if rev else "普通"}.txt', table(rr, rev))
plain_single = sorted(single_all + symbols, key=lambda r: r[1])
for rev in (False, True):
    write(OUT / '普通字词表' / f'{NAME}_普通单字表_{"码前" if rev else "普通"}.txt', table(plain_single, rev))

groups = collections.defaultdict(list)
for t, c in rows + symbols: groups[c].append(t)            # 符号排在同码位原有条目之后
quick = []
for line in (N25 / '主表/快符.txt').read_text(encoding='utf-8-sig').splitlines():
    m = re.fullmatch(r'([a-z]+),(\d+)=(.+)', line)
    if m:
        c, n, t = m.group(1), int(m.group(2)), m.group(3); quick.append((t, c, n))
        if t in groups[c]: groups[c].remove(t)
        assert 1 <= n <= len(groups[c]) + 1, line
        groups[c].insert(n - 1, t)
quickset = {(t, c) for t, c, n in quick}
allrows = [(t, c, n) for c in sorted(groups) for n, t in enumerate(groups[c], 1)]
assert all(groups[c][n - 1] == t for t, c, n in quick)
unsupported = [r for r in allrows if r[0].startswith('$ddcmd(')]
write(OUT / '说明与核验/未移植的源输入法专用宏.txt', ''.join(f'{t}\t{c}\t{n}\r\n' for t, c, n in unsupported))
allrows = [r for r in allrows if not r[0].startswith('$ddcmd(')]
valid = [r for r in allrows if re.fullmatch('[a-z]{1,4}', r[1])]
excluded = [r for r in allrows if len(r[1]) > 4]
write(OUT / '说明与核验/超过四码_原表保留.txt', ''.join(f'{t}\t{c}\t{n}\r\n' for t, c, n in excluded))
for rev in (False, True):
    write(OUT / '普通字词表' / f'{NAME}_综合表_{"码前" if rev else "普通"}.txt', table([(t, c) for t, c, n in allrows], rev))
write(OUT / '普通字词表' / f'{NAME}_快符_码前.txt', ''.join(f'{c}\t{t}\r\n' for t, c, n in quick))

# 手心：模块化挂接（各模块继承完整候选序号）+ 辅助码
modules = collections.defaultdict(list)
for t, c, n in allrows:
    k = '04_快符' if (t, c) in quickset else '05_符号' if (t, c) in symbolset else '01_核心单字' if len(t) == 1 \
        else '03_简词' if short(t, c) else '02_普通全码词'
    modules[k].append((t, c, n))
for k, rr in modules.items():
    write(OUT / '手心/模块化挂接' / f'{k}.txt', ''.join(f'{c}={n},{t}\n' for t, c, n in rr), 'utf-8')
aux = collections.defaultdict(list)
for t, c in single:
    if len(c) == 4 and c[2:] not in aux[t]: aux[t].append(c[2:])
auxtext = ''.join(t + '=' + ' '.join(cs) + '\r\n' for t, cs in sorted(aux.items()))
write(OUT / f'手心/{NAME}_辅助码.txt', auxtext, 'utf-8')
write(OUT / f'手心/{NAME}_辅助码_Unicode.txt', auxtext, 'utf-16')
write(OUT / '手心/使用说明.txt', '四个挂接模块可同时启用；不需要简词或快符可分别停用03或04。不要与旧整合挂接表重复导入。\r\n'
      '各模块继承完整字词表的候选序号，不因关闭模块重新编号。02包含普通二、三字全码词，以及四字及以上词；关闭02会一起停用这些词。\r\n'
      '辅助码与挂接独立导入辅助码设置；两个辅助码文件内容相同，按导入支持选UTF-8或Unicode版之一。辅助码取当前单字全码最后两位，同字多码空格分隔。\r\n')

# 搜狗挂接（自定义短语，不含四码二字词，删词后保留原序号）
sogou = [r for r in allrows if not (len(r[0]) == 2 and len(r[1]) == 4 and (r[0], r[1]) not in quickset)]
assert len(sogou) <= 100000, len(sogou)
write(OUT / f'搜狗挂接/{NAME}_挂接_含快符.txt', ''.join(f'{c},{n}={t}\r\n' for t, c, n in sogou), 'utf-16')
# 搜狗五笔（20 万条上限）
assert len(valid) <= 200000, len(valid)
write(OUT / f'搜狗五笔/{NAME}_五笔_含快符.txt', ''.join(f'{c}\t{t}\r\n' for t, c, n in valid), 'utf-8')
# 冰凌五笔
header = (f'[CODETABLEHEADER]\r\nName={NAME}词库\r\nVersion={VER}\r\nAuthor=nightingale\r\nCodeScheme={NAME}[夜莺]\r\nCodeLength=4\r\n'
          'BWCodeLength=0\r\nSpecialPrefix=0\r\nPhraseRule=3\r\npa2=w11w12w21w22\r\npa3=w11w21w31\r\npe4=w11w21w31r11\r\n[CODETABLE]\r\n')
write(OUT / f'冰凌五笔/{NAME}_词库_含快符.txt', header + ''.join(f'{c}\t{t}\t{10000 - n}\r\n' for t, c, n in valid), 'utf-16')
# Bime（字词 + 拆分）
write(OUT / f'Bime/mb/{NAME}/夜莺字词.txt', ''.join(f'{t}\t{c}\t{100000 - n}\r\n' for t, c, n in valid))
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
chars = sorted({t for t, c in single_all})
missing = [t for t in chars if t not in splits]
write(OUT / f'Bime/mb/{NAME}/夜莺.拆分', ''.join(f'{t}\t{" ＋ ".join(p[0] for p in splits[t])}\r\n' for t in chars if t in splits))
write(OUT / 'Bime/使用说明.txt', f'将mb内的{NAME}文件夹复制到Bime的mb目录，再重载码表、选择{NAME}。最大码长设4。包含快符及全部{len(chars)}字的拆分。没有覆盖个人config.txt或用户调整.txt。旧个人调频可能改变候选顺序。\r\n')

write(OUT / '使用说明.txt', f'{NAME} 码表导出，{datetime.date.today()}：单字（NB46 布局，含手动调整）＋ 词（沿用夜莺2.5词库，按 3.0 字词让位规则重排）＋ 符号表 ＋ 快符。简码位字在前、简词在后。\r\n'
      '普通字词表：普通=字词在前；码前=编码在前；无简词仍保留四字及以上词。普通表不混入快符，快符单列；各平台码表已包含快符，手心为独立模块。\r\n'
      '搜狗挂接为自定义短语格式，UTF-16LE BOM；不包含四码二字词，删词后保留原序号，让位字从2开始。\r\n'
      '搜狗五笔为编码TAB字词，UTF-8。冰凌为UTF-16LE BOM专用文本词库。\r\n手心挂接使用UTF-8；Bime使用UTF-8 BOM、CRLF。\r\n'
      '定长四码平台不导入超过四码的条目，完整内容仍在普通表，并附单独清单。Rime独立打包。\r\n'
      '其他平台本次为格式及数据核验，未在输入法界面实测导入。\r\n')
report = {'来源': str(SRC.relative_to(ROOT)), '来源SHA256': hashlib.sha256(SRC.read_bytes()).hexdigest(),
          '字词表条数': len(rows), '无简词条数': len(no_short), '快符': len(quick), '符号表条数': len(symbols),
          '综合表条数': len(allrows), '四码内含快符': len(valid), '超过四码条目': len(excluded), '普通单字表条数': len(plain_single),
          '手心模块': {k: len(v) for k, v in sorted(modules.items())}, '辅助码字数': len(aux), '搜狗挂接条数': len(sogou),
          '搜狗五笔条数': len(valid), '冰凌及Bime条数': len(valid), 'Bime拆分字数': len(chars) - len(missing), '拆分缺字': ''.join(missing),
          '未移植专用宏': len(unsupported)}
write(OUT / '说明与核验/生成清单.json', json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(report, ensure_ascii=False, indent=1))
