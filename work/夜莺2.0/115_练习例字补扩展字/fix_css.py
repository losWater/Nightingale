# -*- coding: utf-8 -*-
"""修正：两列样式误插在 @media(max-width:600px) 块内（且重跑时插了两次），改为放在样式表末尾。"""
import io, sys, os, re, json, hashlib, zipfile, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'; U = B + '/65_群友离线工具包'; O = U + '/夜莺2.0离线工具包'
def get(s, name):
    m = re.search(r'\b(?:const|let) ' + re.escape(name) + r'\s*=\s*', s); assert m, name
    obj, n = json.JSONDecoder().raw_decode(s[m.end():]); return obj, m.end(), m.end() + n
def put(s, name, obj):
    _, a, b = get(s, name); return s[:a] + json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c') + s[b:]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
bad = '\n#example{display:grid;grid-template-columns:1fr 1fr;column-gap:28px;align-items:start}@media(max-width:600px){#example{grid-template-columns:1fr}}'
good = '#example{display:grid;grid-template-columns:1fr 1fr;column-gap:28px;align-items:start}@media(max-width:600px){#example{grid-template-columns:1fr}}\n</style>'
def fix(pv):
    n = pv.count(bad); assert n >= 1, n
    pv = pv.replace(bad, '')
    i = pv.find('</style>'); assert i > 0 and pv.count('</style>') == 1
    pv = pv[:i] + good + pv[i + len('</style>'):]
    # 确认新规则在 @media 外：它前面最后一个未闭合的 { 数应为 0
    head = pv[:pv.find(good)]
    assert head[head.rfind('<style'):].count('{') == head[head.rfind('<style'):].count('}'), '仍在某个块内'
    return pv
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
rep = json.load(open(B + '/115_练习例字补扩展字/实装报告.json', encoding='utf-8')); rep['单文件SHA256'] = sha(main); rep['啾啾SHA256'] = sha(U + '/夜莺啾啾工具箱.html'); rep['离线包zipSHA256'] = sha(zp); rep['两列样式修正'] = '原插在 @media(max-width:600px) 内，已移到样式表末尾'
json.dump(rep, open(B + '/115_练习例字补扩展字/实装报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已修正；样式位置:', pv[pv.find(good) - 60:pv.find(good) + 40].replace('\n', ' '))
