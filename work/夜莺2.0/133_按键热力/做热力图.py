# -*- coding: utf-8 -*-
"""把按键热力做成一张网页：键盘布局配色，三档可切换，鼠标悬停看明细。"""
import io, sys, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(H + '/按键热力.json', encoding='utf-8'))
bands = d['分档']
ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
data = {b['档']: {r['键']: r for r in b['键位排名']} for b in bands}
meta = {b['档']: {'字数': b['字数'], '平均码长': b['平均码长'], '总按键': b['加权总按键']} for b in bands}
html = '''<!doctype html><html lang="zh"><meta charset="utf-8"><title>夜莺 2.0 按键热力</title>
<style>
:root{--bg:#fbfbfa;--fg:#1a1a1a;--sub:#6b6b6b;--line:#e3e3e0;--card:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16181c;--fg:#e8e8e6;--sub:#9a9a98;--line:#2c2f36;--card:#1d2027}}
:root[data-theme=dark]{--bg:#16181c;--fg:#e8e8e6;--sub:#9a9a98;--line:#2c2f36;--card:#1d2027}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:36px 16px 64px}
h1{font-size:26px;margin:0 0 6px;font-weight:650;letter-spacing:.3px}
.sub{color:var(--sub);font-size:14px;margin:0 0 26px}
.tabs{display:flex;gap:8px;margin:0 0 20px;flex-wrap:wrap}
.tab{padding:7px 18px;border:1px solid var(--line);border-radius:999px;background:var(--card);cursor:pointer;font-size:14px;transition:.15s}
.tab:hover{border-color:var(--sub)}
.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.kb{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 18px;margin-bottom:22px}
.krow{display:flex;justify-content:center;gap:7px;margin-bottom:7px}
.krow:nth-child(2){padding-left:26px}.krow:nth-child(3){padding-left:66px}
.key{width:62px;height:62px;border-radius:9px;display:flex;flex-direction:column;align-items:center;justify-content:center;
 font-size:19px;font-weight:600;color:#1a1a1a;position:relative;cursor:default;transition:.2s}
.key small{font-size:10.5px;font-weight:400;opacity:.72;margin-top:2px}
.key b{position:absolute;top:3px;right:6px;font-size:10px;font-weight:600;opacity:.6}
.stat{display:flex;gap:26px;flex-wrap:wrap;color:var(--sub);font-size:13.5px;margin:0 0 22px;padding:0 4px}
.stat b{color:var(--fg);font-weight:600}
table{border-collapse:collapse;width:100%;font-size:14px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:7px 12px;text-align:left;border-bottom:1px solid var(--line)}
th{font-weight:600;font-size:13px;color:var(--sub);background:transparent}
tr:last-child td{border-bottom:none}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.bar{height:6px;border-radius:3px;display:block}
.note{color:var(--sub);font-size:13px;margin-top:22px;line-height:1.8}
</style>
<div class="wrap">
<h1>夜莺 2.0 · 按键热力</h1>
<p class="sub">打简的前提下，每个键的按键次数。字频取形码盒子 1.0 的默认字频。</p>
<div class="tabs" id="tabs"></div>
<div class="kb" id="kb"></div>
<div class="stat" id="stat"></div>
<table id="tb"></table>
<p class="note">口径：每个字用它最短的正式码（一简 → 二简 → 三简 → 全码）；容错码与特殊简码不计，它们是额外入口不是常打路径。
多音字取最短的那个码，同长度时取码表里靠前的。占比 = 该键按键次数 ÷ 本档加权总按键次数。</p>
</div>
<script>
const DATA=__DATA__, META=__META__, ROWS=__ROWS__;
const FINGER={q:'左小',a:'左小',z:'左小',w:'左无',s:'左无',x:'左无',e:'左中',d:'左中',c:'左中',
 r:'左食',f:'左食',v:'左食',t:'左食',g:'左食',b:'左食',y:'右食',h:'右食',n:'右食',u:'右食',j:'右食',m:'右食',
 i:'右中',k:'右中',o:'右无',l:'右无',p:'右小'};
let cur=Object.keys(DATA)[0];
function color(p,lo,hi){const t=(p-lo)/(hi-lo||1);
 const stops=[[247,249,252],[214,231,243],[161,205,229],[103,169,207],[44,127,184],[8,81,156]];
 const x=Math.min(.999,Math.max(0,t))*(stops.length-1),i=Math.floor(x),f=x-i;
 const a=stops[i],b=stops[i+1]||a;return `rgb(${a.map((v,k)=>Math.round(v+(b[k]-v)*f)).join(',')})`}
function draw(){
 const rows=DATA[cur],vals=Object.values(rows).map(r=>r.占比),lo=Math.min(...vals),hi=Math.max(...vals);
 document.getElementById('tabs').innerHTML=Object.keys(DATA).map(k=>`<div class="tab${k===cur?' on':''}" data-k="${k}">${k} 字</div>`).join('');
 document.getElementById('kb').innerHTML=ROWS.map(r=>'<div class="krow">'+[...r].map(k=>{const d=rows[k];
  return `<div class="key" style="background:${color(d.占比,lo,hi)};color:${d.占比>(lo+hi)/1.75?'#fff':'#1a1a1a'}" title="${k}　第 ${d.名次} 名　${d.占比}%　${FINGER[k]}指">
   <b>${d.名次}</b>${k.toUpperCase()}<small>${d.占比.toFixed(2)}%</small></div>`}).join('')+'</div>').join('');
 const m=META[cur],fg={};Object.entries(rows).forEach(([k,d])=>fg[FINGER[k]]=(fg[FINGER[k]]||0)+d.占比);
 const lh=['左小','左无','左中','左食'].reduce((s,f)=>s+(fg[f]||0),0);
 document.getElementById('stat').innerHTML=
  `<span>字数 <b>${m.字数}</b></span><span>平均码长 <b>${m.平均码长}</b></span>`+
  `<span>左手 <b>${lh.toFixed(1)}%</b> · 右手 <b>${(100-lh).toFixed(1)}%</b></span>`+
  `<span>${Object.entries(fg).sort((a,b)=>b[1]-a[1]).map(([f,v])=>f+' '+v.toFixed(1)+'%').join('　')}</span>`;
 document.getElementById('tb').innerHTML='<tr><th>名次</th><th>键</th><th>手指</th><th style="text-align:right">占比</th><th style="width:38%">　</th></tr>'+
  Object.values(rows).sort((a,b)=>a.名次-b.名次).map(d=>
   `<tr><td class="n">${d.名次}</td><td><b>${d.键.toUpperCase()}</b></td><td>${d.手指}</td><td class="n">${d.占比.toFixed(2)}%</td>
    <td><span class="bar" style="width:${d.占比/hi*100}%;background:${color(d.占比,lo,hi)}"></span></td></tr>`).join('');
}
document.getElementById('tabs').addEventListener('click',e=>{const k=e.target.dataset.k;if(k){cur=k;draw()}});
draw();
</script></html>'''
html = html.replace('__DATA__', json.dumps(data, ensure_ascii=False)).replace('__META__', json.dumps(meta, ensure_ascii=False)).replace('__ROWS__', json.dumps(ROWS))
open(H + '/按键热力.html', 'w', encoding='utf-8', newline='\n').write(html)
print('→ %s/按键热力.html  (%.1f KB)' % (H, os.path.getsize(H + '/按键热力.html') / 1024))
