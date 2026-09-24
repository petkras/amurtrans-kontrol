(() => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.top-nav');
  menu?.addEventListener('click', () => { const open = nav.classList.toggle('open'); menu.setAttribute('aria-expanded', String(open)); });
  const dialog = document.querySelector('.search-dialog');
  const input = dialog.querySelector('input');
  const results = dialog.querySelector('.search-results');
  const pages = JSON.parse(document.getElementById('search-data').textContent);
  function openSearch() { dialog.showModal(); input.value = ''; render(''); input.focus(); }
  function render(value) {
    const q = value.trim().toLocaleLowerCase('ru');
    if (!q) { results.innerHTML = '<p style="padding:12px;color:#63716a">Введите название раздела или термин, например «архитектура», «заказ», «KPI».</p>'; return; }
    const matches = pages.map(p => ({ p, score: (p.title.toLocaleLowerCase('ru').includes(q) ? 3 : 0) + (p.summary.toLocaleLowerCase('ru').includes(q) ? 2 : 0) + (p.text.toLocaleLowerCase('ru').includes(q) ? 1 : 0) })).filter(x => x.score).sort((a,b) => b.score-a.score).slice(0, 12);
    results.replaceChildren();
    if (!matches.length) { results.textContent = 'Ничего не найдено. Попробуйте другой запрос.'; return; }
    for (const {p} of matches) {
      const a = document.createElement('a'); a.href = p.url; a.className = 'search-result';
      const title = document.createElement('strong'); title.textContent = p.title;
      const sub = document.createElement('span'); sub.textContent = p.group + ' · ' + p.summary;
      a.append(title, sub); results.append(a);
    }
  }
  document.querySelector('.search-trigger').addEventListener('click', openSearch);
  input.addEventListener('input', e => render(e.target.value));
  input.addEventListener('keydown', e => { if (e.key === 'Enter') { const first = results.querySelector('a'); if (first) location.href = first.href; e.preventDefault(); } });
  document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); if (dialog.open) dialog.close(); else openSearch(); } });
})();
