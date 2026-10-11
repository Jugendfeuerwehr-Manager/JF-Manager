/*
 * Kleine Helfer für das Handbuch: Seitenleiste auf schmalen Bildschirmen,
 * Suchergebnisse ein- und ausblenden, Taste „/“ für die Suche und
 * Hervorhebung des aktuellen Abschnitts im Inhaltsverzeichnis.
 * Ohne JavaScript bleiben Navigation und Inhalt vollständig nutzbar.
 */
(function () {
  var body = document.body;

  // Seitenleiste
  var toggle = document.querySelector('[data-nav-toggle]');
  var backdrop = document.querySelector('[data-nav-close]');
  function setNav(open) {
    body.classList.toggle('nav-open', open);
    if (toggle) toggle.setAttribute('aria-expanded', String(open));
    if (backdrop) backdrop.hidden = !open;
  }
  if (toggle) toggle.addEventListener('click', function () { setNav(!body.classList.contains('nav-open')); });
  if (backdrop) backdrop.addEventListener('click', function () { setNav(false); });

  // Suche
  var input = document.querySelector('[data-search-input]');
  var panel = document.getElementById('mkdocs-search-results');
  function updatePanel() {
    if (!input || !panel) return;
    panel.hidden = input.value.trim().length < 2;
  }
  if (input && panel) {
    input.addEventListener('input', updatePanel);
    input.addEventListener('focus', updatePanel);
    document.addEventListener('click', function (event) {
      if (!event.target.closest('.search')) panel.hidden = true;
    });
  }
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      if (panel) panel.hidden = true;
      setNav(false);
      return;
    }
    var tag = (event.target.tagName || '').toLowerCase();
    if (event.key === '/' && input && tag !== 'input' && tag !== 'textarea') {
      event.preventDefault();
      input.focus();
    }
  });

  // Aktueller Abschnitt im Inhaltsverzeichnis
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (links.length && 'IntersectionObserver' in window) {
    var byId = {};
    links.forEach(function (link) { byId[decodeURIComponent(link.getAttribute('href').slice(1))] = link; });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (link) { link.classList.remove('is-active'); });
        var link = byId[entry.target.id];
        if (link) link.classList.add('is-active');
      });
    }, { rootMargin: '-80px 0px -70% 0px' });
    Object.keys(byId).forEach(function (id) {
      var heading = document.getElementById(id);
      if (heading) observer.observe(heading);
    });
  }
})();
