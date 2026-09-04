// ── Mobile nav toggle ────────────────────────────────────────────────────────
const navToggle = document.querySelector('.nav-toggle');
const mainNav   = document.getElementById('main-nav');

if (navToggle && mainNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = mainNav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', isOpen);
  });
}

// ── Dropdown menus ───────────────────────────────────────────────────────────
document.querySelectorAll('.dropdown-toggle').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const parent = btn.closest('.dropdown');
    const isOpen = parent.classList.toggle('open');
    btn.setAttribute('aria-expanded', isOpen);
    // close other dropdowns
    document.querySelectorAll('.dropdown').forEach(d => {
      if (d !== parent) {
        d.classList.remove('open');
        d.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', false);
      }
    });
  });
});

// Close dropdowns when clicking outside
document.addEventListener('click', () => {
  document.querySelectorAll('.dropdown.open').forEach(d => {
    d.classList.remove('open');
    d.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', false);
  });
});

// ── Player / Coach bio panel toggle ─────────────────────────────────────────
document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('click', () => {
    const panel = card.querySelector('.bio-panel');
    if (panel) panel.classList.toggle('open');
  });
});
