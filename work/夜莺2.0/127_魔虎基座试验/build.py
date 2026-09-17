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
for l in open(SRC + '/yeying20_rime.dict.yaml', encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) != 3: continue
    ss = f[1].split(' ')
    if all(syl.match(s) for s in ss):
        kept.append(l if l.endswith('\n') else l + '\n')
        if len(ss) == 1 and len(f[0]) == 1:
            a = ss[0][3:]
            if a not in chars_aux[f[0]]: chars_aux[f[0]].append(a)
put('mohu_flypy.yeying.dict.yaml', '# Rime dictionary\n# encoding: utf-8\n# 夜莺 2.0 字词（双拼;首末根键）。由 127 build.py 生成。\n\n---\nname: mohu_flypy.yeying\nversion: "%s"\nsort: by_weight\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n\n' % datetime.date.today().strftime('%Y%m%d') + ''.join(kept))
put('mohu_flypy.extended.dict.yaml', '# Rime dictionary\n# encoding: utf-8\n\n---\nname: mohu_flypy.extended\nversion: "%s"\nsort: by_weight\nuse_preset_vocabulary: false\nimport_tables:\n  - mohu_flypy.yeying     # 夜莺 2.0 字词库\n...\n\n# 用户自定义词库\n# 此处可无码加词\n' % datetime.date.today().strftime('%Y%m%d'))
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
rep('  name: 魔虎·小鹤\n', '  name: 夜莺·魔虎\n')
rep('    基于小鹤双拼和虎码12字根做辅码的魔虎整句输入方案。\n', '    夜莺 2.0（小鹤双拼 + 首根键 + 末根键）码表与词库，运行在魔虎整句方案的功能层与 V5 模型之上。\n')
rep('    - 魔虎方案制作：晴\n', '    - 魔虎方案制作：晴\n    - 夜莺 2.0 码表与词库：losWater\n')
rep('    states: [ 动词, 固词 ] # 「固词」表示「固顶词」\n', '    states: [ 动词, 固词 ] # 「固词」表示「固顶词」\n    reset: 1   # [夜莺] 默认固词：四码按夜莺码表出字词\n')
rep('    states: [ 常用字, 全字集 ]\n', '    states: [ 常用字, 全字集 ]\n    reset: 1   # [夜莺] 默认全字集：扩展字本来就排在各码位末尾，不挡路；Ctrl+x 可切回常用字\n')
rep('  user_dict: mohu_flypy_tiger_prefix2\n', '  user_dict: yeying20_mohu\n')
rep('  inject_prioritize: "any"', '  fixed_table_order: true     # [夜莺] 固定码表按码表原序输出\n  inject_prioritize: "any"')
rep('  four_code_char_yield_exempt: 暮\n', '  four_code_char_yield_exempt: ""\n')
put(p, s)
put('default.custom.yaml', 'patch:\n  schema_list:\n    - schema: mohu_flypy\n  menu/page_size: 5\n')
put('说明.md', '# 夜莺 × 魔虎基座 试验版\n\n功能层与 V5 模型来自魔虎（fcxxxz/rime-mohu，GPL v3，见 LICENSE）；码表、词库、拆分来自夜莺 2.0。\n\n安装：整个目录内容放进 Rime 用户目录，再把 `mohu-sentence-ngram-v5.bin` 放到 `mohu/model/`，重新部署，选「夜莺·魔虎」。\n\n由 work/夜莺2.0/127_魔虎基座试验/build.py 生成。\n')
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '文件': sorted(set(written))}, open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('固定码表 %d 条；整句词典 %d 行；词表 %d 行；辅码 %d 字；字频排名 %d 字；拆分 %d 字；文件 %d 个' % (len(rows), len(kept), lex.count(b'\n'), len(chars_aux), len(rank), len(cf), len(set(written))))
