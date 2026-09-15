"""从已目视核对的 GF0013—2009 第2—3页录入名单，分析当前根集；不修改方案。"""
from pathlib import Path
import csv, json, yaml, html
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BY_STROKES = {
1: '一乙',
2: '二十丁厂七卜八人入儿匕几九刁了刀力乃又',
3: '三干于工土士才下寸大丈与万上小口山巾千川个夕久么凡丸及广亡门丫义之尸己已巳弓子卫也女刃飞习叉马乡',
4: '丰王开井天夫无云专丐木五不犬太歹尤车巨牙屯戈互瓦止少曰日中贝内水见午牛手气毛壬升夭长片斤爪父月氏勿丹乌六文方火为斗户心尺丑巴办予书',
5: '玉未末击正甘世本术丙石戊龙平东卡凸业目且甲申电田由史央冉皿凹四生矢失乍禾丘白斥瓜乎用甩乐匆册鸟主立半头必永民弗出矛母',
6: '耳亚臣吏再西百而页夹夷虫曲肉年朱臼自血囟舟亦衣产亥羊米州农',
7: '严求甫更束两酉来卤里串我身囱言羌弟',
8: '事雨果垂秉肃隶承',
9: '革柬面重鬼禹首',
10: '兼', 11: '象', 13: '鼠',
}
assert [len(x) for x in BY_STROKES.values()] == [2,19,48,65,58,29,17,8,7,1,1,1]
CHARS = ''.join(BY_STROKES.values())
assert len(CHARS) == len(set(CHARS)) == 256

# GF0011—2009第3—5页：同一部首下列明的附形关系。
# 简繁对应单列；同一规范部首组不等于同源，也不要求输入法同键。
VARIANTS = {
'厂': [('𠂆','附形')], '卜': [('⺊','附形')],
'八': [('丷','附形')], '人': [('亻','附形'),('入','同部首附形')],
'入': [('人','同部首主形'),('亻','同部首附形')],
'几': [('⺇','附形')], '刀': [('刂','附形'),('⺈','附形')],
'土': [('士','同部首附形')], '士': [('土','同部首主形')],
'小': [('⺌','附形')], '己': [('已','同部首附形'),('巳','同部首附形')],
'已': [('己','同部首主形'),('巳','同部首附形')],
'巳': [('己','同部首主形'),('已','同部首附形')],
'飞': [('飛','简繁')], '马': [('馬','简繁')],
'王': [('玉','同部首附形')], '玉': [('王','同部首主形')],
'无': [('旡','附形')], '木': [('朩','附形')],
'犬': [('犭','附形')], '歹': [('歺','附形')],
'车': [('车旁','附形'),('車','简繁')],
'日': [('⺜','附形'),('曰','同部首附形')],
'曰': [('日','同部首主形'),('⺜','同部首附形')],
'贝': [('貝','简繁')], '水': [('氵','附形'),('氺','附形')],
'见': [('見','简繁')], '牛': [('牜','附形')],
'手': [('扌','附形'),('龵','附形（看字头）')],
'长': [('镸','附形'),('長','简繁')], '爪': [('爫','附形')],
'月': [('⺝','附形')], '火': [('灬','附形')],
'心': [('忄','附形'),('⺗','附形')], '龙': [('龍','简繁')],
'鸟': [('鳥','简繁')], '母': [('毋','同部首主形')],
'西': [('覀','同部首主形'),('襾','同部首附形')],
'页': [('頁','简繁')], '臼': [('⺽','附形')],
'衣': [('衤','附形')], '羊': [('⺶','附形'),('⺷','附形')],
'言': [('讠','附形')],
}
# 仅是本方案已有相关省形/形近归并，不能冒充上表规范变体。
RELATED = {
'丰':['龶'], '弟':['弟省'], '鸟':['鸟省'], '衣':['衣省'],
'雨':['雨头'], '氏':['氐','旅下角'], '臣':['颐字旁'],
'亦':['亦字底'], '用':[], '肉':['月'],
}
cfg = yaml.safe_load((ROOT/'work/重开工程/01_根集/根集_待完整性复核.yaml').read_text(encoding='utf-8'))
lookup = {}
def add(k, status, host): lookup.setdefault(k, []).append((status,host))
for host, attached in cfg['roots'].items():
    add(host,'主根',host)
    for v in attached: add(v,'归并根',host)
for host, attached in cfg['anchors'].items():
    for v in attached: add(v,'锚定根',host)
for k,v in cfg['presentation_names'].items():
    if k in lookup: lookup.setdefault(v,[]).extend(lookup[k])
splits = {r['汉字']:r['最终规范拆分'] for r in csv.DictReader((ROOT/'work/重开工程/02_规范拆分/最终规范拆分表_待核验.tsv').open(encoding='utf-8-sig'),delimiter='\t')}
def status(c):
    return '；'.join(f'{s}→{h}' for s,h in lookup.get(c,[])) or '未收录整体根'
