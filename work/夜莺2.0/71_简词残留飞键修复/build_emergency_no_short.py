from pathlib import Path
from collections import defaultdict
import re,json,zipfile,hashlib,csv,shutil

W=Path('E:/夜莺2.0/work/夜莺2.0');P=W/'71_简词残留飞键修复'
SRC=W/'64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt'
OUT=P/'夜莺2.0无简词紧急版';OUT.mkdir(exist_ok=True)
def write(p,s,enc='utf-8-sig'):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding=enc,newline='')
rows=[tuple(x.rsplit('\t',1)) for x in SRC.read_text(encoding='utf-8-sig').splitlines() if x]
# 安全口径：单字全部保留；词语只保留四码及以上入口。这样不仅移除二三字简词，
# 也移除少量四字词的非标准二三码别名；其标准四码仍保留。
safe=[(t,c) for t,c in rows if len(t)==1 or len(c)>=4]
assert all(len(t)==1 or len(c)>=4 for t,c in safe)
write(OUT/'普通字词表/夜莺2.0无简词_普通格式.txt',''.join(f'{t}\t{c}\r\n' for t,c in safe))
write(OUT/'普通字词表/夜莺2.0无简词_码前格式.txt',''.join(f'{c}\t{t}\r\n' for t,c in safe))

quick=[]
for s in Path('D:/nightingale/symbo.txt').read_text(encoding='utf-8-sig').splitlines():
 m=re.fullmatch(r'([a-z]+),(\d+)=(.+)',s)
 if m:quick.append((m[3],m[1],int(m[2])))
assert len(quick)==40
groups=defaultdict(list)
for t,c in rows:groups[c].append(t)
for t,c,n in quick:
 if t not in groups[c]:groups[c].insert(n-1,t)
quickset={(t,c) for t,c,n in quick}
allrank=[(t,c,n) for c in sorted(groups) for n,t in enumerate(groups[c],1)]
keep={(t,c) for t,c in safe}|quickset
fixed=[r for r in allrank if (r[0],r[1]) in keep and not r[0].startswith('$ddcmd(')]
assert all(len(t)==1 or len(c)>=4 or (t,c) in quickset for t,c,n in fixed)

for name,rr in {
 '01_核心单字':[r for r in fixed if len(r[0])==1],
 '02_普通全码词':[r for r in fixed if len(r[0])>1 and (r[0],r[1]) not in quickset],
 '04_快符':[r for r in fixed if (r[0],r[1]) in quickset],
}.items():write(OUT/'手心/模块化挂接'/f'{name}.txt',''.join(f'{c}={n},{t}\n' for t,c,n in rr),'utf-8')

aux=defaultdict(list)
for t,c in rows:
 if len(t)==1 and len(c)==4 and c[2:] not in aux[t]:aux[t].append(c[2:])
auxtext=''.join(t+'='+' '.join(cs)+'\r\n' for t,cs in sorted(aux.items()))
write(OUT/'手心/夜莺2.0_辅助码.txt',auxtext,'utf-8')
write(OUT/'手心/夜莺2.0_辅助码_Unicode.txt',auxtext,'utf-16')

sogou=[r for r in fixed if not(len(r[0])==2 and len(r[1])==4 and (r[0],r[1]) not in quickset)]
assert len(sogou)<=100000
write(OUT/'搜狗挂接/夜莺2.0无简词_挂接_含快符.txt',''.join(f'{c},{n}={t}\r\n' for t,c,n in sogou),'utf-16')
wubi=[r for r in fixed if len(r[1])<=4]
assert len(wubi)<=200000
write(OUT/'搜狗五笔/夜莺2.0无简词_五笔_含快符.txt',''.join(f'{c}\t{t}\r\n' for t,c,n in wubi),'utf-8')
header='[CODETABLEHEADER]\r\nName=夜莺2.0无简词紧急版\r\nVersion=2.0|260914\r\nAuthor=nightingale\r\nCodeScheme=夜莺2.0[夜莺]\r\nCodeLength=4\r\nBWCodeLength=0\r\nSpecialPrefix=0\r\nPhraseRule=3\r\npa2=w11w12w21w22\r\npa3=w11w21w31\r\npe4=w11w21w31r11\r\n[CODETABLE]\r\n'
write(OUT/'冰凌五笔/夜莺2.0无简词_含快符.txt',header+''.join(f'{c}\t{t}\t{10000-n}\r\n' for t,c,n in wubi),'utf-16')
write(OUT/'Bime/mb/夜莺2.0无简词/夜莺字词.txt',''.join(f'{t}\t{c}\t{100000-n}\r\n' for t,c,n in wubi))
split=W/'55_拆分继承核验/当前完整拆分表.txt'
ss=list(csv.DictReader(split.open(encoding='utf-8-sig'),delimiter='\t'))
write(OUT/'Bime/mb/夜莺2.0无简词/夜莺.拆分',''.join(f"{r['汉字']}\t{r['完整拆分']}\r\n" for r in ss))

info={
 '来源':str(SRC),'来源SHA256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
 '原表':len(rows),'安全版字词':len(safe),'平台固定条目含快符':len(fixed),
 '快符':len(quick),'搜狗挂接':len(sogou),'搜狗五笔':len(wubi),
 '口径':'单字全部保留；词语只保留四码及以上入口；40条快符例外保留。四字及以上词的标准四码保留，少量二三码别名移除。',
 '候选序号':'继承完整版原候选序号；移除项留空，不把后续候选挤到前面。',
 '状态':'数据与格式核验通过'
}
write(OUT/'使用说明.txt','夜莺2.0无简词紧急安全版。\r\n'+info['口径']+'\r\n'+info['候选序号']+'\r\n手心为01核心单字、02普通全码词、04快符三个模块；没有03简词模块。\r\n搜狗挂接继续排除四码二字词，容量不超过10万；搜狗五笔不超过20万。\r\nRime包体较大，本紧急包先提供普通表、手心、搜狗、冰凌和Bime。\r\n')
write(OUT/'生成核验.json',json.dumps(info,ensure_ascii=False,indent=2),'utf-8')

# Cross-format assertions.
assert len({(t,c) for t,c in safe})==len(safe)
assert {(t,c) for t,c,n in fixed if (t,c) not in quickset}=={(t,c) for t,c in safe if not t.startswith('$ddcmd(')}
assert set(quickset)<={(t,c) for t,c,n in fixed}
assert len(sogou)<100000 and len(wubi)<200000
target=P/'夜莺2.0无简词紧急版_含快符.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(OUT.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(OUT).as_posix())
with zipfile.ZipFile(target) as z:assert z.testzip() is None
h=hashlib.sha256(target.read_bytes()).hexdigest()
write(target.with_suffix('.zip.sha256'),h+'  '+target.name+'\n','utf-8')
print(json.dumps(info,ensure_ascii=False));print(target,target.stat().st_size,h)
