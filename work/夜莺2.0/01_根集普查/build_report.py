"""Read-only census for 2.0 planning. Does not change roots, splits or tables."""
from pathlib import Path
import csv, collections, hashlib, html, json, re, zlib, runpy
import yaml

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
RP=ROOT/'work/重开工程/01_根集/根集_待完整性复核.yaml'
CP=ROOT/'work/重开工程/02_规范拆分/最终规范拆分表_待核验.tsv'
EP=ROOT/'work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv'
FP=ROOT/'work/夜莺2.0/03_字音频率审计/整字频次守恒.tsv'
LP=ROOT/'releases/v1.0/01_正式码表/夜莺码v1.0键位布局.yaml'

# A conservative, reviewed list: complete core usage lists support these labels.
# The label concerns the root's literal shape, NOT all its attached variants.
FAMILIES={r:r+'字形族' for r in '专 利 象 佥 兼 厉 以 夷 丽 来 商 向 甫 俞 无 尧 居 暴 莫 乐 长 韦'.split()}
FAMILIES.update({'秉':'秉本字','赢字架':'嬴/赢/羸/蠃字架族'})
STRUCTURES={'览字头':'临、监/览两支','变字头':'变、弯、蛮等上部结构','禸':'离、禽两支','冓头':'冓、寒/赛两支','定字底':'定、是两支','追字心':'阜/追、薛两支','降下角':'舛/桀、舜、舞等多支'}
# A repeatable screening heuristic, not an IDS/glyph-containment proof.
OUTER=set('亻 彳 讠 言 饣 艹 辶 廴 忄 心 扌 手 氵 水 冫 氺 木 女 虫 月 青字底 口 宀 冖 尸 户 禾 钅 金 纟 糸 马 馬 广 厂 疒 衣 衤 礻 立 日 土 士 王 玉 火 灬 足 足旁 犭 羽 皿 耳 阝 山 石 竹头 刂 力 攵 夂 页 贝 鸟 鳥 鱼 魚 牛 牜'.split())

