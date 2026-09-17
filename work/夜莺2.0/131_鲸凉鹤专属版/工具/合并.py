# -*- coding: utf-8 -*-
"""夜莺单字 × 鲸凉鹤词库 合并工具（给鲸凉鹤作者用，打包成 exe，无需安装 Python）。

放在同一个文件夹里双击运行：自动找到「夜莺核心单字表」和「你的词库」，合并后生成三份新表。
  · 夜莺单字落在核心单字表指定的候选序号上，位置一个都不变。
  · 你的词库一个字节都不动：编码、词、先后顺序照抄；飞键、无理码、特设短语、简词、长码都保留。
  · 同一个码上冲突时，夜莺单字占住它的序号，你的词依次往后排。
以后不管是你的词库更新了，还是夜莺的单字表更新了，把新文件放进来再双击一次就行。
两个输入文件都是手心格式（一行一条：编码=序号,内容）。程序按内容自动分辨哪个是单字表、哪个是词库，认不出来时会提示你改名。
"""
import io, os, re, sys, collections, datetime

# Windows 控制台默认是 GBK 代码页，直接 print 中文会乱码；先把控制台和 stdout 都切到 UTF-8
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

VER = '1.0'
LINE = re.compile(r'([a-z]+)=(\d+),(.+)')
OUT_HAND = '合并结果_手心挂接.txt'
OUT_PLAIN = '合并结果_普通.txt'
OUT_FRONT = '合并结果_码前.txt'
OUT_LOG = '合并报告.txt'
OUTPUTS = {OUT_HAND, OUT_PLAIN, OUT_FRONT, OUT_LOG}


def txts(d):
    try:
        return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith('.txt') and f not in OUTPUTS]
    except OSError:
        return []


def here():
    """双击运行时用 exe 所在目录；那里凑不齐两个 txt 就退回当前目录（命令行运行、或 exe 被放在别处）"""
    d = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
    return d if len(txts(d)) >= 2 else os.getcwd()


def read(path):
    """读手心格式；返回 [(码, 序号, 内容)]，并报告跳过的行"""
    rows, skipped = [], []
    with io.open(path, encoding='utf-8-sig', errors='replace') as f:
        for n, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            m = LINE.fullmatch(s)
            if m:
                rows.append((m.group(1), int(m.group(2)), m.group(3)))
            else:
                skipped.append((n, s[:40]))
    return rows, skipped


def looks_like_chars(rows):
    """单字表的特征：几乎每条都是单个汉字"""
    if not rows:
        return 0.0
    return sum(1 for _, _, t in rows if len(t) == 1) / len(rows)


def pick(files):
    """在候选文件里认出 (单字表, 词库)"""
    scored = []
    for p in files:
        rows, skipped = read(p)
        if len(rows) < 100:
            continue
        scored.append({'路径': p, '名': os.path.basename(p), '行': rows, '跳过': skipped, '单字占比': looks_like_chars(rows)})
    if len(scored) < 2:
        return None, None, scored
    # 先按文件名认；认不出再按内容（单字占比最高的是单字表，最低的是词库）
    named = [x for x in scored if '核心单字' in x['名'] or '单字表' in x['名']]
    by_ratio = sorted(scored, key=lambda x: -x['单字占比'])
    chars = named[0] if len(named) == 1 else by_ratio[0]
    rest = [x for x in scored if x is not chars]
    words = sorted(rest, key=lambda x: x['单字占比'])[0]
    if chars['单字占比'] < 0.9 or words['单字占比'] > 0.5:
        return None, None, scored
    return chars, words, scored


