# -*- coding: utf-8 -*-
"""Rime 主力版「夜莺主力」（魔虎基座）。2026-09-17 第三版：全部改用 yeying 名字，可与魔虎原版装在同一个用户目录。
来历：群友指出包里全是 mohu_ 文件、且会覆盖魔虎原版；你裁定"要改名，不能直接叫魔虎；但声明要有，这确实是魔虎作者的成果"。
做法（全部由本脚本从上游包机械生成，上游更新后重跑即可；锚点对不上会 assert）：
  ① 夜莺自己的：方案 yeying_flypy（显示名 夜莺主力）、固定码表、整句词典、引擎词表、辅码、字频、拆分、反查——数据来自 106 的中间产物。
  ② 魔虎的功能脚本：lua/mohu*.lua、option_*.lua 逐个改名为 lua/yeying_*.lua 的独立副本（模块名、用户库名、数据路径随之改），每个文件头注明原文件名与出处；
     这样两套脚本在同一个 Rime 进程里各自有自己的引擎句柄和缓存，互不干扰。功能改动只有一处：主翻译器"固定码表按码表原序输出"。
  ③ 魔虎的引擎、语义模型原样放进 yeying/（运行时、模型各自一份，不与魔虎共用文件）；配置 mohu.yaml、mohu_defs.yaml、符号表、字集表、OpenCC 配置改名为 yeying_*。
  ④ 不带：魔虎自己的方案与七份大词库、虎码反查、皮肤编辑器、同步助手、default.yaml、macOS 动态库。
产物 Rime_夜莺主力/ 只由本脚本生成，重跑时按上次的 生成清单.json 清理。"""
import io, sys, os, re, json, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
UP = H + '/upstream/pkg'; SRC = W + '/106_全平台导出/Rime_主力版'; OUT = H + '/Rime_夜莺主力'; TODAY = datetime.date.today().strftime('%Y%m%d')
MOHU = 'https://github.com/fcxxxz/rime-mohu'; written = []
def put(rel, data):
    p = OUT + '/' + rel; os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data if isinstance(data, bytes) else data.encode('utf-8')); written.append(rel)
def up(rel, binary=False): return open(UP + '/' + rel, 'rb').read() if binary else open(UP + '/' + rel, encoding='utf-8').read()
class Doc:
    def __init__(self, name, text): self.name, self.s = name, text
    def rep(self, old, new, n=1):
        assert self.s.count(old) == n, (self.name, old[:60], self.s.count(old)); self.s = self.s.replace(old, new); return self
    def cut(self, start, end):
        """删掉从 start 起、到 end（不含）为止的一段"""
        i = self.s.index(start); j = self.s.index(end, i + len(start)); self.s = self.s[:i] + self.s[j:]; return self
mf = OUT + '/生成清单.json'
if os.path.exists(mf):
    for rel in json.load(open(mf, encoding='utf-8'))['文件']:
        if os.path.isfile(OUT + '/' + rel): os.remove(OUT + '/' + rel)