def readtable(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    result={r['汉字']:{'tokens':[x.strip() for x in r['最终规范拆分'].split('＋')], 'head':r['编码首根'],'tail':r['编码末根']} for r in rows if r['汉字']}
    assert len(result)==len([r for r in rows if r['汉字']])
    return result

def main():
    runpy.run_path(str(ROOT/'work/夜莺2.0/03_字音频率审计/rebuild.py'))['check_current']()
    spec=yaml.safe_load(RP.read_text(encoding='utf8'));names=spec['presentation_names'];core=readtable(CP);ext=readtable(EP)
    assert len(core)==8105 and len(ext)==18770 and not set(core)&set(ext)
    freq=collections.Counter()
    with FP.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f,delimiter='\t'):freq[row['汉字']]=float(row['原始总频'])
    assert set(freq)==set(core)
    ranked=sorted((c for c in freq if freq[c]>0),key=lambda c:(-freq[c],c))
    # Competition ranks: equal frequencies receive the same rank.
    rank={};previous=None
    for i,c in enumerate(ranked,1):
        if freq[c]!=previous:current_rank=i
        rank[c]=current_rank;previous=freq[c]
    order=lambda chars:sorted(chars,key=lambda c:(-freq.get(c,0),ord(c)))
    repertoire=json.loads(zlib.decompress((ROOT/'repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate').read_bytes()))
    ids={r['name']:chr(r['unicode']) for r in repertoire if r.get('name')}
    baseline=yaml.safe_load((ROOT/'work/重开工程/04_Chai输入/结构分析基线_待审计.yaml').read_text(encoding='utf8'))
    ids.update({r['name']:c for c,r in baseline['data']['repertoire'].items() if r.get('name')})
    mapping=yaml.safe_load(LP.read_text(encoding='utf8'))['form']['mapping']
    def key(root):
        return mapping.get(root,mapping.get(ids.get(root),mapping.get({'横':'1','竖':'2','撇':'3','点':'4','折':'5'}.get(root))))
    assert all(key(r) for r in spec['roots'])
    roots=set(spec['roots'])|{t for v in spec['roots'].values() for t in v}|{t for v in spec['anchors'].values() for t in v}
    unknown={t for r in list(core.values())+list(ext.values()) for t in r['tokens']}-roots
    unknown_uses={t:[c for c,r in ext.items() if t in r['tokens']] for t in sorted(unknown)}
    index=[]
    for table in (core,ext):
        inv=collections.defaultdict(set)
        for c,row in table.items():
            for t in set(row['tokens']):inv[t].add(c)
        index.append(inv)
    def stats(tokens):
        tokens=set(tokens); users=[set().union(*(idx[t] for t in tokens)) for idx in index];cs=order(users[0]);es=order(users[1])
        hist=collections.defaultdict(list)
        for c in cs:
            seq=['〔本根〕' if t in tokens else names.get(t,t) for t in core[c]['tokens']]
            orig=core[c]['tokens'];lo=0;hi=len(seq)
            while lo<hi and orig[lo] not in tokens and orig[lo] in OUTER:lo+=1
            while hi>lo and orig[hi-1] not in tokens and orig[hi-1] in OUTER:hi-=1
            hist['＋'.join(seq[lo:hi])].append(c)
        patterns=sorted(hist.items(),key=lambda x:(-len(x[1]),x[0]))
        return {'core':len(cs),'extension':len(es),'occurrences':sum(sum(t in tokens for t in core[c]['tokens']) for c in cs),
                'terminal':sum(core[c]['tokens'][0] in tokens or core[c]['tokens'][-1] in tokens for c in cs),
                'top500':sum(rank.get(c,10**9)<=500 for c in cs),'top1500':sum(rank.get(c,10**9)<=1500 for c in cs),'top3000':sum(rank.get(c,10**9)<=3000 for c in cs),
                'weight':sum(freq[c] for c in cs),'zero':sum(freq[c]==0 for c in cs),
                'top':[{'char':c,'rank':rank[c],'frequency':freq[c]} for c in cs if c in rank][:10],
                'chars':cs,'extchars':es,'patternCount':len(patterns),'concentration':len(patterns[0][1])/len(cs) if cs else None,
                'patterns':[{'pattern':p,'count':len(v),'chars':v} for p,v in patterns[:10]]}
    cache={t:stats([t]) for t in roots}
    def shape_label(root,st):
        if root=='负字头':return '名称别名：规范拆分使用⺈，不可当作废根'
        if not st['core']:return '核心未使用；扩展另看' if st['extension'] else '两字集均未使用'
        if root in FAMILIES:return '固定整字/字架族：'+FAMILIES[root]
        if root in STRUCTURES:return '跨若干字形分支：'+STRUCTURES[root]
        if st['core']==1:return '仅1个核心字：'+st['chars'][0]+'（不能外推至扩展字）'
        if st['concentration']>=.9:return '结构集中候选，需核字形'
        return '存在多种搭配骨架，未判为单族'
    records=[]
    for host,attached in spec['roots'].items():
        direct=cache[host];group=stats([host]+attached)
        records.append({'id':'group:'+host,'kind':'主根汇总','root':host,'display':names.get(host,host),'host':host,'key':key(host),'members':attached,'anchors':spec['anchors'].get(host,[]),
                        'literal':direct['core'],'shape':('多形归并；本形：' if attached else '')+shape_label(host,direct),**group})
        records.append({'id':'root:'+host,'kind':'主根本形','root':host,'display':names.get(host,host),'host':host,'key':key(host),'members':[], 'literal':direct['core'],'shape':shape_label(host,direct),**direct})
        for kind,tokens in [('附属根',attached),('锚定根',spec['anchors'].get(host,[]))]:
            for t in tokens:
                st=cache[t]
                records.append({'id':kind+':'+host+':'+t,'kind':kind,'root':t,'display':names.get(t,t),'host':host,'key':key(t) if t in spec['roots'] else key(host),'members':[],'literal':st['core'],'shape':shape_label(t,st),**st})
    # Published table uses display aliases. Record discrepancies, never silently fix.
    published=readtable(ROOT/'releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt');differences=[]
    for c,r in core.items():
        a=[names.get(t,t) for t in r['tokens']];b=[names.get(t,t) for t in published[c]['tokens']]
        if a!=b:differences.append({'char':c,'current':a,'published':b})
    assert len(differences)==1 and differences[0]['char']=='墼',differences
    groups=[r for r in records if r['kind']=='主根汇总']
    manifest={'core_chars':len(core),'extension_chars':len(ext),'main_definitions':len(spec['roots']),'attached_definitions':sum(map(len,spec['roots'].values())),
              'anchor_definitions':sum(map(len,spec['anchors'].values())),'distinct_root_names':len(roots),'frequency_positive_chars':len(ranked),
              'low_group_10':sum(r['core']<=10 for r in groups),'low_group_20':sum(r['core']<=20 for r in groups),'published_differences':differences,'undefined_extension_tokens':unknown_uses,
              'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RP,CP,EP,FP,LP]}}
    data={'meta':manifest,'records':records,'splits':{c:'＋'.join(names.get(t,t) for t in r['tokens']) for c,r in {**ext,**core}.items()},'frequencies':dict(freq),'ranks':rank}
    (OUT/'统计数据.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    (OUT/'统计摘要.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    low=sorted((r for r in groups if r['core']<=20),key=lambda r:(r['core'],r['weight']))
    md='''# 夜莺 2.0 根集压缩前普查

只统计，不修改根集、拆分、键位或码表。

## 口径

- 核心 8105 字、扩展 18770 字分别计数。按完整根名匹配，不能用字符串包含；一个字包含同根多次，用字数计一次，出现次数另列。
- 175 个主根定义、237 个附属定义、11 个锚定定义，共421个不同根名。乙同时列为主根和折的附属；秉同时列为主根和争字底的锚定。定义条目不是互斥数量，不能直接相加当作独立键位数。
- 主根汇总＝主根本形与其附属形覆盖字的并集，**不含锚定根**；逐形页分别列主根本形、附属根、锚定根。每组包含哪些形体可展开核对。
- “负字头”完整根名没有出现，但同形名称“⺈”在使用，不能当作一个完全不用的字形；鱼省则在这两张规范拆分表中都没有直接命中。
- 核心用字≤10标为很少，11–20标为较少，21–50标为有限，>50标为较广。这是便于筛选的阈值，不是删根建议。扩展字不参与这个分档。
- 字频采用2.0审计表“整字频次守恒.tsv”的原始总频，含已分配与待分配频次，避免读音未解决导致整字字频被低估；每根显示最高的前10字及本表排名。同频并列，零频不排名；扩展字不在这张核心频率表内，不能视为零频。这里的排名与网站性能页另一份语料字频排名不混用。旧报告按已分配频次排名，本次切换后排名可变化。
- “拆分首末用字数”仅指根形位于规范拆分首/末位置，不是删根后改码数；简码、容错以及编码首末规则会影响实际改码，尚未做删除模拟。

## 字形是否集中

“固定整字/字架族”是对已逐字查看的**核心本形**使用范围的标记，例如利、暴、居；不表示扩展字也已经全部人工归族，更不表示可以直接删除。

其他根提供可复算的“搭配骨架”初筛：保留待查根，剥除拆分序列两端的常见外加偏旁，比较剩余序列。最大骨架覆盖≥90%标为“结构集中候选”。它只是线性拆分近似，不是二维字形包含证明；不能把“骨架多”直接等同于“跨字族”。页面保留骨架例字、全量用字和拆分，供人工裁决。

## 源数据差异

当前维护拆分与1.0发布拆分在展示名还原后有1个结构差异：墼。维护表使用“車＋凵＋殳＋土”，发布表仍是“一＋日＋十＋凵＋殳＋土”。本次以当前维护表为准并记录差异，没有修改发布表。蹂的足旁只是展示名不同，已按同一形体统计。

扩展拆分还出现未登记根名“乁”，未擅自映射到某个笔画根；相关字列在统计摘要 undefined_extension_tokens 中。核心拆分没有未登记根名。

## 主根汇总覆盖≤20个核心字

|主根|键|本形用字|含附属用字|扩展用字|最高频字（排名）|本形字形范围|
|---|---|---:|---:|---:|---|---|
'''
    for r in low:
        top='、'.join(f"{x['char']}（{x['rank']}）" for x in r['top'][:5]) or '核心语料中无正频字'
        md+=f"|{r['display']}|{r['key']}|{r['literal']}|{r['core']}|{r['extension']}|{top}|{r['shape']}|\n"
    md+='\n完整交互表见“根集使用与字频统计.html”，可按用字量、字频、类型筛选排序，并展开所有覆盖字。原始数据见“统计数据.json”；输入校验值见“统计摘要.json”。\n'
    (OUT/'统计说明.md').write_text(md,encoding='utf8')
    template=(OUT/'report-template.html').read_text(encoding='utf8')
    (OUT/'根集使用与字频统计.html').write_text(template.replace('/*DATA*/',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')),encoding='utf8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
