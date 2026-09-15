"""Revisit decisions on a shared current baseline; no published files are changed."""
from pathlib import Path
import csv, json, runpy, html, hashlib
from collections import defaultdict

P = Path(__file__).resolve().parent
def load(name): return json.loads((P / name).read_text(encoding='utf-8-sig'))
I = load('input.json'); RB = load('active-baseline.json')
N = load('review-native.json'); D = load('review-deletions.json')
ACTIVE = load('wenjiao-selected.json')
INV = {r['id']: r for r in I['inventory']}
def rid(name):
    return I['norm'].get(name, name)
def show(seq): return '＋'.join(INV.get(t, {}).get('display', t) for t in seq)
parent = {x:x for x in INV}
def find(x):
    parent.setdefault(x,x)
    if parent[x] != x: parent[x] = find(parent[x])
    return parent[x]
for a,b in I['edges']: parent[find(b)] = find(a)
ORIG = {x:find(x) for x in parent}
def og(x): return ORIG.get(x,x)
def rows_for(raw, selected):
    rep = {r['id']:r['replacement'] for r in selected}
    rows = {}
    for c,ts in I['expected'].items():
        rows[c] = ([x for t in ts for x in rep.get(t,[t])] if c in RB['manual']
                   else raw[c] if raw[c] != RB['rows'][c] else ts)
    assert len(rows)==8105 and all(rows.values())
    assert not any(t in rep for seq in rows.values() for t in seq)
    return rows
BASE = rows_for(N['current'],ACTIVE)
original = {}
with (P.parents[1]/'重开工程/02_规范拆分/最终规范拆分表_待核验.tsv').open(encoding='utf-8-sig') as f:
    for r in csv.DictReader(f,delimiter='\t'):
        original[r['汉字']] = [rid(t.strip()) for t in r['最终规范拆分'].split('＋') if t.strip()]
# Everything below evaluates root groups, not the old physical keyboard.
DEFAULT = dict(water=True,animal=4,person=False,lai=True,jian=True,nai=True,li=True,wang=True,ju=False,ten=False)
def grouping(**changes):
    opt = DEFAULT | changes
    def group(x):
        g=og(x)
        if opt['water'] and x in map(rid,['水','氺','永']): return '水氺永'
        if opt['nai'] and x in ['及','乃']: return '及乃'
        if opt['lai'] and x=='来': return og('未')
        if opt['jian'] and x=='兼': return og(rid('争字底'))
        if opt['person'] and g in {og(rid(n)) for n in ['亻','彳','卧人','行']}: return '人旁行'
        a=opt['animal']
        if a>=1 and g in {og('兔'),og('象')}: return '兔象鱼龟'
        if a>=2 and g==og('鱼'): return '兔象鱼龟'
        if a>=3 and x=='龟': return '兔象鱼龟'
        if a>=4 and x in ['龜',rid('龟字底')]: return '兔象鱼龟'
        if opt['li'] and g in {og('丽'),og('雨')}: return '丽雨'
        if opt['ju'] and x==rid('举字底'): return '王丰'
        if opt['wang'] and g in {og('王'),og('丰')}: return '王丰'
        if opt['ten'] and (g in {og('十'),og('千')} or x=='万'): return '十千万'
        return g
    return group

runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['check_current']()
readings=defaultdict(set); freq={}; pending={}; totals={}
with (P.parent/'03_字音频率审计/分读音字频_审计版.tsv').open(encoding='utf-8-sig') as f:
    for r in csv.DictReader(f,delimiter='\t'):
        c,s=r['汉字'],r['拼音'];readings[c].add(s);freq[s,c]=int(r['已分配频率'])
        pending[c]=int(r['该字待分配频率']);totals[c]=int(r['该字原始总频'])
den=sum(freq.values())
pair_sets=runpy.run_path(str(P/'report.py'))['pair_sets']
def buckets(rows,g):
    out=defaultdict(list)
    for c,seq in rows.items():
        for s in readings[c]:out[s,g(seq[0])].append(c)
    for (s,k),cs in out.items():cs.sort(key=lambda c:(-freq[s,c],c))
    return out
def metric(rows,g):
    b=buckets(rows,g);wins={(s,cs[0]) for (s,k),cs in b.items()}
    return b,wins,sum(freq[t] for t in wins)
