"""由虎整句 D89-r3 包生成「夜莺整句」Rime 试用方案（不改动原包；产物放到输出目录）。
- Lua：tiger_sentence* → yeying_sentence*（模块名、数据文件名、开关名、学习记录名一并改，和虎整句互不干扰）；
  码表索引改为按读音取本码：单字的本码/最优码按“字 + 码前两位（双拼）”确定（夜莺读音即字）。
- 组件用 @*包装模块 引用，不需要改 rime.lua。
- 码表：夜莺 3.0 NB46 无一简版（方案 C）；字频排名沿用虎整句；白名单、补充词为空。
- 模型：五元模型与词先验原样使用（模型放 models/，词先验改名 yeying_sentence.lexical.bin）。
- 空二码：data/inputs/整句空二码.json 里的字下放到空着的二码（仅整句）；它们腾出的三码给同前缀、只能打全码、
  字频最高的常用字（字音基准里字频 > 0；没有就不给）。
用法：python rime/sentence/build_sentence.py <虎整句包目录> <无一简普通单字表> <输出目录>
"""
import json, re, shutil, sys
from pathlib import Path

src, table, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
(out / 'lua').mkdir(parents=True, exist_ok=True); (out / 'models').mkdir(exist_ok=True)


def rename(s):
    return s.replace('tiger_sentence', 'yeying_sentence')


def rep(s, old, new, count=1):
    assert s.count(old) == count, (old[:70], s.count(old))
    return s.replace(old, new)


# ---- Lua 模块 ----
for f in sorted((src / 'lua').glob('tiger_sentence*.lua')):
    s = rename(f.read_text(encoding='utf-8'))
    if f.name == 'tiger_sentence.lua':
        # 按读音取本码：键 = 字 .. "\0" .. 码前两位
        s = rep(s, """        if is_single_character(word) then
            local character_codes = codes_by_character[word]
            if not character_codes then
                character_codes = {}
                codes_by_character[word] = character_codes
            end""", """        if is_single_character(word) then
            -- 夜莺：读音即字，本码按“字 + 码前两位（双拼）”分别确定
            local reading_key = word .. "\\0" .. code:sub(1, 2)
            key_character[reading_key] = word
            local character_codes = codes_by_character[reading_key]
            if not character_codes then
                character_codes = {}
                codes_by_character[reading_key] = character_codes
            end""")
        s = rep(s, "    local codes_by_character = {}\n", "    local codes_by_character = {}\n    local key_character = {}\n")
        s = rep(s, """    for character, codes in pairs(codes_by_character) do
        local best_first, best_any""", """    for reading_key, codes in pairs(codes_by_character) do
        local character = key_character[reading_key]
        local best_first, best_any""")
        s = rep(s, "            primary[character] = chosen\n", "            primary[reading_key] = chosen\n")
        s = rep(s, """    for character, codes in pairs(codes_by_character) do
        local chosen""", """    for reading_key, codes in pairs(codes_by_character) do
        local chosen""")
        s = rep(s, "            optimal_input[character] = chosen\n", "            optimal_input[reading_key] = chosen\n")
        s = rep(s, """        for index = 1, #texts do
            local text = texts[index]
            local allow_non_primary =""", """        for index = 1, #texts do
            local text = texts[index]
            local reading_key = text .. "\\0" .. code:sub(1, 2)
            local allow_non_primary =""")
        s = rep(s, "            if allow_non_primary or primary[text] == code then", "            if allow_non_primary or primary[reading_key] == code then")
        s = rep(s, "                    optimal_single = optimal_input[text] == code,", "                    optimal_single = optimal_input[reading_key] == code,")
        s = rep(s, "                    primary_single = primary[text] == code\n", "                    primary_single = primary[reading_key] == code\n")
    (out / 'lua' / rename(f.name)).write_text(s, encoding='utf-8')

wrappers = {'yeying_sentence_c_ascii': 'ascii_component', 'yeying_sentence_c_processor': 'processor_component',
            'yeying_sentence_c_translator': 'translator', 'yeying_sentence_c_filter': 'buffer_filter'}
for name, attr in wrappers.items():
    (out / 'lua' / f'{name}.lua').write_text(f'return require("yeying_sentence").{attr}\n', encoding='utf-8')

