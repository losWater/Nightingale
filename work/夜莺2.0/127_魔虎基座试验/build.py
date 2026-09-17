# -*- coding: utf-8 -*-
"""夜莺 × 魔虎基座 试验版（2026-09-17）。
你的要求：保留夜莺自己的东西（码表、词库、拆分），只借魔虎（fcxxxz/rime-mohu，GPL v3）的功能层与新模型。
做法：上游小鹤包原样拷贝 → 只替换数据文件 → 给主翻译器打一处小补丁（固定码表按码表原序输出，保住夜莺的字词让位）。
  换掉的数据：固定码表（两份同内容）、整句用词典、原生引擎词表、辅码表、字频排名、四码让位表、拆分提示、分号以外的符号码。
  不带的东西：上游七份大词库、上游 default.yaml（改给 default.custom.yaml）。
可重复运行；产物目录 夜莺魔虎试验版/ 只由本脚本生成，重跑时按上次的 生成清单.json 清理，不碰别的文件。"""
import io, sys, os, re, json, shutil, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
UP = H + '/upstream/pkg'; MODEL = H + '/upstream/model/mohu-sentence-ngram-v5.bin'
SRC = W + '/106_全平台导出/Rime_主力版'; OUT = H + '/夜莺魔虎试验版'
SKIP_FILES = {'default.yaml', '解除隔离.command', 'recipe.yaml', '安装说明.md', 'README.md',
              'mohu_flypy.base.dict.yaml', 'mohu_flypy.chars.dict.yaml', 'mohu_flypy.classics.dict.yaml', 'mohu_flypy.computer.dict.yaml',
              'mohu_flypy.moe.dict.yaml', 'mohu_flypy.tencent.dict.yaml', 'mohu_flypy.wanxiang.dict.yaml', 'mohu_flypy.words.dict.yaml',
              'mohu_flypy_tiger_fixed.dict.yaml', 'mohu_flypy_tiger_fixed_legacy.dict.yaml'}
SKIP_DIRS = {'recipes', 'etc'}
written = []
def put(rel, data):
    p = OUT + '/' + rel; os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data if isinstance(data, bytes) else data.encode('utf-8')); written.append(rel)
# 0 清理上次产物（只按清单）
mf = OUT + '/生成清单.json'
if os.path.exists(mf):
    for rel in json.load(open(mf, encoding='utf-8'))['文件']:
        p = OUT + '/' + rel
        if os.path.isfile(p): os.remove(p)
# 1 上游原样拷贝
for root, dirs, files in os.walk(UP):
    rel = os.path.relpath(root, UP).replace('\\', '/'); rel = '' if rel == '.' else rel + '/'
    dirs[:] = [d for d in dirs if not (rel == '' and d in SKIP_DIRS) and d != '__MACOSX']
    for fn in files:
        if rel == '' and fn in SKIP_FILES: continue
        if fn.endswith(('.dylib', '.command')) or fn == '.DS_Store': continue
        put(rel + fn, open(root + '/' + fn, 'rb').read())
# 2 固定码表：夜莺定稿次序，魔虎列格式（sort: original）
fixed = [l.rstrip('\n').split('\t') for l in open(SRC + '/yeying20_rime_fixed.dict.yaml', encoding='utf-8') if l.count('\t') == 2]
by = collections.defaultdict(list)
for t, c, w in fixed: by[c].append((-int(w), len(by[c]), t))
rows = []
for c in sorted(by):
    for _, _, t in sorted(by[c]): rows.append((t, c))
def fixed_dict(name):
    head = ('# Rime dictionary\n# encoding: utf-8\n# 夜莺 2.0 固定码表（字词定稿次序）。由 127_魔虎基座试验/build.py 生成，勿手改。\n\n---\nname: %s\nversion: "%s"\nsort: original\n'
            'columns:\n  - text\n  - code\n  - stem\n  - weight\n  - comment\nencoder:\n  rules:\n    - length_equal: 2\n      formula: "AaAbBaBb"\n    - length_equal: 3\n      formula: "AaBaCa"\n'
            '    - length_in_range: [4, 32]\n      formula: "AaBaCaZa"\nimport_tables:\n  - mohu_fixed.symbols\n...\n\n') % (name, datetime.date.today().strftime('%Y%m%d'))
    return head + ''.join('%s\t%s\n' % r for r in rows)
