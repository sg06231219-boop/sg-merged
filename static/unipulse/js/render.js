/* ===== UniPulse Render Engine (ES Module) ===== */
import { DATA, STR, refreshForumPosts } from './data.js';
import State from './state.js';

function el(id) { return document.getElementById(id); }
function esc(s) { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]); }

function tagHTML(tag) { return `<span class="tag ${tag.type}">${esc(tag.text)}</span>`; }

function formatMetric(val) {
  return val === null || val === undefined ? '<span class="metric-na" title="暂无数据">--</span>' : esc(val);
}

function metricColor(val) {
  if (val === null || val === undefined) return 'var(--text-soft)';
  return val >= 85 ? 'var(--green)' : val >= 70 ? 'var(--gold)' : 'var(--red)';
}

function metricClass(val) {
  if (val === null || val === undefined) return 'low';
  return val >= 85 ? 'high' : val >= 70 ? 'mid' : 'low';
}

/* Toast helper */
export function showToast(msg) {
  const t = el('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 2500);
}

/* ==== Main Page Dispatch ==== */
export function renderPage(page) {
  switch (page) {
    case 'discover': renderDiscover(); break;
    case 'rankings': renderRankings(); break;
    case 'programs': renderPrograms(); break;
    case 'forum': renderForum(); break;
  }
}

/* ==== Discover ==== */
export function renderDiscover() {
  const grid = el('uniGrid');
  const noRes = el('noResults');
  if (!grid) return;

  let filtered = DATA.universities;
  if (State.region !== 'all') filtered = filtered.filter(u => u.region === State.region);
  const q = State.searchQuery.toLowerCase();
  if (q) filtered = filtered.filter(u =>
    u.name.toLowerCase().includes(q) || u.cn.includes(q) || u.loc.includes(q) || u.country.includes(q)
  );

  if (filtered.length === 0) {
    grid.innerHTML = '';
    if (noRes) noRes.style.display = 'block';
    return;
  }
  if (noRes) noRes.style.display = 'none';

  const frag = document.createDocumentFragment();
  filtered.forEach(u => {
    const card = document.createElement('div');
    card.className = 'uni-card';
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-label', `${u.cn} - 综合评分 ${u.score} 分`);
    card.addEventListener('click', () => openDetail(u.id));
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDetail(u.id); }});

    const compared = State.isCompared(u.id) ? ' ✓ 已对比' : '';
    const metrics = u.metrics || {};
    card.innerHTML = `
      <div class="uni-card-header">
        <div class="uni-logo" style="background:${u.logo}" aria-hidden="true">${esc(u.initials)}</div>
        <div class="uni-info">
          <h3>${esc(u.cn)}${compared}</h3>
          <div class="loc">${esc(u.loc)}</div>
        </div>
        <div class="uni-rating">
          <span class="score">${esc(u.score)}</span>
          <span class="max">/100</span>
        </div>
      </div>
      <div class="uni-tags">
        ${(u.tags || []).map(tagHTML).join('')}
      </div>
      <div class="uni-metrics">
        <div class="metric"><div class="metric-val">${formatMetric(metrics.academic)}</div><div class="metric-label">学术</div></div>
        <div class="metric"><div class="metric-val">${formatMetric(metrics.campus)}</div><div class="metric-label">校园</div></div>
        <div class="metric"><div class="metric-val">${formatMetric(metrics.career)}</div><div class="metric-label">就业</div></div>
      </div>`;
    frag.appendChild(card);
  });

  grid.innerHTML = '';
  grid.appendChild(frag);
}

/* ==== Rankings ==== */
export function renderRankings() {
  const list = el('rankList');
  if (!list) return;
  const sorted = [...DATA.universities].sort((a, b) => a.rank - b.rank);

  const frag = document.createDocumentFragment();
  sorted.forEach((u, i) => {
    const row = document.createElement('div');
    row.className = 'rank-row';
    row.setAttribute('role', 'row');
    row.setAttribute('tabindex', '0');
    row.setAttribute('aria-label', `第${u.rank}名 ${u.cn} 综合分${u.score}`);
    row.addEventListener('click', () => openDetail(u.id));
    row.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDetail(u.id); }});
    row.setAttribute('data-rank', u.rank);

    const trendIcon = u.trend === 'up' ? '📈' : u.trend === 'down' ? '📉' : '➡️';
    const trendClass = u.trend;
    row.innerHTML = `
      <span class="rank-pos ${i < 3 ? 'top' : ''}" role="cell">#${u.rank}</span>
      <span class="rank-name" role="cell">${esc(u.cn)}<span class="sub">${esc(u.name)}</span></span>
      <span class="rank-score" role="cell">${esc(u.score)}</span>
      <span class="rank-trend ${trendClass}" role="cell">${trendIcon} ${esc(u.trendV)}</span>
      <span class="rank-country" role="cell">${esc(u.country)}</span>
      <span class="rank-stars" role="cell">${'★'.repeat(Math.round(u.stars))}${'☆'.repeat(5 - Math.round(u.stars))} ${u.stars}</span>`;
    frag.appendChild(row);
  });
  list.innerHTML = '';
  list.appendChild(frag);
}

