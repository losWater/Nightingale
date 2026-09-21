# -*- coding: utf-8 -*-
"""最后一轮：直接按字节搜常见主题名与配色词，确认虎娘到底有几个内置主题（2026-09-20）。

前两轮的结论：
  · 「主题」是 config.txt 的键，默认值「默认」，与「字体」「字体大小」「竖排候选」同组；
  · 设置界面有「候选主题」下拉框（COMBOBOX）；
  · 但 UTF-16 和 UTF-8 串里「默认」都只出现一次，没有第二个主题名；
  · 安装脚本里没有任何主题目录。
如果这一轮也搜不到别的主题名和颜色定义，那就说明当前版本的主题只是个占位，
自定义皮肤需要作者先支持，我们做不了。
"""
import io, sys, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
V = 'C:/Program Files/Tigirl/versions/4cd5825d7e87783b/x64'
WORDS = ['默认', '深色', '浅色', '暗色', '亮色', '经典', '护眼', '夜间', '白天', '跟随系统',
         '自定义', '皮肤', '主题', '背景色', '前景色', '文字色', '高亮色', '边框色',
         '毛玻璃', '亚克力', '圆角', '透明度', '暗黑', '明亮', '素雅', 'typora']
files = ['Tigirl.dll', 'Tigirl.exe', 'Tigirl.Reminder.exe']
for fn in files:
    p = os.path.join(V, fn)
    if not os.path.exists(p): continue
    b = open(p, 'rb').read()
    print('═' * 70)
    print('%s  %.1f MB' % (fn, len(b) / 1048576))
    for w in WORDS:
        u16 = w.encode('utf-16-le'); u8 = w.encode('utf-8')
        n16 = b.count(u16); n8 = b.count(u8)
        if n16 or n8:
            print('   %-8s UTF-16 %d 次   UTF-8 %d 次' % (w, n16, n8))
# 顺带看看 config.txt 目前有哪些键，以及键表里「主题」附近那批默认值
print('\n' + '═' * 70)
print('本机 config.txt 现状：')
cfg = os.environ['LOCALAPPDATA'] + '/Tigirl/config.txt'
for l in open(cfg, encoding='utf-8-sig', errors='replace'):
    if l.strip(): print('   ' + l.rstrip('\n').replace('\t', ' = '))
print('\n（未出现的键用内置默认值；「主题」默认「默认」，「字体」默认「#霞鹜文楷 GB 屏幕阅读版」）')