# ---- 方案 ----
s = rename((src / 'tiger_sentence.schema.yaml').read_text(encoding='utf-8'))
s = rep(s, 'schema_id: yeying_sentence', 'schema_id: yeying_sentence')
s = re.sub(r'  name: .*', '  name: 夜莺整句（试用）', s, count=1)
s = re.sub(r'  version: .*', '  version: "3.0-nb46-noyj-d89r3.2"', s, count=1)
s = rep(s, '    - TigerClaw', '    - TigerClaw（虎整句引擎）\n    - LosWater（夜莺码表）')
s = re.sub(r'  description: \|\n(    .*\n)+', '  description: |\n    夜莺 3.0 NB46 无一简码表 + 虎整句 D89-r3 引擎（本码按读音确定）。试用版。\n', s, count=1)
s = rep(s, 'lua_processor@yeying_sentence_ascii', 'lua_processor@*yeying_sentence_c_ascii')
s = rep(s, 'lua_processor@yeying_sentence_processor', 'lua_processor@*yeying_sentence_c_processor')
s = rep(s, 'lua_translator@yeying_sentence_translator', 'lua_translator@*yeying_sentence_c_translator')
s = rep(s, 'lua_filter@yeying_sentence_buffer_filter', 'lua_filter@*yeying_sentence_c_filter')
# 反查：只用 ` 前缀（整句引擎用 ~ 作暂存标记，不能用 2.5 的 ~~/F2）
s = rep(s, '    - lua_processor@*yeying_sentence_c_ascii\n', '    - lua_processor@*yeying_lookup_backtick\n    - lua_processor@*yeying_sentence_c_ascii\n')
s = rep(s, '    - punct_translator\n', '    - lua_translator@*yeying_sentence_lookup\n    - punct_translator\n')
s = rep(s, '  segmentors:\n    - abc_segmentor\n', '  segmentors:\n    - matcher\n    - abc_segmentor\n')
s = rep(s, 'recognizer:\n  import_preset: default\n', "recognizer:\n  import_preset: default\n  patterns:\n    yeying_lookup: '^`[a-z]*$'\n")
(out / 'yeying_sentence.schema.yaml').write_text(s, encoding='utf-8')
a = rename((src / 'tiger_sentence_ascii.schema.yaml').read_text(encoding='utf-8')).replace('虎整句内部切换配置', '夜莺整句内部切换配置')
(out / 'yeying_sentence_ascii.schema.yaml').write_text(a, encoding='utf-8')

# ---- 数据 ----
lines = [l.rstrip('\n') for l in open(table, encoding='utf-8-sig') if '\t' in l]
# 整句先不放符号（作者 2026-10-07，待定）：去掉 2.5 符号表里的条目，符号不混进整句词典
_sym = {tuple(l.rstrip('\n').split('\t')[:2]) for l in open(Path.home() / 'Nightingale/夜莺2.5/主表/符号表.txt', encoding='utf-8-sig') if '\t' in l}
lines = [l for l in lines if tuple(l.split('\t')[:2]) not in _sym]
assert not any(len(l.split('\t')[1]) == 1 for l in lines), '码表里不应有一码'
fill = json.load(open(Path(__file__).resolve().parents[2] / 'data/inputs/整句空二码.json', encoding='utf-8'))['二简']
used = {l.split('\t')[1] for l in lines}
for code, ch in fill.items():
    assert code not in used, f'{code} 不是空码'
    assert any(l.split('\t') == [ch, c] for l in lines for c in [l.split('\t')[1]] if c[:2] == code), f'{ch} 没有以 {code} 开头的码'
    lines.append(f'{ch}\t{code}')
# 腾出的三码：下放字整句里只用二码，原三码转给同前缀最常用的全码字
import collections, yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lib'))
from shuangpin import encode
E = yaml.load(open(Path(__file__).resolve().parents[2] / 'build/out/n30/elements.yaml', encoding='utf-8'),
              Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))
fr = collections.defaultdict(float)
for e in E:
    if e['拼音'] != 'reserved':
        try: fr[(e['词'], encode(e['拼音'], 'xiaohe'))] += e['频率']
        except Exception: pass
pairs = [l.split('\t') for l in lines]
codes = collections.defaultdict(set); first = {}
for ch, c in pairs:
    codes[ch].add(c); first.setdefault(c, ch)
for c2, ch in fill.items():
    for c3 in [c for c in codes[ch] if len(c) == 3 and c[:2] == c2 and first[c] == ch]:
        cands = sorted(((fr[(x, c2)], x) for x, c in pairs if len(c) == 4 and c[:3] == c3 and x != ch
                        and not any(len(k) < 4 and k[:2] == c2 for k in codes[x]) and fr[(x, c2)] > 0), reverse=True)
        if cands:
            x = cands[0][1]
            lines = [l for l in lines if l != f'{ch}\t{c3}'] + [f'{x}\t{c3}']
            print(f'腾出三码 {c3}：{ch} → {x}')
lines.sort(key=lambda l: l.split('\t')[1])
(out / 'yeying_sentence.codes.txt').write_text(
    '# 夜莺整句码表：夜莺 3.0 NB46 无一简版（方案 C）。格式“字<Tab>码”，同码内行序即候选序。\n' + '\n'.join(lines) + '\n', encoding='utf-8')
shutil.copy(src / 'tiger_sentence.char_ranks.txt', out / 'yeying_sentence.char_ranks.txt')
(out / 'yeying_sentence.full_code_whitelist.txt').write_text('# 夜莺整句：按读音取本码，不需要白名单。\n', encoding='utf-8')
(out / 'yeying_sentence.supplement.txt').write_text('# 夜莺整句补充词（格式：词条 [权重]），暂空。\n', encoding='utf-8')
shutil.copy(src / 'models/tiger_sentence.lexical.bin', out / 'models/yeying_sentence.lexical.bin')
print('生成', out, '；码表', len(lines), '行')
