# -*- coding: utf-8 -*-
"""把 专属版/ 打成一个 zip 交付。可复现：条目排序、时间戳固定。"""
import io, sys, os, zipfile, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); D = H + '/专属版'
Z = H + '/夜莺2.0_鲸凉鹤专属版_%s.zip' % datetime.date.today().strftime('%Y%m%d')
items = sorted((f, D + '/' + f) for f in os.listdir(D) if os.path.isfile(D + '/' + f))
with zipfile.ZipFile(Z + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for rel, src in items:
        zi = zipfile.ZipInfo(rel, (2026, 1, 1, 0, 0, 0)); zi.external_attr = 0o644 << 16; zi.create_system = 0; zi.compress_type = zipfile.ZIP_DEFLATED
        with open(src, 'rb') as f: z.writestr(zi, f.read())
os.replace(Z + '.tmp', Z)
with zipfile.ZipFile(Z) as z: assert z.testzip() is None
print('%s  %d 个文件 %.1f MB\nsha256 %s' % (os.path.basename(Z), len(items), os.path.getsize(Z) / 1048576, hashlib.sha256(open(Z, 'rb').read()).hexdigest()))
