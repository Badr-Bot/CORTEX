/* Elarie Paris — apparitions au scroll (premium subtil) */
(function () {
  if (!('IntersectionObserver' in window)) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var TARGETS = [
    '.comparison-table__inner',
    '.before-after__grid',
    '.before-after__stat-card',
    '.feature-showcase__item',
    '.product-showcase__item',
    '.avis-clients__card',
    '.product-faq__item'
  ].join(',');

  function init() {
    var nodes = document.querySelectorAll(TARGETS);
    if (!nodes.length) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('ep-visible');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    nodes.forEach(function (node, i) {
      node.classList.add('ep-reveal');
      node.style.transitionDelay = Math.min(i % 4, 3) * 70 + 'ms';
      io.observe(node);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
