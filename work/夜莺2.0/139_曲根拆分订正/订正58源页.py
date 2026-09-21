# -*- coding: utf-8 -*-
"""订正第二条拆分链的源头：58_拆分查询/夜莺2.0拆分查询.html（2026-09-21）。默认预演，--apply 落盘。

为什么还要改这里：拆分数据在工程里有两条平行的链，各自有源——
    55 + 112  →  106  →  Bime / Rime 拆分
    58 页面   →  114  →  65 工具包  →  123 / 137 虎娘
114/sync.py 对已有字是「拆分逐条不变」，只从 58 继承、只给新扩展字补拆分，
所以改 55 不会传到工具箱和虎娘。要让两条链一致，58 这个源也得改。

替换两处，都已核对在本文件中各出现 24 次、与含曲的 24 个字一一对应：
    根数组： {由,p,田／里／果} + {丨,l,竖}  →  {囗,j,囗} + {横,p,横} + {丨,l,竖} + {丨,l,竖}
    新拆串： 由 ＋ 丨  →  囗 ＋ 横 ＋ 丨 ＋ 丨
根的元数据（键与组名）直接抄自本文件里「曲」本字的条目，保证一字不差。
"""
import io, sys, os, shutil, datetime, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = W + '/58_拆分查询/夜莺2.0拆分查询.html'
BK = H + '/备份'
APPLY = '--apply' in sys.argv[1:]
OLD_R = '{"根": "由", "键": "p", "组": "田／里／果"}, {"根": "丨", "键": "l", "组": "竖"}'
NEW_R = ('{"根": "囗", "键": "j", "组": "囗"}, {"根": "横", "键": "p", "组": "横"}, '
         '{"根": "丨", "键": "l", "组": "竖"}, {"根": "丨", "键": "l", "组": "竖"}')
OLD_S, NEW_S = '"新拆": "', None       # 新拆按子串替换
OLD_T, NEW_T = '由 ＋ 丨', '囗 ＋ 横 ＋ 丨 ＋ 丨'
s = open(P, encoding='utf-8-sig').read()
nr, nt = s.count(OLD_R), s.count(OLD_T)
print('%s\n  文件 %d 字符' % (os.path.relpath(P, W), len(s)))
print('  根数组旧模式 %d 处，新拆旧模式 %d 处' % (nr, nt))
# 模板核对：曲本字必须已经是目标写法
if NEW_R not in s or '"新拆": "%s"' % NEW_T not in s:
    sys.exit('  本文件里找不到「曲」本字的目标写法，模板对不上，停手。')
if nr != 24 or nt != 24:
    sys.exit('  出现次数不是预期的 24 / 24，停手。请先核对。')
out = s.replace(OLD_R, NEW_R).replace(OLD_T, NEW_T)
print('  替换后：根数组旧模式 %d 处，新拆旧模式 %d 处' % (out.count(OLD_R), out.count(OLD_T)))
print('  文件长度 %d → %d（+%d）' % (len(s), len(out), len(out) - len(s)))
# 结构核对：把 const D 解出来，确认仍是合法 JSON 且字数不变
import re
def parse_D(txt):
    m = re.search(r'\bconst D\s*=\s*', txt)
    return json.JSONDecoder().raw_decode(txt[m.end():])[0]
try:
    d0, d1 = parse_D(s), parse_D(out)
except Exception as e:
    sys.exit('  改后 JSON 解析失败：%s' % e)
print('  const D：%d 字 → %d 字' % (len(d0), len(d1)))
if len(d0) != len(d1): sys.exit('  字数变了，停手。')
chk = [t for t in d1 if d1[t].get('新拆') != ' ＋ '.join(r['根'] for r in d1[t].get('根', []))]
print('  根数组与新拆串一致性：%s' % ('全部一致 ✓' if not chk else '有 %d 条不一致 ✗ %s' % (len(chk), chk[:5])))
if chk: sys.exit('  一致性核对不过，停手。')
for t in ('曲', '蛐', '澧', '體'):
    if t in d1: print('    %-3s %s' % (t, d1[t]['新拆']))
if not APPLY:
    print('\n  这是预演。确认后加 --apply 落盘。')
    sys.exit(0)
os.makedirs(BK, exist_ok=True)
stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
bak = '%s/%s_58_夜莺2.0拆分查询.html' % (BK, stamp)
shutil.copy2(P, bak)
open(P, 'w', encoding='utf-8-sig', newline='').write(out)
print('\n  已写入，备份 %s' % os.path.basename(bak))
print('  接下来重跑 export.py，114 会把新拆分带进工具包，123/137 再带进虎娘。')
