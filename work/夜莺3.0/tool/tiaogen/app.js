const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let D, M, k, cur, prevM = null, refM = null, sel = null, heat = 'none', tab = 'group', startName = 'b:喜好第一名', refName = 'b:NB46';
let hist = [], fut = [], log = [], tabu = [], moveCache = null, busy = false, clashSort = 'char', clashAll = false;
const ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
const CELLS = [
  ['形码成本', m => m.形码成本, v => v.toFixed(4), -1], ['三简', m => m.三简, v => v, 1], ['前1500四码', m => m.四码, v => v, -1],
  ['p 占比', m => m.p占比 * 100, v => v.toFixed(2) + '%', -1], ['撞②', m => m.撞码[1], v => v, -1], ['撞③', m => m.撞码[2], v => v, -1],
  ['6 万词冲突', m => m.撞码[3], v => v, -1], ['前1521选重', m => m['1521重'], v => v, -1], ['前3571选重', m => m['3571重'], v => v, -1],
  ['小指干扰≈', m => m['小指干扰%'], v => v.toFixed(2) + '%', -1], ['同指大跨排≈', m => m['同指大跨排%'], v => v.toFixed(2) + '%', -1],
  ['键均当量≈', m => m.键均当量, v => v.toFixed(4), -1], ['换键（对 2.5）', m => m.换键根组, v => v, -1]];
const gname = g => D.groups[g].roots[0];
const groupLink = g => `<span class="g" data-g="${g}" title="${esc(D.groups[g].roots.join(' '))}">${esc(gname(g))}</span>`;
const zi = i => `<span class="zi">${esc(D.readings[i][0])}</span><small>${esc(D.readings[i][1])}</small>`;
const codeOf = i => D.readings[i][2] + M.K[k[M.g1[i]]] + M.K[k[M.g2[i]]];

// 本地版把数据嵌在页面里（window.TIAOGEN_DATA）；网页版从 data.json 取
(window.TIAOGEN_DATA ? Promise.resolve(window.TIAOGEN_DATA) : fetch('data.json').then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })).then(init)
  .catch(e => { $('#loading').textContent = '数据载入失败（' + e.message + '），请刷新页面重试。'; });

function layoutArr(name) { return Int8Array.from(D.groups.map(g => M.KI[D.layouts[name][g.id]])); }
// 下拉框取值：b:内置方案名，s:已保存布局 id
function layoutFor(v) {
  if (v.startsWith('s:')) { const s = saved.find(x => x.id === v.slice(2)); return s ? Int8Array.from(D.groups.map(g => M.KI[s.layout[g.id]])) : null; }
  const n = v.startsWith('b:') ? v.slice(2) : v;
  return D.layouts[n] ? layoutArr(n) : null;
}
function labelFor(v) {
  if (v.startsWith('s:')) { const s = saved.find(x => x.id === v.slice(2)); return s ? s.name : '（已删除的布局）'; }
  return v.startsWith('b:') ? v.slice(2) : v;
}
function fillSelects() {
  if (!D || !M) return;
  if (refName.startsWith('s:') && cur) { const l = layoutFor(refName); if (l) { refM = M.evaluate(l, false); renderMetrics(); } }
  const opts = '<optgroup label="内置方案">' + Object.keys(D.layouts).map(n => `<option value="b:${esc(n)}">${esc(n)}</option>`).join('') + '</optgroup>'
    + (saved.length ? '<optgroup label="已保存">' + saved.map(s => `<option value="s:${esc(s.id)}">${esc(s.name)}</option>`).join('') + '</optgroup>' : '');
  for (const [id, v] of [['#start', startName], ['#ref', refName]]) {
    $(id).innerHTML = opts;
    if ([...$(id).options].some(o => o.value === v)) $(id).value = v;
  }
}

function init(d) {
  D = d; M = makeModel(D);

  let st = null; try { st = JSON.parse(localStorage.getItem('tiaogen') || 'null'); } catch (e) { }
  if (st && st.k && st.k.length === M.NG) {
    k = Int8Array.from(st.k); log = st.log || [];
    startName = st.start ? (/^[bs]:/.test(st.start) ? st.start : 'b:' + st.start) : startName;
    if (st.ref) refName = st.ref;
  } else k = layoutFor(startName);
  fillSelects();
  refM = M.evaluate(layoutFor(refName) || layoutArr('NB46'), false);
  bind(); refresh();
}

function save() { try { localStorage.setItem('tiaogen', JSON.stringify({ k: Array.from(k), start: startName, ref: refName, log: log.slice(0, 200) })); } catch (e) { } }

function refresh() {
  cur = M.evaluate(k, true); moveCache = null; involve();
  renderMetrics(); renderKbd(); renderPane(); save();
  $('#undo').disabled = !hist.length; $('#redo').disabled = !fut.length;
}

let lastDiff = '';
function apply(changes, note) {
  hist.push(Int8Array.from(k)); fut = []; prevM = cur;
  for (const [g, kk] of changes) k[g] = kk;
  refresh();
  lastDiff = diffNote(prevM, cur);
  if (note) log.unshift(note + (lastDiff ? '<br><small>' + lastDiff + '</small>' : ''));
  renderPane(); save();
}

