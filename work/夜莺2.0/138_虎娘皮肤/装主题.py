# -*- coding: utf-8 -*-
"""把「智能ABC」复古配色装进本机虎娘（2026-09-20）。

作者暂时不打算提 PR，只本地自用。虎娘的主题是编译期写死的九条调色板，
数组长度也是编译期常量，加不了第十条——所以只能**改写其中一条**。

选中改写「粉」：九个里最不常用的一个，改了不影响日常。改完在虎娘里把主题选成
「粉」，看到的就是智能ABC的样子。「默认」绝不动，因为它是未知主题名的兜底。

做法与安全措施：
  · 按字节特征定位调色板，不写死偏移；定位不到就退出，绝不盲写。
  · 动手前先核对整张表的九条与预期完全一致，任何一条对不上就退出（说明版本变了）。
  · 原文件先备份到本目录 备份/ 下，带版本号与时间戳。
  · 用「改名再写入」的办法替换：DLL 被输入法进程加载着，直接覆盖会被拒绝，
    但 Windows 允许给已加载的文件改名。旧文件留在原地，重启相关程序后可清理。
  · x64 与 x86 两份都改——32 位程序加载的是 x86 那份。

注意：这会让 manifest.json 里记的 sha256 对不上。虎娘升级或修复时会覆盖回去，
届时重跑本脚本即可。用 --restore 可随时还原。

用法（需要管理员权限）：
    python 装主题.py            # 预演，只检查不写
    python 装主题.py --apply    # 真正写入
    python 装主题.py --restore  # 从备份还原
"""
import io, sys, os, glob, struct, hashlib, shutil, datetime, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
BK = H + '/备份'
ROOT = 'C:/Program Files/Tigirl'
NAMES = ['默认', '通透', '一般通透', '迷雾', '星夜', '纸', '粉', '赛博朋克', '清晨']
SLOT = NAMES.index('粉')                      # 要被改写的那一条
NEW = (0xff000000, 0xffc0c0c0, 0xff808080, 0x66000080, 2.0, (0, 0, 0, 0))
EXPECT = [
    (0xff000000, 0xfffff8f3, 0xff1a7b6b, 0x48000000, 1.25, (5, 5, 5, 5)),
    (0xff2277ee, 0x00000000, 0x00000000, 0x482277ee, 1.25, (5, 5, 5, 5)),
    (0xff2277ee, 0x1a000000, 0x00000000, 0x482277ee, 1.25, (5, 5, 5, 5)),
    (0xffd9d9d9, 0xff2f2f2f, 0xff5a5a5a, 0x48d9d9d9, 1.25, (5, 5, 5, 5)),
    (0xffffdc6a, 0xff232b39, 0xff3a6b9b, 0x48ffdc6a, 1.25, (5, 5, 5, 5)),
    (0xff111111, 0xfff5f2e8, 0xffa8a09d, 0x48111111, 1.30, (5, 5, 5, 5)),
    (0xff000000, 0xfffdf9f5, 0xffdeacac, 0x48000000, 1.25, (5, 5, 5, 5)),
    (0xff71e4fd, 0x88001122, 0xfff651fc, 0x4871e4fd, 1.50, (10, 0, 10, 0)),
    (0xff303030, 0xfffdfdff, 0xff56a1dd, 0x48303030, 1.25, (5, 5, 5, 5)),
]
A = set(sys.argv[1:])
APPLY = '--apply' in A
RESTORE = '--restore' in A

def pack(t):
    fg, bg, bd, sel, bw, cs = t
    b = struct.pack('<IIII', fg, bg, bd, sel) + struct.pack('<d', float(bw))
    for c in cs: b += struct.pack('<d', float(c))
    return b

def unpack(b, off):
    fg, bg, bd, sel = struct.unpack_from('<IIII', b, off)
    bw, = struct.unpack_from('<d', b, off + 16)
    cs = struct.unpack_from('<4d', b, off + 24)
    return (fg, bg, bd, sel, bw, tuple(int(c) if c == int(c) else c for c in cs))

def same(a, b):
    return a[:4] == b[:4] and abs(a[4] - b[4]) < 1e-9 and tuple(a[5]) == tuple(b[5])

