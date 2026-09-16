# -*- coding: utf-8 -*-
"""码圈输入法内置夜莺（2026-09-16）：作者要三样——普通码表（字词）、单字表、手心式辅助码表。全部从 106 导出物取，格式统一为 字\\t码 UTF-8。
可重复运行；产物在本目录 码圈/ 并打 zip。"""
import io, sys, os, shutil, hashlib, zipfile, datetime, collections, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; X = W + '/106_全平台导出/夜莺2.0_字词表与输入法'; H = os.path.dirname(os.path.abspath(__file__)); OUT = H + '/码圈'
DATE = datetime.date.today().strftime('%Y%m%d')
os.makedirs(OUT, exist_ok=True)
rows = [l.rstrip('\r\n').split('\t') for l in open(X + '/普通字词表/夜莺2.0_有简词_普通.txt', encoding='utf-8-sig') if '\t' in l]
def w(name, lines):
    p = OUT + '/' + name; open(p, 'w', encoding='utf-8', newline='\n').write(''.join(lines)); return p
f1 = w('夜莺2.0_码表_字词.txt', ['%s\t%s\n' % (t, c) for t, c in rows])                        # 普通码表：单字+简词+全码词+40快符，按码位顺序
f2 = w('夜莺2.0_单字表.txt', ['%s\t%s\n' % (t, c) for t, c in rows if len(t) == 1 and ('\u3400' <= t <= '\u9fff' or '\U00020000' <= t <= '\U0003134f')])   # 只留汉字（不含快符）
aux = [l.rstrip('\r\n') for l in open(X + '/手心/夜莺2.0_辅助码.txt', encoding='utf-8-sig') if '=' in l]
f3 = w('夜莺2.0_辅助码.txt', ['%s\n' % l for l in aux])                                          # 字=辅助码（全码末两键，多码空格分隔），手心同格式
kf = [l.rstrip('\r\n').split('\t') for l in open(X + '/普通字词表/夜莺2.0_快符_码前.txt', encoding='utf-8-sig') if '\t' in l]
f4 = w('夜莺2.0_快符.txt', ['%s\t%s\n' % (t, c) for c, t in kf])
n1 = len(rows); n2 = sum(1 for _ in open(f2, encoding='utf-8')); n3 = len(aux)
readme = f"""# 夜莺 2.0 · 码圈输入法内置用码表（{DATE}）

三个文件都是 UTF-8、LF、制表符分隔，"文字\\t编码"，同一编码的多个条目按候选顺序排列（上面的在前）。

- 夜莺2.0_码表_字词.txt：完整码表，{n1} 条。含单字（8105 通用规范汉字 + 7391 扩展字）、简词、四码词、40 条快符（如 a→！、no→の，已在各自码位排好次序）。
- 夜莺2.0_单字表.txt：只有汉字，{n2} 条（同一字的一简/二简/三简/全码各一条）。
- 夜莺2.0_辅助码.txt：手心格式 "字=辅助码"，{n3} 字。辅助码 = 该字全码的最后两键（首根键+末根键），一字多码时空格分隔。
- 夜莺2.0_快符.txt：40 条快符单列（文字\\t编码），已包含在完整码表里，单独给一份便于按需开关。

编码规则：前两码小鹤双拼，后两码首根键+末根键，四码定长；单字有一至三简；二字词 = 两字双拼，三字词 = 三字首码（三码），四字及以上 = 前三字首码 + 末字首码；出简让全。
候选次序即最终定稿次序，请按文件顺序，不要按频率重排。
超过四码的 223 条词不在本码表内（普通表口径）。
来源：仓库 losWater/Nightingale，releases/v2.0 与 work/夜莺2.0/106_全平台导出；本目录由 work/夜莺2.0/125_码圈交付/build.py 生成。
"""
open(OUT + '/README.md', 'w', encoding='utf-8', newline='\n').write(readme)
zp = H + f'/Nightingale-2.0-maquan-{DATE}.zip'
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)): z.write(OUT + '/' + fn, fn)
sha = hashlib.sha256(open(zp, 'rb').read()).hexdigest()
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '码表': n1, '单字表': n2, '辅助码': n3, '快符': len(kf), 'zip': zp, 'sha256': sha}, open(H + '/生成报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('码表 %d，单字表 %d，辅助码 %d，快符 %d → %s (%.1f MB)' % (n1, n2, n3, len(kf), zp, os.path.getsize(zp) / 1048576))
