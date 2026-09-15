import {readFileSync,writeFileSync} from 'node:fs';
const root='E:/夜莺2.0/work/夜莺2.0/34_新字频五万步双口径试验';
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const paths=read(root+'/测评码表路径.json');
const chars=read(root+'/../32_多来源字频重建/试验整字频率.json').字表;
const nf=chars.map(r=>[r.字,r.每百万核心字预计次数]);
// Native parser uses parseInt: upscale fractional trial frequencies before passing them in.
const frequencyScale=1e6;
const newtsv=nf.map(([c,f])=>[c,Math.round(f*frequencyScale)].join('\t')).join('\n');
const boxchars=parseFreqTsv(presetHanziFreq);
const byNew=new Map(nf);
const matchedtsv=boxchars.map(([c])=>[c,Math.round((byNew.get(c)||0)*frequencyScale)].join('\t')).join('\n');
const results=[];
for(const [name,path] of Object.entries(paths)){
 const items=readFileSync(path,'utf8').trim().split(/\r?\n/).map((l,i)=>{const [w,c]=l.split(/\s+/);return [w,c,i]});
 for(const [freq,tsv] of [['形码盒子字频',presetHanziFreq],['新字频新排名',newtsv],['盒子固定字档_新权重',matchedtsv]]){
  const r=quickEvaluateHanzi({items,cmLen:4,selectKeys:" ;'456789"},tsv);
  const sums=r.evaluate.map(s=>{
   const covered=s.items.filter(x=>'code' in x),denom=covered.reduce((n,x)=>n+x.freq,0);
   return {档位:`${s.start+1}–${s.end}`,缺字:s.items.length-covered.length,缺失频率比例:1-denom/s.freq,键均当量:covered.reduce((n,x)=>n+x.keyEq,0)/denom,字均当量:covered.reduce((n,x)=>n+x.ziEq,0)/denom,加权键长:covered.reduce((n,x)=>n+x.CL,0)/denom,原生含缺字分母当量:covered.reduce((n,x)=>n+x.keyEq,0)/s.freq};
  });
  results.push({方案:name,字频:freq,分档:sums,明细:r.evaluate,键盘热力:r.usage});
 }
}
writeFileSync(root+'/双字频测评原始.json',JSON.stringify(results,null,2));
const esc=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;');
let page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>新字频五万步 · 双口径当量</title><style>body{font:16px/1.65 system-ui;margin:25px;background:#f4f7fb;color:#234}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:9px}th{background:#dce9f3}.note{background:#fff3cd;padding:15px}</style><h1>新字频五万步 · 双口径当量</h1><p>一个projection起点，参数0、删利后133组，新分音估计字频，50000步。独立试验，没有启动晋级赛。</p><p class="note">相同码表分别换字频，使用形码盒子原生测评函数；四码首选自动上屏，短码加空格，同字取最短码，不限定读音。各档按各表排名，固定字档补充表用于区分换字与换权重。缺字不按零成本算，主表用覆盖字频归一化并列缺失率。单次试验只能报告数值变化，不能证明统计显著。</p><p><a href="五万步_普通单字表.txt">五万步普通单字表</a> · <a href="起点_普通单字表.txt">起点普通单字表</a></p>';
for(const freq of ['形码盒子字频','新字频新排名','盒子固定字档_新权重']){
 page+='<h2>'+freq+'</h2><table><tr><th>档位</th><th>起点</th><th>五万步</th><th>变化（越低越好）</th><th>夜莺1.0</th><th>五万步缺字／缺失频率</th></tr>';
 const a=results.find(r=>r.方案==='起点'&&r.字频===freq),b=results.find(r=>r.方案==='五万步'&&r.字频===freq),c=results.find(r=>r.方案==='夜莺1.0'&&r.字频===freq);
 for(let i=0;i<b.分档.length;i++){
  let x=a.分档[i],y=b.分档[i],z=c.分档[i];page+='<tr>'+[y.档位,x.键均当量.toFixed(6),y.键均当量.toFixed(6),(y.键均当量-x.键均当量).toFixed(6),z.键均当量.toFixed(6),y.缺字+' / '+(y.缺失频率比例*100).toFixed(4)+'%'].map(v=>'<td>'+esc(v)+'</td>').join('')+'</tr>';
 }
 page+='</table>';
}
page+='<h2>完整指标</h2><table><tr><th>方案</th><th>字频</th><th>档位</th><th>键均当量</th><th>字均当量</th><th>加权键长</th></tr>';
for(const r of results)for(const s of r.分档)page+='<tr>'+[r.方案,r.字频,s.档位,s.键均当量.toFixed(6),s.字均当量.toFixed(6),s.加权键长.toFixed(6)].map(v=>'<td>'+esc(v)+'</td>').join('')+'</tr>';
page+='</table></html>';writeFileSync(root+'/双字频当量对照.html',page);console.log(JSON.stringify(results.map(({明细,键盘热力,...rest})=>rest)));