gen = json.load(open(ROOT + '/install.json', encoding='utf-8-sig'))['generation']
ver = json.load(open(ROOT + '/install.json', encoding='utf-8-sig'))['version']
targets = [(a, '%s/versions/%s/%s/Tigirl.dll' % (ROOT, gen, a)) for a in ('x64', 'x86')]
print('虎娘 %s（%s）' % (ver, gen))
print('要改写的主题槽位：第 %d 条「%s」' % (SLOT + 1, NAMES[SLOT]))
print('写入配色：前景 0x%08x  背景 0x%08x  边框 0x%08x  选中 0x%08x  边宽 %g  圆角 %s\n'
      % (NEW[0], NEW[1], NEW[2], NEW[3], NEW[4], ','.join(str(c) for c in NEW[5])))

if RESTORE:
    n = 0
    for arch, path in targets:
        cands = sorted(glob.glob('%s/%s_%s_Tigirl.dll.orig' % (BK, gen, arch)))
        if not cands: print('  %s 没有备份，跳过' % arch); continue
        try:
            if os.path.exists(path):
                os.replace(path, path + '.replaced-%s' % datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            shutil.copy2(cands[0], path); n += 1
            print('  %s 已还原 ← %s' % (arch, os.path.basename(cands[0])))
        except PermissionError as e:
            print('  %s 还原失败（需要管理员权限）：%s' % (arch, e))
    print('\n还原 %d 个文件。重启用到输入法的程序后生效。' % n)
    sys.exit(0)

os.makedirs(BK, exist_ok=True)
plan = []
for arch, path in targets:
    print('── %s ──' % arch)
    if not os.path.exists(path): print('  文件不存在，跳过\n'); continue
    b = open(path, 'rb').read()
    anchor = pack(EXPECT[0])
    at = b.find(anchor)
    if at < 0 or b.find(anchor, at + 1) != -1:
        print('  调色板定位失败（命中 %d 处），不动这个文件\n'
              % (0 if at < 0 else 2)); continue
    bad = []
    for k in range(9):
        got = unpack(b, at + 56 * k)
        if not same(got, EXPECT[k]): bad.append('第 %d 条「%s」' % (k + 1, NAMES[k]))
    if bad:
        print('  九条里有对不上的：%s —— 版本可能变了，不动这个文件\n' % '、'.join(bad)); continue
    cur = unpack(b, at + 56 * SLOT)
    print('  调色板 @ 0x%X，九条与预期完全一致 ✓' % at)
    print('  当前「%s」：0x%08x 0x%08x 0x%08x 0x%08x 边 %g 角 %s'
          % (NAMES[SLOT], cur[0], cur[1], cur[2], cur[3], cur[4], ','.join(str(int(c)) for c in cur[5])))
    print('  原文件 sha256 %s' % hashlib.sha256(b).hexdigest()[:16])
    plan.append((arch, path, b, at))
    print()
if not plan:
    sys.exit('没有可处理的目标。')
if not APPLY:
    print('这是预演。确认无误后加 --apply 真正写入（需要管理员权限）。')
    sys.exit(0)

stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
done = 0
for arch, path, b, at in plan:
    bak = '%s/%s_%s_Tigirl.dll.orig' % (BK, gen, arch)
    try:
        if not os.path.exists(bak): shutil.copy2(path, bak)
        nb = b[:at + 56 * SLOT] + pack(NEW) + b[at + 56 * SLOT + 56:]
        assert len(nb) == len(b), '长度变了，中止'
        assert same(unpack(nb, at + 56 * SLOT), NEW), '回读不一致，中止'
        # DLL 被加载着不能直接覆盖，但可以给已加载的文件改名，再把新文件写到原路径
        old = path + '.old-' + stamp
        os.replace(path, old)
        with open(path, 'wb') as f: f.write(nb)
        shutil.copystat(old, path)
        print('  %s 已写入；旧文件留作 %s' % (arch, os.path.basename(old)))
        print('     备份 %s' % bak)
        print('     新 sha256 %s' % hashlib.sha256(nb).hexdigest()[:16])
        done += 1
    except PermissionError as e:
        print('  %s 写入失败——需要管理员权限：%s' % (arch, e))
    except Exception as e:
        print('  %s 写入失败：%s' % (arch, e))
print('\n完成 %d / %d。' % (done, len(plan)))
if done:
    print('在虎娘里把「主题」选成「%s」即可看到效果。' % NAMES[SLOT])
    print('用到输入法的程序要重开才会加载新 DLL（记事本、浏览器等）。')
    print('还原：python 装主题.py --restore')
