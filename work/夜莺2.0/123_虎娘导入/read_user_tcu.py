# -*- coding: utf-8 -*-
import io, sys, struct, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
b = open('C:/Users/asus/AppData/Local/Tigirl/schemas/夜莺2.0/user.tcu', 'rb').read()
assert b[:8] == b'TIGERU01'; i = 8; recs = []
while i < len(b):
    size, h = struct.unpack_from('<II', b, i); body = b[i + 8:i + 8 + size]
    kind, clen, tlen = struct.unpack_from('<III', body, 0)
    code = body[12:12 + clen * 2].decode('utf-16le'); text = body[12 + clen * 2:12 + (clen + tlen) * 2].decode('utf-16le')
    recs.append((code, text, kind, h)); i += 8 + size
tab = collections.defaultdict(list)
for l in open('E:/夜莺2.0/work/夜莺2.0/113_扩展字入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    t, c = l.rstrip('\r\n').split('\t'); tab[c].append(t)
print('用户记录 %d 条（类型字段均为 %s）' % (len(recs), sorted({k for _, _, k, _ in recs})))
for code, text, kind, h in recs:
    print('  %s → %s   码表现序：%s' % (code, text, '、'.join(tab.get(code, ['（无此码）']))))
