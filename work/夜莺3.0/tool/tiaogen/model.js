// 夜莺 3.0 调根台：全条件评分（与 ~/Yozakura/construct/model.py 同口径）
function makeModel(D) {
  const K = 'abcdefghijklmnopqrstuvwxyz', KI = {}; [...K].forEach((c, i) => KI[c] = i);
  const NG = D.groups.length, N = D.readings.length, SP = 26;
  const sylIdx = {}, sylNames = [];
  const sy = new Int32Array(N), s1 = new Int8Array(N), g1 = new Int16Array(N), g2 = new Int16Array(N), fr = new Float64Array(N), fl = new Int32Array(N);
  D.readings.forEach((r, i) => {
    if (!(r[2] in sylIdx)) { sylIdx[r[2]] = sylNames.length; sylNames.push(r[2]); }
    sy[i] = sylIdx[r[2]]; s1[i] = KI[r[2][1]]; g1[i] = r[3]; g2[i] = r[4]; fr[i] = r[5]; fl[i] = r[6];
  });
  const T1521 = 1, T3571 = 2, TOP = 4, REST = 8, FOUR = 16, SANI = 32, FIXED = 64, T300 = 128, T500 = 256, ONE = 512;
  const bySyl = sylNames.map(() => []);
  for (let i = 0; i < N; i++) bySyl[sy[i]].push(i);
  bySyl.forEach(a => a.sort((x, y) => fr[y] - fr[x] || x - y));
  let totFr = 0; for (let i = 0; i < N; i++) totFr += fr[i];
  const EQ = D.flag.eq, MS = D.flag.ms, PD = D.flag.pd;
  const WC = new Map();
  for (const [code, ws] of Object.entries(D.words)) {
    const s = sylIdx[code.slice(0, 2)]; if (s === undefined) continue;
    let a = 0, b = 0;
    for (const [, r] of ws) { if (r <= 10000) a++; if (r <= 30000) b++; }
    WC.set(s * 676 + KI[code[2]] * 26 + KI[code[3]], [a, b, ws.length, code]);
  }
  const B25 = D.groups.map(g => KI[g.b25]);
  const SCORE = D.score, LOW = D.low, CAL = D.cal, P = KI.p;

  function evaluate(k, detail) {
    const mask = new Uint8Array(N), winner = new Int32Array(N).fill(-1);
    for (const idx of bySyl) {
      const taken = new Map();
      for (const i of idx) {
        if (fl[i] & FIXED) continue;
        const p = k[g1[i]];
        if (taken.has(p)) { mask[i] = 1; winner[i] = taken.get(p); } else taken.set(p, i);
      }
    }
    let topSum = 0, topN = 0, restSum = 0, restW = 0, four = 0, san = 0, tt = 0, pp = 0, fms = 0, fpd = 0, feq = 0;
    for (let i = 0; i < N; i++) {
      if (fl[i] & FIXED) continue;
      const a = k[g1[i]], b = k[g2[i]], full = mask[i];
      const e23 = EQ[s1[i]][a], e34 = EQ[a][b];
      const c = full ? (e23 + e34) / 2 : e23;
      if (fl[i] & TOP) { topSum += c; topN++; }
      if (fl[i] & REST) { restSum += c * fr[i]; restW += fr[i]; }
      if ((fl[i] & FOUR) && full) four++;
      if ((fl[i] & SANI) && !full) san++;
      tt += fr[i] * (full ? 2 : 1); pp += fr[i] * ((a === P) + (full && b === P));
      const nx = full ? b : SP;
      fms += (MS[s1[i]][a] + MS[a][nx]) * fr[i]; fpd += (PD[s1[i]][a] + PD[a][nx]) * fr[i]; feq += (EQ[s1[i]][a] + EQ[a][nx]) * fr[i];
    }
    const top = topN ? topSum / topN : 0, rest = restW ? restSum / restW : top;
    const m = { 形码成本: 0.5 * top + 0.5 * rest, top, rest, 四码: four, 三简: san, p占比: pp / tt };
    const x = [fms / totFr, fpd / totFr, feq / totFr, 1];
    for (const t in CAL) m[t] = CAL[t].reduce((s, c, j) => s + c * x[j], 0);
    const cl = [0, 0, 0, 0], seen = new Map(); let d1 = 0, d3 = 0;
    const dups = [], clashes = [];
    for (let i = 0; i < N; i++) {
      if (!mask[i]) continue;   // 有一二三简的读音：全码位让位，不计重码、不计字词冲突（实际选重口径）
      const code = sy[i] * 676 + k[g1[i]] * 26 + k[g2[i]], sig = g1[i] * 1000 + g2[i];
      let s = seen.get(code);
      if (s) {
        let other = -1;
        for (const [sg, j] of s) if (sg !== sig) { other = j; break; }
        if (other >= 0) {
          if (fl[i] & T1521) d1++; if (fl[i] & T3571) d3++;
          if (detail && (fl[i] & T3571)) dups.push([i, other]);
        }
        if (!s.has(sig)) s.set(sig, i);
      } else seen.set(code, new Map([[sig, i]]));
      const w = WC.get(code);
      if (w) {
        if (fl[i] & T1521) { cl[0] += w[0] > 0; cl[1] += w[1] > 0; }
        if (fl[i] & T3571) cl[2] += w[0] > 0;
        cl[3] += w[2];
        if (detail) clashes.push([i, w[3]]);
      }
    }
    m.撞码 = cl; m['1521重'] = d1; m['3571重'] = d3;
    m.虫鸟 = +(k[D.mutex[0]] === k[D.mutex[1]]);
    let mv = 0; for (let g = 0; g < NG; g++) mv += k[g] !== B25[g]; m.换键根组 = mv;
    const met = { 形码成本: m.形码成本, p占比: m.p占比, '撞码②': cl[1], '撞码③': cl[2], 三简: san, 换键根组: mv,
      '小指干扰%': m['小指干扰%'], '同指大跨排%': m['同指大跨排%'], 键均当量: m.键均当量, 字词冲突6万: cl[3] };
    let S = 0; m.parts = {};
    for (const [name, [wt, zero, full]] of Object.entries(SCORE)) {
      const v = Math.max(LOW[name] ?? -0.5, Math.min(1.2, (met[name] - zero) / (full - zero)));
      m.parts[name] = 100 * v; S += wt * v;
    }
    m.S = S;
    // 分档当量：键均（按实际打法、按字频加权）；2→3、3→4（全码上的键对，只计用形码的读音，档内不加权平均）
    m.tiers = {};
    for (const [name, bit] of [['前300', T300], ['前500', T500], ['前1500', T1521]]) {
      let num = 0, den = 0, a23 = 0, a34 = 0, n = 0;
      for (let i = 0; i < N; i++) {
        if (!(fl[i] & bit)) continue;
        const s0 = KI[sylNames[sy[i]][0]], a = k[g1[i]], b = k[g2[i]];
        let keys;
        if (fl[i] & ONE) keys = [s0, SP];
        else if (fl[i] & FIXED) keys = [s0, s1[i], SP];
        else { keys = mask[i] ? [s0, s1[i], a, b] : [s0, s1[i], a, SP]; a23 += EQ[s1[i]][a]; a34 += EQ[a][b]; n++; }
        let e = 0; for (let j = 0; j + 1 < keys.length; j++) e += EQ[keys[j]][keys[j + 1]];
        num += fr[i] * e; den += fr[i] * (keys.length - 1);
      }
      m.tiers[name] = { 键均当量: num / den, '2→3': a23 / n, '3→4': a34 / n, n };
    }
    m.gates = { '字词撞①=0': cl[0] === 0, '字词撞③≤5': cl[2] <= 5, '前1521实际选重=0': d1 === 0, '前3571实际选重≤9': d3 <= 9,
      '前1500四码≤125': four <= 125, '虫鸟不同键': !m.虫鸟 };
    m.pen = d1 + Math.max(0, d3 - 9) + cl[0] + Math.max(0, cl[2] - 5) + Math.max(0, four - 125) + m.虫鸟;
    m.F = 1000 * m.pen - S;
    if (detail) {
      m.dups = dups; m.clashes = clashes;
      m.losers = [];
      for (let i = 0; i < N; i++) if (mask[i] && (fl[i] & T3571)) m.losers.push([i, winner[i]]);
      m.mask = mask; m.winner = winner;
      const use = new Float64Array(26); let ut = 0;
      for (let i = 0; i < N; i++) {
        if (fl[i] & FIXED) continue;
        use[k[g1[i]]] += fr[i]; ut += fr[i];
        if (mask[i]) { use[k[g2[i]]] += fr[i]; ut += fr[i]; }
      }
      m.keyUse = Array.from(use, u => u / ut);
    }
    return m;
  }
  return { evaluate, K, KI, NG, N, sy, sylNames, g1, g2, fr, fl, B25, WC, flags: { T1521, T3571, TOP, REST, FOUR, SANI, FIXED } };
}
if (typeof module !== 'undefined') module.exports = { makeModel };
