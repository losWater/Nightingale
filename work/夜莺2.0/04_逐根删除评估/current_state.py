"""Current accepted baseline after 用月、甬字底、删角、举字底归王丰。"""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'review_three_codes.py')}
exec((P/'review_three_codes.py').read_text(encoding='utf-8').split('ledgerpath=')[0],ns)
raw=json.loads((P/'yong-yue-jiao-raw.json').read_text(encoding='utf-8'))
variant=json.loads((P/'yong-variant-raw.json').read_text(encoding='utf-8'))['variant']
rows=dict(ns['BASE'])
for c,seq in variant.items():
 if seq!=raw['base'][c]:
  assert rows[c]==raw['base'][c] and c not in ns['RB']['manual']
  rows[c]=seq
# 用户已确认的14根联合删除；保留人工拆分边界。
selected=json.loads((P/'review-deletions.json').read_text(encoding='utf-8'))
removed={selected[f'DEL-{i:03}']['id']:selected[f'DEL-{i:03}']['replacement'] for i in range(3,17)}
joint=json.loads((P/'fourteen-joint-current-raw.json').read_text(encoding='utf-8'))['joint']
for c,seq in list(rows.items()):
 if c in ns['RB']['manual']:
  rows[c]=[x for t in seq for x in removed.get(t,[t])]
 elif joint[c]!=variant[c]:
  assert seq==variant[c],('维护拆分差异',c)
  rows[c]=joint[c]
assert not any(t in removed for seq in rows.values() for t in seq)

# 已确认敖左归横，传播使用已核验的全量结果。
ao_raw=json.loads((P/'ao-left-raw.json').read_text(encoding='utf-8'))['joint']
for c,seq in ao_raw.items():
 if seq!=joint[c]:
  assert rows[c]==joint[c],('敖左传播边界变化',c)
  rows[c]=seq
ns['INV']['\ue05f']={'display':'敖左'}

# 缶牛午马卸左联合方案；击默认二＋山，另一拆法在参数中保留。
JI_ALTERNATIVES = {"er": ["二", "山"], "ju": [ns["rid"]("举字底"), "凵"]}
ACTIVE_JI_VARIANT = "er"
cattle_raw=json.loads((P/'fou-niu-wu-ma-xie-raw.json').read_text(encoding='utf-8'))[ACTIVE_JI_VARIANT]
for c,seq in cattle_raw.items():
 if seq!=ao_raw[c]:
  assert rows[c]==ao_raw[c],('缶牛午卸左传播边界变化',c)
  rows[c]=seq
ns['INV']['午']={'display':'午'}
ns['INV']['\ue021']={'display':'卸左'}
assert all('击' not in seq for seq in rows.values())

# 已确认删除皿组附属根署；保留人工拆分的其他部分。
rows={c:[x for t in seq for x in (["罒","耂","日"] if t=="署" else [t])] for c,seq in rows.items()}
assert not any("署" in seq for seq in rows.values())

# 最新确认：新增万及删除佥，已与署删除等当前方案联合重跑。
wan_before=json.loads((P/'before-wan-qian-raw.json').read_text(encoding='utf-8'))['er']
wan_after=json.loads((P/'wan-qian-raw.json').read_text(encoding='utf-8'))['er']
for c,seq in wan_after.items():
 if seq!=wan_before[c]:
  assert rows[c]==wan_before[c],('万佥边界变化',c)
  rows[c]=seq
ns['INV']['万']={'display':'万'}
assert not any('佥' in seq for seq in rows.values())

ns['INV']['\ue08c']={'display':'甬字底'}
# 人旁四组合并：用户要求暂时纳入，尚未最终确认。
oldgroup=ns['grouping'](person=True)
def group(x):
 if x=="万" or oldgroup(x) in {oldgroup("十"),oldgroup("千")}:return "十千万锚定"
 if oldgroup(x) in {oldgroup("足"),oldgroup("止"),oldgroup(ns["rid"]("定字底"))}:return "走止足定底"
 if x in ["午","\ue021"] or oldgroup(x) in {oldgroup("缶"),oldgroup("牛"),oldgroup("马")}:return "缶牛午马"
 if x=="\ue05f":return oldgroup(ns["rid"]("横"))
 if x=="龷" or oldgroup(x) in {oldgroup("井"),oldgroup("艹"),oldgroup(ns["rid"]("冓头"))}:return "井艹龷冓头"
 if oldgroup(x) in {oldgroup("无"),oldgroup("大")}:return "无大天"
 if oldgroup(x) in {oldgroup("几"),oldgroup("匚")}:return "几匚"
 if x in ['用','\ue08c']:return oldgroup('月')
 if x==ns['rid']('举字底'):return oldgroup('王')
 return oldgroup(x)
