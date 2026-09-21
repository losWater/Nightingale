# -*- coding: utf-8 -*-
"""字根盲点分析页：把四份数据合成一页——键位与字根的错配、头部负担、位置分布、真实代价。"""
import io, sys, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
L = lambda f: json.load(open(H + '/' + f, encoding='utf-8'))
mis, head, pos, ver = L('键根错配.json'), L('头部负担.json'), L('位置与代价.json'), L('避重推论验证.json')
D = {'错配': mis, '头部': head, '位置': pos['位置分布'], '代价': pos['真实代价_前1500'], '验证': ver}
html = r'''<!doctype html><html lang="zh"><meta charset="utf-8"><title>夜莺 2.0 · 字根盲点分析</title>
<style>
:root{--bg:#fbfbfa;--fg:#1a1a1a;--sub:#6b6b6b;--dim:#9b9b99;--line:#e4e4e1;--card:#fff;--hi:#2c7fb8;--warn:#c0562e;--ok:#3d8a5f}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15171b;--fg:#e8e8e6;--sub:#9a9a98;--dim:#6e6e6c;--line:#2b2e35;--card:#1c1f26;--hi:#5aa9d6;--warn:#e08a63;--ok:#6fbf90}}
:root[data-theme=dark]{--bg:#15171b;--fg:#e8e8e6;--sub:#9a9a98;--dim:#6e6e6c;--line:#2b2e35;--card:#1c1f26;--hi:#5aa9d6;--warn:#e08a63;--ok:#6fbf90}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.68 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:1020px;margin:0 auto;padding:40px 18px 80px}
h1{font-size:28px;margin:0 0 8px;font-weight:660;letter-spacing:.3px}
h2{font-size:19px;margin:44px 0 6px;font-weight:630;padding-top:14px;border-top:1px solid var(--line)}
h2:first-of-type{border-top:none;padding-top:0}
.lede{color:var(--sub);font-size:14.5px;margin:0 0 6px}
.q{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--hi);border-radius:10px;padding:15px 19px;margin:20px 0;font-size:14.5px;line-height:1.85}
.q b{font-weight:650}
.tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}
.tab{padding:6px 17px;border:1px solid var(--line);border-radius:999px;background:var(--card);cursor:pointer;font-size:13.5px}
.tab:hover{border-color:var(--sub)}.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:6px 0 4px}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{font-size:12px;color:var(--sub);font-weight:600}
tr:last-child td{border-bottom:none}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr.hot td{background:rgba(44,127,184,.07)}
tr.hot td:first-child{box-shadow:inset 3px 0 0 var(--hi)}
.k{font-weight:700;font-size:15px}
.up{color:var(--ok)}.down{color:var(--warn)}
.bar{display:inline-block;height:6px;border-radius:3px;background:var(--hi);vertical-align:middle}
.note{color:var(--sub);font-size:12.5px;margin:8px 0 0;line-height:1.75}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:780px){.grid{grid-template-columns:1fr}table{font-size:12.5px}th,td{padding:5px 7px}}
.big{display:flex;gap:30px;flex-wrap:wrap;margin:14px 0 4px}
.big div{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:13px 20px;min-width:150px}
.big s{display:block;color:var(--sub);font-size:12.5px;text-decoration:none}
.big em{font-style:normal;font-size:25px;font-weight:660;font-variant-numeric:tabular-nums}
</style>
<div class="wrap">
<h1>夜莺 2.0 · 字根盲点分析</h1>
<p class="lede">起因：群里指出键位热力低不代表键上的根用得少。查下来是一条完整的因果链。</p>

<div class="q"><b>结论先放这里。</b><br>
退火只看键位热力，<code>p</code> 是倒数第二，像个闲键。但它双拼量全键盘最低（1.20%），字根量却是第二高（6.81%），
全码第三位和第四位都排第一。原因是避重算法让字根绕开高频双拼组合，双拼冷门的键成了安全区，
高频根和末根就往那儿堆；末根本来容易拆到笔画，所以 <code>p</code> 天然吸笔画根——1.0 放撇，2.0 放横。
代价是：这个位置在右手小指上排，按当量算是全键盘第二费力的字根键。</div>

<div class="big">
 <div><s>p 的双拼量</s><em>1.20%</em><s>全键盘最低</s></div>
 <div><s>p 的字根量</s><em>6.81%</em><s>全键盘第 2</s></div>
 <div><s>全码第 4 位</s><em>15.9%</em><s>第 1，是第 2 名的 1.4 倍</s></div>
 <div><s>双拼量 × 字根量</s><em>−0.50</em><s>相关系数</s></div>
</div>

<h2>一、双拼量与字根量负相关</h2>
<p class="lede">按双拼量从低到高排。越靠上＝这个音越冷门，字根负担却越重。</p>
<table id="t_ver"></table>
<p class="note">双拼量＝该键在前两码（声母韵母位）的加权占比；首根量、末根量分别是第三、第四位的加权占比。前 1500 档。</p>

<h2>二、键位名次与字根名次的错配</h2>
<p class="lede">错配＝键位名次减去形码名次。正数越大，说明键位热力越是低估了这个键。</p>
<div class="tabs" id="tab_mis"></div>
<table id="t_mis"></table>

<h2>三、是头部几个根撑着，还是长尾堆的</h2>
<p class="lede">每个键只取使用量前 50% / 30% 的根（四舍五入，至少 1 个）再排名。名次不掉＝核心负担在头部。</p>
<div class="tabs" id="tab_head"></div>
<table id="t_head"></table>
<p class="note">p 砍掉 70% 的长尾根后仍是第 2，量只从 6.81% 掉到 6.50%——它是真忙。a、o、w 则明显上升，那是「单根独大」的形态。</p>

<h2>四、第三位与第四位的键分布</h2>
<p class="lede">简码表只看打简后是三码的字；全码表看每个字的四码编码本身。</p>
<div class="tabs" id="tab_pos"></div>
<div class="grid"><div><h3 style="font-size:14px;margin:6px 0">简码 · 第 3 位</h3><table id="t_p1"></table></div>
<div><h3 style="font-size:14px;margin:6px 0">全码 · 第 3 位</h3><table id="t_p2"></table></div></div>
<div style="margin-top:14px"><h3 style="font-size:14px;margin:6px 0">全码 · 第 4 位</h3><table id="t_p3"></table></div>

<h2>五、真实代价</h2>
<p class="lede">把字根位的量乘以进入该键的击键当量。代价量比大于 1，说明这个键比平均更费力。</p>
<table id="t_cost"></table>
<p class="note">当量取自形码盒子的按键当量数据（54/frozen/当量表.tsv）。前 1500 档。</p>
</div>
<script>
const D=__D__;
const pct=v=>v.toFixed(2)+'%';
const bar=(v,max,w)=>`<span class="bar" style="width:${Math.max(1,v/max*(w||60))}px"></span>`;
function tbl(id,head,rows,hot){document.getElementById(id).innerHTML=
 '<tr>'+head.map(h=>`<th class="${h[1]||''}">${h[0]}</th>`).join('')+'</tr>'+
 rows.map(r=>`<tr class="${hot&&hot(r)?'hot':''}">`+r.map((c,i)=>`<td class="${head[i][1]||''}">${c}</td>`).join('')+'</tr>').join('')}
// 一
const V=D.验证,ks=Object.keys(V.双拼量).sort((a,b)=>V.双拼量[a]-V.双拼量[b]),mx=Math.max(...Object.values(V.字根总量));
tbl('t_ver',[['键'],['双拼量','n'],['首根量','n'],['末根量','n'],['字根总量','n'],['']],
 ks.map(k=>[`<span class="k">${k.toUpperCase()}</span>`,pct(V.双拼量[k]),pct(V.首根量[k]),pct(V.末根量[k]),pct(V.字根总量[k]),bar(V.字根总量[k],mx,120)]),
 r=>r[0].includes('>P<'));
// 二
let mb=Object.keys(D.错配)[0];
function drawMis(){document.getElementById('tab_mis').innerHTML=Object.keys(D.错配).map(b=>`<div class="tab${b===mb?' on':''}" data-b="${b}">${b} 字</div>`).join('');
 const rows=D.错配[mb].键.slice().sort((a,b)=>b.错配-a.错配);
 tbl('t_mis',[['键'],['键位量','n'],['键位名次','n'],['形码量','n'],['形码名次','n'],['错配','n'],['根数','n'],['头根'],['前30','n'],['均名次','n']],
  rows.map(r=>[`<span class="k">${r.键.toUpperCase()}</span>`,pct(r.键位量),r.键位名次,pct(r.形码量),r.形码名次,
   `<span class="${r.错配>0?'up':(r.错配<0?'down':'')}">${r.错配>0?'+':''}${r.错配}</span>`,r.根数,
   `${r.头根}<span style="color:var(--dim)"> 第${r.头根名次}名 ${r.头根占本键.toFixed(0)}%</span>`,r['前30'],r.均名次.toFixed(0)]),
  r=>r[0].includes('>P<'))}
// 三
let hb=Object.keys(D.头部)[0];
function drawHead(){document.getElementById('tab_head').innerHTML=Object.keys(D.头部).map(b=>`<div class="tab${b===hb?' on':''}" data-b="${b}">${b} 字</div>`).join('');
 const c=D.头部[hb].口径,all=c['全部'],h50=c['前 50%'],h30=c['前 30%'];
 const rows=Object.keys(all).sort((a,b)=>all[a].名次-all[b].名次).map(k=>{const d=all[k].名次-h30[k].名次;
  return [`<span class="k">${k.toUpperCase()}</span>`,pct(all[k].占比),all[k].名次,pct(h50[k].占比),h50[k].名次,pct(h30[k].占比),h30[k].名次,
   `<span class="${d>0?'up':(d<0?'down':'')}">${d>0?'+':''}${d}</span>`,all[k].根数,
   `<span style="color:var(--dim)">${h30[k].根.slice(0,5).join('、')}</span>`]});
 tbl('t_head',[['键'],['全部根','n'],['名次','n'],['前50%','n'],['名次','n'],['前30%','n'],['名次','n'],['变动','n'],['根数','n'],['前30%的根']],rows,r=>r[0].includes('>P<'))}
// 四
let pb=Object.keys(D.位置)[0];
function drawPos(){document.getElementById('tab_pos').innerHTML=Object.keys(D.位置).map(b=>`<div class="tab${b===pb?' on':''}" data-b="${b}">${b} 字</div>`).join('');
 const t=D.位置[pb],pairs=[['t_p1','简码（打简后三码）','第 3 位'],['t_p2','全码（每字四码）','第 3 位'],['t_p3','全码（每字四码）','第 4 位']];
 pairs.forEach(([id,tab,ps])=>{const x=t[tab][ps];if(!x){document.getElementById(id).innerHTML='';return}
  const tw=Object.values(x.加权).reduce((a,b)=>a+b,0),tn=Object.values(x.字数).reduce((a,b)=>a+b,0);
  const sorted=Object.entries(x.加权).sort((a,b)=>b[1]-a[1]),mx=sorted[0][1];
  tbl(id,[['名次','n'],['键'],['加权占比','n'],['字数','n'],['']],
   sorted.map(([k,v],i)=>[i+1,`<span class="k">${k.toUpperCase()}</span>`,pct(v/tw*100),(x.字数[k]||0),bar(v,mx,70)]),
   r=>r[1].includes('>P<'))})}
// 五
const mxc=Math.max(...D.代价.map(r=>r['代价占比%']));
tbl('t_cost',[['键'],['字根量','n'],['代价占比','n'],['平均当量','n'],['代价量比','n'],['']],
 D.代价.map(r=>[`<span class="k">${r.键.toUpperCase()}</span>`,pct(r['字根量%']),pct(r['代价占比%']),r.平均当量.toFixed(3),
  `<span class="${r.代价量比>1.02?'down':(r.代价量比<0.98?'up':'')}">${r.代价量比.toFixed(3)}</span>`,bar(r['代价占比%'],mxc,90)]),
 r=>r[0].includes('>P<'));
document.getElementById('tab_mis').addEventListener('click',e=>{if(e.target.dataset.b){mb=e.target.dataset.b;drawMis()}});
document.getElementById('tab_head').addEventListener('click',e=>{if(e.target.dataset.b){hb=e.target.dataset.b;drawHead()}});
document.getElementById('tab_pos').addEventListener('click',e=>{if(e.target.dataset.b){pb=e.target.dataset.b;drawPos()}});
drawMis();drawHead();drawPos();
</script></html>'''
open(H + '/字根盲点分析.html', 'w', encoding='utf-8', newline='\n').write(html.replace('__D__', json.dumps(D, ensure_ascii=False)))
print('→ %s/字根盲点分析.html  (%.1f KB)' % (H, os.path.getsize(H + '/字根盲点分析.html') / 1024))