rows=[]
for stroke, chars in BY_STROKES.items():
    for c in chars:
        variants=VARIANTS.get(c,[])
        rows.append({'字':c,'笔画':stroke,'现状':status(c),'拆分':splits.get(c,'不在核心表'),
        '规范关系':'；'.join(f'{v}〔{kind}，{status(v)}〕' for v,kind in variants) or '本次未列出规范附形',
        '方案相关':'；'.join(f'{v}〔{status(v)}〕' for v in RELATED.get(c,[])) or '—'})
missing=[r['字'] for r in rows if r['字'] not in lookup]
counts=Counter('主根' if any(s=='主根' for s,h in lookup.get(c,[])) else '归并根' if any(s=='归并根' for s,h in lookup.get(c,[])) else '锚定根' if c in lookup else '未整体收录' for c in CHARS)
intro = f'''# 256个独体字与夜莺根集、偏旁变体对照

独体字名单按GF0013—2009原扫描件第2—3页逐行核对，256字无重复；附形按GF0011—2009原扫描件第3—5页核对。本次仅分析，不修改根集或拆分。

## 统计

{dict(counts)}。主根优先归类，其次归并、锚定；例如秉同时有主根与锚定身份，统计只算主根，但逐字表保留两种身份。

未整体收录的{len(missing)}字：{'、'.join(missing)}。

## 怎样理解变体

- “附形”是本次部首规范中的形式关系；“同部首附形”可能是不同汉字，不等于字源同一，也不意味着夜莺必须归并。
- 简繁对应单列，不与位置变形混算。
- “方案相关”单独列出现有省形或关联形态，不声称是规范部首变体。肉与月是字源/现代字形需要区分的特殊情况，不能把所有月旁均当作肉。
- 未列出附形，表示本次在所用部首表中没有确认；不代表任何字形、字体或构字环境下都没有变形。女、木等作偏旁时的笔形变化也不一定另有Unicode字符。
- 食、攴、生、辰仍是候选；其中只有生在这256字中。不能用是否入独体字表来否定另外三个候选。
- 新增完整形态与新增独立根组分开评估。下面不把规范关系自动写入根集。

## 来源

- [教育部独体字规范说明](https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/moe_1485/tnull_45766.html)
- [独体字规范原件公开镜像](https://github.com/zispace/hanzi-docs/blob/main/中国大陆/2-GF-语言文字规范/20090324-GF%200013-2009《现代常用独体字规范》.pdf)
- [部首表原件公开镜像](https://github.com/zispace/hanzi-docs/blob/main/中国大陆/2-GF-语言文字规范/20090112-GF%200011-2009《汉字部首表》.pdf)
- 本地原件：现代常用独体字规范.pdf、汉字部首表2009.pdf。部首附形本次按2009版，不声称已核全2022修订版。
- 本地根集：work/重开工程/01_根集/根集_待完整性复核.yaml；拆分：同工程02_规范拆分/最终规范拆分表_待核验.tsv。

## 逐字对照

'''
keys=list(rows[0])
md=intro+'| '+' | '.join(keys)+' |\n|'+ '|'.join(['---']*len(keys))+'|\n'
md+='\n'.join('| '+' | '.join(str(r[k]) for k in keys)+' |' for r in rows)+'\n'
(HERE/'独体字与偏旁变体对照.md').write_text(md,encoding='utf-8')
(HERE/'独体字对照数据.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
head=''.join(f'<th>{k}</th>' for k in keys)
body=''.join('<tr data-missing="'+str(r['字'] not in lookup).lower()+'">'+''.join(f'<td>{html.escape(str(r[k]))}</td>' for k in keys)+'</tr>' for r in rows)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>独体字与偏旁变体对照</title><style>body{font:17px/1.7 "Microsoft YaHei",sans-serif;background:#f5f7fa;color:#233548;padding:30px;margin:auto;max-width:1500px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d8e0e8;padding:10px;text-align:left}th{background:#dae8ed;position:sticky;top:0}td:first-child{font-size:26px}input,select{font:inherit;padding:8px;margin:10px}p{max-width:1100px}</style><h1>256个独体字与偏旁变体</h1>'''
page+=f'<p>本形覆盖：{html.escape(str(dict(counts)))}。主根、归并根、锚定根均计入已有，候选新增尚未计入。</p>'
page+='<p>已核对规范扫描件。附形、简繁和方案相关形态分开标注；没有列出附形不等于绝无变形。肉旁与月旁须按具体字区分。<a href="独体字与偏旁变体对照.md">完整说明与来源</a> · <a href="现代常用独体字规范.pdf">独体字原表</a></p><input id="q" placeholder="搜索字、根或变体"><select id="mode"><option value="all">全部256字</option><option value="missing">只看未整体收录</option></select><span id="count"></span><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table>'
page+='''<script>function filter(){let n=0;document.querySelectorAll('tbody tr').forEach(r=>{let ok=r.textContent.includes(document.getElementById('q').value.trim())&&(document.getElementById('mode').value==='all'||r.dataset.missing==='true');r.hidden=!ok;if(ok)n++});document.getElementById('count').textContent=n+' 字'}document.getElementById('q').oninput=filter;document.getElementById('mode').onchange=filter;filter()</script></html>'''
(HERE/'独体字与偏旁变体对照.html').write_text(page,encoding='utf-8')
print(dict(counts));print('未整体收录：',''.join(missing));print('已标注规范关系',len(VARIANTS))
