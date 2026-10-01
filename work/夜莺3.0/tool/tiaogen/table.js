// 生成普通单字表（与 ~/Yozakura/build/make_plain_table.py 同规则）
function buildTable(D, M, k) {
  const N = M.N, K = M.K, slots = new Map();
  const push = (code, key, ch) => { let s = slots.get(code); if (!s) slots.set(code, s = []); s.push([key, ch]); };
  const m = M.evaluate(k, true), mask = m.mask;
  for (let i = 0; i < N; i++) {
    const r = D.readings[i], syl = r[2], ch = r[0];
    const full = syl + K[k[M.g1[i]]] + K[k[M.g2[i]]];
    const ot = D.oneTwo[i];
    const short = ot === 1 ? syl[0] : ot === 2 ? syl : (!mask[i] ? syl + K[k[M.g1[i]]] : '');
    push(full, [0, short ? 1 : 0, -r[5], i], ch);
    if (short) push(short, [0, 0, 0, i], ch);
  }
  const seen = new Set(); let ext = 0;
  for (const [ch, syl, a, b] of D.ext) {
    const code = syl + K[k[a]] + K[k[b]];
    if (seen.has(ch + code)) continue;
    seen.add(ch + code); push(code, [1, 0, 0, ext++], ch);
  }
  D.sym.forEach(([ch, code], j) => push(code, [2, 0, 0, j], ch));
  const cmp = (x, y) => { for (let t = 0; t < 4; t++) if (x[0][t] !== y[0][t]) return x[0][t] < y[0][t] ? -1 : 1; return x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0; };
  const codes = [...slots.keys()].sort((a, b) => a < b ? -1 : a > b ? 1 : 0);
  const out = [];
  for (const code of codes) {
    const placed = new Set();
    for (const [, ch] of slots.get(code).sort(cmp)) if (!placed.has(ch)) { placed.add(ch); out.push(ch + '\t' + code + '\n'); }
  }
  return out.join('');
}
if (typeof module !== 'undefined') module.exports = { buildTable };
