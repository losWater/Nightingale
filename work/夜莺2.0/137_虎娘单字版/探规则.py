# -*- coding: utf-8 -*-
"""用小样本探出虎娘 main_records 的口径（2026-09-20）。

lexicon_import 的第一种用法 <schema-dir> <pinyin-dir> <new-output.tcd> <culture>
只把码表编译到指定 .tcd 文件，不注册方案、不碰用户的虎娘配置，适合做试验。
造几组结构已知的小码表，看回报的 main_records，就能反推它折掉了什么。
"""
import io, sys, os, glob, json, subprocess, tempfile, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root = os.environ['LOCALAPPDATA'] + '/Tigirl'
imp = sorted(glob.glob('C:/Program Files/Tigirl/versions/*/x64/Tigirl.Import.exe'), key=os.path.getmtime)[-1]
SCR = os.path.join(tempfile.gettempdir(), 'tigirl_probe')
HEAD = ('name: probe\nversion: "1.0"\nsort: by_weight\ncolumns:\n  - text\n  - weight\n  - code\n  - stem\n'
        'encoder:\n  rules:\n    - length_equal: 2\n      formula: "AaAbBaBb"\n'
        '    - length_equal: 3\n      formula: "AaBaCa"\n    - length_in_range: [4, 99]\n      formula: "AaBaCaZa"\n')

def probe(label, entries):
    d = os.path.join(SCR, 'dir')
    shutil.rmtree(SCR, ignore_errors=True); os.makedirs(d)
    body = ''.join('%s\t%d\t%s\n' % (t, 1000000 - i, c) for i, (t, c) in enumerate(entries))
    open(d + '/probe.dict.yaml', 'w', encoding='utf-8', newline='\n').write(HEAD + '...\n\n' + body)
    # 不带快符.txt / 常用符号.txt：它们会并进主表，把基线搅乱（上一版探针就栽在这）
    for n in ('1拼音.注释', 'unicode.注释'):
        src = root + '/码表/夜莺2.0单字/' + n
        if os.path.exists(src): shutil.copy2(src, d + '/' + n)
    out = os.path.join(SCR, 'out.tcd')
    p = subprocess.run([imp, d, os.path.join(root, '拼音反查码表'), out, 'zh-CN'], capture_output=True)
    s = (p.stdout or b'').decode('utf-8', 'replace').strip()
    try: m = json.loads(s).get('main_records')
    except Exception: m = s or (p.stderr or b'').decode('utf-8', 'replace').strip()[:120]
    print('  %-42s 写入 %2d 行 → main_records %s' % (label, len(entries), m))
    return m

print('探针（每组只改一个变量，码都用 z/q 开头避开快符）：')
probe('O 空表（基线）', [])
probe('A 四个字各一个全码，互不相干', [('天', 'zqaa'), ('地', 'zqbb'), ('玄', 'zqcc'), ('黄', 'zqdd')])
probe('B 同一码位两个字（选重）', [('天', 'zqaa'), ('地', 'zqaa')])
probe('C 一个字：全码 + 三简（三简是全码前缀）', [('天', 'zqa'), ('天', 'zqaa')])
probe('D 一个字：全码 + 三简（三简不是前缀）', [('天', 'zqb'), ('天', 'zqaa')])
probe('E 一个字：全码 + 三简 + 二简，层层前缀', [('天', 'zq'), ('天', 'zqa'), ('天', 'zqaa')])
probe('F 两个字同全码 + 其中一个有三简前缀', [('天', 'zqa'), ('天', 'zqaa'), ('地', 'zqaa')])
probe('G 一个字两个不同全码（多音）', [('天', 'zqaa'), ('天', 'zqbb')])
shutil.rmtree(SCR, ignore_errors=True)
print('\n对照：纯单字版 21195 行 → 20046；简码行共 5265，其中 1149 被折。')
