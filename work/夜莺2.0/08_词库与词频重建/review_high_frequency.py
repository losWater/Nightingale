from pathlib import Path
import json,runpy,hashlib,re
from collections import Counter
O=Path(__file__).resolve().parent
m=runpy.run_path(str(O/'auto_review.py'));dc=m['dc']
# 本轮仅处理原高频队列，常用词义主读由逐项复核确定；原有异读证据不删除。
choices_text="""得到|de dao
睡觉|shui jiao
苹果|ping guo
成熟|cheng shu
增长|zeng zhang
似的|shi de
熟悉|shu xi
角色|jue se
钥匙|yao shi
主角|zhu jue
给予|ji yu
睡着|shui zhao
低调|di diao
血液|xue ye
角落|jiao luo
标识|biao shi
模样|mu yang
说服|shuo fu
暴露|bao lu
血管|xue guan
萝卜|luo bo
暖和|nuan huo
尾巴|wei ba
厌恶|yan wu
洗洗|xi xi
血压|xue ya
得以|de yi
专属|zhuan shu
揭露|jie lu
供给|gong ji
劲儿|jin er
熟人|shu ren
血腥|xue xing
庞大|pang da
眼熟|yan shu
调动|diao dong
泄露|xie lou
心血|xin xue
强劲|qiang jing
鲜血|xian xue
埋怨|man yuan
非得|fei dei
橙子|cheng zi
热血|re xue
刹车|sha che
懒觉|lan jiao
反弹|fan tan
薄弱|bo ruo
血迹|xue ji
咖喱|ga li
雪茄|xue jia
便秘|bian mi
熟练|shu lian
露天|lu tian
削减|xue jian
长袖|chang xiu
塞车|sai che
血清|xue qing
贫血|pin xue
堪称|kan cheng
止血|zhi xue
血糖|xue tang
露面|lou mian
午觉|wu jiao
称职|chen zhi
包扎|bao za
雪地|xue di
血肉|xue rou
巷子|xiang zi
小巷|xiao xiang
扎根|zha gen
人参|ren shen
血色|xue se
血统|xue tong
削弱|xue ruo
补给|bu ji
鼻血|bi xue
长成|zhang cheng
模块|mo kuai
配角|pei jue
年长|nian zhang
血型|xue xing
明了|ming liao
动弹|dong tan
高调|gao diao
对称|dui chen
献血|xian xue
提防|di fang
露营|lu ying
猛地|meng de
姥爷|lao ye
血脉|xue mai
血缘|xue yuan"""
choices=dict(line.split('|') for line in choices_text.splitlines())
read=lambda n:[json.loads(x) for x in (O/n).read_text(encoding='utf-8').splitlines()]
rows=read('二字词60000_自动分流.jsonl')
queue=json.loads((O/'高频人工队列.json').read_text(encoding='utf-8'));targets={r['词'] for r in queue}
assert set(choices)<=targets
jl=m['old']['JL'];raw={}
for no,line in enumerate(jl.read_text(encoding='utf-8-sig').splitlines(),1):
 match=re.fullmatch(r'([a-z]{4})=\d+,(.+)',line)
 if match and match[2] in targets:raw.setdefault(match[2],[]).append({'行号':no,'原文':line})
review=[];remaining=[]
for r in rows:
 w=r['词']
 if w not in targets:continue
 py=choices.get(w)
 evidence=r['读音证据'];jlpy=evidence.get('鲸凉鹤',[])
 if py:
  assert m['valid'](w,py)
  assert py in jlpy or w=='洗洗'
  reason='优先参考鲸凉鹤去已知飞键后的整词读音，逐项选择常用词义主读；其他来源证据保留，非权威辞典核验'
  if w=='洗洗':
   assert 'xixi' in evidence.get('墨奇双拼',[])
   reason='鲸凉鹤缺词；按洗的常用动词叠词读音复核，并与墨奇xixi一致'
  r.update(处理分类='高频逐项核对候选',主读音=py,主读双拼=''.join(dc(s) for s in py.split()),处理依据=reason,读音频率说明='采用常用词义主读作候选；没有测量或分配各读音频次')
 else:
  reason='本轮保留：多读音、口语变体、词义或编码歧义尚未定案；无需为了清空队列强行定单音'
  remaining.append(r)
 review.append({'词':w,'二字词排名':r['二字词排名'],'本轮采用':py,'结果':'常用主读候选' if py else '保留待定','理由':r.get('处理依据') if py else reason,'鲸凉鹤读音':jlpy,'鲸凉鹤原始记录':raw.get(w,[]),'全部读音证据':evidence})
core=[r for r in rows if r['处理分类'] in ['沿用通过','自动确定主读','单音字组合通过','高频逐项核对候选']]
for name,data in [('二字词60000_高频复核后.jsonl',rows),('可用二字词_高频复核后.jsonl',core)]:
 (O/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data),encoding='utf-8')
for name,data in [('高频逐项复核记录.json',review),('高频剩余待定.json',remaining)]:
 (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(rows)==60000 and len({r['词'] for r in rows})==60000
assert len(review)==126 and len(choices)+len(remaining)==126
for r in core:assert r['主读双拼']==''.join(dc(s) for s in r['主读音'].split())
summary={'本轮高频复核':126,'新增常用主读候选':len(choices),'高频保留待定':len(remaining),'读音候选总数':len(core),'全表仍待核':60000-len(core),'鲸凉鹤SHA256':hashlib.sha256(jl.read_bytes()).hexdigest(),'检查':'条数、唯一性、读音编码和鲸凉鹤支持检查通过'}
(O/'高频复核摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 高频词读音复核（鲸凉鹤优先）','',f'原126条中，{len(choices)}条确定常用词义主读候选，{len(remaining)}条保留待定。全部60000词中现有{len(core)}条读音候选，仍待核{60000-len(core)}条。','', '优先参考现有鲸凉鹤1.1手心挂接副本，仅使用已确认飞键映射；未知飞键不猜。来源可能同时含多个兼容码，不能直接视为标准读音。逐项记录保留原始文件行号、编码及全部证据。','', '本轮未接新辞典，未测量各读音频次，未改1.0发布表及字频。读音候选不代表词条质量全部通过；复核前结果保留。','', '## 本轮常用主读候选','', '|词|拼音|双拼|','|---|---|---|']
lines += [f"|{w}|{py}|{''.join(dc(s) for s in py.split())}|" for w,py in choices.items()]
lines += ['', '## 保留待定','', '、'.join(r['词'] for r in remaining),'','详细依据见高频逐项复核记录.json；后续采用可用二字词_高频复核后.jsonl作为候选输入。']
(O/'高频词复核说明.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False));print('保留：','、'.join(r['词'] for r in remaining))
