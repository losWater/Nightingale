import {readFileSync,writeFileSync} from 'node:fs';
const P='E:/夜莺2.0/work/夜莺2.0/35_同种子三字频对照',W=P+'/..';
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const old=read(W+'/27_删利根参数0晋级赛/frozen/字音基准.json'),nw=read(W+'/32_多来源字频重建/试验整字频率.json').字表;
const counts=new Map();for(const r of old)counts.set(r.字,(counts.get(r.字)||0)+r.频率);
const oldRows=[...counts].sort((a,b)=>b[1]-a[1]||(a[0]<b[0]?-1:1));
const tables={'老表':oldRows.map(r=>r.join('\t')).join('\n'),'新表':nw.map(r=>[r.字,Math.round(r.每百万核心字预计次数*1e6)].join('\t')).join('\n'),'盒子表':presetHanziFreq};
const results=[];
for(const train of ['老表','新表','盒子表'])for(const phase of ['起点','五万步']){
 const path=P+'/'+train+'_'+phase+'单字表.txt';const items=readFileSync(path,'utf8').trim().split(/\r?\n/).map((l,i)=>{const [w,c]=l.split(/\s+/);return [w,c,i]});
 for(const [evalName,tsv] of Object.entries(tables)){
  const r=quickEvaluateHanzi({items,cmLen:4,selectKeys:" ;'456789"},tsv);
  const sums=r.evaluate.map(s=>{const covered=s.items.filter(x=>'code' in x),denom=covered.reduce((n,x)=>n+x.freq,0);return {档位:`${s.start+1}–${s.end}`,缺字:s.items.length-covered.length,缺失频率比例:1-denom/s.freq,键均当量:covered.reduce((n,x)=>n+x.keyEq,0)/denom,字均当量:covered.reduce((n,x)=>n+x.ziEq,0)/denom,加权键长:covered.reduce((n,x)=>n+x.CL,0)/denom};});
  results.push({训练字频:train,阶段:phase,测评字频:evalName,分档:sums,明细:r.evaluate,键盘热力:r.usage});
 }
}
writeFileSync(P+'/三字频交叉测评.json',JSON.stringify(results,null,2));
let page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>同种子三字频对照</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;margin:25px;color:#234}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:9px}th{background:#dce9f3}.note{background:#fff1c8;padding:16px}</style><h1>同种子 · 三字频 · 各五万步</h1><p>参考g01_projection_01的已保存起点；统一种子202609121701。旧引擎未保存内部随机流，本次用种子版引擎重跑三组。2000步重复运行已验证码表和分数一致。</p><p class="note">根集、初始布局、参数、锁定简码、步数、随机数算法及种子相同。只更换输入频率及排序。盒子整字频率按新表分音比例拆分；盒子未覆盖的2145个核心字记为来源缺失、输入0，不借旧表补齐。最终交叉测评使用自然整字频率，不使用优化权重。这里只是一组三臂探索，不是多种子统计显著性结论。盒子有频而新表无分音比例的52字，在方案读音集合内均分（单音则全配）；详见最终核验。</p>';
for(const ev of ['盒子表','新表','老表']){
 page+='<h2>统一用'+ev+'测评：键均当量</h2><p>越低越好；括号内是相对各自起点的变化。</p><table><tr><th>档位</th><th>老表退火</th><th>新表退火</th><th>盒子表退火</th><th>缺字（各组相同）</th></tr>';
 for(let i=0;i<5;i++){
  page+='<tr><td>'+results[0].分档[i].档位+'</td>';
  for(const train of ['老表','新表','盒子表']){const end=results.find(r=>r.训练字频===train&&r.阶段==='五万步'&&r.测评字频===ev).分档[i],start=results.find(r=>r.训练字频===train&&r.阶段==='起点'&&r.测评字频===ev).分档[i];const delta=end.键均当量-start.键均当量;page+='<td>'+end.键均当量.toFixed(6)+' ('+(delta>=0?'+':'')+delta.toFixed(6)+')</td>';}
  const r=results.find(r=>r.阶段==='五万步'&&r.测评字频===ev).分档[i];page+='<td>'+r.缺字+' / '+(100*r.缺失频率比例).toFixed(4)+'%</td></tr>';
 }page+='</table>';
}
page+='<p>盒子表1501–3000档缺2字、3001–6000档缺38字。主表只在覆盖字上归一化，未将缺字按零成本算。各测评表的分档字名单不同；同一张表的三列可以直接对照。</p><h2>普通单字表</h2>';
for(const train of ['老表','新表','盒子表'])page+='<p><a href="'+train+'_五万步单字表.txt">'+train+'退火 · 普通单字表</a></p>';
page+='<h2>完整指标</h2><table><tr><th>训练字频</th><th>阶段</th><th>测评字频</th><th>档位</th><th>键均当量</th><th>字均当量</th><th>键长</th></tr>';
for(const r of results)for(const s of r.分档)page+='<tr>'+[r.训练字频,r.阶段,r.测评字频,s.档位,s.键均当量.toFixed(6),s.字均当量.toFixed(6),s.加权键长.toFixed(6)].map(x=>'<td>'+x+'</td>').join('')+'</tr>';
page+='</table></html>';writeFileSync(P+'/三字频当量对照.html',page);console.log(JSON.stringify(results.filter(r=>r.阶段==='五万步').map(({明细,键盘热力,...r})=>r)));