/* ==== Programs ==== */
export function renderPrograms() {
  const grid = el('programsGrid');
  if (!grid) return;
  grid.innerHTML = DATA.programs.map(p => `
    <div class="prog-card" role="article" aria-label="${esc(p.name)}学科排名">
      <h4>${p.icon || ''} ${esc(p.name)}</h4>
      ${(p.univs || []).map(u => `
      <div class="prog-univ">
        <div class="prog-rank ${u.tier || ''}" aria-hidden="true">${u.rank}</div>
        <span class="prog-univ-name">${esc(u.univ)}</span>
        <span style="font-size:12px;color:var(--text-soft)">#${u.rank}</span>
      </div>`).join('')}
    </div>`).join('');
}

/* ==== Forum ==== */
export function renderForum() {
  const posts = el('forumPosts');
  if (!posts) return;

  const activeCat = State.forumCat;
  let filtered = activeCat === 'all' ? DATA.forumPosts : DATA.forumPosts.filter(p => p.cat === activeCat);

  posts.innerHTML = filtered.map(p => `
    <div class="post-card">
      <div class="post-title">
        <button aria-label="打开帖子：${esc(p.title)}" onclick="openForumPost(${p.id})">${esc(p.title)}</button>
      </div>
      <div class="post-body" aria-hidden="true">${esc((p.content || '').replace(/<[^>]*>/g, '').substring(0, 120))}...</div>
      <div class="post-meta">
        <span>👤 ${esc(p.author || '匿名用户')}</span>
        <span>🕐 ${esc(p.time)}</span>
        <span>💬 ${p.replies || 0} 回复</span>
        <span>👁 ${p.views || 0} 浏览</span>
        <span class="tag">${esc(p.cat || p.category || '')}</span>
        ${(p.tags || []).slice(0, 2).map(t => `<span class="tag blue">${esc(t)}</span>`).join('')}
      </div>
    </div>`).join('');

  renderHotTopics();
}

function renderHotTopics() {
  const hot = document.querySelector('.forum-hot');
  if (!hot) return;
  const existing = hot.querySelectorAll('.hot-item');
  if (existing.length > 0) return;
  (DATA.hotTopics || []).forEach(t => {
    const div = document.createElement('div');
    div.className = 'hot-item';
    div.setAttribute('tabindex', '0');
    div.innerHTML = `"${esc(t.text)}" <span class="views">${esc(t.views)} 浏览</span>`;
    hot.appendChild(div);
  });
}

