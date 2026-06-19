/* ===== UniPulse Data Layer (API-backed) ===== */
/* ES Module - fetches real data from FastAPI backend */

const API = '/api/v1/unipulse';

/**
 * Fetch JSON from API (relative URL, served by same FastAPI)
 */
export async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${url}`);
  return resp.json();
}

/**
 * Normalise forum post shape:
 *   API returns {category, created_at, ...}
 *   Render expects {cat, time, ...}
 */
function normalisePost(p) {
  return {
    ...p,
    cat: p.category || '全部话题',
    time: p.created_at || p.time || '刚刚',
    replies: p.replies ?? 0,
    views: p.views ?? 0,
    tags: Array.isArray(p.tags) ? p.tags : (p.tags ? JSON.parse(p.tags) : []),
    comments: (p.comments || []).map(c => ({
      ...c,
      time: c.created_at || c.time || '刚刚',
    })),
  };
}

/**
 * Normalise university shape:
 *   API returns {metrics: "{}", tags: "[]", ...}
 *   Render expects {metrics: {...}, tags: [...], ...}
 */
function normaliseUni(u) {
  if (typeof u.metrics === 'string') {
    try { u.metrics = JSON.parse(u.metrics); } catch { u.metrics = {}; }
  }
  if (typeof u.tags === 'string') {
    try { u.tags = JSON.parse(u.tags); } catch { u.tags = []; }
  }
  return u;
}

// ── Fetch all data on module load (top-level await) ──

const [
  rawUnis,
  rawDims,
  rawPrograms,
  rawPosts,
  rawCats,
  rawHot,
] = await Promise.all([
  fetchJSON(`${API}/universities`).catch(() => []),
  fetchJSON(`${API}/dimensions`).catch(() => []),
  fetchJSON(`${API}/programs`).catch(() => []),
  fetchJSON(`${API}/forum/posts`).catch(() => []),
  fetchJSON(`${API}/forum/categories`).catch(() => []),
  fetchJSON(`${API}/forum/hot`).catch(() => []),
]);

const universities = (rawUnis || []).map(normaliseUni);
const ratingDims   = rawDims || [];
const programs     = rawPrograms || [];
const forumPosts   = (rawPosts || []).map(normalisePost);
const forumCategories = (rawCats || []).map(c => ({
  key:  c.key  || c.category || 'all',
  label: c.label || c.category || '全部话题',
  count: c.count || 0,
}));
const hotTopics = (rawHot || []).map(h => ({
  text:  h.text || h.title || '',
  views: h.views || 0,
}));

// Refresh function: call this after creating new posts/comments
export async function refreshForumPosts() {
  const raw = await fetchJSON(`${API}/forum/posts`);
  return (raw || []).map(normalisePost);
}

/** Static strings (not from API) */
export const STR = {
  COMPARE_ADDED:      '✅ 已加入对比列表',
  COMPARE_LIMIT:       '⚠️ 最多同时对比4所高校',
  COMPARE_MIN:         '⚠️ 请至少添加2所高校进行对比',
  COMPARE_ADD_HINT:    '📋 点击高校卡片中的「加入对比」来添加',
  DEMO_MODE:           '👤 演示模式 - 点击即用',
  NO_DATA:             '暂无数据',
  POST_SENT:           '✅ 发帖成功！',
  POST_EMPTY:          '⚠️ 标题和内容不能为空',
  REPLY_SUCCESS:       '✅ 回复成功！',
  FAVORITED:           '⭐ 已收藏',
  FILTER_EMPTY:        '😕 当前筛选条件下没有匹配的高校',
  FILTER_CLEAR:        '清空筛选条件',
  POST_OPENING:         '📖 正在打开帖子',
  FORM_EMPTY:          '⚠️ 请填写内容',
};

/** Default reviews (used when no university-specific reviews exist) */
export const _defaultReviews = [
  { author: '匿名用户', stars: 4, text: '学术氛围很好，科研资源丰富。' },
  { author: 'Sarah K.', stars: 5, text: '校园美极了！教授都非常supportive。' },
  { author: '田中学',   stars: 4, text: '作为国际生，适应起来需要时间。学校国际学生办公室帮助很大。' },
];

/** Export the DATA object (same shape as before) */
export const DATA = {
  universities,
  ratingDims,
  programs,
  forumPosts,
  forumCategories,
  hotTopics,
  regions: ['all', '北美', '欧洲', '亚洲', '大洋洲'],
  STR,
  univReviews: {},
  _defaultReviews,
};

export default DATA;