// 这一步改了什么：三简得失（前1521）、重码、字词冲突的增减
function diffNote(p, c) {
  if (!p || !p.losers || !c.losers) return '';
  const T = M.flags.T1521, parts = [];
  const lp = new Map(p.losers.filter(([i]) => M.fl[i] & T).map(x => [x[0], x[1]]));
  const lc = new Map(c.losers.filter(([i]) => M.fl[i] & T).map(x => [x[0], x[1]]));
  const lost = [...lc].filter(([i]) => !lp.has(i)), got = [...lp.keys()].filter(i => !lc.has(i));
  if (lost.length) parts.push('<b>失去三简</b>：' + lost.slice(0, 8).map(([i, j]) => `${zi(i)}（${D.readings[i][2]}${M.K[k[M.g1[i]]]} 被 ${j >= 0 ? zi(j) : '?'} 占）`).join('、') + (lost.length > 8 ? ` 等 ${lost.length} 个` : ''));
  if (got.length) parts.push('<b>拿到三简</b>：' + got.slice(0, 8).map(zi).join('、') + (got.length > 8 ? ` 等 ${got.length} 个` : ''));
  const dk = x => x[0] + ':' + x[1];
  const dp = new Set(p.dups.map(dk)), dc = new Set(c.dups.map(dk));
  const dNew = c.dups.filter(x => !dp.has(dk(x))), dGone = p.dups.filter(x => !dc.has(dk(x)));
  if (dNew.length) parts.push('<b>新重码</b>：' + dNew.slice(0, 6).map(([i, j]) => `${zi(i)}=${zi(j)}`).join('、') + (dNew.length > 6 ? ` 等 ${dNew.length} 处` : ''));
  if (dGone.length) parts.push('<b>消除重码</b>：' + dGone.slice(0, 6).map(([i, j]) => `${zi(i)}=${zi(j)}`).join('、') + (dGone.length > 6 ? ` 等 ${dGone.length} 处` : ''));
  const ck = x => x[0] + ':' + x[1];
  const cp = new Set(p.clashes.map(ck)), cc = new Set(c.clashes.map(ck));
  const cNew = c.clashes.filter(x => !cp.has(ck(x))).sort((a, b) => a[0] - b[0]), cGone = p.clashes.filter(x => !cc.has(ck(x))).sort((a, b) => a[0] - b[0]);
  const cs = x => `${zi(x[0])}/${esc(D.words[x[1]].slice().sort((u, v) => u[1] - v[1])[0][0])}`;
  if (cNew.length) parts.push(`<b>新字词冲突</b> ${cNew.length} 处：` + cNew.slice(0, 6).map(cs).join('、'));
  if (cGone.length) parts.push(`<b>消除字词冲突</b> ${cGone.length} 处：` + cGone.slice(0, 6).map(cs).join('、'));
  return parts.length ? parts.join('<br>') : '这一步没有改变三简、重码和字词冲突。';
}

// 每组牵涉的问题数
let INV = {};
function involve() {
  const add = (o, g, v = 1) => { o[g] = (o[g] || 0) + v; };
  const dup = {}, clash = {}, lose = {};
  for (const [i, j] of cur.dups) for (const g of new Set([M.g1[i], M.g2[i], M.g1[j], M.g2[j]])) add(dup, g);
  for (const [i, code] of cur.clashes) { const n = D.words[code].length; add(clash, M.g1[i], n); if (M.g2[i] !== M.g1[i]) add(clash, M.g2[i], n); }
  for (const [i, j] of cur.losers) { if (M.fl[i] & M.flags.T1521) { add(lose, M.g1[i]); if (j >= 0 && M.g1[j] !== M.g1[i]) add(lose, M.g1[j]); } }
  INV = { dup, clash, lose };
}

function delta(v, base, dir, fmt) {
  if (base === undefined || base === null) return '';
  const d = v - base;
  if (Math.abs(d) < 1e-9) return `<span class="d zero">±0</span>`;
  const good = d * dir > 0;
  const s = (d > 0 ? '+' : '') + (Number.isInteger(d) ? d : Math.abs(d) < 0.01 ? d.toFixed(4) : d.toFixed(Math.abs(d) < 1 ? 3 : 1));
  return `<span class="d ${good ? 'up' : 'down'}">${s}</span>`;
}

function renderMetrics() {
  const m = cur, r = refM, p = prevM;
  const gates = Object.entries(m.gates).map(([n, ok]) => `<span class="gate ${ok ? '' : 'fail'}">${ok ? '✓' : '✗'} ${esc(n)}</span>`).join('');
  const cells = CELLS.map(([n, f, fmt, dir]) => `<div class="cell"><div class="n">${n}</div><div class="v">${fmt(f(m))}</div>`
    + `<div>${r ? `<small style="color:var(--muted)">对照</small>${delta(f(m), f(r), dir)}` : ''} ${p ? `<small style="color:var(--muted)">上步</small>${delta(f(m), f(p), dir)}` : ''}</div></div>`).join('');
  $('#metrics').innerHTML = `<div class="mrow"><div class="total"><span>总分</span><b>${m.S.toFixed(1)}</b>`
    + `${delta(m.S, r && r.S, 1)}<small style="color:var(--muted)">对照 ${esc(labelFor(refName))}</small>${p ? delta(m.S, p.S, 1) + '<small style="color:var(--muted)">上步</small>' : ''}</div>`
    + `<div class="gates">${gates}</div></div><div class="cells">${cells}</div>` + tierTable(m, r, p);
}