/* ==== Detail Modal ==== */
export function openDetail(id) {
  const u = DATA.universities.find(x => x.id === id);
  if (!u) return;

  document.body.classList.add('scroll-locked');

  const hero = el('modalHero');
  const body = el('modalBody');
  const metrics = u.metrics || {};

  hero.innerHTML = `
    <div class="detail-hero">
      <div class="detail-logo" style="background:${u.logo}" aria-hidden="true">${esc(u.initials)}</div>
      <div>
        <h3 id="modalTitle">${esc(u.cn)}</h3>
        <p>${esc(u.name)} · ${esc(u.loc)}</p>
      </div>
    </div>`;

  const reviews = DATA.univReviews[u.id] || DATA._defaultReviews;
  const reviewsHTML = reviews.map(r => `
    <div class="review">
      <div class="review-author">${esc(r.author)} ${'⭐'.repeat(r.stars)}</div>
      <div class="review-text">"${esc(r.text)}"</div>
    </div>`).join('');

  body.innerHTML = `
    <p style="margin-bottom:20px">${esc(u.description || u.desc || '')}</p>
    <h4 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:12px">📊 多维评分</h4>
    <div class="rating-bars">
      ${(DATA.ratingDims || []).map(d => {
        const val = metrics[d.key];
        const cls = metricClass(val);
        const color = metricColor(val);
        const displayVal = val !== null && val !== undefined ? val : STR.NO_DATA;
        const pct = val !== null && val !== undefined ? val : 0;
        return `
          <div class="rating-bar">
            <span class="rating-label">${esc(d.label)} <span style="font-size:10px;color:var(--text-soft)">${d.weight}%</span></span>
            <div class="rating-track"><div class="rating-fill ${cls}" style="width:${pct}%;background:${color}"></div></div>
            <span class="rating-val">${displayVal}</span>
          </div>`;
      }).join('')}
    </div>
    <div class="review-section">
      <h4>💬 学生评价（${u.reviews || 0}条）</h4>
      ${reviewsHTML}
    </div>
    <div style="margin-top:20px;display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-primary" id="detailCompareBtn" onclick="window._toggleCompareFromDetail(${u.id})">
        ${State.isCompared(u.id) ? '✓ 已加入对比' : '🔄 加入对比'}
      </button>
      <button class="btn btn-ghost" onclick="window._showToast('${STR.FAVORITED}「${esc(u.cn)}」到你的关注列表')">⭐ 收藏</button>
      <button class="btn btn-ghost" onclick="openMethodology()">📋 评分方法论</button>
    </div>`;

  el('modalOverlay').classList.add('show');
  setTimeout(() => { const cb = el('modalClose'); if (cb) cb.focus(); }, 100);
  window.location.replace('#/' + State.page + '/' + u.rank);
}

/* ==== Methodology Modal ==== */
export function openMethodology() {
  const hero = el('modalHero');
  const body = el('modalBody');
  document.body.classList.add('scroll-locked');
  hero.innerHTML = `<h3 style="font-family:'Fraunces',serif;font-size:22px">📋 UniPulse 评分方法论</h3>`;
  body.innerHTML = `
    <p style="margin-bottom:20px;color:var(--text-soft);font-size:14px">UniPulse 综合评分基于公开数据和社区反馈，采用加权多维度模型。我们承诺：<strong>透明、公正、可验证</strong>。</p>
    <h4 style="font-size:15px;margin-bottom:12px">🧮 评分权重</h4>
    <div style="margin-bottom:20px">
      ${(DATA.ratingDims || []).map(d => `
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
          <span style="width:90px;text-align:right;font-size:13px">${esc(d.label)}</span>
          <div style="flex:1;height:8px;background:var(--bg);border-radius:4px;overflow:hidden"><div style="width:${d.weight * 4}%;height:100%;background:var(--gold);border-radius:4px"></div></div>
          <span style="width:36px;font-size:13px;font-weight:600">${d.weight}%</span>
        </div>`).join('')}
    </div>
    <h4 style="font-size:15px;margin-bottom:12px">📖 各维度说明</h4>
    <div style="font-size:13px;color:var(--text-soft);margin-bottom:20px">
      <p style="margin-bottom:8px"><strong style="color:var(--text)">学术水平：</strong>基于QS/ARWU学科排名、诺奖/菲尔兹奖得主数量。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">科研产出：</strong>Nature/Science发表量、论文引用率、科研经费。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">行业声誉：</strong>雇主调查 + LinkedIn数据。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">校园环境：</strong>Campus Quality评分、安全指数。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">学生关怀：</strong>心理咨询资源、住宿质量。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">国际化：</strong>国际生比例、合作论文比例。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">性价比：</strong>学费 vs 毕业后薪资增长。</p>
      <p style="margin-bottom:8px"><strong style="color:var(--text)">就业前景：</strong>就业率、起薪、顶级雇主校招。</p>
    </div>
    <h4 style="font-size:15px;margin-bottom:12px">⚠️ 已知局限性</h4>
    <div style="font-size:13px;color:var(--text-soft);margin-bottom:20px">
      <p style="margin-bottom:6px">• 部分高校的「学生关怀」和「就业前景」数据暂缺</p>
      <p style="margin-bottom:6px">• 评分模型对理工科大学有一定偏好</p>
      <p style="margin-bottom:6px">• 学生评价来自社区自愿提交，存在幸存者偏差</p>
      <p style="margin-bottom:6px">• 本平台评分仅供参考，选校决策请结合自身情况</p>
    </div>
    <p style="font-size:12px;color:var(--text-soft);padding:12px;background:var(--bg);border-radius:8px">📅 数据更新频率：综合评分每年1月/7月各更新一次。</p>`;
  el('modalOverlay').classList.add('show');
  setTimeout(() => { const cb = el('modalClose'); if (cb) cb.focus(); }, 100);
  window.location.replace('#/' + State.page + '/methodology');
}

