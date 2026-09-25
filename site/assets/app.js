(() => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.top-nav');
  menu?.addEventListener('click', () => { const open = nav.classList.toggle('open'); menu.setAttribute('aria-expanded', String(open)); });
  nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    nav.classList.remove('open');
    menu?.setAttribute('aria-expanded', 'false');
  }));
  const sidebar = document.querySelector('.sidebar');
  const groups = [...(sidebar?.querySelectorAll('details') || [])];
  groups.forEach(group => group.addEventListener('toggle', () => {
    if (group.open) groups.forEach(other => { if (other !== group) other.open = false; });
  }));
  sidebar?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    groups.forEach(group => { group.open = false; });
  }));
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

  // Add gentle easing to page-level mouse-wheel scrolling without overriding
  // native scrolling inside independently scrollable panels.
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let targetY = window.scrollY;
    let frame = 0;
    let previousScrollBehavior = '';
    const stopWheelAnimation = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      document.documentElement.style.scrollBehavior = previousScrollBehavior;
      targetY = window.scrollY;
    };
    const easeWheel = event => {
      if (event.defaultPrevented || event.ctrlKey || event.deltaY === 0) return;
      if (event.target.closest('dialog, .sidebar, .article-toc, .search-results, pre, .prose table')) return;
      const multiplier = event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? (parseFloat(getComputedStyle(document.body).lineHeight) || 24)
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? window.innerHeight : 1;
      const delta = event.deltaY * multiplier;
      if (Math.abs(delta) < 35) return;

      event.preventDefault();
      if (!frame) {
        previousScrollBehavior = document.documentElement.style.scrollBehavior;
        document.documentElement.style.scrollBehavior = 'auto';
      }
      targetY = Math.max(0, Math.min(document.documentElement.scrollHeight - window.innerHeight, targetY + delta * 1.15));
      if (frame) return;

      const animate = () => {
        const distance = targetY - window.scrollY;
        if (Math.abs(distance) < 1) {
          window.scrollTo(0, targetY);
          frame = 0;
          document.documentElement.style.scrollBehavior = previousScrollBehavior;
          return;
        }
        window.scrollTo(0, window.scrollY + distance * 0.18);
        frame = requestAnimationFrame(animate);
      };
      frame = requestAnimationFrame(animate);
    };
    window.addEventListener('wheel', easeWheel, { passive: false });
    window.addEventListener('keydown', event => {
      if (['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(event.key)) stopWheelAnimation();
    }, { passive: true });
    window.addEventListener('pointerdown', stopWheelAnimation, { passive: true });
  }
})();
