# -*- coding: utf-8 -*-
"""确认拆分串真的完整进了虎娘的编译产物（2026-09-20）。

虎娘按空白分列读 .拆分 文件，原来写的「又 ＋ 寸」被截成「又」，候选注释里只显示第一个根。
改成间隔号「又·寸」后，这里直接在编译出来的方案文件里找这些串，
找得到就说明分隔符没被当成分列符，完整拆分已经落地。
"""
import io, sys, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root = os.environ['LOCALAPPDATA'] + '/Tigirl'
CASES = [('对', '又·寸'), ('是', '日·定字底'), ('在', '在字框·土'), ('的', '白·勹·丶'), ('变', '变字头·又')]
for name in ('夜莺2.0', '夜莺2.0单字'):
    d = root + '/schemas/' + name
    if not os.path.isdir(d): print('%-10s 方案目录不存在' % name); continue
    files = [f for f in glob.glob(d + '/**/*', recursive=True) if os.path.isfile(f)]
    blob = b''
    for f in files: blob += open(f, 'rb').read()
    print('%-10s %d 个文件，共 %.1f MB' % (name, len(files), len(blob) / 1048576))
    for ch, want in CASES:
        full = want.encode('utf-8') in blob
        head = want.split('·')[0].encode('utf-8') in blob
        print('   %s  完整「%s」%s   首根「%s」%s'
              % (ch, want, '找到 ✓' if full else '没有 ✗', want.split('·')[0], '在' if head else '不在'))
