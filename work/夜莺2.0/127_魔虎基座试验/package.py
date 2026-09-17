# -*- coding: utf-8 -*-
"""Rime 主力版打包：Rime_夜莺主力/ + V5 模型 → 夜莺2.0_Rime主力版.zip。
可复现：条目按路径排序、时间戳固定、外部属性固定，所以只要内容没变，重跑打出的 zip 逐字节相同、SHA256 不变
（2026-09-17：原先带文件 mtime，每次重跑校验值都变，发布目录与 Release 对不上）。"""
import io, sys, os, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); PKG = H + '/Rime_夜莺主力'; Z = H + '/夜莺2.0_Rime主力版.zip'
STAMP = (2026, 1, 1, 0, 0, 0)      # 固定时间戳，只为可复现，不代表内容日期
items = [(os.path.relpath(os.path.join(d, f), PKG).replace('\\', '/'), os.path.join(d, f)) for d, _, fs in os.walk(PKG) for f in fs if f != '生成清单.json']
items.append(('yeying/model/mohu-sentence-ngram-v5.bin', H + '/upstream/model/mohu-sentence-ngram-v5.bin'))
with zipfile.ZipFile(Z + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for rel, src in sorted(items):
        zi = zipfile.ZipInfo(rel, STAMP); zi.external_attr = 0o644 << 16; zi.create_system = 0
        zi.compress_type = zipfile.ZIP_STORED if rel.endswith('.bin') else zipfile.ZIP_DEFLATED
        with open(src, 'rb') as f: z.writestr(zi, f.read())
os.replace(Z + '.tmp', Z)
with zipfile.ZipFile(Z) as z:
    assert z.testzip() is None and '使用说明.md' in z.namelist() and 'LICENSE' in z.namelist() and 'yeying/model/mohu-sentence-ngram-v5.bin' in z.namelist()
print('夜莺2.0_Rime主力版.zip %d 个文件 %.1f MiB PASS' % (len(items), os.path.getsize(Z) / 1048576))
