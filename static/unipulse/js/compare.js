/* ===== UniPulse Compare Module (ES Module) ===== */
import State from './state.js';
import { DATA } from './data.js';

function el(id) { return document.getElementById(id); }
function esc(s) { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]); }

function updateBar() {
  const bar = el('compareBar');
  const count = el('compareCount');
  const chips = el('compareChips');
  const list = State.compareList;

  if (count) count.textContent = list.length;
  if (list.length === 0) {
    if (bar) bar.style.display = 'none';
    return;
  }
  if (bar) bar.style.display = 'flex';
  if (chips) {
    chips.innerHTML = list.map(id => {
      const u = DATA.universities.find(x => x.id === id);
      if (!u) return '';
      return `<div class="compare-chip">${esc(u.cn)} <span role="button" tabindex="0" aria-label="移除${esc(u.cn)}" onclick="window._Compare.removeItem(${id})" onkeydown="if(event.key==='Enter')window._Compare.removeItem(${id})">✕</span></div>`;
    }).join('');
  }
}

function toggleItem(id) {
  if (State.isCompared(id)) {
    State.removeCompare(id);
    return;
  }
  const ok = State.addCompare(id);
  if (ok) {
    showToast(DATA.STR.COMPARE_ADDED);
  } else {
    showToast(DATA.STR.COMPARE_LIMIT);
  }
}

function toggleFromDetail(id) {
  toggleItem(id);
  const btn = el('detailCompareBtn');
  if (btn) btn.textContent = State.isCompared(id) ? '✓ 已加入对比' : '🔄 加入对比';
}

function removeItem(id) {
  State.removeCompare(id);
}

/* Toast helper */
function showToast(msg) {
  const t = el('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 2500);
}

/* Compare Result (in modal) */
async function doCompare() {
  const list = State.compareList;
  if (list.length < 2) { showToast(DATA.STR.COMPARE_MIN); return; }

  const selected = list.map(id => DATA.universities.find(x => x.id === id)).filter(Boolean);
  if (selected.length < 2) return;

  const body = el('modalBody');
  const hero = el('modalHero');

  document.body.classList.add('scroll-locked');
  hero.innerHTML = `<h3 style="font-family:'Fraunces',serif;font-size:22px">🔄 高校对比</h3>`;

  const summaryHTML = `<div class="compare-summary">${selected.map(u =>
    `<div class="compare-summary-item"><div class="uni">${esc(u.cn)}</div><div class="score">${esc(u.score)}</div><div style="font-size:11px;color:var(--text-soft)">综合评分</div></div>`
  ).join('')}</div>`;

  let rows = '';
  DATA.ratingDims.forEach(d => {
    const vals = selected.map(u => u.metrics[d.key]);
    const max = Math.max(...vals.filter(v => v !== null && v !== undefined));
    const min = Math.min(...vals.filter(v => v !== null && v !== undefined));
    const allEqual = (max === min);

    rows += `<tr>
      <td style="padding:10px 14px;border-bottom:1px solid var(--border)">${esc(d.label)}</td>
      ${selected.map(u => {
        const v = u.metrics[d.key];
        if (v === null || v === undefined) return `<td style="padding:10px 14px;border-bottom:1px solid var(--border);text-align:center;color:var(--text-soft)">${DATA.STR.NO_DATA}</td>`;
        const isBest = (v === max && !allEqual);
        const isWorst = (v === min && !allEqual);
        const cls = isBest ? 'best' : isWorst ? 'worst' : '';
        return `<td style="padding:10px 14px;border-bottom:1px solid var(--border);text-align:center" class="${cls}">${v}</td>`;
      }).join('')}
    </tr>`;
  });

  body.innerHTML = `
    ${summaryHTML}
    <div style="overflow-x:auto;margin-top:16px">
    <table class="compare-table">
      <thead><tr><th style="text-align:left">维度</th>${selected.map(u => `<th>${esc(u.cn)}</th>`).join('')}</tr></thead>
      <tbody>${rows}</tbody>
    </table></div>
    <p style="margin-top:16px;font-size:13px;color:var(--text-soft)">👑 = 该维度最高分 | 红色 = 该维度最低分</p>
    <div style="margin-top:20px;display:flex;gap:8px">
      <button class="btn btn-ghost" id="shareCompareBtn" onclick="window._shareCompare()">🔗 复制分享链接</button>
    </div>`;

  el('modalOverlay').classList.add('show');
  setTimeout(() => {
    const closeBtn = el('modalClose');
    if (closeBtn) closeBtn.focus();
  }, 100);

  window.location.replace('#/discover/compare');
}

/* Expose share function */
window._shareCompare = function() {
  const list = State.compareList;
  if (list.length < 2) return;
  const url = window.location.origin + window.location.pathname + '#/compare/' + list.join(',');
  navigator.clipboard.writeText(url).then(() => showToast('🔗 对比链接已复制到剪贴板！')).catch(() => showToast('🔗 ' + url));
};

/* Subscribe */
State.on('compare', () => {
  updateBar();
  if (State.page === 'discover') {
    import('./render.js').then(mod => mod.renderDiscover());
  }
});

const Compare = { updateBar, toggleItem, toggleFromDetail, removeItem, doCompare };
export default Compare;
