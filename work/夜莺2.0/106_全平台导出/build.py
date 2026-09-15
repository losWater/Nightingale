from pathlib import Path
from collections import defaultdict,Counter
import json,re,csv,zipfile,shutil,hashlib

P=Path(__file__).resolve().parent; W=P.parent
OUT=P/'夜莺2.0_字词表与输入法'; OUT.mkdir(exist_ok=True)
SRC=W/'113_扩展字入表/夜莺2.0最终表_普通格式.txt'   # 2026-09-16 含扩展字   # 2026-09-15 换源：最终表（78 单字 + 91 普通词 + 102 二字简词 + 103 三字词三码）
def write(p,s,enc='utf-8-sig'):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding=enc,newline='')
def js(p,obj):write(p,json.dumps(obj,ensure_ascii=False,indent=2),'utf-8')
rows=[tuple(x.rsplit('\t',1)) for x in SRC.read_text(encoding='utf-8-sig').splitlines() if x]
assert len(rows)==len(set(rows))
pointer={'单字表':'78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt','字词表':'113_扩展字入表/夜莺2.0最终表_普通格式.txt（110 投票序 + 112 扩展字）'}
baseline=W/'78_纯单字表核验'
single=[tuple(x.rsplit('\t',1)) for x in (baseline/'夜莺2.0纯单字表_普通格式.txt').read_text(encoding='utf-8-sig').splitlines() if x]+[tuple(x.rsplit('\t',1)) for x in (W/'112_扩展字继承/夜莺2.0扩展字表_普通格式.txt').read_text(encoding='utf-8-sig').splitlines() if x]   # 2026-09-16 加扩展字
assert set(single)=={(t,c) for t,c in rows if len(t)==1}
def short(t,c):
 # Punctuation is not a word character: 说道：“ is still the two-character phrase 说道.
 return len(c)<4 and len(t)>1 and (sum('\u3400'<=x<='\u9fff' for x in t)<4 or t.startswith('$ddcmd('))
no_short=[(t,c) for t,c in rows if not short(t,c)]
for label,rr in [('有简词',rows),('无简词',no_short)]:
 for reverse in [False,True]:
  write(OUT/'普通字词表'/f'夜莺2.0_{label}_{"码前" if reverse else "普通"}.txt',''.join(f'{c}\t{t}\r\n' if reverse else f'{t}\t{c}\r\n' for t,c in rr))
groups=defaultdict(list)
for t,c in rows:groups[c].append(t)
quick=[]
for line in (P/'参考模板/快符原表.txt').read_text(encoding='utf-8-sig').splitlines():
 m=re.fullmatch(r'([a-z]+),(\d+)=(.+)',line)
 if m:
  c,n,t=m.groups();n=int(n);quick.append((t,c,n))
  if t not in groups[c]:groups[c].insert(n-1,t)
assert len(quick)==40
quickset={(t,c) for t,c,n in quick}
allrows=[(t,c,n) for c in sorted(groups) for n,t in enumerate(groups[c],1)]
assert all(groups[c][n-1]==t for t,c,n in quick)
unsupported=[r for r in allrows if r[0].startswith('$ddcmd(')]
write(OUT/'说明与核验/未移植的源输入法专用宏.txt',''.join(f'{t}\t{c}\t{n}\r\n' for t,c,n in unsupported))
allrows=[r for r in allrows if not r[0].startswith('$ddcmd(')]
valid=[(t,c,n) for t,c,n in allrows if re.fullmatch('[a-z]{1,4}',c)]
excluded=[(t,c,n) for t,c,n in allrows if len(c)>4]
write(OUT/'说明与核验/超过四码_原表保留.txt',''.join(f'{t}\t{c}\t{n}\r\n' for t,c,n in excluded))
write(OUT/'普通字词表/夜莺2.0_快符_码前.txt',''.join(f'{c}\t{t}\r\n' for t,c,n in quick))
modules=defaultdict(list)
for t,c,n in allrows:
 if (t,c) in quickset:k='04_快符'
 elif len(t)==1:k='01_核心单字'
 elif short(t,c):k='03_简词'
 else:k='02_普通全码词'
 modules[k].append((t,c,n))
