# -*- coding: utf-8 -*-
"""纯单字表核验。口径：容错码与特殊简码不参与任何规则判定；
   用户已裁定保留的兼占位登记为白名单。同时验证“去掉容错码后仍规则完整”。"""
import io,sys,json,collections,datetime
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
rank={e['字']:e['字频'] for e in json.load(open(B+'/59_单字当量排行/单字当量排行.json',encoding='utf-8'))}
TOL={'jv':'剧','jvb':'居','jvn':'巨','jvo':'狙','xv':'绪',
     'yvl':'欲','yvz':'予','yvc':'郁','yvo':'羽',
     'jbx':'金','igpf':'承','zde':'载','zdt':'哉','zdw':'栽','dzp':'兜'}   # 2026-09-17 第二十六批          # 54批次登记容错码
SPEC={'eh':'鹤','by':'莺'}                                            # 57盘点特殊简码
IRR={'lqq':'六'}                                            # 尚存无理码
KEEP={'bje':'般','gjb':'敢','hop':'火','isa':'冲','qtq':'却','zid':'自'}  # 用户裁定保留兼占
YIELD_EXC = {'pubp': '暴', 'yeuy': '邪'}  # 第二十三批补读音：用户裁定新读音全码排最后（暴让曝、邪让铘）
def load(drop_tol):
    seq=[];codes=collections.defaultdict(set);order=collections.defaultdict(list)
    for line in open(B+'/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt',encoding='utf-8-sig'):
        p=line.rstrip('\n').rstrip('\r').split('\t')
        if len(p)<2 or len(p[0])!=1 or not p[1].isalpha(): continue
        w,c=p[0],p[1]
        if drop_tol and (TOL.get(c)==w or SPEC.get(c)==w): continue
        seq.append((c,w)); codes[w].add(c); order[c].append(w)
    return seq,codes,order
def run(tag,drop_tol):
    seq,codes,order=load(drop_tol)
    EXTRA=set() if drop_tol else set(TOL)|set(SPEC)
    real=lambda w: {c for c in codes[w] if not (c in EXTRA and (TOL.get(c)==w or SPEC.get(c)==w))}
    full={w:{c for c in real(w) if len(c)>=4} for w in codes}
    short={w:{c for c in real(w) if len(c)<=2} for w in codes}
    fails=collections.OrderedDict()
    def chk(n,bad): fails[n]=sorted(bad)
    chk('字数8105',[] if len(codes)==8105 else ['%d'%len(codes)])
    chk('字集与59一致',set(rank)^set(codes))
    chk('重复条目',[k for k,v in collections.Counter(seq).items() if v>1])
    chk('编码为小写字母',[c for c in order if not (c.isalpha() and c.islower())])
    chk('每字有全码',[w for w in codes if not full[w]])
    chk('全码不超四码',[w+c for w in codes for c in codes[w] if len(c)>4])
    chk('一简26键齐全',set('abcdefghijklmnopqrstuvwxyz')-{c for c in order if len(c)==1})
    chk('一简每键一字',[c for c in order if len(c)==1 and len(order[c])>1])
    chk('三简位最多一字',[c for c in order if len(c)==3 and len(order[c])>1])
    bad=[]
    for w in codes:
        for s in real(w):
            if len(s)<4 and full[w] and not any(f.startswith(s) for f in full[w]):
                if IRR.get(s)!=w: bad.append(w+s)
    chk('无未登记无理码',bad)
    y=lambda w,F: any(len(s)<len(F) and F.startswith(s) for s in real(w))
    bad=[]
    for F,c in order.items():
        if len(F)<4: continue
        free=[i for i,w in enumerate(c) if not y(w,F)]
        for i,w in enumerate(c):
            if y(w,F) and any(j>i for j in free) and YIELD_EXC.get(F)!=c[-1]: bad.append('%s[%s]'%(F,'、'.join(c))); break
    chk('出简让全·字对字',bad)
    pref=collections.defaultdict(set)
    for w,fs in full.items():
        for f in fs: pref[f[:3]].add(w)
    bad=[]
    for w in codes:
        for X in (c for c in real(w) if len(c)==3):
            if not any(f.startswith(X) for f in full[w]): continue
            if not any(X.startswith(s) for s in short[w]): continue
            comp=[e for e in pref.get(X,()) if e!=w and not any(X.startswith(s) for s in short[e])
                  and not any(len(s)<4 for s in real(e))]
            if comp and KEEP.get(X)!=w: bad.append('%s %s占,竞争%s'%(X,w,comp))
    chk('二三简兼占',bad)
    bad=[]
    for w in codes:
        r=real(w); ones=[c for c in r if len(c)==1]
        for t in (c for c in r if len(c)==2):
            if not ones or not t.startswith(ones[0]): continue
            if not any(f.startswith(t) for f in full[w]): continue
            comp=[e for e in codes if e!=w and any(f.startswith(t) for f in full[e])
                  and not any(len(s2)<=2 for s2 in real(e))]
            if comp: bad.append('%s %s占一简%s+二简,竞争%s'%(t,w,ones[0],comp[:3]))
    chk('一简二简兼占',bad)
    nf=[k for k,v in fails.items() if v]
    print('【%s】单字 %d，条目 %d，码位 %d  →  %d 项检查，未通过 %d 项'
          % (tag,len(codes),len(seq),len(order),len(fails),len(nf)))
    for k in nf:
        print('    ✗ %s：%s' % (k,'；'.join(map(str,fails[k][:8]))))
    return {'概况':{'单字':len(codes),'条目':len(seq),'码位':len(order)},
            '未通过':{k:v for k,v in fails.items() if v}}
a=run('完整表（含容错码，容错不参与判定）',False)
print()
b=run('去容错码版（验证规则完整性）',True)
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
  '口径':{'容错码':TOL,'特殊简码':SPEC,'尚存无理码':IRR,'已裁定保留兼占':KEEP},
  '完整表':a,'去容错码版':b},open('核验报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