/* ==== Forum Post Detail (API-backed) ==== */
async function openForumPostAsync(postId) {
  document.body.classList.add('scroll-locked');
  const hero = el('modalHero');
  const body = el('modalBody');
  hero.innerHTML = `<div style="text-align:center;padding:40px"><p>⏳ 加载帖子中...</p></div>`;
  body.innerHTML = '';
  el('modalOverlay').classList.add('show');
  window.location.replace('#/forum/' + postId);

  try {
    const resp = await fetch(`/api/v1/unipulse/forum/posts/${postId}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const post = await resp.json();

    const tags = Array.isArray(post.tags) ? post.tags : [];
    const comments = post.comments || [];
    const catName = post.category || post.cat || '';
    const replyCount = comments.length;

    hero.innerHTML = `<h3 style="font-family:'Fraunces',serif;font-size:20px">${esc(post.title)}</h3>`;

    const commentsHTML = comments.length > 0 ? comments.map(c => `
      <div class="review" style="border-left:3px solid var(--gold);padding-left:16px;margin-bottom:12px">
        <div class="review-author">${esc(c.author || '匿名用户')} <span style="font-size:11px;color:var(--text-soft)">${esc(c.created_at || c.time || '刚刚')}</span> <span style="color:var(--gold)">❤ ${c.likes || 0}</span></div>
        <div class="review-text">"${esc(c.text)}"</div>
      </div>`).join('') : '<p style="color:var(--text-soft);font-size:14px">暂无回复，快来抢沙发！</p>';

    body.innerHTML = `
      <div class="post-meta" style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid var(--border)">
        <span>👤 ${esc(post.author || '匿名用户')}</span>
        <span>🕐 ${esc(post.created_at || post.time || '刚刚')}</span>
        <span>💬 ${replyCount} 回复</span>
        <span>👁 ${post.views || 0} 浏览</span>
        <span class="tag">${esc(catName)}</span>
        ${tags.map(t => `<span class="tag blue">${esc(t)}</span>`).join('')}
      </div>
      <div class="post-content" style="font-size:14px;line-height:1.8;margin-bottom:24px">${post.content || ''}</div>
      <h4 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:12px">💬 回复（${replyCount}条）</h4>
      ${commentsHTML}
      <div style="margin-top:20px;padding:16px;background:var(--bg);border-radius:8px">
        <p style="font-size:13px;color:var(--text-soft);margin-bottom:8px">✍️ 发表回复</p>
        <textarea id="replyTextArea" placeholder="写下你的观点..." style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px;resize:vertical;min-height:80px;box-sizing:border-box" aria-label="回复内容"></textarea>
        <div style="display:flex;align-items:center;gap:8px;margin-top:8px">
          <input id="replyAuthorInput" placeholder="昵称（选填）" style="flex:1;padding:8px 10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px" aria-label="回复昵称">
          <button class="btn btn-primary" onclick="window._submitReply(${postId})">💬 提交回复</button>
        </div>
        <p id="replyStatus" style="font-size:12px;color:var(--green);margin-top:8px;display:none"></p>
      </div>`;
  } catch (e) {
    hero.innerHTML = `<h3>⚠️ 加载失败</h3>`;
    body.innerHTML = `<p style="color:var(--red)">无法加载帖子：${esc(e.message)}</p>`;
  }
}

/* ==== Submit Reply ==== */
window._submitReply = async function(postId) {
  const textarea = document.getElementById('replyTextArea');
  const authorInp = document.getElementById('replyAuthorInput');
  const statusEl = document.getElementById('replyStatus');
  const text = (textarea?.value || '').trim();
  if (!text) { showToast(STR.FORM_EMPTY); return; }

  const btn = document.querySelector('[onclick*="_submitReply"]');
  if (btn) { btn.disabled = true; btn.textContent = '发送中...'; }

  try {
    const resp = await fetch(`/api/v1/unipulse/forum/posts/${postId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, author: (authorInp?.value || '').trim() || '匿名用户' }),
    });
    if (!resp.ok) { const e = await resp.text(); throw new Error(e); }
    if (textarea) textarea.value = '';
    if (statusEl) { statusEl.textContent = STR.REPLY_SUCCESS; statusEl.style.display = 'block'; statusEl.style.color = 'var(--green)'; }
    setTimeout(() => openForumPostAsync(postId), 800);
  } catch (e) {
    if (statusEl) { statusEl.textContent = '❌ 失败: ' + esc(e.message); statusEl.style.display = 'block'; statusEl.style.color = 'var(--red)'; }
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '💬 提交回复'; }
  }
};

