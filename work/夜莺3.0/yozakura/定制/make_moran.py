"""夜桜版魔然：在魔然官方简体全量包上只换“码”——辅助码改用夜桜全码的后两位（首根＋末根），其余（方案、Lua、按键、模型、词库词条与词频）一律不动。
- moran.chars.dict.yaml：夜桜收的字按读音取夜桜辅码（该读音没有夜桜全码时取字的主辅码），一个字有几个夜桜辅码就出几行，首行原权重、其余 ×3/4（同魔然 gen_chars.py）；
- moran.base/tencent/moe/computer/words 词库：逐音节换成该字的夜桜辅码（同魔然 update-compact-dict 的做法，按读音取）；
- lua/zrmdb.txt（辅筛、提示）、opencc 拆分提示：换成夜桜辅码与夜桜拆分；拆分提示改用文本词典（免装 opencc 工具）；
- 四码字词序照夜桜字词表（lua/yozakura_order.txt）：魔然的 YYXX 单字是 abbrev，四码有词时单字被吞，补 o 才出；
- 只收夜桜有码的字（作者 2026-10-22：夜桜支持的字少一些就少一些）：夜桜没收的字从单字表、辅筛库、拆分提示里去掉，含这些字的词条也去掉；
- moran_fixed_simp（字词定长码表）：用户自己的表，按 yozakura/定制/make_custom.py 只换单字。
用法：.venv/bin/python yozakura/定制/make_moran.py <魔然简体全量包解压目录> <用户 moran_fixed_simp.dict.yaml> <输出目录>
"""
import collections, json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC, FIXED, OUT = map(Path, sys.argv[1:4])
B = json.load(open(ROOT / 'yozakura/品牌.json', encoding='utf-8'))

# ---- 夜桜辅码：字 → [主辅码, 其余…]；(字, 双拼) → 该读音的辅码 ----
custom = {c for c, _, _ in json.load(open(ROOT / 'yozakura/手动调整.json', encoding='utf-8')).get('自定义码', [])}   # 保留原拆法的码排在后面
by_sound, order = collections.defaultdict(list), collections.defaultdict(list)
for l in open(ROOT / 'yozakura' / B['单字表'], encoding='utf-8-sig'):
    t, c = l.rstrip('\n').split('\t')[:2]
    if len(t) != 1 or len(c) != 4 or 'CJK' not in unicodedata.name(t, ''): continue   # 只收汉字（夜桜单字表里的符号码不算）
    a = c[2:]
    if a not in by_sound[t, c[:2]]: by_sound[t, c[:2]].append(a)
    order[t].append((c in custom, c[:2] == 'pp', a))           # 偏旁读音（pp）的码不当主辅码
AUX = {t: list(dict.fromkeys(a for _, _, a in sorted(v, key=lambda x: x[:2]))) for t, v in order.items()}
aux_of = lambda ch, sp: (by_sound.get((ch, sp)) or AUX[ch])[0]
# 夜桜拆分：取本版码表导出里的 Bime 拆分表（字\t根 ＋ 根 ＋ …）
SPLITS = Path.home() / f'Downloads/{B["名称"]}_发布附件/{B["名称"]}_字词表与输入法/Bime/mb/{B["名称"]}/{B["名称"].removesuffix(B["版本"])}.拆分'
assert SPLITS.exists(), f'缺 {SPLITS}（先跑 release/export_platforms.py）'

if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
stat = collections.Counter()

# ---- 单字表 ----
p = OUT / 'moran.chars.dict.yaml'; lines, done = [], set()
rows = collections.defaultdict(list)                            # (字, 双拼) → [(行号, 权重)]
src = p.read_text(encoding='utf-8').split('\n')
for i, l in enumerate(src):
    m = re.fullmatch(r'(\S)\t([a-z]{2});([a-z]{2})\t(\d+)', l)
    if m and m[1] in AUX: rows[m[1], m[2]].append(int(m[4]))
for l in src:
    m = re.fullmatch(r'(\S)\t([a-z]{2});([a-z]{2})\t(\d+)', l)
    if re.match(r'\S\t[a-z]{2};[a-z]{2}', l) and l[0] not in AUX: stat['去掉的单字行'] += 1; continue
    if not m: lines.append(l); continue
    k = (m[1], m[2])
    if k in done: continue
    done.add(k); w = max(rows[k])
    auxes = list(dict.fromkeys((by_sound.get(k) or []) + AUX[m[1]]))
    lines += [f'{m[1]}\t{m[2]};{a}\t{w if n == 0 else w // 4 * 3}' for n, a in enumerate(auxes)]
    stat['单字读音'] += 1
