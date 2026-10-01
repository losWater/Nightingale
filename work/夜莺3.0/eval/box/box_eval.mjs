// 形码盒子（schema-box）离线测评封装：node box_eval.mjs <码表.tsv> <输出.json>
// 码表每行「字\t码」，行序即候选序。参数同 2.0 第30号复测：cmLen=4，选重键 " ;'456789"。
import { readFileSync, writeFileSync } from 'node:fs';
const lib = readFileSync(new URL('./box_lib.mjs', import.meta.url), 'utf8');
const mod = await import('data:text/javascript;base64,' + Buffer.from(lib + '\nexport { quickEvaluateHanzi };').toString('base64'));
const [,, tablePath, outPath] = process.argv;
const items = readFileSync(tablePath, 'utf8').trim().split(/\r?\n/).map((l, i) => { const [w, c] = l.split('\t'); return [w, c, i]; });
const r = mod.quickEvaluateHanzi({ items, cmLen: 4, selectKeys: " ;'456789" });
const flags = ['dh', 'ms', 'ss', 'pd', 'lfd'];
const sections = r.evaluate.map(s => {
  let f = 0, pairs = 0, sel = 0, trible = 0, miss = 0, ziEq = 0, keyEq = 0, CL = 0;
  const cnt = Object.fromEntries(flags.map(k => [k, 0]));
  for (const x of s.items) {
    if (!('code' in x)) { miss++; continue; }
    f += x.freq; ziEq += x.ziEq; keyEq += x.keyEq; CL += x.CL;
    pairs += x.freq * Math.max(0, x.cdLen - 1);
    if (x.collision > 1) sel += x.freq;
    trible += x.freq * x.trible;
    for (const k of flags) cnt[k] += x.freq * x[k];
  }
  return { range: `${s.start + 1}-${s.end}`, freq: s.freq, pairs, missing: miss, keyEq: keyEq / s.freq, ziEq: ziEq / s.freq,
           keyLength: CL / s.freq, selectRate: sel / s.freq, tribleRate: trible / s.freq,
           ...Object.fromEntries(flags.map(k => [k + 'Rate', pairs ? cnt[k] / pairs : 0])) };
});
writeFileSync(outPath, JSON.stringify({ sections, usage: r.usage, baseFinLoadRate: r.baseFinLoadRate }, null, 1));
