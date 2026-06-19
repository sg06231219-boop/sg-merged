/* ===== UniPulse State Manager (ES Module) ===== */
/* Centralized reactive state. All mutations go through this module. */

let _page = 'discover';
let _region = 'all';
let _searchQuery = '';
let _compareList = [];
let _forumCat = 'all';
let _searchDebounce = null;

const _listeners = {};

function _emit(event, data) {
  (_listeners[event] || []).forEach(fn => fn(data));
}

const State = {
  /* Getters */
  get page() { return _page; },
  get region() { return _region; },
  get searchQuery() { return _searchQuery; },
  get compareList() { return [..._compareList]; },
  get forumCat() { return _forumCat; },

  /* Page navigation */
  setPage(page) {
    if (page === _page) return;

    /* Show/hide page containers */
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const el = document.getElementById('page-' + page);
    if (el) el.classList.add('active');

    /* Update nav button states */
    document.querySelectorAll('#navLinks button').forEach(b => {
      b.classList.remove('active');
      b.removeAttribute('aria-current');
    });
    const btn = document.querySelector(`#navLinks button[data-page="${page}"]`);
    if (btn) { btn.classList.add('active'); btn.setAttribute('aria-current', 'page'); }

    _page = page;
    _emit('page', page);

    /* Render the page */
    import('./render.js').then(mod => mod.renderPage(page));
  },

  /* Region filter */
  setRegion(region) {
    _region = region;
    _emit('region', region);
    import('./render.js').then(mod => mod.renderDiscover());
  },

  /* Search with debounce (300ms) */
  setSearch(query) {
    clearTimeout(_searchDebounce);
    _searchQuery = query;
    _searchDebounce = setTimeout(() => {
      import('./render.js').then(mod => mod.renderDiscover());
    }, 300);
  },

  /* Reset all filters */
  resetFilters() {
    _region = 'all';
    _searchQuery = '';
    const si = document.getElementById('searchInput');
    if (si) si.value = '';
    document.querySelectorAll('#regionFilters .filter-tab').forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-checked', 'false');
    });
    const allBtn = document.querySelector('#regionFilters .filter-tab[data-region="all"]');
    if (allBtn) { allBtn.classList.add('active'); allBtn.setAttribute('aria-checked', 'true'); }
    import('./render.js').then(mod => mod.renderDiscover());
  },

  /* Compare list */
  addCompare(id) {
    if (_compareList.includes(id)) return false;
    if (_compareList.length >= 4) return false;
    _compareList.push(id);
    _emit('compare', _compareList);
    return true;
  },
  removeCompare(id) {
    const i = _compareList.indexOf(id);
    if (i > -1) _compareList.splice(i, 1);
    _emit('compare', _compareList);
  },
  isCompared(id) { return _compareList.includes(id); },
  clearCompare() {
    _compareList = [];
    _emit('compare', _compareList);
  },

  /* Forum category */
  setForumCat(cat) {
    _forumCat = cat;
    import('./render.js').then(mod => mod.renderForum());
  },

  /* Subscribe */
  on(event, fn) {
    _listeners[event] = _listeners[event] || [];
    _listeners[event].push(fn);
  }
};

export default State;