for k,rr in modules.items():write(OUT/'手心/模块化挂接'/f'{k}.txt',''.join(f'{c}={n},{t}\n' for t,c,n in rr),'utf-8')
aux=defaultdict(list)
for t,c in single:
 if len(c)==4 and c[2:] not in aux[t]:aux[t].append(c[2:])
auxtext=''.join(t+'='+' '.join(cs)+'\r\n' for t,cs in sorted(aux.items()))
write(OUT/'手心/夜莺2.0_辅助码.txt',auxtext,'utf-8')
write(OUT/'手心/夜莺2.0_辅助码_Unicode.txt',auxtext,'utf-16')
write(OUT/'手心/使用说明.txt','四个挂接模块可同时启用；不需要简词或快符可分别停用03或04。不要与旧整合挂接表重复导入。\r\n各模块继承完整字词表的候选序号，不因关闭模块重新编号。02包含普通二、三字全码词，以及四字及以上词；关闭02会一起停用这些词。\r\n辅助码与挂接独立导入辅助码设置；两个辅助码文件内容相同，按导入支持选UTF-8或Unicode版之一。辅助码取当前单字全码最后两位，同字多码空格分隔。\r\n本次字集15496字：8105通用规范汉字加7391个扩展字（新华字典多出的字，含繁体旧字形）；扩展字全码排在同码位现有字词之后，01模块与辅助码文件均已包含。\r\n')
sogou=[r for r in allrows if not(len(r[0])==2 and len(r[1])==4 and (r[0],r[1]) not in quickset)]
assert len(sogou)<=100000
write(OUT/'搜狗挂接/夜莺2.0_挂接_含快符.txt',''.join(f'{c},{n}={t}\r\n' for t,c,n in sogou),'utf-16')
# Candidate numbers are assigned BEFORE filtering: omitted words leave a real empty slot.
gaps=[r for r in sogou if len(r[0])==1 and r[2]==2 and len(groups[r[1]][0])==2 and len(r[1])==4]
assert gaps
wordmeta={}
for name in ['综合词表_审计候选.jsonl','鲸凉鹤补全候选.jsonl']:
 for line in (W/'08_词库与词频重建'/name).read_text(encoding='utf-8-sig').splitlines():
  r=json.loads(line);wordmeta.setdefault(r['词'],r)
