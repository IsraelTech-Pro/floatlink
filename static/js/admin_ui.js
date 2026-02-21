(function () {
  function ensureToggles() {
    if (document.getElementById('fl-admin-toggles')) return;

    var header = document.getElementById('header');
    if (!header) return;

    var container = document.createElement('div');
    container.id = 'fl-admin-toggles';

    var leftBtn = document.createElement('button');
    leftBtn.type = 'button';
    leftBtn.className = 'fl-toggle-btn';
    leftBtn.textContent = 'Menu';
    leftBtn.addEventListener('click', function () {
      document.body.classList.toggle('fl-nav-collapsed');
      try {
        localStorage.setItem('fl-nav-collapsed', document.body.classList.contains('fl-nav-collapsed') ? '1' : '0');
      } catch (e) {}
    });

    var filterBtn = document.createElement('button');
    filterBtn.type = 'button';
    filterBtn.className = 'fl-toggle-btn';
    filterBtn.textContent = 'Filters';
    filterBtn.addEventListener('click', function () {
      document.body.classList.toggle('fl-filters-collapsed');
      try {
        localStorage.setItem('fl-filters-collapsed', document.body.classList.contains('fl-filters-collapsed') ? '1' : '0');
      } catch (e) {}
    });

    container.appendChild(leftBtn);
    container.appendChild(filterBtn);
    header.appendChild(container);
  }

  function restoreState() {
    try {
      if (localStorage.getItem('fl-nav-collapsed') === '1') {
        document.body.classList.add('fl-nav-collapsed');
      }
      if (localStorage.getItem('fl-filters-collapsed') === '1') {
        document.body.classList.add('fl-filters-collapsed');
      }
    } catch (e) {}
  }

  function init() {
    restoreState();
    ensureToggles();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
