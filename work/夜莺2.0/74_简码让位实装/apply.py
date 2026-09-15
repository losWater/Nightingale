# -*- coding: utf-8 -*-
"""简码让位实装：有一简/二简的字让出三简位给真实竞争者。
口径：三简让位＝该码位直接不出占位字（非降序）；接手字继承候选1，后续简词序号不变。
裁定来源：用户逐条确认，见 让位清单.json。"""
import io,sys,os,json,hashlib,datetime,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'

PLAN={'ufp':('身','申'),'jpo':('接','捷'),'cis':('此','雌'),'pio':('批','披'),'hub':('户','弧'),
 'yup':('与','煜'),'kxs':('跨','姱'),'kho':('抗','扛'),'jxp':('加','夹'),'vog':('桌','卓'),
 'lom':('落','萝'),'saa':('洒','挲'),'moa':('没','漠'),'bat':('吧','叭'),'ify':('陈','尘'),
 'hya':('混','浑'),'zhm':('藏','葬'),'lnp':('了','辽'),'xmv':('先','咸'),'diq':('地','堤'),
 'tsn':('同','彤'),'pgx':('碰','砰'),'kjx':('砍','龛'),'wjj':('完','宛'),'nia':('泥','溺'),
 'kcv':('靠','犒'),'hro':('换','獾'),'hgw':('横','桁'),'klo':('狂','\U0002b6ed'),
 'noo':('挪','搦'),'sum':('苏','蔌')}
KEEP={'muw':'待定','isa':'涌chong读音零频且涌已有ysa','hop':'用户保留','zid':'用户保留',
      'qtq':'用户保留','gjb':'用户保留','bje':'用户保留'}

FILES=[('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt','utf-8-sig','plain'),
       ('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_码前格式.txt','utf-8-sig','code1st'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt','utf-8-sig','plain'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_码前格式.txt','utf-8-sig','code1st'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_手心格式.txt','utf-8-sig','shouxin'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_搜狗.txt','utf-16','sogou')]

def parse(line,fmt):
    if fmt=='plain':
        p=line.split('\t');  return (p[1],p[0]) if len(p)>=2 else (None,None)
    if fmt=='code1st':
        p=line.split('\t');  return (p[0],p[1]) if len(p)>=2 else (None,None)
    if fmt=='shouxin':
        if '=' not in line or ',' not in line: return (None,None)
        c,rest=line.split('=',1); n,w=rest.split(',',1); return (c,w)
    if fmt=='sogou':
        if '=' not in line or ',' not in line: return (None,None)
        left,w=line.split('=',1); c,n=left.rsplit(',',1); return (c,w)
    return (None,None)

def rebuild(line,fmt,new):
    if fmt=='plain':   p=line.split('\t'); p[0]=new; return '\t'.join(p)
    if fmt=='code1st': p=line.split('\t'); p[1]=new; return '\t'.join(p)
    if fmt=='shouxin': c,rest=line.split('=',1); n,w=rest.split(',',1); return c+'='+n+','+new
    if fmt=='sogou':   left,w=line.split('=',1); return left+'='+new
    return line

report={'时间':datetime.datetime.now().isoformat(timespec='seconds'),
        '让位条数':len(PLAN),'维持条数':len(KEEP),'文件':[]}
for rel,enc,fmt in FILES:
    path=B+'/'+rel
    raw=open(path,'rb').read(); txt=raw.decode(enc)
    nl='\r\n' if '\r\n' in txt else '\n'
    lines=txt.split(nl); tail=lines.pop() if lines and lines[-1]=='' else None
    hit=collections.Counter(); out=[]
    for line in lines:
        c,w=parse(line,fmt)
        if c in PLAN and w==PLAN[c][0]:
            hit[c]+=1; out.append(rebuild(line,fmt,PLAN[c][1]))
        else:
            out.append(line)
    missing=[c for c in PLAN if hit[c]==0]; dup=[c for c in PLAN if hit[c]>1]
    assert not missing, ('未找到占位行',rel,missing)
    assert not dup, ('占位行重复',rel,dup)
    assert len(out)==len(lines), '行数变化'
    new=nl.join(out+([tail] if tail is not None else []))
    data=new.encode(enc if enc!='utf-16' else 'utf-16')
    open(path,'wb').write(data)
    report['文件'].append({'文件':rel,'替换行数':sum(hit.values()),'行数':len(lines),
                           '新sha256':hashlib.sha256(data).hexdigest()})
    print('%-46s 替换 %2d 行  %s' % (rel.split('/')[-1],sum(hit.values()),
                                   report['文件'][-1]['新sha256'][:16]))
json.dump({'让位':{k:{'占位字':v[0],'接手字':v[1]} for k,v in PLAN.items()},'维持':KEEP},
          open('让位清单.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
json.dump(report,open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('\n让位 %d 处，维持 %d 处；清单与报告已写入。' % (len(PLAN),len(KEEP)))