assert all('角' not in seq for seq in rows.values())

# 已确认新增生、乍独立；亡归亠，不归横。赢字架保持整体。
rows=json.loads((P/'生亡乍不累计拆分.json').read_text(encoding='utf-8'))
for x in '生亡乍不':ns['INV'][x]={'display':x}
_group_before_swzb=group
def group(x):
 if x in ['生','乍']:return '新增独立根:'+x
 if x=='亡':return _group_before_swzb(ns['rid']('亠'))
 if x=='不':return _group_before_swzb(ns['rid']('横'))
 return _group_before_swzb(x)

# 已确认删除居根；沿用试算的尸＋古拆法，保持其他边界。
rows={ch:[x for t in seq for x in (['尸','古'] if t=='居' else [t])] for ch,seq in rows.items()}
assert all('居' not in seq for seq in rows.values())

# 已确认新增果归里；保留里根，沿用已核验的字族传播。
rows=json.loads((P/'果归里累计拆分.json').read_text(encoding='utf-8'))
ns['INV']['果']={'display':'果'}
_group_before_guo=group
def group(x):
 if x=='果':return _group_before_guo('里')
 return _group_before_guo(x)

# 四组形象锚定已确认；禾木保持分开。
_group_before_four=group
_four_pairs=[('黑','白'),('鸟','虫'),('大','小'),('犭','豸')]
_four_hosts={_group_before_four(ns['rid'](b)):_group_before_four(ns['rid'](a)) for a,b in _four_pairs}
def group(x):
 g=_group_before_four(x)
 return _four_hosts.get(g,g)

# 已确认删除贤字头和览字头；包括临字手工拆分中的部件。
_xian_lan_replacements={ns['rid']('贤字头'):['丨','丨','又'],ns['rid']('览字头'):['丨','丨',ns['rid']('卧人'),'丶']}
rows={ch:[x for t in seq for x in _xian_lan_replacements.get(t,[t])] for ch,seq in rows.items()}
assert not any(t in _xian_lan_replacements for seq in rows.values() for t in seq)

# 已确认㐄归竖；保留完整根形及原拆分。
_group_before_kuai=group
def group(x):
 if x=='㐄':return _group_before_kuai(ns['rid']('竖'))
 return _group_before_kuai(x)

# 已确认恢复尺，沿用原根族归属。
rows=json.loads((P/"恢复尺累计拆分.json").read_text(encoding="utf-8"))

# 已确认耒归未族，保留完整耒根形。
_group_before_lei_wei=group
def group(x):
 if x=="耒":return _group_before_lei_wei(ns["rid"]("未"))
 return _group_before_lei_wei(x)

# 已确认新增匈归框族，保留匃。
rows=json.loads((P/"匈加根累计拆分.json").read_text(encoding="utf-8"))
ns["INV"]["匈"]={"display":"匈"}
_group_before_xiong=group
def group(x):
 if x=="匈":return _group_before_xiong("匃")
 return _group_before_xiong(x)

# 已确认恢复啇归商，沿用原有根族归属。
rows=json.loads((P/"恢复啇累计拆分.json").read_text(encoding="utf-8"))

# 已确认厉里儿三项锚定，保留主根身份。
_group_before_lile=group
_lile_hosts={_group_before_lile(ns['rid'](a)):_group_before_lile(ns['rid'](b)) for a,b in [('厉','万'),('里','田'),('儿','子')]}
def group(x):
 g=_group_before_lile(x)
 return _lile_hosts.get(g,g)

# 剩余候选联合确认；亥独立，人旁四组正式确认，付保留。
rows=json.loads((P/'剩余候选累计拆分.json').read_text(encoding='utf-8'))
for x in '食攴支辰刃亥':ns['INV'][x]={'display':x}
_group_before_final=group
_final_hosts={'食':'饣','攴':'又','支':'又','辰':'氏','刃':'刀'}
def group(x):
 if x=='亥':return '新增独立根:亥'
 if x in _final_hosts:return _group_before_final(ns['rid'](_final_hosts[x]))
 g=_group_before_final(x)
 if g==_group_before_final('皮'):return _group_before_final('毛')
 if g==_group_before_final(ns['rid']('氵')):return _group_before_final(ns['rid']('点'))
 return g

# 2026-09-12 已确认删除利根，全字族展开禾＋刂。
rows={ch:[x for t in seq for x in (["禾","刂"] if t=="利" else [t])] for ch,seq in rows.items()}
assert all("利" not in seq for seq in rows.values())