# ── ② 魔虎功能脚本 → yeying_ 独立副本 ─────────────────────────────────────────
SKIP_LUA = {'rime_skin_editor.lua', 'mohu_skin_command.lua'}
HEAD = '-- 【出处】本文件是魔虎（rime-mohu，作者 晴，%s ，GPL v3；魔虎基于 ksqsf 的魔然）的 lua/%%s 的改名副本。\n-- 为了能与魔虎原版装在同一个 Rime 用户目录，夜莺把模块名、用户库名、数据路径改成了 yeying 前缀；功能代码是魔虎原作%%s。\n' % MOHU
newname = lambda fn: 'yeying_' + fn
REQ = re.compile(r'''(require\s*[(,]\s*["'])(mohu(?:_\w+)?|option_state|option_sync)(["'])''')
for fn in sorted(os.listdir(UP + '/lua')):
    if not fn.endswith('.lua') or fn in SKIP_LUA: continue
    d = Doc(fn, up('lua/' + fn)); d.s = REQ.sub(lambda m: m.group(1) + 'yeying_' + m.group(2) + m.group(3), d.s); extra = ''
    if fn == 'mohu.lua':
        d.rep("Module.open_rime_file('lua' .. pathsep .. 'zrmdb.txt', pathsep)", "Module.open_rime_file('yeying' .. pathsep .. 'yeying_aux.txt', pathsep)")
        d.rep("Module.open_rime_file('lua' .. pathsep .. 'tiger_rank.txt', pathsep)", "Module.open_rime_file('yeying' .. pathsep .. 'yeying_char_rank.txt', pathsep)")
        d.rep("        'mohu' .. pathsep .. 'four_code_yield_pairs_' .. variant .. '.txt',", "        'yeying' .. pathsep .. 'four_code_yield_pairs_' .. variant .. '.txt',")
    if fn == 'mohu_runtime.lua': d.rep('local root = join(base, "mohu")', 'local root = join(base, "yeying")')
    if fn == 'mohu_tiger_sentence.lua':
        d.rep('  if value == "mohu" or value:sub(1, #"mohu/") == "mohu/" then\n    return root .. value:sub(#"mohu" + 1)', '  if value == "yeying" or value:sub(1, #"yeying/") == "yeying/" then\n    return root .. value:sub(#"yeying" + 1)')
    if fn == 'mohu_pin.lua': d.rep('pcall(LevelDb, "mohu_pin")', 'pcall(LevelDb, "yeying_pin")')
    if fn == 'mohu_candidate_override.lua':
        d.rep('local deleted_user_property = "mohu_user_deleted_phrases"', 'local deleted_user_property = "yeying_user_deleted_phrases"').rep('    return "mohu_user_deleted_"', '    return "yeying_user_deleted_"')
        d.rep('config:get_string("mohu/candidate_override/db_name") or "mohu_candidate_override"', 'config:get_string("mohu/candidate_override/db_name") or "yeying_candidate_override"')
    if fn == 'mohu_charset_filter.lua': d.rep('ReverseLookup("mohu_charset")', 'ReverseLookup("yeying_charset")')
    if fn == 'option_state.lua': d.rep('"option_state_data.lua"', '"yeying_option_state_data.lua"')
    if fn == 'mohu_express_translator.lua':
        extra = '；唯一的功能改动：增加 mohu/fixed_table_order 选项（固定码表按码表原序输出，标 [夜莺] 处）'
        a1 = '    env.quick_code_indicator_skip_chars = env.engine.schema.config:get_bool("mohu/quick_code_indicator_skip_chars") or false\n'
        d.rep(a1, a1 + '    -- [夜莺] 固定码表按码表原序输出（夜莺的字词让位写在码表次序里），不再先字后词；开启后等同常驻"固词"。\n    env.fixed_table_order = env.engine.schema.config:get_bool("mohu/fixed_table_order") or false\n')
        d.rep('    local inflexible = env.engine.context:get_option("inflexible")\n', '    local inflexible = env.fixed_table_order or env.engine.context:get_option("inflexible")   -- [夜莺]\n')
        a2 = '    local chars = {}\n    local words = {}\n    local fixed_name = lexical_translator_name(env, contextual.get_runtime(env))\n    for cand in translation:iter() do\n        bind_lexical_provenance(env, cand, "fixed", fixed_name)\n        local cand_len = utf8.len(cand.text)\n'
        d.rep(a2, a2 + '        if env.fixed_table_order then\n            -- [夜莺] 原序直出\n            if cand_len == 1 then\n                if include_chars and (char_filter == nil or char_filter(cand)) then top.output_char_from_fixed(env, cand) end\n'
                  '            elseif include_word and include_word(cand_len) then\n                top.output_word_from_fixed(env, cand, is_sentence_making)\n            end\n            goto continue\n        end\n')
        d.rep("            table.insert(words, cand)\n        end\n    end\n    for _, cand in ipairs(chars) do\n", "            table.insert(words, cand)\n        end\n        ::continue::\n    end\n    for _, cand in ipairs(chars) do\n")
    put('lua/' + newname(fn), HEAD % (fn, extra) + d.s)