function tierTable(m, r, p) {
  const cols = [['键均当量', '按实际打法（一二三简接空格），档内按字频加权'], ['2→3', '音码末键→首根键，只计用形码的读音，档内不加权平均'], ['3→4', '首根键→末根键（全码），只计用形码的读音，档内不加权平均']];
  const cell = (t, c) => {
    const v = m.tiers[t][c];
    return `<td class="num">${v.toFixed(4)}${r ? delta(v, r.tiers[t][c], -1) : ''}${p ? ' <small style="color:var(--muted)">上步</small>' + delta(v, p.tiers[t][c], -1) : ''}</td>`;
  };
  return `<div class="tiers"><table><thead><tr><th>分档当量</th>${cols.map(([c, tip]) => `<th title="${tip}">${c}</th>`).join('')}<th>用形码的读音</th></tr></thead><tbody>`
    + Object.keys(m.tiers).map(t => `<tr><td>${t}</td>${cols.map(([c]) => cell(t, c)).join('')}<td class="num">${m.tiers[t].n}</td></tr>`).join('')
    + `</tbody></table><small style="color:var(--muted)">键均当量按实际打法、按字频加权；2→3 和 3→4 只计用到形码的读音（不含一二简），按全码键对、档内不加权平均。前 1500 档即 1521 个读音。</small></div>`;
}

function renderKbd() {
  const byKey = Array.from({ length: 26 }, () => []);
  for (let g = 0; g < M.NG; g++) byKey[k[g]].push(g);
  const keyHeat = new Array(26).fill(0);
  if (heat === 'use') cur.keyUse.forEach((u, i) => keyHeat[i] = u);
  else if (heat !== 'none') { const o = INV[heat]; for (const g in o) keyHeat[k[g]] += o[g]; }
  const mx = Math.max(...keyHeat, 1e-9);
  const ginv = heat === 'none' || heat === 'use' ? {} : INV[heat];
  $('#kbd').innerHTML = ROWS.map((row, ri) => `<div class="row r${ri + 1}">` + [...row].map(ch => {
    const ki = M.KI[ch];
    const chips = byKey[ki].sort((a, b) => (ginv[b] || 0) - (ginv[a] || 0) || a - b).map(g => {
      const n = ginv[g] || 0, moved = k[g] !== M.B25[g];
      return `<span class="chip${moved ? ' moved' : ''}${n ? ' hot' : ''}${sel === g ? ' sel' : ''}" draggable="true" data-g="${g}" title="${esc(D.groups[g].roots.join(' '))}${moved ? '（2.5 在 ' + M.K[M.B25[g]].toUpperCase() + '）' : ''}">${esc(gname(g))}${n ? `<span class="x">${n}</span>` : ''}</span>`;
    }).join('');
    return `<div class="key" data-k="${ki}"><div class="heat" style="opacity:${(0.28 * keyHeat[ki] / mx).toFixed(3)}"></div><div class="kh"><b>${ch}</b><small>${(100 * cur.keyUse[ki]).toFixed(1)}%</small></div><div class="chips">${chips}</div></div>`;
  }).join('') + (ri ? '<div></div>' : '') + '</div>').join('');
}

// 三简得失：这组做首根而没拿到三简的字；这组的字占掉别人三简的字（一二简字不参与）
function sanPanel(g) {
  const F = M.flags, lost = [], took = [];
  for (let i = 0; i < M.N; i++) {
    if (!cur.mask[i]) continue;
    const j = cur.winner[i];
    if (M.g1[i] === g) lost.push([i, j]);
    else if (j >= 0 && M.g1[j] === g) took.push([i, j]);
  }
  const tier = i => (M.fl[i] & F.T1521) ? ' <span class="gate fail">1521</span>' : (M.fl[i] & F.T3571) ? ' <span class="gate">3571</span>' : '';
  const tbl = (rows, head, f) => rows.length ? `<table><thead><tr>${head}</tr></thead><tbody>` + rows.slice(0, 100).map(f).join('') + '</tbody></table>'
    + (rows.length > 100 ? `<p>只列前 100 个，共 ${rows.length} 个。</p>` : '') : '<p class="empty">没有。</p>';
  const n1 = rows => rows.filter(([i]) => M.fl[i] & F.T1521).length;
  return `<h3>这组做首根、没拿到三简的字：${lost.length} 个（前1521 ${n1(lost)} 个）</h3>`
    + tbl(lost, '<th>字</th><th>三简位</th><th>被谁占</th><th>占位字的首根组</th>', ([i, j]) =>
      `<tr><td>${zi(i)}${tier(i)}</td><td class="num">${D.readings[i][2]}${M.K[k[g]]}</td><td>${j >= 0 ? zi(j) : '—'}</td><td>${j >= 0 ? groupLink(M.g1[j]) : ''}</td></tr>`)
    + `<h3>这组的字占了别人的三简：${took.length} 个（前1521 ${n1(took)} 个）</h3>`
    + tbl(took, '<th>丢三简的字</th><th>三简位</th><th>被这组的哪个字占</th><th>丢的字的首根组</th>', ([i, j]) =>
      `<tr><td>${zi(i)}${tier(i)}</td><td class="num">${D.readings[i][2]}${M.K[k[M.g1[i]]]}</td><td>${zi(j)}</td><td>${groupLink(M.g1[i])}</td></tr>`);
}

