(async () => {
  try {
    const response = await fetch('performance-data.json');
    if (!response.ok) throw new Error('Data unavailable');
    const data = await response.json();
    function render(scope) {
      const countRow = data.rows[scope === '1500' ? 3 : 7].values;
      const weighted = data.rows[scope === '1500' ? 4 : 8].values;
      document.querySelector('#scope-title').textContent = `前${scope}字`;
      document.querySelector('#short-share').textContent = weighted.slice(0,3).reduce((sum,v) => sum + parseFloat(v),0).toFixed(2) + '%';
      document.querySelector('#code-bar').innerHTML = weighted.slice(0,4).map(v => `<span style="flex:${parseFloat(v)}"></span>`).join('');
      document.querySelector('#code-legend').innerHTML = weighted.slice(0,4).map((v,i) => `<div><i></i>${i+1}码<strong>${v}</strong><small>${countRow[i]}字 · 字频加权比重如上</small></div>`).join('');
      document.querySelector('#scope-metrics').innerHTML = [[weighted[4],'加权选重率'],[Number(countRow[7]).toFixed(2),'加权键长'],[countRow[8],'加权字均当量']].map(([v,l]) => `<div><b>${v}</b><span>${l}</span></div>`).join('');
      document.querySelectorAll('[data-scope]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scope === scope)));
    }
    document.querySelectorAll('[data-scope]').forEach(b => b.addEventListener('click', () => render(b.dataset.scope)));
    render('6000');
    document.querySelector('#key-rows').innerHTML = ['qwertyuiop','asdfghjkl','zxcvbnm'].map(row => `<div class="keyboard-row">${[...row].map(k => `<div class="load-key" style="--load:${data.keyboard[k]/8.82*70}" title="${k.toUpperCase()}：${data.keyboard[k].toFixed(2)}%"><span>${k}</span><b>${data.keyboard[k].toFixed(2)}</b></div>`).join('')}</div>`).join('');
  } catch {
    document.querySelector('#scope-results').textContent = '图表数据暂时无法加载，请查看下方完整数据表。';
    document.querySelectorAll('[data-scope]').forEach(b => b.disabled = true);
  }
})();
