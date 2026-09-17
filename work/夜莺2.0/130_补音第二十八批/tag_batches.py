# -*- coding: utf-8 -*-
"""给补音批次加显式标记 "类别": "补音"（rebuild.py 的登记关卡只认这个标记，不靠文件名猜）。"""
import io, sys, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/83_单字表重放/裁定/'
for fn in ('29_第二十三批_补标准读音.json', '33_第二十七批_实战反馈第二批.json', '34_第二十八批_补音.json'):
    d = json.load(open(D + fn, encoding='utf-8')); d['类别'] = '补音'; json.dump(d, open(D + fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print(fn)