/* ==== New Post Form ==== */
export function showNewPostForm() {
  document.body.classList.add('scroll-locked');
  const hero = el('modalHero');
  const body = el('modalBody');
  hero.innerHTML = `<h3 style="font-family:'Fraunces',serif;font-size:20px">✏️ 发布新话题</h3>`;
  const catOptions = (DATA.forumCategories || []).filter(c => c.key !== 'all').map(c =>
    `<option value="${esc(c.key)}">${esc(c.label)}</option>`
  ).join('');
  body.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:12px">
      <input id="newPostTitle" placeholder="标题（必填）" maxlength="100"
        style="padding:10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:14px" aria-label="帖子标题">
      <div style="display:flex;gap:8px">
        <select id="newPostCategory" aria-label="话题分类" style="padding:8px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px">${catOptions}</select>
        <input id="newPostAuthor" placeholder="昵称（选填，默认匿名用户）" maxlength="20" style="flex:1;padding:8px 10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px" aria-label="发帖昵称">
      </div>
      <textarea id="newPostContent" placeholder="内容（必填）..." style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px;resize:vertical;min-height:140px;box-sizing:border-box" aria-label="帖子内容"></textarea>
      <p id="newPostStatus" style="font-size:12px;margin:0;display:none"></p>
      <button class="btn btn-primary" onclick="window._submitNewPost()" style="align-self:flex-start">📝 发布</button>
    </div>`;
  el('modalOverlay').classList.add('show');
  setTimeout(() => { const cb = document.getElementById('newPostTitle'); if (cb) cb.focus(); }, 150);
}

window._submitNewPost = async function() {
  const title = (document.getElementById('newPostTitle')?.value || '').trim();
  const content = (document.getElementById('newPostContent')?.value || '').trim();
  const category = document.getElementById('newPostCategory')?.value || '全部话题';
  const author = (document.getElementById('newPostAuthor')?.value || '').trim() || '匿名用户';
  const statusEl = document.getElementById('newPostStatus');
  if (!title || !content) { showToast(STR.POST_EMPTY); return; }

  const btn = document.querySelector('[onclick*="_submitNewPost"]');
  if (btn) { btn.disabled = true; btn.textContent = '发布中...'; }

  try {
    const resp = await fetch('/api/v1/unipulse/forum/posts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, category, author, tags: [] }),
    });
    if (!resp.ok) { const e = await resp.text(); throw new Error(e); }
    if (statusEl) { statusEl.textContent = STR.POST_SENT; statusEl.style.display = 'block'; statusEl.style.color = 'var(--green)'; }
    // Refresh forum data
    setTimeout(async () => {
      try {
        const posts = await refreshForumPosts();
        if (posts.length > 0) { DATA.forumPosts.splice(0, DATA.forumPosts.length, ...posts); }
      } catch {}
      document.body.classList.remove('scroll-locked');
      el('modalOverlay').classList.remove('show');
      renderForum();
      window.location.replace('#/forum');
    }, 1000);
  } catch (e) {
    if (statusEl) { statusEl.textContent = '❌ 失败: ' + esc(e.message); statusEl.style.display = 'block'; statusEl.style.color = 'var(--red)'; }
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '📝 发布'; }
  }
};

/* ==== Close Modal ==== */
export function closeModal(e) {
  if (e && e.target !== e.currentTarget) return;
  document.body.classList.remove('scroll-locked');
  el('modalOverlay').classList.remove('show');
  window.location.replace('#/' + State.page);
}

const Render = { renderPage, renderDiscover, renderRankings, renderPrograms, renderForum, openDetail, openMethodology, openForumPost: openForumPostAsync, closeModal, showNewPostForm };
export default Render;

/* Expose for inline onclick handlers */
window.openForumPost     = openForumPostAsync;
window.openMethodology   = openMethodology;
window.showNewPostForm   = showNewPostForm;