function moveTable(g) {
  if (moveCache && moveCache.g === g) return moveCache.rows;
  const rows = [];
  const old = k[g];
  for (let kk = 0; kk < 26; kk++) {
    k[g] = kk; const m = M.evaluate(k, false);
    rows.push({ kk, m });
  }
  k[g] = old;
  rows.sort((a, b) => a.m.F - b.m.F);
  moveCache = { g, rows };
  return rows;
}

function renderPane() {
  const P = $('#pane');
  $('#lastdiff').innerHTML = lastDiff ? '<b>上一步改了什么</b><br>' + lastDiff : '';
  $('#lastdiff').hidden = !lastDiff;
  document.querySelectorAll('.tabs button').forEach(b => b.setAttribute('aria-pressed', b.dataset.tab === tab));
  if (tab === 'group') {
    if (sel === null) { P.innerHTML = '<p class="empty">点键盘上的根组，查看它在 26 个键上各自的得失，点一行即可挪过去。</p>'; return; }
    const g = sel, gid = D.groups[g].id, pref = D.prefs[gid] || [];
    const rows = moveTable(g);
    const curRow = rows.find(r => r.kk === k[g]).m;
    const rk = pref.indexOf(M.K[k[g]]);
    P.innerHTML = `<h3>${esc(D.groups[g].roots.join(' '))}</h3>
      <p>当前 <b>${M.K[k[g]].toUpperCase()}</b> · 2.5 在 ${M.K[M.B25[g]].toUpperCase()} · 算法喜好：${pref.slice(0, 5).map((x, i) => (x === M.K[k[g]] ? '<b>' : '') + (i + 1) + '.' + x.toUpperCase() + (x === M.K[k[g]] ? '</b>' : '')).join(' ')}${rk >= 5 ? `（当前键排第 ${rk + 1}）` : ''}</p>
      <p>牵涉：重码 ${INV.dup[g] || 0} · 字词冲突 ${INV.clash[g] || 0} 条 · 前1521没拿到三简 ${INV.lose[g] || 0}</p>
      ${sanPanel(g)}
      <table><thead><tr><th>挪到</th><th>总分变化</th><th>门禁</th><th>6万冲突</th><th>三简</th><th>形码成本</th></tr></thead><tbody>`
      + rows.map(({ kk, m }) => `<tr class="click${kk === k[g] ? ' cur' : ''}" data-move="${kk}"><td><b>${M.K[kk].toUpperCase()}</b>${kk === M.B25[g] ? ' <small>2.5</small>' : ''}</td>`
        + `<td class="num">${kk === k[g] ? '当前' : (m.S - curRow.S >= 0 ? '+' : '') + (m.S - curRow.S).toFixed(2)}</td>`
        + `<td>${m.pen ? `<span class="gate fail">✗${m.pen}</span>` : '✓'}</td>`
        + `<td class="num">${m.撞码[3] - curRow.撞码[3] >= 0 ? '+' : ''}${m.撞码[3] - curRow.撞码[3]}</td>`
        + `<td class="num">${m.三简 - curRow.三简 >= 0 ? '+' : ''}${m.三简 - curRow.三简}</td>`
        + `<td class="num">${(m.形码成本 - curRow.形码成本).toFixed(4)}</td></tr>`).join('') + '</tbody></table>';
  } else if (tab === 'dup') {
    const items = cur.dups.slice().sort((a, b) => a[0] - b[0]);
    P.innerHTML = `<h3>实际选重（前 3571 档）：${items.length} 处</h3><p>只看必须打全码的字：同一全码上，前面已有首末根组不全相同、也必须打全码的字，就要选重。有一二三简的字在全码位让位，不计。前 1521 档必须为 0，前 3571 档不超过 9。</p>`
      + (items.length ? `<table><thead><tr><th>字</th><th>与谁重</th><th>全码</th><th>根组</th></tr></thead><tbody>` + items.map(([i, j]) =>
        `<tr><td>${zi(i)}${M.fl[i] & M.flags.T1521 ? ' <span class="gate fail">1521</span>' : ''}</td><td>${zi(j)}</td><td class="num">${codeOf(i)}</td><td>${groupLink(M.g1[i])}+${groupLink(M.g2[i])} / ${groupLink(M.g1[j])}+${groupLink(M.g2[j])}</td></tr>`).join('') + '</tbody></table>' : '<p class="empty">没有重码。</p>');
  } else if (tab === 'clash') {
    const pairs = {};
    for (const [i, code] of cur.clashes) { const key = M.g1[i] + ',' + M.g2[i]; (pairs[key] = pairs[key] || [0, M.g1[i], M.g2[i]])[0] += D.words[code].length; }
    const top = Object.values(pairs).sort((a, b) => b[0] - a[0]).slice(0, 15);
    const info = cur.clashes.map(([i, code]) => {
      const ws = D.words[code]; const r1 = ws.some(w => w[1] <= 10000), r3 = ws.some(w => w[1] <= 30000);
      const t1 = M.fl[i] & M.flags.T1521, t3 = M.fl[i] & M.flags.T3571;
      const tag = (t1 && r1 ? '①' : '') + (t1 && r3 ? '②' : '') + (t3 && r1 ? '③' : '');
      const sev = t1 && r1 ? 0 : t3 && r1 ? 1 : t1 && r3 ? 2 : 3;
      const ws2 = ws.slice().sort((x, y) => x[1] - y[1]);
      return { i, code, ws: ws2, tag, sev, wr: ws2[0][1] };
    });
    const cmp = { char: (a, b) => a.i - b.i, word: (a, b) => a.wr - b.wr || a.i - b.i, sev: (a, b) => a.sev - b.sev || a.i - b.i }[clashSort];
    info.sort(cmp);
    const shown = clashAll ? info : info.slice(0, 300);
    const opt = (v, t) => `<button data-csort="${v}" aria-pressed="${clashSort === v}">${t}</button>`;
    P.innerHTML = `<h3>字词冲突：${cur.撞码[3]} 条（6 万词）</h3><p>只算必须打全码的读音。① 前1521×前1万词，② 前1521×前3万，③ 前3571×前1万。</p>
      <h3>贡献最多的根组对</h3><table><thead><tr><th>首根组</th><th>末根组</th><th>冲突条数</th></tr></thead><tbody>`
      + top.map(([n, a, b]) => `<tr><td>${groupLink(a)}</td><td>${groupLink(b)}</td><td class="num">${n}</td></tr>`).join('') + `</tbody></table>
      <h3>明细（${info.length} 个字音）</h3><div class="tabs" role="group" aria-label="排序">${opt('char', '按字频（默认）')}${opt('word', '按词频')}${opt('sev', '按严重程度')}`
      + `<button data-call="1">${clashAll ? '只看前 300' : '显示全部'}</button></div>
      <table><thead><tr><th>字</th><th>全码</th><th>撞的词（词频序）</th><th>根组</th></tr></thead><tbody>`
      + shown.map(x => `<tr><td>${zi(x.i)}<small style="color:var(--muted)"> #${x.i + 1}</small>${x.tag ? ` <span class="gate fail">${x.tag}</span>` : ''}</td><td class="num">${x.code}</td>`
        + `<td>${x.ws.slice(0, 3).map(w => esc(w[0]) + '<small>' + w[1] + '</small>').join(' ')}${x.ws.length > 3 ? ` …共${x.ws.length}` : ''}</td><td>${groupLink(M.g1[x.i])}+${groupLink(M.g2[x.i])}</td></tr>`).join('')
      + '</tbody></table>' + (!clashAll && info.length > 300 ? `<p>还有 ${info.length - 300} 条，点“显示全部”查看。</p>` : '');
  } else if (tab === 'lose') {
    const items = cur.losers.filter(([i]) => M.fl[i] & M.flags.T1521).sort((a, b) => a[0] - b[0]);
    P.innerHTML = `<h3>前 1521 档没拿到三简：${items.length} 个（四码门禁 ≤ 125 只计前 1500）</h3><p>同音、首根同键时只有更常用的字能拿三简。</p>`
      + `<table><thead><tr><th>字</th><th>三简被谁占</th><th>首根组</th><th>键</th></tr></thead><tbody>` + items.map(([i, j]) =>
        `<tr><td>${zi(i)}</td><td>${j >= 0 ? zi(j) + ' ' + groupLink(M.g1[j]) : '—'}</td><td>${groupLink(M.g1[i])}</td><td class="num">${D.readings[i][2]}${M.K[k[M.g1[i]]]}</td></tr>`).join('') + '</tbody></table>';
  } else if (tab === 'saved') {
    P.innerHTML = `<h3>已保存的布局（${saved.length}）</h3><p>${db ? '保存在云端，换设备打开也在；Claude 也能直接读取做正式评测。' : '只存在这个浏览器里（清除浏览器数据会丢失）。重要的布局请“导出全部”存成文件。'}</p>`
      + `<p><button data-export>导出全部</button> <button data-import>导入…</button><input type="file" id="importfile" accept=".json,application/json" hidden></p>`
      + (saved.length ? `<table><thead><tr><th>名称</th><th>总分</th><th>门禁</th><th>形码</th><th>6万</th><th>换键</th><th></th></tr></thead><tbody>` + saved.map(s =>
        `<tr><td>${esc(s.name)}<br><small style="color:var(--muted)">${esc((s.savedAt || '').slice(0, 16).replace('T', ' '))}</small></td><td class="num">${(+s.S).toFixed(1)}</td>`
        + `<td>${s.pen ? '<span class="gate fail">✗</span>' : '✓'}</td><td class="num">${(+s.形码成本).toFixed(4)}</td><td class="num">${s.冲突6万}</td><td class="num">${s.换键}</td>`
        + `<td><button data-load="${esc(s.id)}">载入</button> <button data-del="${esc(s.id)}">删除</button></td></tr>`).join('') + '</tbody></table>'
        : '<p class="empty">还没有保存过布局。在顶部起个名字，点“保存当前布局”。</p>');
  } else {
    P.innerHTML = '<h3>修改记录</h3>' + (log.length ? '<div class="log">' + log.map(x => `<div>${x}</div>`).join('') + '</div>' : '<p class="empty">还没有修改。</p>');
  }
}