def main():
    base = here()
    print('夜莺单字 × 鲸凉鹤词库 合并工具  v%s' % VER)
    print('工作目录：%s\n' % base)
    files = txts(base)
    if len(files) < 2:
        print('！这个文件夹里没有找到两个 .txt 文件。')
        print('  请把「夜莺核心单字表」和「你的词库」两个手心格式的 txt 放进来，再运行一次。')
        return 1
    chars, words, scored = pick(files)
    if not chars:
        print('！认不出哪个是单字表、哪个是词库。找到这些文件：')
        for x in scored:
            print('   %-40s %d 条，其中单字占 %.0f%%' % (x['名'], len(x['行']), x['单字占比'] * 100))
        print('  请把夜莺的那份改名成含「核心单字」三个字，例如 01_核心单字.txt，再运行一次。')
        return 1
    print('单字表：%s（%d 条）' % (chars['名'], len(chars['行'])))
    print('词  库：%s（%d 条）\n' % (words['名'], len(words['行'])))
    for x in (chars, words):
        if x['跳过']:
            print('  注意：%s 有 %d 行不是「编码=序号,内容」格式，这些条目不会出现在结果里：' % (x['名'], len(x['跳过'])))
            for n, s in x['跳过'][:12]:
                why = '序号后面少了逗号' if re.fullmatch(r'[a-z]+=\d+[^,].*', s) else ('内容是空的' if re.fullmatch(r'[a-z]+=\d+,', s) else '格式不认识')
                print('     第 %-7d 行  %-24s ← %s' % (n, s, why))
            if len(x['跳过']) > 12:
                print('     …… 其余 %d 行见 %s' % (len(x['跳过']) - 12, OUT_LOG))
            print('     想保留它们，把格式改好再运行一次。')
    # 夜莺单字：码 → {序号: 字}
    core = collections.defaultdict(dict)
    dup = []
    for c, i, t in chars['行']:
        if i in core[c] and core[c][i] != t:
            dup.append('%s=%d 既是 %s 又是 %s' % (c, i, core[c][i], t))
        core[c][i] = t
    if dup:
        print('！单字表里有 %d 处同一个「编码=序号」对应不同的字，无法确定位置：' % len(dup))
        for d in dup[:5]:
            print('   ' + d)
        return 1
    # 词库：码 → [(原序号, 内容)]。只把"你用普通编码打的那个字"换成夜莺的同一个字，其余一律保留：
    #   · 占位符与符号（①②③、α、の、！、× 等）是你自己的设置，不按字符长度一刀切；
    #   · o 开头的特设区（of 繁体字、ox 部件检索、oy 圈号与宏、ot 希腊字母、od 生僻字……）里的字一律不动，
    #     只要夜莺的单字表没用到那个码位。夜莺根本不用 of、ob 这些码位。
    core_chars = set()
    for d in core.values():
        core_chars.update(d.values())
    special = lambda c: c.startswith('o') and c not in core
    his = collections.defaultdict(list)
    dropped = kept_special = 0
    for c, i, t in words['行']:
        if len(t) == 1 and t in core_chars:
            if not special(c):
                dropped += 1
                continue
            kept_special += 1
        his[c].append((i, t))
    for c in his:
        his[c].sort()
    # 合并：单字占住自己的序号，词按原顺序填剩下的位置
    merged = {}
    same_code = gaps_total = 0
    for c in sorted(set(core) | set(his)):
        slots = dict(core.get(c, {}))
        pos = 1
        for _, w in his.get(c, []):
            while pos in slots:
                pos += 1
            slots[pos] = w
            pos += 1
        if core.get(c) and his.get(c):
            same_code += 1
        gaps_total += sum(1 for i in range(1, max(slots) + 1) if i not in slots)
        merged[c] = slots
    # 自检：单字位置、词的先后都不能变
    for c, d in core.items():
        for i, t in d.items():
            assert merged[c].get(i) == t, '单字位置变了：%s=%d' % (c, i)
    for c, ws in his.items():
        got = [merged[c][i] for i in sorted(merged[c]) if not (c in core and i in core[c])]
        assert got == [w for _, w in ws], '词的先后变了：%s' % c
    keep_single = sum(1 for c in his for _, t in his[c] if len(t) == 1)
    flat = [(t, c) for c in sorted(merged) for _, t in sorted(merged[c].items())]
    w = lambda name, body, bom: io.open(os.path.join(base, name), 'wb').write(body.encode('utf-8-sig' if bom else 'utf-8'))
    w(OUT_HAND, '\r\n'.join('%s=%d,%s' % (c, i, t) for c in sorted(merged) for i, t in sorted(merged[c].items())) + '\r\n', False)
    w(OUT_PLAIN, '\r\n'.join('%s\t%s' % (t, c) for t, c in flat) + '\r\n', True)
    w(OUT_FRONT, '\r\n'.join('%s\t%s' % (c, t) for t, c in flat) + '\r\n', True)
    log = ['夜莺单字 × 鲸凉鹤词库 合并报告',
           '时间：%s   工具版本：v%s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), VER),
           '',
           '单字表：%s，%d 条' % (chars['名'], len(chars['行'])),
           '词  库：%s，%d 条（其中 %d 条单字已换成夜莺的同一个字；占位符、符号、夜莺没收的生僻字，以及 o 开头特设区里的 %d 条字，共 %d 条原样保留）' % (words['名'], len(words['行']), dropped, kept_special, keep_single),
           '',
           '合并后：%d 条，%d 个码位' % (len(flat), len(merged)),
           '字词同码的码位：%d 个' % same_code,
           '序号没人填的空位：%d 个（手心会自动紧凑显示，不影响使用）' % gaps_total,
           '',
           '规则：夜莺单字落在核心单字表指定的序号上，位置一个都不变；你的词按原顺序填剩下的位置。',
           '      你的编码、词、先后顺序一个字节都没改，飞键、无理码、特设短语、简词、长码全部保留。',
           '      占位符与符号（①②③、α、の、！ 等）照原样留着；o 开头的特设区（of 繁体、ox 部件、oy 圈号与宏、ot 希腊字母、od 生僻字……）整个不动。',
           '',
           '产物：',
           '  %s   手心格式（编码=序号,内容），UTF-8 无 BOM，CRLF' % OUT_HAND,
           '  %s        文字<Tab>编码，UTF-8 带 BOM，CRLF' % OUT_PLAIN,
           '  %s        编码<Tab>文字，UTF-8 带 BOM，CRLF' % OUT_FRONT] + \
          (['', '被跳过的行（格式不是「编码=序号,内容」，没有进入结果；改好格式再运行一次即可收回）：'] +
           ['  %s 第 %d 行  %s' % (x['名'], n, s) for x in (chars, words) for n, s in x['跳过']]
           if (chars['跳过'] or words['跳过']) else [])
    w(OUT_LOG, '\r\n'.join(log) + '\r\n', True)
    print('合并完成：%d 条，%d 个码位。字词同码 %d 个码位，空位 %d 个。\n' % (len(flat), len(merged), same_code, gaps_total))
    print('已生成：')
    for n in (OUT_HAND, OUT_PLAIN, OUT_FRONT, OUT_LOG):
        print('   %s' % n)
    return 0


if __name__ == '__main__':
    code = 1
    try:
        code = main()
    except Exception as e:
        print('\n！出错了：%s: %s' % (type(e).__name__, e))
        print('  把这段话连同两个输入文件发给夜莺作者就能定位。')
    try:
        input('\n按回车键关闭。')
    except Exception:
        pass
    sys.exit(code)
