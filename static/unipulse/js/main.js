/* ===== UniPulse Main Entry (ES Module) ===== */
/* Bootstraps the app: imports, event bindings, initial render. */

import { DATA } from './data.js';
import State from './state.js';
import Router from './router.js';
import Compare from './compare.js';
import { showToast, showNewPostForm } from './render.js';

/* ==== Expose globals for inline onclick handlers ==== */
/* These are intentionally global - used in HTML onclick attributes for simplicity */
window.State = State;
window._showToast = showToast;
window._toggleCompareFromDetail = function(id) {
  Compare.toggleFromDetail(id);
  if (State.page === 'discover') {
    import('./render.js').then(mod => mod.renderDiscover());
  }
};
window._Compare = {
  removeItem: Compare.removeItem,
  doCompare: Compare.doCompare
};

function el(id) { return document.getElementById(id); }

/* ==== App Init ==== */
document.addEventListener('DOMContentLoaded', () => {

  /* --- Navigation clicks --- */
  document.querySelectorAll('#navLinks button').forEach(btn => {
    btn.addEventListener('click', () => Router.navigate(btn.dataset.page));
  });

  /* Logo click → home */
  const logo = document.querySelector('.logo');
  if (logo) {
    logo.addEventListener('click', () => Router.navigate('discover'));
    logo.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); Router.navigate('discover'); }
    });
  }

  /* --- Region filters --- */
  el('regionFilters').addEventListener('click', e => {
    const tab = e.target.closest('.filter-tab');
    if (!tab) return;
    document.querySelectorAll('#regionFilters .filter-tab').forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-checked', 'false');
    });
    tab.classList.add('active');
    tab.setAttribute('aria-checked', 'true');
    State.setRegion(tab.dataset.region);
  });

  /* --- Search --- */
  el('searchInput').addEventListener('input', () => {
    State.setSearch(el('searchInput').value);
  });
  el('searchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      State.setSearch(el('searchInput').value);
    }
  });

  /* --- Forum category --- */
  el('catList').addEventListener('click', e => {
    const li = e.target.closest('li');
    if (!li) return;
    document.querySelectorAll('#catList li').forEach(l => {
      l.classList.remove('active');
      l.setAttribute('aria-selected', 'false');
    });
    li.classList.add('active');
    li.setAttribute('aria-selected', 'true');
    State.setForumCat(li.dataset.cat);
  });

  /* --- Modal close --- */
  el('modalOverlay').addEventListener('click', (e) => {
    if (e.target === el('modalOverlay')) closeModal(e);
  });
  el('modalClose').addEventListener('click', () => closeModal());
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && el('modalOverlay').classList.contains('show')) closeModal();
  });

  /* --- Compare toggle button --- */
  el('compareToggle').addEventListener('click', () => {
    if (State.compareList.length === 0) { showToast(DATA.STR.COMPARE_ADD_HINT); return; }
    Compare.updateBar();
  });

  /* --- Do Compare button --- */
  el('doCompareBtn').addEventListener('click', Compare.doCompare);

  /* --- Login button --- */
  el('loginBtn').addEventListener('click', () => showToast(DATA.STR.DEMO_MODE));

  /* --- New post button --- */
  el('newPostBtn').addEventListener('click', () => showNewPostForm());

  /* --- Hamburger menu --- */
  let mobileMenuOpen = false;
  const hamburger = el('hamburger');

  function buildMobileNav() {
    document.querySelector('.mobile-nav')?.remove();
    document.querySelector('.mobile-nav-overlay')?.remove();

    const overlay = document.createElement('div');
    overlay.className = 'mobile-nav-overlay';
    overlay.addEventListener('click', closeMobileMenu);

    const menu = document.createElement('div');
    menu.className = 'mobile-nav';
    document.querySelectorAll('#navLinks button').forEach(btn => {
      const clone = document.createElement('button');
      clone.className = 'btn btn-ghost';
      clone.textContent = btn.textContent;
      clone.addEventListener('click', () => {
        Router.navigate(btn.dataset.page);
        closeMobileMenu();
      });
      menu.appendChild(clone);
    });

    document.body.appendChild(overlay);
    document.body.appendChild(menu);
  }

  function openMobileMenu() {
    if (window.innerWidth > 768) return;
    buildMobileNav();
    mobileMenuOpen = true;
    hamburger.classList.add('open');
    hamburger.setAttribute('aria-expanded', 'true');
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
    hamburger.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
    document.querySelector('.mobile-nav-overlay')?.remove();
    document.querySelector('.mobile-nav')?.remove();
    document.body.classList.remove('scroll-locked');
  }

  hamburger.addEventListener('click', () => {
    if (mobileMenuOpen) closeMobileMenu();
    else openMobileMenu();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 768 && mobileMenuOpen) closeMobileMenu();
  });

  /* --- Router init (triggers initial render) --- */
  Router.init();
});

function closeModal(e) {
  if (e && e.target !== e.currentTarget) return;
  document.body.classList.remove('scroll-locked');
  el('modalOverlay').classList.remove('show');
  window.location.replace('#/' + State.page);
}
