import {quickEvaluateHanzi,presetHanziFreq} from 'D:/nightingale/repos/schema-box/src/libs/evaluate/hanzi/hanzi';
import {readFileSync,writeFileSync} from 'node:fs';
const out=process.argv[2];
const txt=readFileSync('E:/夜莺2.0/releases/v1.0/01_正式码表/夜莺码v1.0单字版.txt','utf8');
const original=txt.trim().split(/\r?\n/).map((l,i)=>{const [w,c]=l.split(/\s+/);return [w,c,i]});
const results=[];
for(const sorted of [false,true])for(const cmLen of [4,5]){
 const items=sorted?[...original].sort((a,b)=>a[1]<b[1]?-1:a[1]>b[1]?1:0):original;
 const r=quickEvaluateHanzi({items,cmLen,selectKeys:" ;'456789"} as any);
 const sums=r.evaluate.map(s=>({range:`${s.start+1}–${s.end}`,missing:s.items.filter(x=>!('code' in x)).length,keyEq:s.items.reduce((n,x)=>n+('keyEq' in x?x.keyEq:0),0)/s.freq,ziEq:s.items.reduce((n,x)=>n+('ziEq' in x?x.ziEq:0),0)/s.freq,keyLength:s.items.reduce((n,x)=>n+('CL' in x?x.CL:0),0)/s.freq}));
 results.push({sorted,cmLen,sums,details:r.evaluate});
}
writeFileSync(out+'/原生结果.json',JSON.stringify(results,null,2));writeFileSync(out+'/默认字频.txt',presetHanziFreq);console.log(JSON.stringify(results.map(({details,...rest})=>rest)));
