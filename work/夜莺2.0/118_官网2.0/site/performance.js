(async () => {
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  try {
    const response = await fetch('performance-data.json');
    if (!response.ok) throw new Error('Data unavailable');
    const data = await response.json();
    const byScope = Object.fromEntries(data.rows.map(r => [r.scope, r]));
    function render(scope) {
      const r = byScope['前' + scope + '字'];
      document.querySelector('#scope-title').textContent = `前${scope}字`;
      document.querySelector('#short-share').textContent = r['码长加权%'].slice(0, 3).reduce((s, v) => s + v, 0).toFixed(2) + '%';
      document.querySelector('#code-bar').innerHTML = r['码长加权%'].map(v => `<span style="flex:${v}"></span>`).join('');
      document.querySelector('#code-legend').innerHTML = r['码长加权%'].map((v, i) => `<div><i></i>${i + 1}码<strong>${v.toFixed(2)}%</strong><small>${r['码长字数'][i]}字 · 字频加权比重如上</small></div>`).join('');
      document.querySelector('#scope-metrics').innerHTML = [[r['选重加权%'].toFixed(3) + '%', '加权选重率'], [r['加权键长'].toFixed(2), '加权键长'], [r['加权字均当量'].toFixed(2), '加权字均当量']].map(([v, l]) => `<div><b>${v}</b><span>${l}</span></div>`).join('');
      document.querySelectorAll('[data-scope]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scope === scope)));
    }
    document.querySelectorAll('[data-scope]').forEach(b => b.addEventListener('click', () => render(b.dataset.scope)));
    render('6000');
    const maxLoad = Math.max(...Object.values(data.keyboard));
    document.querySelector('#key-rows').innerHTML = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'].map(row => `<div class="keyboard-row">${[...row].map(k => `<div class="load-key" style="--load:${data.keyboard[k] / maxLoad * 70}" title="${k.toUpperCase()}：${data.keyboard[k].toFixed(2)}%"><span>${k}</span><b>${data.keyboard[k].toFixed(2)}</b></div>`).join('')}</div>`).join('');
    document.querySelector('#hand-left').textContent = data.hands[0].toFixed(2) + '%';
    document.querySelector('#hand-right').textContent = data.hands[1].toFixed(2) + '%';
    document.querySelector('#hand-bar').style.width = data.hands[0] + '%';
    const six = byScope['前6000字'];
    document.querySelector('#feel').innerHTML = [[six['左右互击%'], '左右互击 · 加权比重'], [six['同指大跨排%'], '同指大跨排 · 加权比重'], [six['同指小跨排%'], '同指小跨排 · 加权比重']].map(([v, l]) => `<article><strong>${v.toFixed(2)}%</strong><span>${l}</span></article>`).join('');
    document.querySelector('#full-table').innerHTML = data.rows.map(r => `<tr><th scope="row">${esc(r.scope)}</th><td>${r['字数']}</td>${r['码长字数'].map(v => `<td>${v}</td>`).join('')}<td>${r['选重']}</td><td>${r['选重加权%'].toFixed(3)}%</td><td>${r['全码重']}</td><td>${r['加权键长'].toFixed(2)}</td><td>${r['加权字均当量'].toFixed(2)}</td><td>${r['加权键均当量'].toFixed(3)}</td><td>${r['左右互击%'].toFixed(2)}%</td><td>${r['同指大跨排%'].toFixed(2)}%</td><td>${r['同指小跨排%'].toFixed(2)}%</td></tr>`).join('');
    const c = data.conflict;
    document.querySelector('#conflict-full').textContent = c['全部单字全码'];
    document.querySelector('#conflict-left').textContent = c['剔除有简码的字'];
    document.querySelector('#conflict-full-bar').textContent = c['全部单字全码'] + ' 对';
    document.querySelector('#conflict-left-bar').textContent = c['剔除有简码的字'] + ' 对';
    document.querySelector('#conflict-left-fill').style.width = (c['全部单字全码'] ? c['剔除有简码的字'] / c['全部单字全码'] * 100 : 0) + '%';
    document.querySelector('#conflict-pct').innerHTML = (c['全部单字全码'] ? (100 - c['剔除有简码的字'] / c['全部单字全码'] * 100).toFixed(1) : '0') + '<span>%</span>';
    const rest = document.querySelector('#conflict-rest');
    if (c['剩余'].length) {
      rest.innerHTML = `<h3>剩余的 ${c['剩余'].length} 对高频冲突</h3><div class="conflict-table-wrap"><table class="conflict-table"><thead><tr><th scope="col">编码</th><th scope="col">单字</th><th scope="col">词语</th></tr></thead><tbody>${c['剩余'].map(x => `<tr><td><code>${esc(x[1])}</code></td><td>${esc(x[0])}</td><td>${esc(x[2])}</td></tr>`).join('')}</tbody></table></div>`;
    } else {
      rest.innerHTML = `<h3>让位前的 ${c['全部'].length} 对高频同码</h3><p class="note">这些字都有简码；下表是它们的全码与同码词，供对照。</p><div class="conflict-table-wrap"><table class="conflict-table"><thead><tr><th scope="col">编码</th><th scope="col">单字（字频名次）</th><th scope="col">词语（词频名次）</th></tr></thead><tbody>${c['全部'].slice(0, 60).map(x => `<tr><td><code>${esc(x[1])}</code></td><td>${esc(x[0])}（${x[3]}）</td><td>${esc(x[2])}（${x[4]}）</td></tr>`).join('')}</tbody></table></div>`;
    }
  } catch (e) {
    document.querySelector('#scope-results').textContent = '图表数据暂时无法加载，请下载 JSON 查看。';
    document.querySelectorAll('[data-scope]').forEach(b => b.disabled = true);
  }
})();