put('mohu_flypy_fixed.dict.yaml', fixed_dict('mohu_flypy_fixed'))
put('mohu_flypy_fixed_legacy.dict.yaml', fixed_dict('mohu_flypy_fixed_legacy'))
# 符号表只留分号引导的（上游 o 开头的符号码会挤进夜莺码位）
sym = open(UP + '/mohu_fixed.symbols.dict.yaml', encoding='utf-8').read(); head, body = sym.split('\n...\n', 1)
keep = [l for l in body.split('\n') if l.count('\t') >= 1 and l.split('\t')[1].startswith(';')]
put('mohu_fixed.symbols.dict.yaml', head + '\n...\n\n' + '\n'.join(keep) + '\n')
# 3 整句用词典：夜莺词库里"每个音节都是 双拼;辅码"的行
syl = re.compile(r'^[a-z]{2};[a-z]{2}$'); kept = []; chars_aux = collections.defaultdict(list)
base_rows = set()
for l in open(SRC + '/yeying20_rime.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) != 3: continue
    ss = f[1].split(' ')
    whole = len(ss) == 1 and ss[0].isalpha() and ss[0].islower() and len(f[0]) >= 2      # 多字词的整词规则码（如 万变不离其宗 wbbz），整句里当一个音节用；旧主力版同此
    if all(syl.match(s) for s in ss) or whole:
        kept.append(l if l.endswith('\n') else l + '\n'); base_rows.add((f[0], f[1]))
        if len(ss) == 1 and len(f[0]) == 1:
            a = ss[0][3:]
            if a not in chars_aux[f[0]]: chars_aux[f[0]].append(a)
put('mohu_flypy.yeying.dict.yaml', '# Rime dictionary\n# encoding: utf-8\n# 夜莺 2.0 字词（双拼;首末根键）。由 127 build.py 生成。\n\n---\nname: mohu_flypy.yeying\nversion: "%s"\nsort: by_weight\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n\n' % datetime.date.today().strftime('%Y%m%d') + ''.join(kept))
put('mohu_flypy.extended.dict.yaml', '# Rime dictionary\n# encoding: utf-8\n\n---\nname: mohu_flypy.extended\nversion: "%s"\nsort: by_weight\nuse_preset_vocabulary: false\nimport_tables:\n  - mohu_flypy.yeying     # 夜莺 2.0 字词库\n...\n\n# 用户自定义词库\n# 此处可无码加词\n' % datetime.date.today().strftime('%Y%m%d'))
# 3b 可选"简词进整句"（默认不启用，不参与部署编译；启用方法见 使用说明）：简词增量词典 + 合并词典 + 编译垫片方案 + 含简词引擎词表
TODAY = datetime.date.today().strftime('%Y%m%d'); short = []
for l in open(SRC + '/yeying20_rime_short.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) == 3 and (f[0], f[1]) not in base_rows and ' ' not in f[1] and f[1].isalpha() and len(f[0]) >= 2: short.append(l if l.endswith('\n') else l + '\n')
put('mohu_flypy.yeying_short.dict.yaml', '# Rime dictionary\n# encoding: utf-8\n# 夜莺 2.0 简词（二字简词、三字词三码），只在启用"简词进整句"时使用。\n\n---\nname: mohu_flypy.yeying_short\nversion: "%s"\nsort: by_weight\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n\n' % TODAY + ''.join(short))
put('mohu_flypy.extended_short.dict.yaml', '# Rime dictionary\n# encoding: utf-8\n\n---\nname: mohu_flypy.extended_short\nversion: "%s"\nsort: by_weight\nuse_preset_vocabulary: false\nimport_tables:\n  - mohu_flypy.yeying\n  - mohu_flypy.yeying_short\n...\n' % TODAY)
core = open(UP + '/mohu_flypy_sentence_core.schema.yaml', encoding='utf-8').read()
for old, new, n in (('  schema_id: mohu_flypy_sentence_core\n', '  schema_id: mohu_flypy_short_core\n', 1), ('  dictionary: mohu_flypy.extended\n', '  dictionary: mohu_flypy.extended_short\n', 2), ('  prism: mohu_flypy\n', '  prism: mohu_flypy_short\n', 2),
                    ('  user_dict: mohu_flypy_sentence_tiger_prefix2\n', '  user_dict: mohu_flypy_short_core\n', 2)):
    assert core.count(old) == n, (old, core.count(old)); core = core.replace(old, new)
put('mohu_flypy_short_core.schema.yaml', core)
put('mohu/data/flypy/mohu_flypy_short.lexicon.txt', open(SRC + '/mohu/data/yeying20_short.lexicon.txt', 'rb').read())
put('简词进整句_启用方法.txt','# 默认整句里不混入简词（二字简词、三字词三码）。想让简词也参与整句：\n# 把本文件的 patch 内容并入用户目录的 mohu_flypy.custom.yaml（没有就把本文件改名为 mohu_flypy.custom.yaml），重新部署。\n# 关闭：删掉这几行，重新部署。\npatch:\n'
    '  schema/dependencies/+:\n    - mohu_flypy_short_core\n  smart/dictionary: mohu_flypy.extended_short\n  smart/prism: mohu_flypy_short\n  smart_static/dictionary: mohu_flypy.extended_short\n  smart_static/prism: mohu_flypy_short\n  tiger/lexicon: mohu/data/flypy/mohu_flypy_short.lexicon.txt\n')
# 4 原生引擎词表、辅码表、字频排名
lex = open(SRC + '/mohu/data/yeying20.lexicon.txt', 'rb').read(); put('mohu/data/flypy/mohu_flypy.lexicon.txt', lex)
rank = {}
for l in lex.decode('utf-8').split('\n'):
    f = l.split('\t')
    if len(f) >= 4 and len(f[1]) == 1 and f[3].isdigit() and int(f[3]) < 20001: rank.setdefault(f[1], int(f[3]))
put('lua/tiger_rank.txt', ''.join('%s\t%d\n' % (c, r) for c, r in sorted(rank.items(), key=lambda x: x[1])))
put('lua/zrmdb.txt', ''.join('%s\t%s\n' % (c, ' '.join(a)) for c, a in sorted(chars_aux.items())))
put('mohu/four_code_yield_pairs_flypy.txt', '# 夜莺的字词让位已经写在固定码表的次序里，这张表留空。\n')
# 5 拆分提示（Ctrl+i）：OpenCC 文本词典
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
cf = []
for c, d in sorted(D.items()):
    if len(c) != 1 or not d.get('根'): continue
    g = d['根']; first, last = g[0], g[-1]
    cf.append('%s\t〔%s·%s%s〕\n' % (c, ''.join(x['根'] if len(x['根']) == 1 else '{%s}' % x['根'] for x in g), first['键'], last['键']))
put('opencc/mohu_chaifen.txt', ''.join(cf))
put('opencc/mohu_chaifen.json', json.dumps({'name': 'chaifen', 'segmentation': {'type': 'mmseg', 'dict': {'type': 'text', 'file': 'mohu_chaifen.txt'}},
    'conversion_chain': [{'dict': {'type': 'group', 'dicts': [{'type': 'text', 'file': 'mohu_chaifen.txt'}]}}]}, ensure_ascii=False, indent=2))
if os.path.exists(OUT + '/opencc/mohu_chaifen.ocd2'): os.remove(OUT + '/opencc/mohu_chaifen.ocd2'); written.remove('opencc/mohu_chaifen.ocd2')
# 6 主翻译器补丁：固定码表按码表原序输出
p = 'lua/mohu_express_translator.lua'; s = open(UP + '/' + p, encoding='utf-8').read()
a1 = '    env.quick_code_indicator_skip_chars = env.engine.schema.config:get_bool("mohu/quick_code_indicator_skip_chars") or false\n'; assert s.count(a1) == 1
s = s.replace(a1, a1 + '    -- [夜莺] 固定码表按码表原序输出（字词让位由码表次序决定），不再先字后词。\n    env.fixed_table_order = env.engine.schema.config:get_bool("mohu/fixed_table_order") or false\n')
a2 = '    local chars = {}\n    local words = {}\n    local fixed_name = lexical_translator_name(env, contextual.get_runtime(env))\n    for cand in translation:iter() do\n        bind_lexical_provenance(env, cand, "fixed", fixed_name)\n        local cand_len = utf8.len(cand.text)\n'; assert s.count(a2) == 1
s = s.replace(a2, a2 + '        if env.fixed_table_order then\n            -- [夜莺] 原序直出\n            if cand_len == 1 then\n                if include_chars and (char_filter == nil or char_filter(cand)) then top.output_char_from_fixed(env, cand) end\n'
              '            elseif include_word and include_word(cand_len) then\n                top.output_word_from_fixed(env, cand, is_sentence_making)\n            end\n            goto continue\n        end\n')
a3 = "            table.insert(words, cand)\n        end\n    end\n    for _, cand in ipairs(chars) do\n"; assert s.count(a3) == 1
s = s.replace(a3, "            table.insert(words, cand)\n        end\n        ::continue::\n    end\n    for _, cand in ipairs(chars) do\n")
put(p, s)
# 7 方案：改名、固词默认开、用户词典独立、开原序选项
p = 'mohu_flypy.schema.yaml'; s = open(UP + '/' + p, encoding='utf-8').read()
def rep(old, new, n=1):
    global s; assert s.count(old) == n, (old, s.count(old)); s = s.replace(old, new)
rep('  name: 魔虎·小鹤\n', '  name: 夜莺主力\n')
# 反查：反引号引导的虎码反查换成夜莺反查（`双拼 或 ~全拼 → 字 + 拆分与全部编码；F2 查当前编码）；ohm 引导的虎码反查原样保留
rep('    - reverse_lookup_translator@reverse_tiger_backtick\n', '    - lua_translator@*yeying20_lookup      # [夜莺] `双拼 / ~全拼 反查\n')
rep('    reverse_tiger_backtick: "^`[a-z]+$"\n', '    yeying20_lookup: "^([`~][a-z]*|~~[a-z]*)$"   # [夜莺]\n')
rep('    - lua_processor@*option_sync\n    - key_binder\n', '    - lua_processor@*option_sync\n    - lua_processor@*yeying20_lookup_key   # [夜莺] F2\n    - key_binder\n')
for fn in ('yeying20_lookup.lua', 'yeying20_lookup_key.lua', 'yeying20_lookup_data.lua'): put('lua/' + fn, open(SRC + '/lua/' + fn, 'rb').read())
rep('    基于小鹤双拼和虎码12字根做辅码的魔虎整句输入方案。\n', '    夜莺 2.0（小鹤双拼 + 首根键 + 末根键）码表与词库，运行在魔虎整句方案的功能层与 V5 模型之上。\n')
rep('    - 魔虎方案制作：晴\n', '    - 魔虎方案制作：晴\n    - 夜莺 2.0 码表与词库：losWater\n')
rep('    states: [ 动词, 固词 ] # 「固词」表示「固顶词」\n', '    states: [ 动词, 固词 ] # 「固词」表示「固顶词」\n    reset: 1   # [夜莺] 默认固词：四码按夜莺码表出字词\n')
rep('    states: [ 常用字, 全字集 ]\n', '    states: [ 常用字, 全字集 ]\n    reset: 1   # [夜莺] 默认全字集：扩展字本来就排在各码位末尾，不挡路；Ctrl+x 可切回常用字\n')
rep('  user_dict: mohu_flypy_tiger_prefix2\n', '  user_dict: yeying20_mohu\n')
rep('  inject_prioritize: "any"', '  fixed_table_order: true     # [夜莺] 固定码表按码表原序输出\n  inject_prioritize: "any"')
rep('  four_code_char_yield_exempt: 暮\n', '  four_code_char_yield_exempt: ""\n')
put(p, s)
put('default.custom.yaml', 'patch:\n  schema_list:\n    - schema: mohu_flypy\n  menu/page_size: 5\n')
if os.path.exists(OUT + '/说明.md'): os.remove(OUT + '/说明.md')      # 试验版时期本脚本生成的旧说明
put('使用说明.md', '''# 夜莺 2.0 · Rime 主力版

码表、词库、拆分是夜莺 2.0 的；整句引擎、V5 模型和全部功能来自魔虎（rime-mohu）。方案选单里叫「夜莺主力」。

## 安装（Windows 小狼毫）

1. 把本包全部文件解压到 Rime 用户目录（小狼毫托盘图标右键 →「用户文件夹」）。包里已带模型 `mohu/model/mohu-sentence-ngram-v5.bin`。
2. 包里的 `default.custom.yaml` 会把方案列表设为只有「夜莺主力」。你自己已有这个文件的话，不要覆盖，把 `- schema: mohu_flypy` 加进你的 schema_list。
3. 重新部署，Ctrl+` 或 F4 选「夜莺主力」。

原生整句引擎只有 Windows 和 macOS 版；手机请用「Rime 手机版」。

## 和夜莺码表的关系

- 一到四码严格按夜莺码表的候选次序出字词（默认"固词"模式，Ctrl+Shift+G 可切到魔虎原本的"动词"模式）。
- 超过四码、或四码后继续打，就是整句。辅码（首根键、末根键）可以随时补在任一音节后面筛字。
- 默认全字集，7391 个扩展字排在各码位末尾；Ctrl+x 切到只出常用字。

## 常用按键

- Ctrl+i：拆分提示（夜莺拆分）。Ctrl+.：拼音提示。Ctrl+u：Unicode。Ctrl+q：emoji。
- 反查：`` ` `` 加双拼、或 `~` 加全拼，列出同音字及其拆分和全部编码；打到一半按 F2 查当前编码上的字。`ohm` 加虎码是魔虎自带的虎码反查。
- 置顶、加词、隐藏候选、候选管理（`==`）用魔虎自带的一套，见魔虎文档。
- 日期 `orq`、时间 `osj`、大写数字 `S123`、Unicode `U9b54`。

## 简词进整句（默认关）

默认整句里不混入二字简词、三字词三码。想打开，看包里的 `简词进整句_启用方法.txt`。

## 许可与出处

- 魔虎：https://github.com/fcxxxz/rime-mohu ，GPL v3，全文见 `LICENSE`。本包对魔虎的改动只有三处：`lua/mohu_express_translator.lua` 增加"固定码表按码表原序输出"选项；`mohu_flypy.schema.yaml` 改名、改默认开关、接入夜莺反查；数据文件（码表、词库、词表、辅码、字频、拆分）换成夜莺的。上游的七份大词库未随包分发。
- 夜莺 2.0：https://github.com/losWater/Nightingale 。
- 本包整体按 GPL v3 分发。由 work/夜莺2.0/127_魔虎基座试验/build.py 生成。
''')
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '文件': sorted(set(written))}, open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('固定码表 %d 条；整句词典 %d 行；词表 %d 行；辅码 %d 字；字频排名 %d 字；拆分 %d 字；文件 %d 个' % (len(rows), len(kept), lex.count(b'\n'), len(chars_aux), len(rank), len(cf), len(set(written))))
