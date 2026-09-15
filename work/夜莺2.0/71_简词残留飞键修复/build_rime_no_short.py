from pathlib import Path
import re,shutil,os,zipfile,hashlib,json

W=Path('E:/夜莺2.0/work/夜莺2.0');P=W/'71_简词残留飞键修复'
BASE=W/'70_全平台导出';SAFE=P/'夜莺2.0无简词紧急版'
fixed=[]
for p in (SAFE/'手心/模块化挂接').glob('*.txt'):
 for s in p.read_text(encoding='utf-8-sig').splitlines():
  c,tail=s.split('=',1);n,t=tail.split(',',1);fixed.append((t,c,int(n)))
fixed.sort(key=lambda r:(r[1],r[2]))
assert all(len(t)==1 or len(c)>=4 or p for t,c,n in fixed)

def dictionary(name,rows):
 return '# Rime dictionary\n---\nname: '+name+'\nversion: "2.0-noshort-20260914"\nsort: by_weight\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n'+''.join(f'{t}\t{c}\t{w}\n' for t,c,w in rows)

reports={}
for kind,label in [('light','轻量版'),('main','主力版')]:
 src=BASE/f'Rime_{label}';dst=P/f'Rime无简词_{label}'
 if dst.exists():shutil.rmtree(dst)
 def copier(a,b):
  if str(a).endswith('.bin'):os.link(a,b)
  else:shutil.copy2(a,b)
 shutil.copytree(src,dst,copy_function=copier)
 # Remove generated dictionaries; rebuild them with independent names.
 oldfixed=dst/'yeying20_rime_fixed.dict.yaml'; oldsmart=dst/'yeying20_rime.dict.yaml'
 smart=[];removed_smart=[]
 for s in oldsmart.read_text(encoding='utf-8').split('...\n',1)[1].splitlines():
  if not s:continue
  t,c,w=s.split('\t',2)
  # Plain 1-3 key phrase spellings are fixed short phrases. Spaced/semicolon
  # spellings are normal syllable/full-character spellings and remain.
  if len(t)>1 and re.fullmatch(r'[a-z]{1,3}',c):removed_smart.append((t,c,w))
  else:smart.append((t,c,w))
 oldfixed.unlink();oldsmart.unlink()
 (dst/'yeying20_noshort_rime_fixed.dict.yaml').write_text(dictionary('yeying20_noshort_rime_fixed',[(t,c,100000-n) for t,c,n in fixed]),encoding='utf-8')
 (dst/'yeying20_noshort_rime.dict.yaml').write_text(dictionary('yeying20_noshort_rime',smart),encoding='utf-8')
 schema=dst/f'yeying20_{kind}.schema.yaml';text=schema.read_text(encoding='utf-8')
 text=text.replace('yeying20_rime_fixed','yeying20_noshort_rime_fixed').replace('yeying20_rime','yeying20_noshort_rime')
 text=text.replace(f'yeying20_{kind}',f'yeying20_noshort_{kind}').replace('夜莺2.0·', '夜莺2.0·无简词·')
 new_schema=dst/f'yeying20_noshort_{kind}.schema.yaml';new_schema.write_text(text,encoding='utf-8');schema.unlink()
 fs=dst/'yeying20_rime_fixed.schema.yaml';text=fs.read_text(encoding='utf-8').replace('yeying20_rime_fixed','yeying20_noshort_rime_fixed').replace('夜莺固定码表（辅助）','夜莺2.0无简词固定码表（辅助）')
 (dst/'yeying20_noshort_rime_fixed.schema.yaml').write_text(text,encoding='utf-8');fs.unlink()
 default=dst/'default.custom.yaml.example';default.write_text('patch:\n  schema_list:\n    - schema: yeying20_noshort_'+kind+'\n',encoding='utf-8')
 removed_native=[]
 if kind=='main':
  lex=dst/'mohu/data/yeying20.lexicon.txt';kept=[]
  for s in lex.read_text(encoding='utf-8').splitlines():
   fields=s.split('\t');c,t=fields[:2]
   if len(t)>1 and len(c)<4:removed_native.append((t,c))
   else:kept.append(s)
  newlex=dst/'mohu/data/yeying20_noshort.lexicon.txt';newlex.write_text('\n'.join(kept)+'\n',encoding='utf-8');lex.unlink()
  s=new_schema.read_text(encoding='utf-8').replace('mohu/data/yeying20.lexicon.txt','mohu/data/yeying20_noshort.lexicon.txt')
  new_schema.write_text(s,encoding='utf-8')
 readme=f'''# 夜莺2.0 Rime 无简词 · {label}\n\n复制本包内容到Rime用户目录，在schema_list加入 `yeying20_noshort_{kind}` 后重新部署。方案使用独立ID和用户词典，不覆盖含简词版。\n\n本包移除了二三码词入口；保留全部单字、四码及以上词和40条快符。四字及以上词的标准四码保留，少量二三码别名不保留。整句输入仍可通过逐字完整音码组成词句。\n\nF2拆分提示、反引号双拼反查和波浪号全拼反查保留。主力版继续使用V5模型及Windows x64原生引擎；轻量版使用Rime原生整句。\n'''
 (dst/'使用说明.md').write_text(readme,encoding='utf-8')
 reports[kind]={'固定条目':len(fixed),'整句词典保留':len(smart),'移除整句简词拼写':len(removed_smart),'移除原生简词边':len(removed_native),'方案':f'yeying20_noshort_{kind}'}

(P/'Rime无简词生成核验.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
for kind,label in [('light','轻量版'),('main','主力版')]:
 src=P/f'Rime无简词_{label}';target=P/f'夜莺2.0_Rime无简词_{label}_含快符.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  for f in sorted(src.rglob('*')):
   if f.is_file() and '.userdb' not in f.name and 'build' not in f.parts:z.write(f,f.relative_to(src).as_posix())
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 h=hashlib.sha256(target.read_bytes()).hexdigest();target.with_suffix('.zip.sha256').write_text(h+'  '+target.name+'\n',encoding='utf-8')
 print(label,target.stat().st_size,h)
print(json.dumps(reports,ensure_ascii=False))
