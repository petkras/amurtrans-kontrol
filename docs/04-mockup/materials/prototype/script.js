const buttons = [...document.querySelectorAll('nav button[data-tab]')];
const screens = [...document.querySelectorAll('.screen')];
function show(id) {
  if (!screens.some(screen => screen.id === id)) id = 'request';
  buttons.forEach(button => button.classList.toggle('active', button.dataset.tab === id));
  screens.forEach(screen => screen.classList.toggle('active', screen.id === id));
  history.replaceState(null, '', '#' + id);
}
buttons.forEach(button => button.addEventListener('click', () => show(button.dataset.tab)));
window.addEventListener('hashchange', () => show(location.hash.slice(1)));
show(location.hash.slice(1));
