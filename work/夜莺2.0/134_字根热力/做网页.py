# -*- coding: utf-8 -*-
"""字根热力网页：三档 × 两口径的排名，加每个键的根贡献分解（回答"这个频率被这个常用偏旁独占了吗"）。"""
import io, sys, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(H + '/字根热力.json', encoding='utf-8'))
kd = json.load(open(H + '/每键的根贡献.json', encoding='utf-8'))['前 1500 档']
bands = {b['档']: b for b in d['分档']}
html = '''<!doctype html><html lang="zh"><meta charset="utf-8"><title>夜莺 2.0 字根热力</title>
<style>
:root{--bg:#fbfbfa;--fg:#1a1a1a;--sub:#6b6b6b;--line:#e4e4e1;--card:#fff;--hi:#2c7fb8}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16181c;--fg:#e8e8e6;--sub:#9a9a98;--line:#2c2f36;--card:#1d2027;--hi:#5aa9d6}}
:root[data-theme=dark]{--bg:#16181c;--fg:#e8e8e6;--sub:#9a9a98;--line:#2c2f36;--card:#1d2027;--hi:#5aa9d6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:36px 16px 72px}
h1{font-size:26px;margin:0 0 6px;font-weight:650}
h2{font-size:18px;margin:38px 0 14px;font-weight:620}
.sub{color:var(--sub);font-size:14px;margin:0 0 8px}
.tabs{display:flex;gap:8px;margin:18px 0;flex-wrap:wrap}
.tab{padding:7px 18px;border:1px solid var(--line);border-radius:999px;background:var(--card);cursor:pointer;font-size:14px}
.tab:hover{border-color:var(--sub)}.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:720px){.cols{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:16px 18px}
.card h3{margin:0 0 12px;font-size:15px;font-weight:620}
.row{display:flex;align-items:center;gap:9px;padding:3px 0;font-size:14px}
.row .i{width:24px;text-align:right;color:var(--sub);font-size:12px;font-variant-numeric:tabular-nums}
.row .r{min-width:132px;font-size:15px}
.row .k{color:var(--sub);font-size:12px;min-width:20px}
.row .p{width:54px;text-align:right;font-variant-numeric:tabular-nums;font-size:13px}
.row .b{flex:1;height:7px;background:var(--line);border-radius:4px;overflow:hidden}
.row .b i{display:block;height:100%;background:var(--hi);border-radius:4px}
.keys{display:flex;flex-direction:column;gap:7px}
.kb{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:14px 16px}
.kb .hd{display:flex;align-items:baseline;gap:12px;margin-bottom:7px}
.kb .kk{font-size:21px;font-weight:700;width:26px}
.kb .m{color:var(--sub);font-size:13px}
.seg{display:flex;height:22px;border-radius:5px;overflow:hidden;font-size:11px;color:#fff}
.seg span{display:flex;align-items:center;justify-content:center;white-space:nowrap;overflow:hidden}
.note{color:var(--sub);font-size:13px;margin-top:26px;line-height:1.85}
.lead{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--hi);border-radius:10px;padding:14px 18px;margin:18px 0;font-size:14px;line-height:1.8}
</style>
<div class="wrap">
<h1>夜莺 2.0 · 字根热力</h1>
<p class="sub">打简的前提下，每个字根实际被敲到的次数。字频取形码盒子 1.0 的默认字频。</p>

<div class="lead"><b>为什么要按根看，而不是按键看。</b><br>
键位热力低，不等于键上的根用得少。<code>a</code> 键按键位排第 24，但它 67% 的量来自「氵」一个根；
<code>o</code> 键 89% 来自「扌」。反过来 <code>p</code> 键挂了 30 个根在用，最大的一个也才占本键 14%，
是全键盘最分散的。只看键位会把这两种情况混为一谈。</div>

<div class="tabs" id="tabs"></div>
<div class="cols">
 <div class="card"><h3>130 组（归并后）</h3><div id="g"></div></div>
 <div class="card"><h3>403 根形（不归并）</h3><div id="s"></div></div>
</div>

<h2>每个键的量由哪些根贡献</h2>
<p class="sub">前 1500 档。色块宽度＝该根占本键的比例；括号里是这个键占全部形码按键的比例。</p>
<div class="keys" id="keys"></div>

<p class="note">口径：每个字取最短的正式码（容错码、特殊简码不计）。字根只在实际打出来时才计数——一简二简不碰形码，三简只用首根，全码用首末两根。
所以高频区的字根样本偏小：前 500 字里 66% 打的是一二简，只有 33% 打到三简、1% 打全码。</p>
</div>
<script>
const B=__BANDS__, K=__KEYS__;
let cur=Object.keys(B)[0];
const bar=(list,key,n)=>{const hi=list[0].占比;
 return list.slice(0,n).map(r=>`<div class="row"><span class="i">${r.名次}</span><span class="r">${r[key]}</span>
 <span class="k">${r.键||''}</span><span class="p">${r.占比.toFixed(2)}%</span>
 <span class="b"><i style="width:${r.占比/hi*100}%"></i></span></div>`).join('')};
function draw(){
 document.getElementById('tabs').innerHTML=Object.keys(B).map(k=>`<div class="tab${k===cur?' on':''}" data-k="${k}">${k} 字</div>`).join('');
 document.getElementById('g').innerHTML=bar(B[cur].组排名,'组',30);
 document.getElementById('s').innerHTML=bar(B[cur].根形排名,'根',30);
}
const PAL=['#2c7fb8','#41a5c4','#7fcdbb','#a8ddb5','#ccebc5','#e0f3db','#f7fcf0','#dfe6ec','#c9d4de','#b3c2d0'];
document.getElementById('keys').innerHTML=Object.entries(K).map(([k,v])=>{
 const top=v.各根贡献, big=top[0];
 return `<div class="kb"><div class="hd"><span class="kk">${k.toUpperCase()}</span>
  <span class="m">占形码量 <b>${v['键占形码量%'].toFixed(2)}%</b>　${top.length} 个根在用，最大的占本键 ${big['占本键%'].toFixed(0)}%</span></div>
  <div class="seg">${top.map((r,i)=>`<span style="width:${r['占本键%']}%;background:${PAL[i%PAL.length]};color:${i<3?'#fff':'#333'}"
   title="${r.根}　占本键 ${r['占本键%']}%　占全局 ${r['占全局%']}%">${r['占本键%']>5?r.根:''}</span>`).join('')}</div></div>`}).join('');
document.getElementById('tabs').addEventListener('click',e=>{const k=e.target.dataset.k;if(k){cur=k;draw()}});
draw();
</script></html>'''
html = html.replace('__BANDS__', json.dumps(bands, ensure_ascii=False)).replace('__KEYS__', json.dumps(kd, ensure_ascii=False))
open(H + '/字根热力.html', 'w', encoding='utf-8', newline='\n').write(html)
print('→ %s/字根热力.html  (%.1f KB)' % (H, os.path.getsize(H + '/字根热力.html') / 1024))
