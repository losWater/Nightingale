# -*- coding: utf-8 -*-
"""例字两列之间加竖分隔线（2026-09-16 你建议）：右列每行左侧一条竖线；窄屏单列时不显示。同步离线包/单文件/啾啾/zip/核验。"""
import io, sys, os, re, json, hashlib, zipfile, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; U = B + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); assert m, name
    obj, n = json.JSONDecoder().raw_decode(s[m.end():]); return obj, m.end(), m.end() + n
def put(s, name, obj):
    _, a, b = get(s, name); return s[:a] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + s[b:]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
old = '#example{display:grid;grid-template-columns:1fr 1fr;column-gap:28px;align-items:start}@media(max-width:600px){#example{grid-template-columns:1fr}}'
new = ('#example{display:grid;grid-template-columns:1fr 1fr;column-gap:0;align-items:start}'
       '#example .example-row:nth-child(odd){padding-right:18px}'
       '#example .example-row:nth-child(even){padding-left:18px;border-left:2px solid #9fb3a8}'
       '@media(max-width:600px){#example{grid-template-columns:1fr}#example .example-row:nth-child(odd){padding-right:0}#example .example-row:nth-child(even){padding-left:0;border-left:0}}')
def fix(pv):
    assert pv.count(old) == 1, pv.count(old); return pv.replace(old, new)
p = O + '/字根练习.html'; pv = fix(open(p, encoding='utf-8-sig').read()); open(p, 'w', encoding='utf-8', newline='').write(pv)
main = U + '/夜莺2.0随身工具_单文件.html'; shell = open(main, encoding='utf-8-sig').read(); views, _, _ = get(shell, 'views')
views['practice'] = fix(views['practice']); assert views['practice'] == pv
shell = put(shell, 'views', views); open(main, 'w', encoding='utf-8', newline='').write(shell); shutil.copy2(main, U + '/夜莺啾啾工具箱.html')
assert len(re.findall(r'</script', shell, re.I)) == 1
zp = U + '/夜莺2.0离线工具包.zip'
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(O)): z.write(O + '/' + fn, '夜莺2.0离线工具包/' + fn)
files = {fn: sha(O + '/' + fn) for fn in sorted(os.listdir(O))}
json.dump(files, open(U + '/文件核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
bj = json.load(open(U + '/构建核验.json', encoding='utf-8')); bj['文件'] = files; json.dump(bj, open(U + '/构建核验.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
rep = json.load(open(B + '/115_练习例字补扩展字/实装报告.json', encoding='utf-8')); rep['单文件SHA256'] = sha(main); rep['啾啾SHA256'] = sha(U + '/夜莺啾啾工具箱.html'); rep['离线包zipSHA256'] = sha(zp); rep['两列分隔线'] = '右列左侧 2px 竖线，窄屏单列时不显示'
json.dump(rep, open(B + '/115_练习例字补扩展字/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# sync.py 里的规则同步改掉，重跑不会退回
sp = B + '/115_练习例字补扩展字/sync.py'; s = open(sp, encoding='utf-8').read(); assert old in s; open(sp, 'w', encoding='utf-8').write(s.replace(old, new))
print('分隔线已加')
