# -*- coding: utf-8 -*-
import io,sys,os,json,collections,csv,difflib
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
PLAN=json.load(open('让位清单.json',encoding='utf-8'))['让位']
FILES=[('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt','utf-8-sig'),
       ('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_码前格式.txt','utf-8-sig'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt','utf-8-sig'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_码前格式.txt','utf-8-sig'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_手心格式.txt','utf-8-sig'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_搜狗.txt','utf-16')]
ok=True
print('=== 1. 逐文件差异（应恰为 31 行，且只改字不改码/序号）===')
for rel,enc in FILES:
    new=open(B+'/'+rel,'rb').read(); old=open('实装前备份/'+rel.replace('/','__'),'rb').read()
    a=old.decode(enc).splitlines(); b=new.decode(enc).splitlines()
    d=[(x,y) for x,y in zip(a,b) if x!=y]
    bad=[p for p in d if sum(c1!=c2 for c1,c2 in zip(p[0],p[1]))>len(p[0])]
    same_len=len(a)==len(b)
    nlok=(b'\r\n' in new); bomok=new.startswith(b'\xff\xfe') if enc=='utf-16' else new.startswith(b'\xef\xbb\xbf')
    print('  %-44s 差异%3d行 行数一致%s CRLF%s BOM%s' % (rel.split('/')[-1],len(d),same_len,nlok,bomok))
    if len(d)!=31 or not(same_len and nlok and bomok): ok=False
print('\n  样例差异（64普通）：')
a=open('实装前备份/64_加入鲸凉鹤简词__夜莺2.0含简词字词表_普通格式.txt',encoding='utf-8-sig').read().splitlines()
b=open(B+'/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt',encoding='utf-8-sig').read().splitlines()
for x,y in [(x,y) for x,y in zip(a,b) if x!=y][:6]:
    print('    %-18s → %s' % (x.strip(),y.strip()))

def load(p,enc='utf-8-sig'):
    o=collections.defaultdict(list); c=collections.defaultdict(set)
    for line in open(p,encoding=enc):
        q=line.rstrip('\n').rstrip('\r').split('\t')
        if len(q)>=2: o[q[1]].append(q[0]); c[q[0]].add(q[1])
    return o,c
order,codes=load(B+'/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt')

print('\n=== 2. 四格式一致性（62 无简词表）===')
sets={}
for rel,enc,fmt in [('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt','utf-8-sig','plain'),
                    ('62_无简词字词表导出/夜莺2.0无简词字词表_码前格式.txt','utf-8-sig','code1st'),
                    ('62_无简词字词表导出/夜莺2.0无简词字词表_手心格式.txt','utf-8-sig','shouxin'),
                    ('62_无简词字词表导出/夜莺2.0无简词字词表_搜狗.txt','utf-16','sogou')]:
    s=[]
    for line in open(B+'/'+rel,encoding=enc).read().splitlines():
        if fmt=='plain': p=line.split('\t'); s.append((p[1],p[0])) if len(p)>=2 else None
        elif fmt=='code1st': p=line.split('\t'); s.append((p[0],p[1])) if len(p)>=2 else None
        elif fmt=='shouxin':
            if '=' in line and ',' in line: c,r=line.split('=',1); n,w=r.split(',',1); s.append((c,w))
        else:
            if '=' in line and ',' in line: l,w=line.split('=',1); c,n=l.rsplit(',',1); s.append((c,w))
    sets[fmt]=s
base=sets['plain']
for k,v in sets.items():
    same=(v==base)
    print('  %-8s 条数 %d  与普通格式逐行一致：%s' % (k,len(v),same))
    if not same: ok=False

print('\n=== 3. 让位结果核对 ===')
for X in sorted(PLAN):
    w,r=PLAN[X]['占位字'],PLAN[X]['接手字']
    cur=order.get(X,[])
    good=(cur and cur[0]==r and w not in cur and X in codes[r])
    print('  %-5s → %-2s  候选[%s]  %s' % (X,r,'、'.join(cur),'OK' if good else '✗'))
    if not good: ok=False

print('\n=== 4. 兼占重扫（应只剩维持的 7 处）===')
rank={e['字']:e['字频'] for e in json.load(open(B+'/59_单字当量排行/单字当量排行.json',encoding='utf-8'))}
full={w:{c for c in cs if len(c)>=4} for w,cs in codes.items() if len(w)==1}
short={w:{c for c in cs if len(c)<=2} for w,cs in codes.items() if len(w)==1}
pref=collections.defaultdict(set)
for w,fs in full.items():
    for f in fs: pref[f[:3]].add(w)
left=[]
for w,cs in codes.items():
    if len(w)!=1: continue
    for X in (c for c in cs if len(c)==3):
        if not any(f.startswith(X) for f in full.get(w,())): continue
        if not any(X.startswith(s) for s in short[w]): continue
        comp=[e for e in pref.get(X,()) if e!=w and not any(X.startswith(s) for s in short.get(e,()))]
        if comp: left.append((X,w,sorted(comp,key=lambda e:rank.get(e,99999))[0]))
print('  剩余需让位 %d 处：%s' % (len(left),'、'.join('%s(%s→%s)'%t for t in sorted(left))))
if len(left)!=7: ok=False

print('\n=== 结论：%s ===' % ('全部通过' if ok else '存在未通过项'))