for fn in ('yeying20_lookup.lua', 'yeying20_lookup_key.lua', 'yeying20_lookup_data.lua'): put('lua/' + fn, open(SRC + '/lua/' + fn, 'rb').read())     # 夜莺反查（夜莺自己的）

# ── ③ 魔虎的引擎、语义模型、配置 → yeying 名下 ───────────────────────────────
for fn in sorted(os.listdir(UP + '/mohu/runtime')):
    if not fn.endswith('.dylib'): put('yeying/runtime/' + fn, up('mohu/runtime/' + fn, True))
for fn in sorted(os.listdir(UP + '/mohu_semantic')): put('yeying/semantic/' + fn, up('mohu_semantic/' + fn, True))
put('yeying/model/请把模型放在这里.txt', '整句模型 mohu-sentence-ngram-v5.bin（魔虎 V5 模型，来自 %s 的 Release）放在本目录。发布包里已带。\n' % MOHU)
put('yeying/config/说明.txt', '运行时这里会生成 user-ngram.snapshot（你的整句调频记录）。更新夜莺主力时不要删它。\n')
NOTE = '# 【出处】魔虎（rime-mohu，%s ，GPL v3）的 %%s 的改名副本，为与魔虎原版共存而改名%%s。\n' % MOHU
d = Doc('mohu.yaml', up('mohu.yaml')); d.s = d.s.replace('mohu_defs:/', 'yeying_mohu_defs:/')
d.rep('    __append:\n      __patch:\n        - yeying_mohu_defs:/fly/qx_qo  # ZRM-SPECIFIC\n        - yeying_mohu_defs:/fly/xq_xo  # ZRM-SPECIFIC\n        - yeying_mohu_defs:/fly/wz_wk  # ZRM-SPECIFIC\n',
      '    # [夜莺] 去掉了自然码专用的三条飞键（qx→qo、xq→xo、wz→wk）。要加模糊音：取消下面三行和所需条目的注释。\n    # __append:\n    #   __patch:\n')
d.rep('      - erase/^pp$/                     # ZRM-SPECIFIC\n', '')          # 小鹤里 pp=pie 是正常音节
put('yeying_mohu.yaml', NOTE % ('mohu.yaml', '；去掉了自然码专用的三条飞键和 pp 音节屏蔽') + d.s)
put('yeying_mohu_defs.yaml', NOTE % ('mohu_defs.yaml', '') + up('mohu_defs.yaml'))
put('yeying_symbols.yaml', NOTE % ('symbols.yaml', '') + up('symbols.yaml'))
d = Doc('mohu_charset.dict.yaml', up('mohu_charset.dict.yaml')).rep('name: mohu_charset\n', 'name: yeying_charset\n'); put('yeying_charset.dict.yaml', NOTE % ('mohu_charset.dict.yaml', '') + d.s)
put('yeying_charset.schema.yaml', NOTE % ('mohu_charset.schema.yaml', '') + Doc('cs', up('mohu_charset.schema.yaml')).s.replace('mohu_charset', 'yeying_charset'))
for base in ('emoji', 'pinyinhint'):
    put('opencc/yeying_%s.json' % base, up('opencc/mohu_%s.json' % base).replace('mohu_%s.ocd2' % base, 'yeying_%s.ocd2' % base)); put('opencc/yeying_%s.ocd2' % base, up('opencc/mohu_%s.ocd2' % base, True))
put('LICENSE', up('LICENSE', True))

# ── ① 夜莺自己的数据 ─────────────────────────────────────────────────────────
fixed = [l.rstrip('\n').split('\t') for l in open(SRC + '/yeying20_rime_fixed.dict.yaml', encoding='utf-8') if l.count('\t') == 2]
by = collections.defaultdict(list)
for t, c, w in fixed: by[c].append((-int(w), len(by[c]), t))
rows = [(t, c) for c in sorted(by) for _, _, t in sorted(by[c])]
def fixed_dict(name):
    return ('# Rime dictionary\n# encoding: utf-8\n# 夜莺 2.0 固定码表（字词定稿次序）。由 127 build.py 生成，勿手改。\n\n---\nname: %s\nversion: "%s"\nsort: original\ncolumns:\n  - text\n  - code\n  - stem\n  - weight\n  - comment\n'
            'encoder:\n  rules:\n    - length_equal: 2\n      formula: "AaAbBaBb"\n    - length_equal: 3\n      formula: "AaBaCa"\n    - length_in_range: [4, 32]\n      formula: "AaBaCaZa"\nimport_tables:\n  - yeying_fixed.symbols\n...\n\n') % (name, TODAY) + ''.join('%s\t%s\n' % r for r in rows)