seen = {k[0] for k in done}
extra = [f'{ch}\t{sp};{a}\t0' for (ch, sp), auxes in by_sound.items() if ch not in seen and sp != 'pp' for a in auxes]   # 魔然单字表没有的夜桜字，按夜桜读音补上
stat['补入魔然没有的夜桜字'] = len({x[0] for x in extra})
lines[-1:-1] = extra
p.write_text('\n'.join(lines), encoding='utf-8')

# ---- 词库 ----
for name in ('moran.base', 'moran.tencent', 'moran.moe', 'moran.computer', 'moran.words'):
    p = OUT / f'{name}.dict.yaml'
    if not p.exists(): continue
    out = []
    for l in p.read_text(encoding='utf-8').split('\n'):
        w = re.match(r'([^\t#][^\t]*)\t', l)
        if w and any(c not in AUX for c in w[1] if unicodedata.category(c)[0] == 'L' and 'CJK' in unicodedata.name(c, '')):
            stat['去掉的词条（含夜桜没收的字）'] += 1; continue
        m = re.fullmatch(r'([^\t#][^\t]*)\t([a-z]{2};[a-z]{2}(?: [a-z]{2};[a-z]{2})*)(\t.*)?', l)
        if m:
            chars = [c for c in m[1] if unicodedata.category(c)[0] in 'LN']   # 只按字对应音节，标点（·，（）：–- 等）不占音节
            codes = m[2].split(' ')
            if any(ch not in AUX for ch in chars): stat['去掉的词条（含夜桜没收的字）'] += 1; continue
            if len(chars) == len(codes):
                new = ' '.join(c[:3] + aux_of(ch, c[:2]) for ch, c in zip(chars, codes))
                if new != m[2]: stat['词条改码'] += 1
                l = f'{m[1]}\t{new}{m[3] or ""}'
            else: stat['词条字数与码数不符（原样）'] += 1
        out.append(l)
    p.write_text('\n'.join(out), encoding='utf-8')

# ---- Lua 辅码库 zrmdb.txt ----
p = OUT / 'lua/zrmdb.txt'; out = []
for l in p.read_text(encoding='utf-8').split('\n'):
    t = l.split('\t')[0]
    if '\t' in l and t not in AUX: continue                    # 夜桜没收的字不留辅码
    out.append(f'{t}\t{" ".join(AUX[t])}' if t in AUX else l)
have = {l.split('\t')[0] for l in out if '\t' in l}
out[-1:-1] = [f'{t}\t{" ".join(a)}' for t, a in AUX.items() if t not in have]   # 魔然辅码库里没有的夜桜字补上
p.write_text('\n'.join(out), encoding='utf-8')

# ---- 拆分提示（opencc）：夜桜拆分＋辅码 ----
YSPLIT = {}
for l in open(SPLITS, encoding='utf-8-sig'):
    t, s = l.rstrip('\n').split('\t', 1); YSPLIT[t] = s.replace(' ＋ ', '＋')
tips = collections.OrderedDict()
for t in AUX: tips[t] = ''.join(f'〔{YSPLIT[t]}·{a}〕' if n == 0 and t in YSPLIT else f'〔{a}〕' for n, a in enumerate(AUX[t]))   # 其余辅码是保留的旧拆法，不配拆分
(OUT / 'opencc/moran_chaifen.txt').write_text(''.join(f'{t}\t{s}\n' for t, s in tips.items()), encoding='utf-8')
(OUT / 'opencc/moran_chaifen.ocd2').unlink()
j = (OUT / 'opencc/moran_chaifen.json').read_text(encoding='utf-8')
assert j.count('"type": "ocd2",\n        "file": "moran_chaifen.ocd2"') == 1 and j.count('"file": "moran_chaifen.ocd2"') == 2, j
j = j.replace('"type": "ocd2",\n      "file": "moran_chaifen.ocd2"', '"type": "text",\n      "file": "moran_chaifen.txt"')
j = j.replace('"type": "ocd2",\n        "file": "moran_chaifen.ocd2"', '"type": "text",\n        "file": "moran_chaifen.txt"')
assert 'ocd2' not in j, j
(OUT / 'opencc/moran_chaifen.json').write_text(j, encoding='utf-8')

# ---- 四码字词序：按夜桜字词表 ----
# 魔然把单字 YYXX 设为 abbrev（moran.yaml「降低 YYXX 優先級」），四码整段对上词时单字全码根本不出，要补 o 才能打。
# 夜桜单字全码＝自然码＋首末根，与魔然 YYXX 同码，二字词码也同为自然码，所以四码上字词谁先直接照夜桜字词表
# （作者的规则：字有简码或词频超过字频 16 倍才让词）。只收有单字的四码；其余码、夜桜没有的词、魔然多出的辅码排在后面。
seq = collections.defaultdict(list)
for l in open(ROOT / 'yozakura' / B['字词表'], encoding='utf-8-sig'):
    t, c = l.rstrip('\n').split('\t')[:2]
    if len(c) == 4 and c.isalpha() and ' ' not in t: seq[c].append(t)
