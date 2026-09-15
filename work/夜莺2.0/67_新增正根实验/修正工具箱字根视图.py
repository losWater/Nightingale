from pathlib import Path
import json,re,zipfile,hashlib

W=Path('E:/夜莺2.0/work/夜莺2.0')
U=W/'65_群友离线工具包'; O=U/'夜莺2.0离线工具包'
MAIN=U/'夜莺2.0随身工具_单文件.html'

def load_views(shell):
 i=shell.index('const views=')+len('const views=')
 views,n=json.JSONDecoder().raw_decode(shell[i:])
 return views,i,i+n

def save(path,text,encoding='utf-8'):
 path.write_text(text,encoding=encoding,newline='')

shell=MAIN.read_text(encoding='utf-8-sig')
views,a,b=load_views(shell)

# 字根表：把此前为了练习进度而追加在表尾的“正”移回 S 键的止根族中。
roots=views['roots']
row='<tr><td>s</td><td>正</td><td>走／止／足／定字底</td><td>政、整、焉、证</td></tr>'
roots=re.sub(r'<tr><td>s</td><td>正</td><td>(?:归并：止|走／止／足／定字底)</td><td>.*?</td></tr>','',roots)
anchor=re.search(r'<tr><td>s</td><td>止</td><td>走／止／足／定字底</td><td>.*?</td></tr>',roots)
assert anchor and row not in roots
roots=roots[:anchor.end()]+row+roots[anchor.end():]
views['roots']=roots

# 字根图：紧凑键盘和展开表都直接写出“正”，不再只能靠搜索/展开发现。
image=views['image']
image=image.replace('走／止／足／定字底','走／止／正／足／定字底')
assert '走／止／正／足／定字底' in image and '止、正、足' in image
views['image']=image

for key,name in {'roots':'字根总表.html','image':'字根图.html'}.items():
 save(O/name,views[key])

# 配套纯文本表使用实际根族名；练习页面及其队列不改。
keyfile=O/'字根键位表.txt'
keytext=keyfile.read_text(encoding='utf-8-sig')
keytext=keytext.replace('正\ts\t归并：止','正\ts\t走／止／足／定字底')
save(keyfile,keytext,'utf-8-sig')

newshell=shell[:a]+json.dumps(views,ensure_ascii=False,separators=(',',':'))+shell[b:]
save(MAIN,newshell)
save(U/'夜莺啾啾工具箱.html',newshell)

with zipfile.ZipFile(U/'夜莺2.0离线工具包.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(O.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(U).as_posix())
with zipfile.ZipFile(U/'夜莺2.0离线工具包.zip') as z:assert z.testzip() is None

audit={
 '字根表':'正位于S键止根之后，所属根族为走／止／足／定字底',
 '字根图':'紧凑与展开标题显示走／止／正／足／定字底，成员含正',
 '练习进度':'未改练习页面、题序或本地存储签名',
 '单文件SHA256':hashlib.sha256(MAIN.read_bytes()).hexdigest(),
 '离线包SHA256':hashlib.sha256((U/'夜莺2.0离线工具包.zip').read_bytes()).hexdigest(),
 '状态':'通过'
}
save(U/'正根视图同步核验.json',json.dumps(audit,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(audit,ensure_ascii=False))