def audit(id,title,before,after,bg,ag,status):
    bh,bt=pair_sets(before,readings,bg);ah,at=pair_sets(after,readings,ag)
    bb,bw,bf=metric(before,bg);ab,aw,af=metric(after,ag)
    hp=ah-bh; removed=bh-ah
    groups=[]
    involved={(s,ag(after[a][0])) for s,a,b in hp}
    for s,k in involved:
        cs=ab[s,k]
        groups.append({'音节':s,'组':k,'字':[{'字':c,'拆分':show(after[c]),'分音频次':freq[s,c],'待分配频次':pending[c]} for c in cs]})
    groups.sort(key=lambda r: -sum(x['分音频次'] for x in r['字'][1:]))
    lost=sorted(bw-aw,key=lambda t:(-freq[t],t)); gained=sorted(aw-bw,key=lambda t:(-freq[t],t))
    details=lambda ts:[{'音节':s,'字':c,'分音频次':freq[s,c],'待分配频次':pending[c]} for s,c in ts]
    newfull=(ah&at)-(bh&bt)
    return dict(id=id,方案=title,状态=status,新增首根字对=len(hp),消除首根字对=len(removed),
        三码位净减少=len(bb)-len(ab),三码加权覆盖率下降百分点=round((bf-af)/den*100,5),
        新增完整重码=len(newfull),消除完整重码=len((bh&bt)-(ah&at)),
        失去三简首选=details(lost),获得三简首选=details(gained),新增首根候选组=groups,
        新增首根明细=[{'音节':s,'字1':a,'拆分1':show(after[a]),'字2':b,'拆分2':show(after[b])} for s,a,b in sorted(hp)],
        新增完整明细=[list(x) for x in sorted(newfull)],
        前覆盖率=round(bf/den*100,5),后覆盖率=round(af/den*100,5))

ledgerpath=P.parent/'02_改动台账/改动台账.json'
ledger=json.loads(ledgerpath.read_text(encoding='utf-8-sig'))
entries={e['id']:e for e in ledger['entries']}
results=[]
def add(id,title,b,a,bg,ag,status=None):
    results.append(audit(id,title,b,a,bg,ag,status or entries[id]['decision']))
G=grouping()
# Confirmed deletions: restore just this root; other selected decisions stay active.
for id in ['DEL-001','DEL-002']:
    root=rid(entries[id]['proposal']['root']);before=dict(BASE)
    for c,ts in original.items():
        if root in ts:before[c]=ts
    add(id,entries[id]['title'],before,BASE,G,G)
for id in ['DEL-019','DEL-020','DEL-024','DEL-025']:
    selected=[r for r in ACTIVE if r['id']!=D[id]['id']]
    add(id,entries[id]['title'],rows_for(N[id],selected),BASE,G,G)
for id,option in [('MERGE-005','water'),('MERGE-016','person'),('MERGE-017','lai'),('MERGE-018','jian'),('MERGE-019','nai'),('MERGE-020','li')]:
    add(id,entries[id]['title'],BASE,BASE,grouping(**{option:False}),grouping(**{option:True}),
        '已接受，补复核' if id=='MERGE-020' else entries[id].get('selection_status') or entries[id]['decision'])
# Animal group is a chain: use explicit stages to avoid attributing the same merge twice.
no_gui=dict(BASE)
for c,seq in BASE.items():
    if '龟' in seq:no_gui[c]=I['expected'][c]
add('MERGE-001','象归兔（动物组第1步）',no_gui,no_gui,grouping(animal=0),grouping(animal=1),'已沿用的前提')
add('MERGE-011','鱼归兔象（第2步）',no_gui,no_gui,grouping(animal=1),grouping(animal=2),'已沿用的前提')
add('ADD-013','加龟归动物组（第3步）',no_gui,BASE,grouping(animal=2),grouping(animal=3),'已沿用的前提')
add('MERGE-012','龟字底、龜转入（第4步）',BASE,BASE,grouping(animal=3),G,'已选用分法')
# Pending positive proposals are independent additions, not silently enabled together.
for id in [f'DEL-{n:03}' for n in range(3,17)]+['DEL-018']:
    add(id,entries[id]['title'],BASE,rows_for(N[id],ACTIVE+[D[id]]),G,G,'候选，未定案')
add('MERGE-009','王玉玨、丰龶同组',BASE,BASE,grouping(wang=False),grouping(wang=True),'已确认')
add('MERGE-010','举字底加入王丰组',BASE,BASE,grouping(wang=True),grouping(wang=True,ju=True),'依赖王丰合并，未定案')
wan=load('add-wan-raw.json');after=dict(BASE)
for c,seq in wan.items():
    if seq!=RB['rows'][c] and ('万' in seq):
        # No currently deleted root appears in these changed sequences.
        assert not any(t in {r['id'] for r in ACTIVE} for t in seq)
        after[c]=seq
add('MERGE-013','十千万主根锚定（含新增万）',BASE,after,G,grouping(ten=True),'可以考虑，未定案')
add('TOTAL','当前已确认及选用方案整体',original,BASE,og,G,'累计，不含其他候选')