function problemWeights() {
  const w = {};
  const add = (g, v) => { w[g] = (w[g] || 0) + v; };
  for (const [i, j] of cur.dups) {
    const v = (M.fl[i] & M.flags.T1521) ? 1000 : cur['3571重'] > 9 ? 300 : 5;
    for (const g of new Set([M.g1[i], M.g2[i], M.g1[j], M.g2[j]])) add(g, v);
  }
  for (const [i, code] of cur.clashes) {
    const ws = D.words[code], r1 = ws.some(x => x[1] <= 10000), r3 = ws.some(x => x[1] <= 30000);
    const t1 = M.fl[i] & M.flags.T1521, t3 = M.fl[i] & M.flags.T3571;
    const v = (t1 && r1 ? 1000 : 0) + (t3 && r1 && cur.撞码[2] > 5 ? 300 : t3 && r1 ? 20 : 0) + (t1 && r3 ? 30 : 0) + ws.length;
    add(M.g1[i], v); if (M.g2[i] !== M.g1[i]) add(M.g2[i], v);
  }
  for (const [i, j] of cur.losers) if (M.fl[i] & M.flags.T1521) { const v = cur.四码 > 125 ? 300 : 3; add(M.g1[i], v); if (j >= 0) add(M.g1[j], v); }
  return w;
}