seq = {c: v for c, v in seq.items() if any(len(t) == 1 for t in v)}
(OUT / 'lua/yozakura_order.txt').write_text(''.join(f'{c}\t{" ".join(v)}\n' for c, v in sorted(seq.items())), encoding='utf-8')
stat['四码字词序'] = len(seq)
p = OUT / 'lua/moran_express_translator.lua'; s = p.read_text(encoding='utf-8')
a = '''    local smart_iter = top.raw_query_smart(env, input, seg, env.enable_word_filter and env.enable_aux_hint)
'''
assert s.count(a) == 1 and s.count('''        local ijrq_enabled = env.ijrq_enable
''') == 1 and s.count('''function top.output_begin(env)''') == 1
s = s.replace(a, a + '''    -- 夜桜：四碼按夜桜字詞表排序（YYXX 單字在 moran.yaml 是 abbrev，有詞時不出，故按 YYXXo 另查）
    local yozakura_ordered = false
    local order = smart_iter ~= nil and input_len == 4 and not is_sentence_making and top.yozakura_order()[input]
    if order then
        local full, chars, words, rest, list, used = {}, {}, {}, {}, {}, {}
        for cand in top.raw_query_smart(env, input .. "o", seg, false) do
            if utf8.len(cand.text) == 1 and cand._end - cand._start == 5 and not full[cand.text] then
                cand._end = seg._end
                cand.preedit = input
                full[cand.text] = cand
                table.insert(chars, cand)
            end
        end
        for cand in smart_iter do
            if utf8.len(cand.text) > 1 and cand._end - cand._start == 4 and not full[cand.text] then
                full[cand.text] = cand
                table.insert(words, cand)
            else
                table.insert(rest, cand)
            end
        end
        local function add(cand)
            if not used[cand.text] then table.insert(list, cand); used[cand.text] = true end
        end
        for _, t in ipairs(order) do
            if full[t] then add(full[t]) end
        end
        -- 夜桜此碼沒有的：魔然的詞、魔然多出的輔碼（字的其他讀音、舊拆法），按原次序排在後面
        for _, cand in ipairs(words) do add(cand) end
        for _, cand in ipairs(chars) do add(cand) end
        for _, cand in ipairs(rest) do add(cand) end
        local i = 0
        smart_iter = function() i = i + 1; return list[i] end
        yozakura_ordered = true
    end
''')
s = s.replace('''        local ijrq_enabled = env.ijrq_enable
''', '''        local ijrq_enabled = env.ijrq_enable and not yozakura_ordered  -- 夜桜字詞表已按簡碼讓位
''')
s = s.replace('''function top.output_begin(env)''', '''-- | 夜桜四碼字詞序（lua/yozakura_order.txt：碼\\t候選 候選…）
function top.yozakura_order()
    if top.yozakura_order_table == nil then
        top.yozakura_order_table = {}
        local pathsep = (package.config or '/'):sub(1, 1)
        local file = moran.open_rime_file('lua' .. pathsep .. 'yozakura_order.txt', pathsep)
        if file then
            for line in file:lines() do
                local code, items = line:match("^(%a+)\\t(.+)$")
                if code then
                    local list = {}
                    for t in items:gmatch("%S+") do table.insert(list, t) end
                    top.yozakura_order_table[code] = list
                end
            end
            file:close()
        end
    end
    return top.yozakura_order_table
end

function top.output_begin(env)''')
p.write_text(s, encoding='utf-8')

# ---- 方案显示名：魔然 → 夜桜魔然（只改菜单显示名，方案 ID 不变，用户的 *.custom.yaml 照样生效）----
for f, old in (('moran', '魔然'), ('moran_fixed', '字詞·魔然'), ('moran_aux', '輔篩·魔然'), ('moran_sentence', '整句·魔然')):
    s = (OUT / f'{f}.schema.yaml').read_text(encoding='utf-8')
    assert s.count(f'\n  name: {old}\n') == 1, (f, old)
    (OUT / f'{f}.schema.yaml').write_text(s.replace(f'\n  name: {old}\n', f'\n  name: {old.replace("魔然", "夜桜魔然")}\n'), encoding='utf-8')

# ---- 字词定长码表：用户自己的表，只换单字 ----
subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'yozakura/定制/make_custom.py'), str(FIXED), str(OUT / 'moran_fixed_simp.dict.yaml')], check=True)

print(OUT, dict(stat), '夜桜辅码字', len(AUX), '拆分提示', len(tips))
