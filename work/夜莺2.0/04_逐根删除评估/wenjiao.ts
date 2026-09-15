import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'fs';
import {createHash} from 'crypto';
import {获取原始字库,读取配置,决策图,计算全部合法元素与元素映射,获取自定义分析与元素映射} from '../../../repos/webchai/packages/hanzi-chai/src/index.js';
import {标准化自定义,构建强类型决策与决策空间,构建强类型自定义分析} from '../../../repos/webchai/packages/hanzi-chai/src/utils.js';
import {合并分类器} from '../../../repos/webchai/packages/hanzi-chai/src/classifier.js';
const dir=import.meta.dir;
const input=JSON.parse(readFileSync(dir+'/input.json','utf8'));
const cfg=读取配置(dir+'/active.yaml');
const fingerprint=createHash('sha256').update(readFileSync(dir+'/input.json')).update(readFileSync(dir+'/active.yaml')).update(readFileSync(dir+'/source-fingerprints.json')).update(readFileSync(import.meta.path)).digest('hex');
const raw=获取原始字库(Object.values(cfg.data?.repertoire??{}) as any);
const determined=raw.确定(标准化自定义(cfg.data?.glyph_customization??{}),cfg.data?.transformers??[],(cfg.data?.glyph_sources??['G']) as any);
if(!determined.ok)throw determined.error;
const repertoire=determined.value;
const {自定义元素映射}=获取自定义分析与元素映射({},raw);
const {名称映射}=计算全部合法元素与元素映射([...repertoire].map(({字符})=>字符),合并分类器(cfg.analysis?.classifier),new Map(),自定义元素映射);
const norm=(n:string)=>input.norm[n]??n;
function analyze(mapping:any,custom:any,requested:string[]){
  const {决策,决策空间}=构建强类型决策与决策空间(mapping,{},名称映射);
  const lin=new 决策图(决策).线性化();if(!lin.ok)throw lin.error;
  const {自定义分析映射,动态自定义分析映射}=构建强类型自定义分析(repertoire,raw,名称映射,custom,{});
  const chars=new Set<any>();const names=new Map<string,string>();
  for(const s of requested){const c=raw.校验(s)?.character;if(!c)throw new Error('unresolved '+s);chars.add(c);names.set(c.获取名称(),s)}
  const result=repertoire.分析({决策,决策空间,线性化决策:lin.value,自定义分析映射,动态自定义分析映射,分析配置:cfg.analysis??{}} as any,chars);
  if(!result.ok)throw result.error;
  const rows:Record<string,string[]>={};
  for(const [c,as] of (result.value as any).分析结果){const key=names.get(c.获取名称());if(key===undefined)continue;
    rows[key]=(as[0]?.字根序列??[]).map((r:any)=>norm(r.字符?.获取名称?.()??r.获取名称?.()??String(r)));
    if(!rows[key].length)throw new Error('empty split '+key);
  }
  if(Object.keys(rows).length!==requested.length)throw new Error('incomplete analysis');
  return rows;
}
const sel=JSON.parse(readFileSync(dir+'/wenjiao-selected.json','utf8'));const out:any={};for(const ids of [[0,1,2],[0,1,3],[0,1,2,3]]){const mapping={...cfg.form.mapping};const rep=new Map<string,string[]>();for(const i of ids){const t=sel[i];for(const id of t.ids)delete mapping[id];rep.set(t.id,t.replacement)}const custom=Object.fromEntries(Object.entries(cfg.analysis?.customize??{}).map(([k,v])=>[k,(v as string[]).flatMap(x=>rep.get(norm(x))??[x])]));const rows=analyze(mapping,custom,Object.keys(input.expected));for(const [c,s]of Object.entries(rows))if(s.some(t=>rep.has(t)))throw new Error('残留 '+c);out[ids.join(',')]=rows;}writeFileSync(dir+'/wenjiao-raw.json',JSON.stringify(out));console.log('三组重拆完成');