function fixStep(fullScan) {
  const w = problemWeights();
  let cands = Object.keys(w).map(Number).filter(g => !tabu.includes(g)).sort((a, b) => w[b] - w[a]).slice(0, 16);
  if (fullScan) cands = [...Array(M.NG).keys()].filter(g => !tabu.includes(g));
  let best = null;
  for (const g of cands) {
    const old = k[g];
    for (let kk = 0; kk < 26; kk++) {
      if (kk === old) continue;
      k[g] = kk; const m = M.evaluate(k, false);
      if (!best || m.F < best.F) best = { g, kk, F: m.F, m };
    }
    k[g] = old;
  }
  if (!best || best.F >= cur.F - 1e-9) return fullScan ? false : 'scan';
  const before = { clash: new Set(cur.clashes.map(c => c[0] + c[1])), dups: cur.dups.length, S: cur.S, c6: cur.撞码[3] };
  const g = best.g, from = M.K[k[g]].toUpperCase(), to = M.K[best.kk].toUpperCase();
  tabu.push(g); if (tabu.length > 8) tabu.shift();
  const S0 = cur.S;
  apply([[g, best.kk]], null);
  log.unshift(`自动${fullScan ? '（全量扫描）' : '（按冲突）'}：挪 ${groupLink(g)} ${from}→${to}，总分 ${(cur.S - S0 >= 0 ? '+' : '') + (cur.S - S0).toFixed(2)}<br><small>${lastDiff}</small>`);
  renderPane(); save();
  return true;
}

function runFix(n) {
  if (busy) return; busy = true;
  const btns = ['#fix1', '#fix10']; btns.forEach(b => $(b).disabled = true);
  let i = 0;
  const done = () => { busy = false; $('#savestat').textContent = ''; btns.forEach(b => $(b).disabled = false); tab = 'log'; renderPane(); };
  const step = (full) => {
    const r = fixStep(full);
    if (r === 'scan') { $('#savestat').textContent = '冲突相关的根组里没有能提分的一步，正在把 129 组全部扫一遍（约 10 秒）……'; setTimeout(() => step(true), 30); return; }
    $('#savestat').textContent = '';
    if (!r) { log.unshift('自动：129 组都试过了，没有能让总分变好的单步挪动。'); done(); return; }
    i++;
    if (i < n) setTimeout(() => step(false), 10); else done();
  };
  setTimeout(() => step(false), 10);
}