explicit=json.loads((W/'64_加入鲸凉鹤简词/码位人工指定.json').read_text(encoding='utf-8-sig'))
protected={(t,c) for c,ts in explicit.items() for t in ts}|quickset
removable=[r for r in valid if len(r[0])>1 and len(r[1])==4 and r[2]>1 and (r[0],r[1]) not in protected]
# Remove tail candidates first, then lower corpus index. Never remove a character, short code,
# first candidate, explicitly assigned entry or quick symbol.
removable.sort(key=lambda r:(-r[2],wordmeta.get(r[0],{}).get('排序指数',0),r[1],r[0]))
cut=removable[:max(0,len(valid)-200000)];cutset=set(cut);wubi=[r for r in valid if r not in cutset]
assert len(wubi)<=200000 and len(wubi)+len(cut)==len(valid)
write(OUT/'搜狗五笔/夜莺2.0_五笔_含快符.txt',''.join(f'{c}\t{t}\r\n' for t,c,n in wubi),'utf-8')
write(OUT/'说明与核验/搜狗五笔_容量裁剪明细.txt','字词\t编码\t原候选位\r\n'+''.join(f'{t}\t{c}\t{n}\r\n' for t,c,n in cut))
header='[CODETABLEHEADER]\r\nName=夜莺2.0词库\r\nVersion=2.0|260915\r\nAuthor=nightingale\r\nCodeScheme=夜莺2.0[夜莺]\r\nCodeLength=4\r\nBWCodeLength=0\r\nSpecialPrefix=0\r\nPhraseRule=3\r\npa2=w11w12w21w22\r\npa3=w11w21w31\r\npe4=w11w21w31r11\r\n[CODETABLE]\r\n'
write(OUT/'冰凌五笔/夜莺2.0_词库_含快符.txt',header+''.join(f'{c}\t{t}\t{10000-n}\r\n' for t,c,n in valid),'utf-16')
write(OUT/'Bime/mb/夜莺2.0/夜莺字词.txt',''.join(f'{t}\t{c}\t{100000-n}\r\n' for t,c,n in valid))
splitrows=list(csv.DictReader((W/'55_拆分继承核验/当前完整拆分表.txt').open(encoding='utf-8-sig'),delimiter='\t'))
splits={r['汉字']:r['完整拆分'] for r in splitrows}
for r in csv.DictReader((W/'112_扩展字继承/夜莺2.0扩展字拆分表.txt').open(encoding='utf-8-sig'),delimiter='	'):splits.setdefault(r['汉字'],r['完整拆分'])   # 2026-09-16 扩展字拆分一并进 Bime 拆分文件与 Rime 反查
write(OUT/'Bime/mb/夜莺2.0/夜莺.拆分',''.join(f'{t}\t{s}\r\n' for t,s in splits.items()))
write(OUT/'Bime/使用说明.txt','将mb内的夜莺2.0文件夹复制到Bime的mb目录，再重载码表、选择夜莺2.0。最大码长设4。包含快符及全部15496字（8105通用规范汉字+7391扩展字）的拆分。没有覆盖个人config.txt或用户调整.txt。旧个人调频可能改变候选顺序。\r\n')
report={'基线':pointer,'来源SHA256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'原表条数':len(rows),'无简词条数':len(no_short),'无简词口径':'删除二、三字且不足四码的简词；保留全部单字、四码及以上词、四字及以上词。快符单列。','快符':len(quick),'四码内含快符':len(valid),'超过四码条目':len(excluded),'手心模块':{k:len(v) for k,v in modules.items()},'辅助码字数':len(aux),'搜狗挂接条数':len(sogou),'搜狗挂接保留次选起步单字数':len(gaps),'搜狗五笔条数':len(wubi),'搜狗五笔裁剪条数':len(cut),'裁剪口径':'只裁全码非首选词；候选位越后越先裁，同位按现有综合排序指数由低到高；保留所有单字、简词、快符及人工指定项。未回写源表。','冰凌及Bime条数':len(valid)}
report['未移植专用宏']=len(unsupported)
report['无简词口径']='不足四码的词条，仅保留含四个及以上汉字的词；标点不计字数，因此说道：“属于简词。不足四码的外文短语、符号串及源输入法专用宏一并从无简词版移除；快符独立提供。单字和全部四码及以上条目保留。'
js(OUT/'说明与核验/生成清单.json',report)
write(OUT/'使用说明.txt','夜莺2.0 最终表导出，2026-09-16：单字表（78，8105 字 13 项核验）+ 普通词（109 四家共识筛选）+ 二字简词（102）+ 三字词三码（103）合并，词序三家投票（110），再加 7391 个扩展字（112/113，新华字典多出的字，含繁体旧字形；全码排同码位现有字词之后）为最终表 155139 条；简码位字在前、简词在后。\r\n普通字词表：普通=字词在前；码前=编码在前；无简词仍保留四字及以上词。普通表不混入快符，快符单列；各平台码表已包含快符，手心为独立模块。\r\n搜狗挂接为自定义短语格式，UTF-16LE BOM；不包含四码二字词，删词后保留原序号，让位字从2开始。\r\n搜狗五笔为编码TAB字词，UTF-8；按20万条上限裁剪，清单见说明与核验。冰凌为UTF-16LE BOM专用文本词库。\r\n手心挂接使用UTF-8；Bime使用UTF-8 BOM、CRLF。\r\n定长四码平台不导入超过四码的条目，完整内容仍在普通表，并附单独清单。Rime独立打包。\r\n除Rime引擎核验外，其他平台本次为格式及数据核验，未在输入法界面实测导入。\r\n')

# Reuse the published adapters and model only. All character/word tables and split data
# are rebuilt from this E: workspace; do not carry over 1.0 dictionaries or user data.
freqrows=json.loads((W/'32_多来源字频重建/试验整字频率.json').read_text(encoding='utf-8-sig'))['字表']
rank={r['字']:r['新排名'] for r in freqrows}
freq={r['字']:max(1,int(r['每百万核心字预计次数']*100)) for r in freqrows}
soundrows=json.loads((W/'54_补删鹿旁保留羊南心四起点试跑/frozen/字音基准.json').read_text(encoding='utf-8-sig'))
pinyin={r['拼音']:r['音码'] for r in soundrows};pinyin['en']='en'
full=defaultdict(list)
for t,c in single:
 if len(c)==4:full[t,c[:2]].append(c)
fallback={};lex={};short_fb=set();short_lex=set()   # 2026-09-16 简词（词条码长<4）单独记，默认不进整句
def add(t,c,f):fallback[t,c]=max(fallback.get((t,c),0),max(1,int(f)))
def native(t,c,f,n=1):lex[c,t]=(n,rank.get(t,20001),max(1,int(f)))
for (t,py),cs in full.items():
 for c in cs:
  add(t,c[:2]+';'+c[2:],freq.get(t,1))
  for spelling in [c[:2],c[:3],c]:native(t,spelling,freq.get(t,1))
word_sound={}; unresolved=[]
for t,c,n in valid:
 if len(t)<2 or (t,c) in quickset or not all('\u3400'<=ch<='\u9fff' for ch in t):continue
 f=max(1,int(wordmeta.get(t,{}).get('排序指数',0)*1000000))
 # The reviewed fixed spelling always remains available, including short phrases.
 add(t,c,max(f,100000//n) if len(c)<4 else f);native(t,c,f,n)
 if len(c)<4:short_fb.add((t,c));short_lex.add((c,t))
 pys=[c[:2],c[2:]] if len(t)==2 and len(c)==4 else None
 if pys is None:
  r=wordmeta.get(t,{})
  py=r.get('采用拼音') or r.get('主读音')
  if py:pys=[pinyin.get(x) for x in py.split()]
 if pys and len(pys)==len(t) and all((ch,py) in full for ch,py in zip(t,pys)):
  word_sound[t]=pys
for t,pys in word_sound.items():
 codes=[full[ch,py][0] for ch,py in zip(t,pys)]
 f=max(1,int(wordmeta.get(t,{}).get('排序指数',0)*1000000))
 add(t,' '.join(c[:2]+';'+c[2:] for c in codes),f);native(t,''.join(pys),f)
 if len(t)==2:
  add(t,pys[0]+' '+pys[1]+codes[0][2],f);native(t,''.join(pys)+codes[0][2],f)
sounds=defaultdict(list)
for (t,py),cs in full.items():sounds[py].append([t,splits.get(t,''),cs,99999,1])
for v in sounds.values():v.sort(key=lambda r:(rank.get(r[0],99999),r[0]))
def lua(v):
 if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
 if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
 if isinstance(v,dict):return '{'+','.join('['+lua(k)+']='+lua(val) for k,val in v.items())+'}'
 return str(v)
def dicttext(name,rr):return '# Rime dictionary\n---\nname: '+name+'\nversion: "2.0-20260915"\nsort: by_weight\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n'+''.join('\t'.join(map(str,r))+'\n' for r in rr)
legacy=Path('D:/nightingale/releases/v1.0/02_输入法挂接/rime/发布包')
for kind,label in [('light','轻量版'),('main','主力版')]:
 dest=P/f'Rime_{label}';dest.mkdir(exist_ok=True)
 z=zipfile.ZipFile(next(legacy.glob(f'*-{kind}-*.zip')))
 for name in z.namelist():
  if name in ['yeying_rime.dict.yaml','yeying_rime_fixed.dict.yaml','mohu/data/yeying.lexicon.txt','lua/yeying_lookup_data.lua','使用说明.md','测试报告与维护记录.md','Rime试用调整记录.md'] or name.startswith('maintenance/'):continue
  data=z.read(name)
  newname=name.replace('yeying_','yeying20_')
  if name.endswith(('.yaml','.lua')) or name.endswith('.yaml.example'):
   s=data.decode('utf-8-sig').replace('yeying_','yeying20_').replace('1.0-rime-test1','2.0-20260915').replace('夜莺·','夜莺2.0·')
   # Give the 2.0 lexicon its own path while retaining the shared licensed V5 model.
   s=s.replace('mohu/data/yeying.lexicon.txt','mohu/data/yeying20.lexicon.txt')
   if name=='lua/yeying_mix.lua':s=s.replace('if #input <= 4 then','if #input > 0 then')
   data=s.encode('utf-8')
  q=dest/newname;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 # 2026-09-16 群友需求：Ctrl+N 钉选 + 自动造词。覆盖层 rime_overlay/：新 lua（pin、pin_key、改过的 mix）与 fixed 配置块；主力/轻量两方案生效，形码模式不动。
 ov=P/'rime_overlay'
 for f in sorted((ov/'lua').glob('*.lua')):shutil.copy2(f,dest/'lua'/f.name)
 for sch in ['yeying20_main.schema.yaml','yeying20_light.schema.yaml']:
  sp=dest/sch
  if not sp.exists():continue
  s=sp.read_text(encoding='utf-8')
  proc='  - lua_processor@*yeying20_lookup_key\n';old_fixed='fixed:\n  dictionary: yeying20_rime_fixed\n  enable_user_dict: false\n  enable_sentence: false\n  enable_completion: false\n  initial_quality: 100\n'
  assert s.count(proc)==1 and s.count(old_fixed)==1,sch
  s=s.replace(proc,proc+'  - lua_processor@*yeying20_pin_key\n').replace(old_fixed,(ov/'fixed_block.yaml').read_text(encoding='utf-8'))
  sw='  states:\n  - 。，\n  - ．，\n';assert s.count(sw)==1,sch
  s=s.replace(sw,sw+'- name: yeying_short_words\n  reset: 0\n  states:\n  - 简词不进整句\n  - 简词进整句\n')   # 2026-09-16 群友反馈：简词混进整句影响识别，默认关
  ts='translator_short:\n  dictionary: yeying20_rime_short\n  user_dict: yeying20_%s_short\n  enable_user_dict: true\n  enable_completion: false\n  contextual_suggestions: false\n  max_homophones: 7\n  max_homographs: 7\n  max_sentences: 2\n'%kind
  assert s.count('fixed:\n  dictionary: yeying20_rime_fixed\n')==1,sch;s=s.replace('fixed:\n  dictionary: yeying20_rime_fixed\n',ts+'fixed:\n  dictionary: yeying20_rime_fixed\n')
  if '  lexicon: mohu/data/yeying20.lexicon.txt\n' in s:s=s.replace('  lexicon: mohu/data/yeying20.lexicon.txt\n','  lexicon: mohu/data/yeying20.lexicon.txt\n  lexicon_short: mohu/data/yeying20_short.lexicon.txt\n')
  sp.write_text(s,encoding='utf-8')
 write(dest/'yeying20_rime_fixed.dict.yaml',dicttext('yeying20_rime_fixed',[(t,c,100000-n) for t,c,n in allrows]),'utf-8')
 write(dest/'yeying20_rime.dict.yaml',dicttext('yeying20_rime',[(t,c,f) for (t,c),f in sorted(fallback.items()) if (t,c) not in short_fb]),'utf-8')   # 默认：简词不进整句
 write(dest/'yeying20_rime_short.dict.yaml',dicttext('yeying20_rime_short',[(t,c,f) for (t,c),f in sorted(fallback.items())]),'utf-8')   # 开关开启：含简词
 write(dest/'lua/yeying20_lookup_data.lua','return '+lua({'sounds':dict(sounds),'pinyin':pinyin})+'\n','utf-8')
 if kind=='main':
  write(dest/'mohu/data/yeying20.lexicon.txt',''.join('\t'.join(map(str,[c,t,*v]))+'\n' for (c,t),v in sorted(lex.items()) if (c,t) not in short_lex),'utf-8')
  write(dest/'mohu/data/yeying20_short.lexicon.txt',''.join('\t'.join(map(str,[c,t,*v]))+'\n' for (c,t),v in sorted(lex.items())),'utf-8')
 order=['yeying20_main','yeying20_light'] if kind=='main' else ['yeying20_light','yeying20_main']   # 2026-09-15 用户要求解压即用：直接提供 default.custom.yaml，缺失方案 Rime 仅记日志不影响部署（已实测）
 write(dest/'default.custom.yaml','patch:'+chr(10)+'  schema_list:'+chr(10)+''.join('    - schema: '+x+chr(10) for x in order+['yeying20_xm']),'utf-8');(dest/'default.custom.yaml.example').unlink(missing_ok=True)
 write(dest/'使用说明.md',f'# 夜莺2.0 Rime · {label}\n\n把本包全部文件解压到 Rime 用户目录（小狼毫：右键托盘图标 → 用户文件夹），然后右键托盘图标 → 重新部署，即可直接使用，不需要手动改任何配置。包内 default.custom.yaml 已把 `yeying20_{kind}` 设为首选方案；如果你原来有自己的 default.custom.yaml，解压时会被覆盖，请先备份并把 schema_list 合并。两个包可共存（后解压的为首选，F4 可切换）；文件和用户词典使用 2.0 独立名称。\n\n包含当前定稿单字、简词、全码词和40条快符；空格首选、分号次选、单引号三选。支持F2持续拆分提示以及反引号双拼、波浪号全拼反查。拆分和辅助码已更新2.0（含正根）。\n\n轻量版使用Rime原生整句；主力版沿用V5模型及Windows x64原生引擎，最多36键进入V5，超过后原生整句接续。主力运行库沿用原包，未验证其他操作系统。\n\n固定码表逐项继承当前字词表顺序。整句词典重新生成；只有能与当前字音、全码对应的词生成逐字辅助拼写，其余保留固定入口，没有猜测多音字读音。旧版准确率报告不适用于2.0；本次验证记录见包内核验结果。\n','utf-8')
 write(dest/'使用说明.md',(dest/'使用说明.md').read_text(encoding='utf-8').rstrip('\n')+'\n\n## 钉选与造词（2026-09-16 新增，主力版/轻量版）\n\n- **Ctrl+数字 钉选 / 加词**：候选里第 N 个是你想要的，按 Ctrl+N 上屏。它若是码表候选，就同时钉为这个编码的首选，原来的候选依次后退，再钉别的会排到它前面（记在用户目录 `yeying20_pin.txt`，一行一个编码，制表符分隔，重启不丢，想撤销就删掉那一行再重新部署）；它若是整句或联想出来、码表里没有的词，就按夜莺词规则自动加进 `yeying20_words.txt`，下次打它的码就在候选里（带〔造〕）。\n- **自动造词（只限二字词）**：连续打出两个字，Rime 自动把这两个字按双拼四码存进用户词典 `yeying20_fixed_user`；下次打这个四码它出现在候选末尾。不想要的词选中后按 Shift+Delete 删除。\n- **Ctrl+Enter 主动造词（不限长度）**：把想要的词打出来（整句拼、逐字打都行），在上屏前按 Ctrl+Enter：当前将要上屏的整段文字按夜莺词规则编码（二字取两字双拼四码，三字取三字首码，四字及以上取前三字首码加末字首码；多音字取全部读音组合）写进用户目录 `yeying20_words.txt`，同时上屏。下次打那个码它就在候选里，带〔造〕标记；选中后 Shift+Delete 删除，Ctrl+N 可钉。\n- 码表候选的顺序不会随使用频率自动变化：钉过的在前，其余按码表原序，造的词排最后。\n- **简词进整句（开关，默认关）**：整句默认只用单字与四码词拼句，不混入简词（二简词、三字三码等），识别更稳；想让简词也参与整句，按 Ctrl+` 打开方案菜单，切到"简词进整句"即可，主力版切换时会重新加载整句引擎，约几秒。\n','utf-8')
 report['Rime固定条数']=len(allrows);report['Rime整句词典条数']=len(fallback)-len(short_fb);report['Rime整句词典条数_含简词']=len(fallback);report['简词条数_默认不进整句']=len(short_fb);report['Rime逐字拼写词数']=len(word_sound);report['Rime原生词边数']=len(lex)
 print('generated',label,flush=True)
js(OUT/'说明与核验/生成清单.json',report)
print(json.dumps(report,ensure_ascii=False),flush=True)
