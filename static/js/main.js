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
    document.querySelectorAll('.dropdown').forEach(d => {
      if (d !== parent) {
        d.classList.remove('open');
        d.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', false);
      }
    });
  });
});

document.addEventListener('click', () => {
  document.querySelectorAll('.dropdown.open').forEach(d => {
    d.classList.remove('open');
    d.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', false);
  });
});

// ── Roster table row bio expand ──────────────────────────────────────────────
document.querySelectorAll('.roster-table-row').forEach(row => {
  row.addEventListener('click', () => {
    const id = row.dataset.playerId;
    if (!id) return;
    const bio = document.getElementById('bio-' + id);
    if (!bio) return;
    const isOpen = bio.classList.toggle('open');
    const toggle = row.querySelector('.rt-bio-toggle');
    if (toggle) toggle.textContent = isOpen ? '▼ Full Bio' : '▶ Full Bio';
  });
});

// ── Coach name bio expand ────────────────────────────────────────────────────
document.querySelectorAll('.coach-name-link').forEach((link, i) => {
  link.addEventListener('click', (e) => {
    e.stopPropagation();
    const bio = document.getElementById('coach-bio-' + (i + 1));
    if (bio) bio.classList.toggle('open');
  });
});