// 保存：优先云端（db），不可用时退回本浏览器
let db = null, saved = [];
function localSaved() { try { return JSON.parse(localStorage.getItem('tiaogen_saved') || '[]'); } catch (e) { return []; } }
function setLocal(list) { saved = list; try { localStorage.setItem('tiaogen_saved', JSON.stringify(list)); } catch (e) { stat('浏览器存储不可用，请用“导出全部”另存文件'); } fillSelects(); if (tab === 'saved' && M) renderPane(); }
// 合并导入的布局：同 id 的跳过；返回新增条数
function mergeLocal(list) {
  const have = new Set(saved.map(s => s.id)), add = list.filter(s => s && s.id && s.name && s.layout && !have.has(s.id));
  if (add.length) setLocal(saved.concat(add).sort((a, b) => (b.savedAt || '').localeCompare(a.savedAt || '')));
  return add.length;
}
function seedLocal() {
  saved = localSaved();
  let seeded = false; try { seeded = localStorage.getItem('tiaogen_seeded') === '1'; localStorage.setItem('tiaogen_seeded', '1'); } catch (e) { }
  if (!seeded && window.TIAOGEN_SEED) mergeLocal(window.TIAOGEN_SEED);
}
(async () => {
  try { if (window.claude && window.claude.use) db = await window.claude.use('db'); } catch (e) { db = null; }
  if (db) {
    db.collection('layouts').orderBy('savedAt', 'desc').onSnapshot(s => {
      saved = s.docs.map(d => Object.assign({ id: d.id }, d.data())); fillSelects(); if (tab === 'saved' && M) renderPane();
    }, e => { db = null; seedLocal(); fillSelects(); if (tab === 'saved' && M) renderPane(); });
  } else { seedLocal(); fillSelects(); if (tab === 'saved' && M) renderPane(); }
})();
function stat(t) { $('#savestat').textContent = t; setTimeout(() => { if ($('#savestat').textContent === t) $('#savestat').textContent = ''; }, 3000); }
async function saveLayout() {
  const name = $('#savename').value.trim() || ('布局 ' + new Date().toLocaleString('zh-CN', { hour12: false }));
  const doc = { name, layout: Object.fromEntries(D.groups.map((g, i) => [g.id, M.K[k[i]]])), savedAt: new Date().toISOString(),
    S: +cur.S.toFixed(3), pen: cur.pen, 形码成本: +cur.形码成本.toFixed(5), 三简: cur.三简, 冲突6万: cur.撞码[3], 换键: cur.换键根组, 起点: labelFor(startName) };
  $('#save').disabled = true;
  try {
    if (db) { await db.collection('layouts').add(doc); }
    else { doc.id = 'l' + Date.now(); setLocal([doc].concat(saved)); }
    stat('已保存：' + name); $('#savename').value = ''; tab = 'saved'; renderPane();
  } catch (e) {
    stat(e && e.code === 'quota_exceeded' ? '存储已满，请先删掉一些旧布局' : '保存失败，请再试一次');
  } finally { $('#save').disabled = false; }
}
async function deleteSaved(id, btn) {
  if (btn.dataset.confirm !== '1') { btn.dataset.confirm = '1'; btn.textContent = '确认删除'; return; }
  try {
    if (db) await db.collection('layouts').doc(id).delete();
    else setLocal(saved.filter(s => s.id !== id));
  } catch (e) { stat('删除失败，请再试一次'); }
}

