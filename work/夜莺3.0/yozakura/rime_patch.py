"""夜桜 Rime 搭台补丁：release/stage_rime.py 在设了 YZ_BRAND（标识不是 nightingale）时调用。
对搭台目录里复制出来的夜莺构建工具（tools/）逐条做文本替换，把 夜莺/小鹤 换成 夜桜/自然码；~/Nightingale 本身不动。
每条替换都先断言原文存在（夜莺工具改了就报错，不会悄悄漏改）。
- 标识：yeying_*（stage 已去掉 25 版本号）→ <标识>_*；名称 夜莺 → 夜桜；目录名检查、显示版本替换跟着换。
- 双拼：魔虎上游包 flypy → zrm（tiger/scheme、candidate_type、包名）；新运行库（2026-10-15 起）Mac 只有 libtigerengine.dylib，不再有 libonnxruntime。
- 数据：export.py 里取自 2.5 小鹤数据的多字词读音、~ 反查的全拼→双拼表，换成自然码。
- 测试：小鹤整句换自然码；夜莺专属的码（你好 nihc、zid 自、sl 第三选）按夜桜换（ni 两方案同码同序，原期望照用）。
- 包名 Nightingale-Rime → <英文名>-Rime；源码链接指向本仓库。
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode, recode, syllables

TEXT = ('.py', '.yaml', '.lua', '.md', '.c', '.json', '.txt', '.sh')


def sub(path, pairs):
    t = path.read_text(encoding='utf-8')
    for a, b in pairs:
        assert a in t, (str(path), a[:80])
        t = t.replace(a, b)
    path.write_text(t, encoding='utf-8')


def zr(s):
    """小鹤双拼串（整句测试用，逐两码一个音节）换成自然码。"""
    return ''.join(recode(s[i:i + 2], 'xiaohe', 'ziranma') for i in range(0, len(s), 2))


def patch(tools, C, eng='Yozakura'):
    ID, BRAND, V = C.ID, C.NAME.removesuffix(C.V), C.V
    rm = tools / 'rime_mac'; mt = tools / 'maintenance'
    # ---- 测试：先改与夜莺码表、小鹤绑定的期望（在全局替换之前，免得“夜莺”二字被换掉）----
    s1, s2, s3 = 'jbtmtmqihfhc', 'woxihruurufa', 'woxihryeyk'
    sub(rm / 'verify_v5.py', [
        (f"'{s1}': '今天天气很好'", f"'{zr(s1)}': '今天天气很好'"),
        (f"'{s3}': '我喜欢夜莺'", f"'{zr(s3)}': '我喜欢夜莺'"),
        ("other = ['womfkeyiyiqixtxi', 'vegeuurufaviiiyikbqiuuruyivgjuhw',\n             'jbtmtmqihfhcwoxihruurufa', 'wozdysshuujrdaizi',\n             'nihcnkycjibuifmexmuh', 'woxihryeyk'*5,",
         f"other = ['{zr('womfkeyiyiqixtxi')}', '{zr('vegeuurufaviiiyikbqiuuruyivgjuhw')}',\n             '{zr(s1 + s2)}', '{zr('nihcnkycjibuifmexmuh')}', '{zr(s3)}'*5,"),
        ("'woxihryeyk'*10]", f"'{zr(s3)}'*10]"),
        ("'woxihryeyk{BackSpace}', 'woxihryeyk{Left}{Right}',\n            'woxihryeyk{space}',",
         f"'{zr(s3)}{{BackSpace}}', '{zr(s3)}{{Left}}{{Right}}',\n            '{zr(s3)}{{space}}',"),
        ("'jbtmtmqihfhc{Escape}'", f"'{zr(s1)}{{Escape}}'"),
        ("assert commits['woxihryeyk{space}'] == '我喜欢夜莺'", f"assert commits['{zr(s3)}{{space}}'] == '我喜欢夜莺'"),
        ("run(directory, ['woxihryeyk', 'ni'])", f"run(directory, ['{zr(s3)}', 'ni'])"),
        ("assert restarted_sources['woxihryeyk'][0] == 'V5'", f"assert restarted_sources['{zr(s3)}'][0] == 'V5'"),
        ("run(directory, ['jbtmtmqihfhc'], deploy=True)", f"run(directory, ['{zr(s1)}'], deploy=True)"),
        ("assert fallback['jbtmtmqihfhc'][1] == '今天天气很好'", f"assert fallback['{zr(s1)}'][1] == '今天天气很好'"),
        ("assert 'V5' not in fallback_sources['jbtmtmqihfhc'].values()", f"assert 'V5' not in fallback_sources['{zr(s1)}'].values()"),
    ])
    sub(rm / 'verify_single.py', [("assert commits['zid{space}'] == '自'", "assert commits['zid{space}'] == table['zid'][0]   # 夜桜：zid 归码表首选")])
    vs = rm / 'verify_shape.py'                         # 你好的码按自然码（小鹤 nihc → 自然码 nihk）；sl 第三选按码表
    sub(vs, [("commits['ni;'] == '拿出' and commits[\"sl'\"] == '思路'", "commits['ni;'] == '拿出' and commits[\"sl'\"] == fixed['sl'][2]")])
    t = vs.read_text(encoding='utf-8'); assert "'nihc" in t
    vs.write_text(t.replace('nihc', zr('nihc')), encoding='utf-8')
    sub(rm / 'release_checks.py', [("sentence = ('woxihryeyk', '我喜欢夜莺')        # 小鹤双拼整句",
                                     f"sentence = ('{zr(s3)}', '我喜欢夜莺')        # 自然码整句")])

    # ---- 双拼：魔虎上游 flypy → zrm；新运行库 ----
    for f in tools.rglob('*'):
        if f.is_file() and f.suffix in TEXT:
            t = f.read_text(encoding='utf-8')
            t2 = t.replace('rime-mohu-flypy-latest.zip', 'rime-mohu-zrm-latest.zip')
            if t2 != t: f.write_text(t2, encoding='utf-8')
    sub(rm / 'src/v5-tiger.yaml', [('scheme: flypy', 'scheme: zrm'), ('candidate_type: mohu_flypy', 'candidate_type: mohu_zrm'),
                                   ('nightingale.lexicon.txt', f'{ID}.lexicon.txt')])
    sub(rm / 'build_v5.py', [("'nightingale.lexicon.txt'", f"'{ID}.lexicon.txt'")])   # onnxruntime 的适配已移到 release/stage_rime.py（夜莺也用新运行库）

    # ---- 数据：多字词读音、~ 反查表换自然码 ----
    rc = {encode(p, 'xiaohe'): encode(p, 'ziranma') for p in syllables()}
    py = {p: encode(p, 'ziranma') for p in syllables() if p.isalpha()}
    sub(mt / 'export.py', [
        ("                readings[text] = [t[:2] for t in tokens]",
         f"                readings[text] = [_RC.get(t[:2], t[:2]) for t in tokens]   # 夜桜：2.5 读音是小鹤码，换自然码"),
        ("    pinyin = dict(re.findall(r'\\[\"([a-z]+)\"\\]=\"([a-z]+)\"',pinyin_part))",
         "    pinyin = dict(_PY)   # 夜桜：全拼 → 自然码（不用 2.5 小鹤表）"),
        ("def export(", f"_RC = {json.dumps(rc)}\n_PY = {json.dumps(py)}\n\n\ndef export("),
    ])

    # ---- 名称与标识（全局）----
    for f in sorted(tools.rglob('*'), key=lambda p: -len(p.parts)):
        if f.is_file() and f.suffix in TEXT:
            t = f.read_text(encoding='utf-8')
            t2 = (t.replace('yeying_', f'{ID}_').replace('夜莺', BRAND).replace('Nightingale-Rime-', f'{eng}-Rime-')
                   .replace('https://github.com/losWater/Nightingale/releases/tag/v' + V, f'https://github.com/losWater/{eng}/releases/tag/{ID}-v{V}'))
            if t2 != t: f.write_text(t2, encoding='utf-8')
        if 'yeying_' in f.name: f.rename(f.with_name(f.name.replace('yeying_', f'{ID}_')))
    import re                                            # 注释与说明里的英文名（不动链接 losWater/Nightingale、文件名 nightingale-*、Nightingale-Rime 已换）
    for f in tools.rglob('*'):
        if f.is_file() and f.suffix in ('.lua', '.yaml', '.md'):
            t = f.read_text(encoding='utf-8'); t2 = re.sub(r'(?<![/\w-])Nightingale(?![-/\w])', eng, t)
            if t2 != t: f.write_text(t2, encoding='utf-8')
    for f in (rm / 'verify_v5.py', rm / 'release_checks.py'):    # 整句期望“我喜欢夜莺”是词，不是方案名
        sub(f, [(f'我喜欢{BRAND}', '我喜欢夜莺')])
    # 2.5 轻量包里的 Lua/YAML（构建时读出改名）也换名称
    sub(rm / 'build.py', [("text = text.replace('2.0-20260915', '2.5-mac.1')",
                           f"text = text.replace('2.0-20260915', '2.5-mac.1').replace('夜莺', '{BRAND}')")])
    print('夜桜补丁：标识', ID, '名称', BRAND, '双拼 zrm')
