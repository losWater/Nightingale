from pathlib import Path
import zipfile,json,hashlib,shutil
P=Path(__file__).resolve().parent;O=P/'夜莺2.0_字词表与输入法'
report=json.loads((O/'说明与核验/生成清单.json').read_text(encoding='utf-8'))
data=json.loads((P/'引擎核验.json').read_text(encoding='utf-8'))
note=f'''最终核验：含简词普通表{report['原表条数']}条；无简词表{report['无简词条数']}条。快符40条。
搜狗挂接{report['搜狗挂接条数']}条，未超过10万；搜狗五笔200000条，未超过20万。
搜狗挂接排除四码二字词；快符xing=彳亍作为快符保留。1257个让位单字保留从序号2开始，未挤回首选。
搜狗五笔只裁剪{report['搜狗五笔裁剪条数']}条靠后的全码词，原始表不变，附完整清单。
所有平台保留已定稿简码与40条快符。手心模块化：01单字、02普通全码词（含四字以上）、03简词、04快符。
无简词版保留四字及以上词；标点不计字数，所以“说道：“”仍算简词。外文短语及符号的短码也移除；快符独立提供。
原表混有{report['未移植专用宏']}条源输入法$ddcmd设置/时间宏，各平台不移植这些不兼容命令；普通有简词表照原样保留，附未移植清单。
226条超过四码入口：普通表、手心、搜狗挂接及Rime完整保留；搜狗五笔、冰凌五笔及Bime按四码方案不导入，附清单。
数据核验：候选顺序、模块合集、辅助码、快符位置、容量限制全部通过。
Rime轻量版及主力版：小狼毫0.17.4独立目录重新部署成功；29个固定入口候选抽检及正字全拼/双拼反查通过；整句仅做运行样例，不宣称准确率已全面验证。
其他输入法未做本次界面导入实测。所有压缩包均检验CRC。没有改动个人输入法安装目录或1.0发布版。
'''
(O/'说明与核验/最终核验.txt').write_text(note,encoding='utf-8-sig')
shutil.copy2(P/'数据核验.json',O/'说明与核验/数据核验.json')
shutil.copy2(P/'引擎核验.json',O/'说明与核验/Rime引擎核验.json')
for label in ['轻量版','主力版']:
 p=P/f'Rime_{label}'
 (p/'核验结果.txt').write_text(note,encoding='utf-8-sig')
 shutil.copy2(P/'引擎核验.json',p/'引擎核验.json')
targets=[(O,'夜莺2.0_字词表与输入法_含快符.zip'),(P/'Rime_轻量版','夜莺2.0_Rime轻量版_含快符.zip'),(P/'Rime_主力版','夜莺2.0_Rime主力版_含快符.zip'),(P/'Rime_手机版','夜莺2.0_Rime手机版_万象模型_含快符.zip')]
manifest=[]
for folder,name in targets:
 target=P/name
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  for f in sorted(folder.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(folder).as_posix())
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  assert not any('.userdb' in x or x.startswith('build/') for x in z.namelist())
 h=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
 target.with_suffix('.zip.sha256').write_text(h+'  '+name+'\n',encoding='utf-8')
 manifest.append({'文件':name,'字节':target.stat().st_size,'SHA256':h,'CRC':'通过'})
 print(name,round(target.stat().st_size/1024/1024,2),'MiB PASS',flush=True)
(P/'交付清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
