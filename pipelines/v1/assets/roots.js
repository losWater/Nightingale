const board = document.querySelector('#root-board');
const compactButton = document.querySelector('#compact-view');
const fullButton = document.querySelector('#full-view');
function setRootView(compact) {
  board.classList.toggle('hide-alias', compact);
  compactButton.setAttribute('aria-pressed', String(compact));
  fullButton.setAttribute('aria-pressed', String(!compact));
  document.querySelector('#merge-list').hidden = !compact;
  document.querySelector('.root-guide p').textContent = compact ? '主根键盘 · 金色为横、竖、撇、折、点 · 归并根见下方归并字根表' : '主根与归并根使用同一键位 · 金色为五个笔画 · 锚定同键单独标注';
}
compactButton.addEventListener('click', () => setRootView(true));
fullButton.addEventListener('click', () => setRootView(false));
document.querySelector('#print-roots').addEventListener('click', () => window.print());
const names = {'𠂆':'反字框','𢀖':'轻右','𫠣':'拣右','𠤎':'化右','𡗗':'春字头','𠂤':'追字心','𠂉':'卧人','𠃓':'杨字边','𦣞':'颐字旁','𣦼':'餐字头','𠀐':'贵字头','𠀎':'冓头'};
const cards = [...document.querySelectorAll('.root-key')];
for (const card of cards) {
  for (const [glyph,name] of Object.entries(names)) {
    if (card.dataset.search.includes(glyph)) card.dataset.search += ' ' + name;
  }
}
document.querySelector('#root-search').addEventListener('input', event => {
  const query = event.target.value.trim().toLowerCase();
  let count = 0;
  for (const card of cards) {
    const match = card.dataset.search.toLowerCase().includes(query);
    card.classList.toggle('unmatched', !!query && !match);
    card.classList.toggle('matched', !!query && match);
    if (match) count++;
  }
  document.querySelector('#search-status').textContent = query ? `找到 ${count} 个对应键位` : '按 QWERTY 键位排列';
  document.querySelector('#no-roots').hidden = count !== 0;
});
