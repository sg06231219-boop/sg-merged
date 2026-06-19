/* ===== UniPulse Router (ES Module) ===== */
/* Hash-based router. Delegates rendering to State. */

import State from './state.js';

function init() {
  window.addEventListener('hashchange', onHashChange);
  onHashChange();
}

function onHashChange() {
  const raw = window.location.hash.slice(2) || 'discover';
  const parts = raw.split('/');
  const page = parts[0];

  /* Compare share URL: #/compare/1,3,5 */
  if (page === 'compare' && parts[1]) {
    handleCompareURL(parts[1]);
    return;
  }

  const validPages = ['discover', 'rankings', 'programs', 'forum'];
  if (validPages.includes(page)) {
    navigate(page, false);
  } else {
    navigate('discover', false);
  }
}

function handleCompareURL(idsStr) {
  State.clearCompare();
  const ids = idsStr.split(',').map(Number).filter(n => n > 0);
  ids.forEach(id => State.addCompare(id));
  /* Navigate to discover first to set up the page context */
  State.setPage('discover');
  /* Then open the compare modal */
  import('./compare.js').then(mod => mod.default.doCompare());
}

function navigate(page, pushState = true) {
  if (pushState) window.location.hash = '#/' + page;
  State.setPage(page);
}

const Router = { init, navigate };
export default Router;