// 下载普通单字表（与 make_plain_table.py 同规则：核心字全码+简码、有简让全、扩展字、符号表）
let dls = null;
const LOCAL = !(window.claude && window.claude.use);
function saveFile(filename, blob) {
  if (dls) return dls.save({ filename, data: blob });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  return Promise.resolve();
}
(async () => { try { if (!LOCAL) dls = await window.claude.use('downloads'); } catch (e) { dls = null; } if (dls || LOCAL) { $('#dl').hidden = false; $('#dl2').hidden = false; } })();
async function downloadTable(codeFirst) {
  const base = $('#savename').value.trim() || labelFor(startName) + (hist.length ? '_调整版' : '');
  const fname = ('夜莺_' + base + '_普通单字表' + (codeFirst ? '_码前' : '') + '.txt').replace(/[\\/:*?"<>|]/g, '_');
  $('#dl').disabled = true; $('#dl2').disabled = true;
  try {
    let txt = buildTable(D, M, k);
    if (codeFirst) txt = txt.split('\n').filter(Boolean).map(l => { const [ch, code] = l.split('\t'); return code + '\t' + ch; }).join('\n') + '\n';
    await saveFile(fname, new Blob([txt], { type: 'text/plain' }));
    stat('已下载：' + fname);
  } catch (e) {
    const c = e && e.code;
    if (c === 'declined') stat('已取消下载');
    else if (c === 'rate_limited') stat('上一个下载提示还没关，请稍后再试');
    else { stat('这里无法下载文件'); $('#dl').hidden = true; $('#dl2').hidden = true; }
  } finally { $('#dl').disabled = false; $('#dl2').disabled = false; }
}

function exportSaved() {
  const name = '夜莺调根台_布局_' + new Date().toISOString().slice(0, 10) + '.json';
  saveFile(name, new Blob([JSON.stringify(saved, null, 1)], { type: 'application/json' })).then(() => stat('已导出：' + name), () => stat('导出失败'));
}
async function importSaved(file) {
  try {
    const list = JSON.parse(await file.text()), arr = Array.isArray(list) ? list : [list];
    if (db) { let n = 0; for (const s of arr) if (s && s.name && s.layout && !saved.some(x => x.id === s.id)) { const c = Object.assign({}, s); delete c.id; await db.collection('layouts').add(c); n++; } stat(`导入 ${n} 个布局`); }
    else stat(`导入 ${mergeLocal(arr)} 个布局（同名同 id 的已跳过）`);
  } catch (e) { stat('导入失败：不是调根台导出的 JSON 文件'); }
}

function bind() {
  $('#pane').addEventListener('change', e => { if (e.target.id === 'importfile' && e.target.files[0]) importSaved(e.target.files[0]); });
  $('#dl').addEventListener('click', () => downloadTable(false));
  $('#dl2').addEventListener('click', () => downloadTable(true));
  $('#save').addEventListener('click', saveLayout);
  $('#savename').addEventListener('keydown', e => { if (e.key === 'Enter') saveLayout(); });
  $('#pane').addEventListener('click', e => {
    const l = e.target.closest('[data-load]'), d = e.target.closest('[data-del]');
    if (l) { const s = saved.find(x => x.id === l.dataset.load); if (s) { tabu = []; apply(D.groups.map((g, i) => [i, M.KI[s.layout[g.id]]]), `载入：${esc(s.name)}`); } }
    if (d) deleteSaved(d.dataset.del, d);
    if (e.target.closest('[data-export]')) exportSaved();
    if (e.target.closest('[data-import]')) $('#importfile').click();
    const cs = e.target.closest('[data-csort]'); if (cs) { clashSort = cs.dataset.csort; renderPane(); }
    if (e.target.closest('[data-call]')) { clashAll = !clashAll; renderPane(); }
  });
  $('#heat').addEventListener('change', e => { heat = e.target.value; renderKbd(); });
  $('#ref').addEventListener('change', e => { const l = layoutFor(e.target.value); if (!l) return; refName = e.target.value; refM = M.evaluate(l, false); renderMetrics(); save(); });
  $('#start').addEventListener('change', e => { const l = layoutFor(e.target.value); if (!l) return; startName = e.target.value; tabu = []; apply([...l].map((v, g) => [g, v]), `换起点：${esc(labelFor(startName))}`); });
  $('#undo').addEventListener('click', () => { if (!hist.length) return; fut.push(Int8Array.from(k)); prevM = cur; k = hist.pop(); refresh(); lastDiff = diffNote(prevM, cur); log.unshift('撤销<br><small>' + lastDiff + '</small>'); renderPane(); });
  $('#redo').addEventListener('click', () => { if (!fut.length) return; hist.push(Int8Array.from(k)); prevM = cur; k = fut.pop(); refresh(); lastDiff = diffNote(prevM, cur); log.unshift('重做<br><small>' + lastDiff + '</small>'); renderPane(); });
  $('#fix1').addEventListener('click', () => runFix(1));
  $('#fix10').addEventListener('click', () => runFix(10));
  $('#copy').addEventListener('click', () => {
    const txt = JSON.stringify(Object.fromEntries(D.groups.map((g, i) => [g.id, M.K[k[i]]])));
    const show = () => { tab = 'log'; log.unshift('当前布局（复制给 Claude 做正式评测）：<textarea readonly style="width:100%;height:80px">' + esc(txt) + '</textarea>'); renderPane(); };
    if (navigator.clipboard) navigator.clipboard.writeText(txt).then(() => { $('#copy').textContent = '已复制'; setTimeout(() => $('#copy').textContent = '复制当前布局', 1500); }, show); else show();
  });
  document.querySelector('.tabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { tab = b.dataset.tab; renderPane(); } });
  document.addEventListener('click', e => {
    const c = e.target.closest('.chip, .g');
    if (c) { sel = +c.dataset.g; tab = 'group'; renderKbd(); renderPane(); return; }
    const r = e.target.closest('tr[data-move]');
    if (r && sel !== null) {
      const kk = +r.dataset.move; if (kk === k[sel]) return;
      apply([[sel, kk]], `手动：挪 ${groupLink(sel)} ${M.K[k[sel]].toUpperCase()}→${M.K[kk].toUpperCase()}`);
    }
  });
  const kbd = $('#kbd');
  kbd.addEventListener('dragstart', e => { const c = e.target.closest('.chip'); if (c) e.dataTransfer.setData('text/plain', c.dataset.g); });
  kbd.addEventListener('dragover', e => { const key = e.target.closest('.key'); if (key) { e.preventDefault(); key.classList.add('drop'); } });
  kbd.addEventListener('dragleave', e => { const key = e.target.closest('.key'); if (key) key.classList.remove('drop'); });
  kbd.addEventListener('drop', e => {
    const key = e.target.closest('.key'); if (!key) return; e.preventDefault();
    const g = +e.dataTransfer.getData('text/plain'), kk = +key.dataset.k;
    if (k[g] === kk) { renderKbd(); return; }
    sel = g; apply([[g, kk]], `手动：挪 ${groupLink(g)} ${M.K[k[g]].toUpperCase()}→${M.K[kk].toUpperCase()}`);
  });
}