outdir=P.parent/'05_既有裁定三码复核';outdir.mkdir(exist_ok=True)
notes='''本轮覆盖已确认、已选用及此前提出可考虑的方案。各项按当前累计背景独立比较（实施前/后只改变该项）；动物组按四步链条列出。候选项未纳入累计背景，各行不可相加。\n\n三码位指“去声调完整音节＋首根组”：每组允许一个首选，按已分配字频最大者占位。净减少是可容纳首选的读音项数减少，不是新增冲突对数，也不是必然退到四码的汉字数。多音字逐读音统计；零频并列仅用字序稳定展示，不裁决首选。加权覆盖率下降按全部已分配分音频次作分母。未加入一、二简的分流，也未排物理键位，不能当成最终码表三码率。负值表示改善。完整重码仍要求同音、首末均同组。\n\n拆分以8105字维护表为准，已删除根重新运行结构分析；244个既有人工差异字保留维护边界，仅展开涉及的删除根。秉、暴撤销对照恢复原维护表中的对应字族。午等尚未定分组的新根没有偷偷启用。结果用于重新裁决，未撤销或实装任何既有决定。'''
payload={'说明':notes,'结果':results,'未进入数值复核':[{'id':e['id'],'方案':e['title'],'状态':e['decision'],'原因':'未定拆分/分组，尚无可比较方案' if e['id'].startswith('ADD') else '不采用、已被后续方案替代或互斥未选分支，保留原记录'} for e in ledger['entries'] if e['id'] not in {r['id'] for r in results}]}
(outdir/'复核结果.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
cols=['方案','状态','新增首根字对','消除首根字对','三码位净减少','三码加权覆盖率下降百分点','新增完整重码']
md=['# 既有裁定：三码与完整重码复核','',notes,'','| '+' | '.join(cols)+' |','|'+'---|'*len(cols)]
for r in results:md.append('| '+' | '.join(str(r[k]) for k in cols)+' |')
for r in results:
    md+=['',f"## {r['id']} {r['方案']}",'',f"新失去三简首选（未分流）："+'、'.join(f"{x['字']}({x['音节']}，{x['分音频次']})" for x in r['失去三简首选'])]
    for g in r['新增首根候选组']:
        md.append('- '+g['音节']+'：'+'；'.join(f"{x['字']}〔{x['拆分']}，频次{x['分音频次']}〕" for x in g['字']))
(outdir/'既有裁定三码复核.md').write_text('\n'.join(md),encoding='utf-8')
esc=lambda x:html.escape(str(x))
rows=''.join('<tr>'+''.join('<td>'+esc(r[k])+'</td>' for k in cols)+'</tr>' for r in results)
details=''
for r in results:
    details+=f"<details><summary>{esc(r['id']+' '+r['方案'])} · 新增首根字对 {r['新增首根字对']}</summary><p>失去三简首选："+esc('、'.join(f"{x['字']}({x['音节']}，频次{x['分音频次']})" for x in r['失去三简首选']) or '无')+'</p>'
    for g in r['新增首根候选组']:details+='<p><b>'+esc(g['音节'])+'</b> '+esc('；'.join(f"{x['字']}〔{x['拆分']}，频次{x['分音频次']}〕" for x in g['字']))+'</p>'
    details+='</details>'
page='<!doctype html><meta charset="utf-8"><title>既有裁定三码复核</title><style>body{font:16px/1.7 Microsoft YaHei,sans-serif;background:#f5f7fa;color:#233548;margin:32px}table{border-collapse:collapse;background:white}td,th{border:1px solid #cdd9e0;padding:8px}th{position:sticky;top:0;background:#dae9ed}details{background:white;padding:12px;margin:12px 0}summary{cursor:pointer;font-weight:bold}p{max-width:1300px}</style><h1>既有裁定三码复核</h1>'+''.join('<p>'+esc(s)+'</p>' for s in notes.split('\n\n'))+'<table><thead><tr>'+''.join('<th>'+esc(k)+'</th>' for k in cols)+'</tr></thead><tbody>'+rows+'</tbody></table><h2>逐项展开：完整候选组和拆分</h2>'+details
(outdir/'既有裁定三码复核.html').write_text(page,encoding='utf-8')
sources=[P/'input.json',P/'review-native.json',P/'review-deletions.json',P/'review_three_codes.py',ledgerpath,P.parent/'评估规则.md',P.parent/'03_字音频率审计/分读音字频_审计版.tsv']
(outdir/'来源指纹.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},ensure_ascii=False,indent=2),encoding='utf-8')
for r in results: print(r['id'],r['方案'],'首根+',r['新增首根字对'],'位-',r['三码位净减少'],'覆盖-',r['三码加权覆盖率下降百分点'],'完整+',r['新增完整重码'],'重点',','.join(x['字'] for x in r['失去三简首选'][:10]))
