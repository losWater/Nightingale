# -*- coding: utf-8 -*-
"""Rime 主力版打包：夜莺魔虎试验版/（build.py 产物，目录名沿用）+ V5 模型 → 夜莺2.0_Rime主力版.zip。不带 macOS 动态库以外的任何删减。"""
import io, sys, os, zipfile, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); PKG = H + '/Rime_夜莺主力'; Z = H + '/夜莺2.0_Rime主力版.zip'; n = 0
with zipfile.ZipFile(Z + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, _, fs in os.walk(PKG):
        for fn in sorted(fs):
            if fn == '生成清单.json': continue
            p = os.path.join(root, fn); z.write(p, os.path.relpath(p, PKG).replace('\\', '/')); n += 1
    z.write(H + '/upstream/model/mohu-sentence-ngram-v5.bin', 'yeying/model/mohu-sentence-ngram-v5.bin', compress_type=zipfile.ZIP_STORED); n += 1
os.replace(Z + '.tmp', Z)
with zipfile.ZipFile(Z) as z: assert z.testzip() is None and '使用说明.md' in z.namelist() and 'LICENSE' in z.namelist()
print('夜莺2.0_Rime主力版.zip %d 个文件 %.1f MiB PASS' % (n, os.path.getsize(Z) / 1048576))
