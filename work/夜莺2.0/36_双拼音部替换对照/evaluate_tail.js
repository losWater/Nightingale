import {readFileSync,writeFileSync} from 'node:fs';
const P='E:/夜莺2.0/work/夜莺2.0/36_双拼音部替换对照',W=P+'/..';
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const old=read(W+'/27_删利根参数0晋级赛/frozen/字音基准.json'),nw=read(W+'/32_多来源字频重建/试验整字频率.json').字表;
const split=read(W+'/32_多来源字频重建/分音字频_试验.json');const mapping=read(P+'/全音节映射.json');
const counts=new Map();for(const r of old)counts.set(r.字,(counts.get(r.字)||0)+r.频率);
const oldRows=[...counts].sort((a,b)=>b[1]-a[1]||(a[0]<b[0]?-1:1));
const tables={'老表':oldRows.map(r=>r.join('\t')).join('\n'),'新表':nw.map(r=>[r.字,Math.round(r.每百万核心字预计次数*1e6)].join('\t')).join('\n'),'盒子表':presetHanziFreq};
const labels=['小鹤','自然码','拼音加加','智能ABC'],results=[],costs=[];
for(const label of labels)for(const phase of ['起点','五万步']){
 const path=P+'/'+label+'_'+phase+'单字表.txt';const items=readFileSync(path,'utf8').trim().split(/\r?\n/).map((l,i)=>{const [w,c]=l.split(/\s+/);return [w,c,i]});
 for(const [evalName,tsv] of Object.entries(tables)){
  const r=quickEvaluateHanzi({items,cmLen:4,selectKeys:" ;'456789"},tsv);
  const sums=r.evaluate.map(s=>{const covered=s.items.filter(x=>'code' in x),denom=covered.reduce((n,x)=>n+x.freq,0);return {档位:`${s.start+1}–${s.end}`,缺字:s.items.length-covered.length,缺失频率比例:1-denom/s.freq,键均当量:covered.reduce((n,x)=>n+x.keyEq,0)/denom,字均当量:covered.reduce((n,x)=>n+x.ziEq,0)/denom,加权键长:covered.reduce((n,x)=>n+x.CL,0)/denom};});
  results.push({双拼:label,阶段:phase,测评字频:evalName,分档:sums,明细:r.evaluate,键盘热力:r.usage});
  if(evalName==='盒子表'){
   const band=r.evaluate[1],arr=band.items.filter(x=>'code' in x),denom=arr.reduce((n,x)=>n+x.freq,0);let totals=[0,0,0,0];
   const details=arr.map(x=>{const c=x.code,end=x.selectKey||'',pairs=c.length+end.length-1;const a=[c.length>=2?calcEq(c.slice(0,2)):0,c.length>=3?calcEq(c.slice(1,3)):0,c.length>=4?calcEq(c.slice(2,4)):0,end?calcEq(c.slice(-1)+end):0];
    const eq=calcEq(c+end)/pairs; if(Math.abs(eq*x.freq-x.keyEq)>1e-5)throw Error('decomposition mismatch '+x.wd);
    a.forEach((v,i)=>totals[i]+=v/pairs*x.freq/denom);return {字:x.wd,码:c,选键:end,字频:x.freq,键均当量:eq,贡献:a.map(v=>v/pairs)};
   });
   if(Math.abs(totals.reduce((a,b)=>a+b)-sums[1].键均当量)>1e-10)throw Error('band sum mismatch');costs.push({双拼:label,阶段:phase,档位:'盒子固定301–500',音码内部:totals[0],音形衔接:totals[1],形码内部:totals[2],上屏选重键:totals[3],总键均当量:sums[1].键均当量,逐字:details});
  }
 }
}
const box200=parseFreqTsv(presetHanziFreq).slice(300,500),by=new Map();for(const r of split){if(!by.has(r.字))by.set(r.字,[]);by.get(r.字).push(r)}
const pure=labels.map(label=>{let cost=0,denom=0;const rows=box200.map(([c,f])=>{const opts=by.get(c);if(!opts)throw Error(c);const tot=opts.reduce((s,x)=>s+x.频率,0);const vs=opts.map(r=>({拼音:r.拼音,音码:mapping[label][r.拼音],比例:tot?r.频率/tot:1/opts.length}));const v=vs.reduce((s,x)=>s+calcEq(x.音码)*x.比例,0);cost+=v*f;denom+=f;return {字:c,字频:f,音部双键当量:v,读音:vs}});return {双拼:label,固定200字音部双键当量:cost/denom,说明:'盒子同200字同整字权重；读音比例按新表；假设每次输入完整两键音码，不计简码省略、形码或上屏键，不能当完整单字键均当量',逐字:rows}});
writeFileSync(P+'/双拼交叉测评.json',JSON.stringify(results,null,2));writeFileSync(P+'/固定200字成本分解.json',JSON.stringify(costs,null,2));writeFileSync(P+'/固定200字纯音部.json',JSON.stringify(pure,null,2));
let page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>26键双拼音部对照</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;margin:25px;color:#234}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:9px}th{background:#dce9f3}.note{background:#fff1c8;padding:16px}</style><h1>26键双拼音部替换 · 各五万步</h1><p>小鹤、自然码、拼音加加、智能ABC。训练字频统一用新表，参数0，起点形根布局相同，种子202609121701。只替换音部及与音部相联的词码和字词碰撞目标。</p><p class="note">为兼容ABC零声母，四组统一释放啊、而、哦的一简锁定，其余一简身份、复的二简长度保持。简词随声母迁移（ABC知道→ad）。本轮重新跑小鹤作公平基线，不直接与35号小鹤混比。ng/m/hng保留共同实验音码ng/mm/hg，别名不额外加入。单一种子仅用于探索，不能直接给双拼方案排总体优劣。</p><p>规则来源：<a href="https://github.com/rime/rime-double-pinyin">Rime官方双拼方案库</a>，具体提交和文件校验见<a href="来源记录.json">来源记录</a>。采用主变换，必要时取两键零声母别名；不是对所有输入法容错功能的模拟。</p>';
for(const ev of ['盒子表','新表','老表']){
 page+='<h2>统一用'+ev+'测评：键均当量</h2><p>越低越好；括号内是各自相对同布局起点的变化。</p><table><tr><th>档位</th>'+labels.map(l=>'<th>'+l+'</th>').join('')+'<th>缺字</th></tr>';
 for(let i=0;i<5;i++){
  page+='<tr><td>'+results[0].分档[i].档位+'</td>';
  for(const l of labels){const end=results.find(r=>r.双拼===l&&r.阶段==='五万步'&&r.测评字频===ev).分档[i],start=results.find(r=>r.双拼===l&&r.阶段==='起点'&&r.测评字频===ev).分档[i];const delta=end.键均当量-start.键均当量;page+='<td>'+end.键均当量.toFixed(6)+' ('+(delta>=0?'+':'')+delta.toFixed(6)+')</td>';}
  const r=results.find(r=>r.阶段==='五万步'&&r.测评字频===ev).分档[i];page+='<td>'+r.缺字+'</td></tr>';
 }page+='</table>';
}
page+='<p>盒子后两档分别缺2、38字，主表按覆盖频率归一化。码表取字的最短码，未强制对应具体读音，与盒子原生习惯一致。</p><h2>盒子固定200字 · 实际码表成本分解</h2><p>下列四部分按每字实际键对数归一化、再按盒子频率加权；相加等于该档键均当量。一简不含音码内部键对。</p><table><tr><th>方案</th><th>阶段</th><th>音码内部</th><th>音形衔接</th><th>形码内部</th><th>上屏／选重</th><th>总计</th></tr>';
for(const r of costs)page+='<tr>'+[r.双拼,r.阶段,...['音码内部','音形衔接','形码内部','上屏选重键','总键均当量'].map(k=>r[k].toFixed(6))].map(x=>'<td>'+x+'</td>').join('')+'</tr>';page+='</table><h2>固定200字 · 假设完整输入双拼音部</h2><p>此项只测两个拼音键形成的一个键对，不含简码和形部，不能与完整单字键均当量直接等同。</p><table><tr><th>方案</th><th>音部双键当量</th></tr>';
for(const r of pure)page+='<tr><td>'+r.双拼+'</td><td>'+r.固定200字音部双键当量.toFixed(6)+'</td></tr>';page+='</table><h2>普通单字表</h2>';
for(const l of labels)page+='<p><a href="'+l+'_五万步单字表.txt">'+l+' · 普通单字表</a></p>';page+='</html>';writeFileSync(P+'/双拼当量对照.html',page);console.log(JSON.stringify(results.filter(r=>r.阶段==='五万步'&&r.测评字频==='盒子表').map(({明细,键盘热力,...r})=>r)));
