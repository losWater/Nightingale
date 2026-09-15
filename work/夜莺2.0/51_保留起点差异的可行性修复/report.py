from pathlib import Path
import json,html,itertools
P=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
results=read(P/'结果.json');rows=list(results.values())
def table(h,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(str(v))+'</th>' for v in h)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in r)+'</tr>' for r in rows)+'</table></div>'
s='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>不同起点可行性验证</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:28px}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:8px}.scroll{overflow:auto}</style><h1>不同起点可行性验证</h1><p>当前可行布局、小改8根组、大改60根组、全133根组随机赋键；各两个种子。固定音键与归并锚定组不拆散。随机起点先独立可行化：违规主音数×10000＋修复改动根组数×10＋原目标，最多50000步，修复温度1→0.01，达到零即停止；失败不进入正式搜索，也不替换为基线。</p><p>可行后关闭修复模式，使用原均衡参数和硬保护正式运行5000步，再独立重编码。只是启动管线和布局多样性验证，不是5万步性能测评或500组正式大跑。</p>'
s+=table(['任务','状态','初始缺口','修复步数','初始距基线','修复后距基线','修复改动根组','正式5000步后距基线','剩余缺口'],[[r['id'],r['状态'],r['初始主音缺口'],r['修复步数'],r['初始偏离基线根组'],r.get('可行起点偏离基线根组','—'),r.get('修复改变初始根组','—'),r.get('终点偏离基线根组','—'),r.get('剩余缺口',r.get('终点缺口','—'))] for r in rows])
passed=[r for r in rows if r['状态']=='通过'];maps={r['id']:read(P/r['id']/'可行起点.json')['form']['mapping'] for r in passed}
dist=[]
for a,b in itertools.combinations(maps,2):dist.append({'起点A':a,'起点B':b,'不同根组数':sum(maps[a][k]!=maps[b][k] for k in maps[a] if k.startswith('G'))})
s+='<h2>修复后起点的两两距离</h2>'+table(['起点A','起点B','不同根组数'],[[r['起点A'],r['起点B'],r['不同根组数']] for r in dist])
s+='<h2>仍不达标的字</h2>'+table(['任务','不达标主音'],[[r['id'],r.get('修复后不达标',[])] for r in rows if r['状态']!='通过'])
s+='<details><summary>各起点原始缺口</summary>'+table(['任务','缺口'],[[r['id'],r['初始不达标']] for r in rows])+'</details>'
s+='<h2>已通过结果的普通单字表</h2>'
for r in passed:s+=f'<p><a href="{(P/r["id"]/"普通单字表.txt").as_uri()}">{r["id"]}</a></p>'
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text(encoding='utf8').splitlines()]
summary={'通过数':len(passed),'总数':len(rows),'通过任务修复后不同起点数':len({json.dumps(v,sort_keys=True) for v in maps.values()}),'最低可用内存GiB':min(r['availableGiB'] for r in resources),'最低E盘可用GiB':min(r['EfreeGiB'] for r in resources),'正式最大缓存差':max((r['正式缓存差'] for r in passed),default=None),'500组启动':False}
(P/'核验摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
(P/'起点距离.json').write_text(json.dumps(dist,ensure_ascii=False,indent=2),encoding='utf8')
s+='<h2>核验摘要</h2>'+table(['项目','结果'],summary.items())
if (P/'结论片段.html').exists():s+=(P/'结论片段.html').read_text(encoding='utf8')
(P/'可行性验证.html').write_text(s+'</html>',encoding='utf8')
print(json.dumps(summary,ensure_ascii=False),flush=True)