put('yeying_flypy_fixed.dict.yaml', fixed_dict('yeying_flypy_fixed')); put('yeying_flypy_fixed_legacy.dict.yaml', fixed_dict('yeying_flypy_fixed_legacy'))
STUB = ('# 仅用于编译码表，不进方案选单。\nschema:\n  schema_id: %s\n  version: "%s"\n\nengine:\n  translators:\n    - table_translator@translator\n\nspeller:\n  alphabet: abcdefghijklmnopqrstuvwxyz;\n  max_code_length: 4\n\n'
        'translator:\n  dictionary: %s\n  enable_completion: false\n  enable_sentence: false\n  enable_user_dict: false\n')
for n in ('yeying_flypy_fixed', 'yeying_flypy_fixed_legacy'): put(n + '.schema.yaml', STUB % (n, TODAY, n))
sym = up('mohu_fixed.symbols.dict.yaml'); head, body = sym.split('\n...\n', 1)      # 魔虎的分号快符（;w → ？ 等）；o 开头的符号码会挤进夜莺码位，不收
put('yeying_fixed.symbols.dict.yaml', NOTE % ('mohu_fixed.symbols.dict.yaml', '；只保留分号引导的符号') + head.replace('name: mohu_fixed', 'name: yeying_fixed') + '\n...\n\n' + '\n'.join(l for l in body.split('\n') if l.count('\t') >= 1 and l.split('\t')[1].startswith(';')) + '\n')
syl = re.compile(r'^[a-z]{2};[a-z]{2}$'); kept = []; chars_aux = collections.defaultdict(list); base_rows = set()
for l in open(SRC + '/yeying20_rime.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) != 3: continue
    ss = f[1].split(' '); whole = len(ss) == 1 and ss[0].isalpha() and ss[0].islower() and len(f[0]) >= 2      # 多字词的整词规则码（万变不离其宗 wbbz），整句里当一个音节用
    if all(syl.match(s) for s in ss) or whole:
        kept.append(l if l.endswith('\n') else l + '\n'); base_rows.add((f[0], f[1]))
        if len(ss) == 1 and len(f[0]) == 1 and ss[0][3:] not in chars_aux[f[0]]: chars_aux[f[0]].append(ss[0][3:])
short = []
for l in open(SRC + '/yeying20_rime_short.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) == 3 and (f[0], f[1]) not in base_rows and ' ' not in f[1] and f[1].isalpha() and len(f[0]) >= 2: short.append(l if l.endswith('\n') else l + '\n')
DH = '# Rime dictionary\n# encoding: utf-8\n# %s\n\n---\nname: %s\nversion: "' + TODAY + '"\nsort: by_weight\nuse_preset_vocabulary: false\n%s...\n\n'
put('yeying_flypy.words.dict.yaml', DH % ('夜莺 2.0 字词（双拼;首末根键）', 'yeying_flypy.words', 'columns: [text, code, weight]\n') + ''.join(kept))
put('yeying_flypy.shortwords.dict.yaml', DH % ('夜莺 2.0 简词，只在启用"简词进整句"时使用', 'yeying_flypy.shortwords', 'columns: [text, code, weight]\n') + ''.join(short))
put('yeying_flypy.extended.dict.yaml', DH % ('夜莺主力整句词典', 'yeying_flypy.extended', 'import_tables:\n  - yeying_flypy.words\n') + '# 此处可无码加词\n')
put('yeying_flypy.extended_short.dict.yaml', DH % ('夜莺主力整句词典（含简词）', 'yeying_flypy.extended_short', 'import_tables:\n  - yeying_flypy.words\n  - yeying_flypy.shortwords\n'))
ALG = ('yeying_generate_code:      # 与魔虎 generate_code 相同，去掉了自然码专用的 pp 屏蔽\n  __append:\n    - derive|^(.+);(\\w)(\\w)$|$1$2$3o|\n    - derive|^(.+);(\\w)(\\w)$|$1$2$3/|\n    - derive|^(.+);(\\w)(\\w)$|$1$2/|\n'
       '    - abbrev/^(.+);(\\w)(\\w)$/$1$2$3/\n    - derive/^(.+);(\\w)(\\w)$/$1$2/\n    - derive/^(.+);(\\w)(\\w)$/$1/\n    - erase/^(.+);(.+)$/\n')
CORE = ('# 仅用于编译整句词典与棱镜，不进方案选单。\nschema:\n  schema_id: %s\n  version: "' + TODAY + '"\n\nengine:\n  translators:\n    - script_translator@translator\n\nspeller:\n  alphabet: \'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/=;\'\n  delimiter: " \'"\n'
        '  algebra:\n    __patch:\n      - yeying_mohu:/algebra/user_force_top?\n      - yeying_flypy_defs:/yeying_generate_code\n      - yeying_mohu:/algebra/user_sentence_bottom?\n      - yeying_mohu:/algebra/user_force_bottom?\n\ntranslator:\n  dictionary: %s\n  prism: %s\n  enable_user_dict: false\n')
put('yeying_flypy_core.schema.yaml', CORE % ('yeying_flypy_core', 'yeying_flypy.extended', 'yeying_flypy'))
put('yeying_flypy_short_core.schema.yaml', CORE % ('yeying_flypy_short_core', 'yeying_flypy.extended_short', 'yeying_flypy_short'))
lex = open(SRC + '/mohu/data/yeying20.lexicon.txt', 'rb').read(); put('yeying/data/yeying_flypy.lexicon.txt', lex)
put('yeying/data/yeying_flypy_short.lexicon.txt', open(SRC + '/mohu/data/yeying20_short.lexicon.txt', 'rb').read())
rank = {}
for l in lex.decode('utf-8').split('\n'):
    f = l.split('\t')
    if len(f) >= 4 and len(f[1]) == 1 and f[3].isdigit() and int(f[3]) < 20001: rank.setdefault(f[1], int(f[3]))
put('yeying/yeying_char_rank.txt', ''.join('%s\t%d\n' % (c, r) for c, r in sorted(rank.items(), key=lambda x: x[1])))
put('yeying/yeying_aux.txt', ''.join('%s\t%s\n' % (c, ' '.join(a)) for c, a in sorted(chars_aux.items())))
put('yeying/four_code_yield_pairs_flypy.txt', '# 夜莺的字词让位已经写在固定码表的次序里，这张表留空。\n')
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read(); D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]; cf = []
for c, x in sorted(D.items()):
    if len(c) == 1 and x.get('根'): g = x['根']; cf.append('%s\t〔%s·%s%s〕\n' % (c, ''.join(r['根'] if len(r['根']) == 1 else '{%s}' % r['根'] for r in g), g[0]['键'], g[-1]['键']))
put('opencc/yeying_chaifen.txt', ''.join(cf))
put('opencc/yeying_chaifen.json', json.dumps({'name': 'yeying_chaifen', 'segmentation': {'type': 'mmseg', 'dict': {'type': 'text', 'file': 'yeying_chaifen.txt'}}, 'conversion_chain': [{'dict': {'type': 'group', 'dicts': [{'type': 'text', 'file': 'yeying_chaifen.txt'}]}}]}, ensure_ascii=False, indent=2))
put('yeying_flypy_custom_phrases.txt', '# Rime table\n# coding: utf-8\n#@db/db_name\tyeying_flypy_custom_phrases\n#@db/db_type\ttabledb\n#\n# 夜莺主力 · 自定义短语。修改后重新部署生效。自定义短语总是排在主词库之前。\n# 每行格式：文字 <tab> 编码 <tab> 权重\n#\n')

# ── 方案 yeying_flypy ────────────────────────────────────────────────────────
d = Doc('schema', up('mohu_flypy.schema.yaml'))
d.s = d.s.replace('@*mohu', '@*yeying_mohu').replace('@*option_sync', '@*yeying_option_sync').replace('mohu:/', 'yeying_mohu:/')
d.rep('  schema_id: mohu_flypy\n', '  schema_id: yeying_flypy\n').rep('  name: 魔虎·小鹤\n', '  name: 夜莺主力\n')
d.rep('    - 魔虎方案制作：晴\n', '    - 魔虎方案制作：晴（本方案的整句引擎、模型与全部功能脚本的原作者）\n    - 夜莺 2.0 码表、词库与本改编：losWater\n')
d.rep('    基于小鹤双拼和虎码12字根做辅码的魔虎整句输入方案。\n', '    夜莺 2.0（小鹤双拼 + 首根键 + 末根键）的 Rime 主力方案。\n    【声明】本方案改编自魔虎（rime-mohu，作者 晴，%s ，GPL v3；魔虎基于 ksqsf 的魔然）。\n'
      '    整句引擎、V5 模型、全部功能脚本与配置是魔虎作者的成果；夜莺换上了自己的码表、词库、辅码与拆分，并为了能与魔虎原版共存而把文件改成 yeying 名字。详见 使用说明.md。\n' % MOHU)
d.rep('    - mohu_flypy_fixed\n    # 部署只会编译一级依赖的码表，因此 legacy 码表也需直接列出\n    - mohu_flypy_fixed_legacy\n', '    - yeying_flypy_fixed\n    - yeying_flypy_fixed_legacy\n')
d.cut('    # mohu_flypy_sentence_core 在发布包中', '    - mohu_flypy_sentence_core\n').rep('    - mohu_flypy_sentence_core\n    - mohu_charset\n    - tiger\n', '    - yeying_flypy_core        # 编译整句词典与棱镜用的垫片\n    - yeying_charset\n')
d.cut('  - name: inflexible\n', '  - name: chaifen\n')                                   # 夜莺固定码表常驻原序输出，不需要 动词/固词 开关
d.rep('    states: [ 常用字, 全字集 ]\n', '    states: [ 常用字, 全字集 ]\n    reset: 1   # [夜莺] 默认全字集：扩展字排在各码位末尾，不挡路；Ctrl+x 切换\n')
d.rep('    - lua_processor@*yeying_mohu_skin_command\n', '').rep('    - lua_processor@*yeying_option_sync\n    - key_binder\n', '    - lua_processor@*yeying_option_sync\n    - lua_processor@*yeying20_lookup_key   # [夜莺] F2\n    - key_binder\n')
d.rep('    - reverse_lookup_translator@reverse_tiger\n    - reverse_lookup_translator@reverse_tiger_backtick\n', '    - lua_translator@*yeying20_lookup      # [夜莺] `双拼 / ~全拼 反查\n')
d.rep('      - yeying_mohu:/algebra/generate_code\n', '      - yeying_flypy_defs:/yeying_generate_code\n')
d.rep('  dictionary: mohu_flypy.extended\n', '  dictionary: yeying_flypy.extended\n', 2).rep('  prism: mohu_flypy\n', '  prism: yeying_flypy\n', 2).rep('  user_dict: mohu_flypy_tiger_prefix2\n', '  user_dict: yeying_flypy\n')
d.rep('  dictionary: mohu_flypy_fixed\n', '  dictionary: yeying_flypy_fixed\n').rep('  dictionary: mohu_flypy_fixed_legacy\n', '  dictionary: yeying_flypy_fixed_legacy\n', 2).rep('  user_dict: mohu_flypy_custom_phrases\n', '  user_dict: yeying_flypy_custom_phrases\n')
d.rep('  semantic_model: mohu_semantic/mohu_semantic.onnx\n  semantic_vocab: mohu_semantic/vocab.tsv\n', '  semantic_model: yeying/semantic/mohu_semantic.onnx\n  semantic_vocab: yeying/semantic/vocab.tsv\n')
d.rep('  model: mohu/model\n', '  model: yeying/model\n').rep('  lexicon: mohu/data/flypy/mohu_flypy.lexicon.txt\n', '  lexicon: yeying/data/yeying_flypy.lexicon.txt\n').rep('  user_model_snapshot: mohu/config/user-ngram.snapshot\n', '  user_model_snapshot: yeying/config/user-ngram.snapshot\n')
d.rep('  opencc_config: mohu_chaifen.json\n', '  opencc_config: yeying_chaifen.json\n').rep('  opencc_config: mohu_pinyinhint.json\n', '  opencc_config: yeying_pinyinhint.json\n').rep('  opencc_config: mohu_emoji.json\n', '  opencc_config: yeying_emoji.json\n')
d.cut('reverse_tiger:\n', 'punctuator:\n').rep('  import_preset: symbols\n', '  import_preset: yeying_symbols\n')
d.rep('      - yeying_mohu:/key_bindings/mohu_toggle_inflexible\n', '')
d.rep('    # 反查\n    reverse_tiger: "^ohm[a-z]+$"\n    reverse_tiger_backtick: "^`[a-z]+$"\n', '    # [夜莺] 反查\n    yeying20_lookup: "^([`~][a-z]*|~~[a-z]*)$"\n')
d.rep('  inject_prioritize: "any"', '  fixed_table_order: true     # [夜莺] 固定码表按码表原序输出（常驻）\n  inject_prioritize: "any"').rep('  four_code_char_yield_exempt: 暮\n', '  four_code_char_yield_exempt: ""\n')
d.rep('  candidate_override:\n    __include: yeying_mohu:/candidate_override\n', '  candidate_override:\n    __include: yeying_mohu:/candidate_override\n    db_name: yeying_candidate_override\n')
left = [l for l in d.s.split('\n') if not l.lstrip().startswith('#') and re.search(r'mohu_flypy|mohu_zrm|reverse_tiger|\btiger\.|: tiger\b', l) and 'candidate_type' not in l]; assert not left, left[:8]
put('yeying_flypy.schema.yaml', '# 【出处】改编自魔虎（rime-mohu，%s ，GPL v3）的 mohu_flypy.schema.yaml；标 [夜莺] 处为改动。\n' % MOHU + d.s)
put('yeying_flypy_defs.yaml', '# 夜莺主力的拼写运算（主方案与两个编译垫片共用，保证棱镜一致）\n' + ALG)
put('default.custom.yaml', 'patch:\n  schema_list:\n    - schema: yeying_flypy      # 夜莺主力\n  menu/page_size: 5\n')
put('简词进整句_启用方法.txt', '默认整句里不混入简词（二字简词、三字词三码）。想让简词也参与整句：\n把下面 patch 的内容并入用户目录的 yeying_flypy.custom.yaml（没有就新建这个文件，整段贴进去），重新部署。关闭：删掉，重新部署。\n\npatch:\n'
    '  schema/dependencies/+:\n    - yeying_flypy_short_core\n  smart/dictionary: yeying_flypy.extended_short\n  smart/prism: yeying_flypy_short\n  smart_static/dictionary: yeying_flypy.extended_short\n  smart_static/prism: yeying_flypy_short\n  tiger/lexicon: yeying/data/yeying_flypy_short.lexicon.txt\n')
DECL = ('【声明】夜莺主力的整句引擎和功能来自魔虎（rime-mohu）\n\n- 魔虎：作者 晴，%s ，GPL v3。魔虎又基于 ksqsf 的魔然（rime-moran）。\n'
        '- 本包里的整句引擎（yeying/runtime 下的 libtigerengine 等）、V5 整句模型、语义模型，以及 lua/yeying_mohu*.lua、lua/yeying_option_*.lua、yeying_mohu.yaml、yeying_mohu_defs.yaml、yeying_symbols.yaml、yeying_charset、opencc 的 emoji 与拼音提示，都是魔虎作者的成果。\n'
        '- 这些文件改成 yeying 名字，只是为了能和魔虎原版装在同一个 Rime 用户目录里互不覆盖；每个文件开头都注明了它在魔虎里的原文件名。功能代码只改了一处（主翻译器加"固定码表按码表原序输出"选项）。\n'
        '- 夜莺自己的部分：方案 yeying_flypy 的改编、固定码表、整句词典、引擎词表、辅码、字频、拆分提示、反查。\n- 没有带上的魔虎功能：虎码反查、皮肤编辑器、同步助手。想用它们，或者想用虎码辅码的原版，请直接安装魔虎。喜欢这些功能，请去给魔虎点星。\n'
        '- 本包整体按 GPL v3 分发，许可全文见 LICENSE。\n') % MOHU
put('【声明】整句引擎与功能来自魔虎rime-mohu.txt', DECL)
put('使用说明.md', '''# 夜莺 2.0 · Rime 主力版「夜莺主力」

> **声明：本方案改编自魔虎（rime-mohu，作者 晴，%s ，GPL v3；魔虎基于 ksqsf 的魔然）。**
> 整句引擎、V5 模型和全部功能脚本是魔虎作者的成果；夜莺换上了自己的码表、词库、辅码与拆分。
> 包里的文件用 yeying 名字，是为了能和魔虎原版装在一起互不覆盖；每个改名文件的开头都写着它在魔虎里的原名。喜欢这些功能，请去给魔虎点星。

## 安装（Windows 小狼毫）

1. 把本包全部文件解压到 Rime 用户目录（小狼毫托盘图标右键 →「用户文件夹」）。包里已带模型 `yeying/model/mohu-sentence-ngram-v5.bin`。
2. 包里的 `default.custom.yaml` 会把方案列表设为只有「夜莺主力」。你自己已有这个文件的话不要覆盖，把 `- schema: yeying_flypy` 加进你的 schema_list。
3. 重新部署，Ctrl+` 或 F4 选「夜莺主力」。

可以和魔虎原版装在同一个用户目录：两边的方案、词库、脚本、引擎、用户数据都是各自一份。原生整句引擎只有电脑版；手机请用「Rime 手机版」。

## 和夜莺码表的关系

- 一到四码严格按夜莺码表的候选次序出字词。超过四码、或四码后继续打，就是整句；辅码（首根键、末根键）可以补在任一音节后面筛字。
- 默认全字集，7391 个扩展字排在各码位末尾；Ctrl+x 切到只出常用字。

## 常用按键

- Ctrl+i：拆分提示（夜莺拆分）。Ctrl+.：拼音提示。Ctrl+u：Unicode。Ctrl+q：emoji。
- 反查：`` ` `` 加双拼、或 `~` 加全拼，列出同音字及其拆分和全部编码；打到一半按 F2 查当前编码上的字。
- 分号快符（`;w` → ？ 等）、置顶、加词、隐藏候选、候选管理（`==`）、日期 `orq`、时间 `osj`、大写数字 `S123`、Unicode `U9b54`：都是魔虎的功能，用法见魔虎文档。

## 简词进整句（默认关）

见包里的 `简词进整句_启用方法.txt`。

## 改动清单（相对魔虎）

1. 数据全部换成夜莺 2.0 的：固定码表、整句词典、引擎词表、辅码、字频、拆分提示。魔虎自己的方案和七份大词库不在包里。
2. 功能代码一处：主翻译器增加"固定码表按码表原序输出"选项并常驻开启（夜莺的字词让位写在码表次序里），因此去掉了"动词/固词"开关。
3. 反引号反查换成夜莺反查；去掉虎码反查、皮肤编辑器、同步助手；去掉自然码专用的三条飞键和 pp 音节屏蔽。
4. 文件、模块、用户库、数据目录改成 yeying 名字，以便与魔虎原版共存。

夜莺 2.0：https://github.com/losWater/Nightingale 。本包整体按 GPL v3 分发（见 LICENSE）。由 work/夜莺2.0/127_魔虎基座试验/build.py 生成。
''' % MOHU)
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '文件': sorted(set(written))}, open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('固定码表 %d 条；整句词典 %d 行（简词另 %d）；词表 %d 行；辅码 %d 字；拆分 %d 字；改名脚本 %d 个；文件 %d 个' % (len(rows), len(kept), len(short), lex.count(b'\n'), len(chars_aux), len(cf), sum(1 for w in written if w.startswith('lua/yeying_')), len(set(written))))
