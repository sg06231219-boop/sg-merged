(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))o(i);new MutationObserver(i=>{for(const s of i)if(s.type==="childList")for(const r of s.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&o(r)}).observe(document,{childList:!0,subtree:!0});function n(i){const s={};return i.integrity&&(s.integrity=i.integrity),i.referrerPolicy&&(s.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?s.credentials="include":i.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function o(i){if(i.ep)return;i.ep=!0;const s=n(i);fetch(i.href,s)}})();const ne="modulepreload",re=function(e){return"/"+e},W={},x=function(t,n,o){let i=Promise.resolve();if(n&&n.length>0){let r=function(p){return Promise.all(p.map(f=>Promise.resolve(f).then(v=>({status:"fulfilled",value:v}),v=>({status:"rejected",reason:v}))))};document.getElementsByTagName("link");const a=document.querySelector("meta[property=csp-nonce]"),c=a?.nonce||a?.getAttribute("nonce");i=r(n.map(p=>{if(p=re(p),p in W)return;W[p]=!0;const f=p.endsWith(".css"),v=f?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${p}"]${v}`))return;const g=document.createElement("link");if(g.rel=f?"stylesheet":ne,f||(g.as="script"),g.crossOrigin="",g.href=p,c&&g.setAttribute("nonce",c),document.head.appendChild(g),f)return new Promise((Y,J)=>{g.addEventListener("load",Y),g.addEventListener("error",()=>J(new Error(`Unable to preload CSS for ${p}`)))})}))}function s(r){const a=new Event("vite:preloadError",{cancelable:!0});if(a.payload=r,window.dispatchEvent(a),!a.defaultPrevented)throw r}return i.then(r=>{for(const a of r||[])a.status==="rejected"&&s(a.reason);return t().catch(s)})},w="/api";async function $(e){const t=await fetch(e);if(!t.ok)throw new Error(`API error ${t.status}: ${e}`);return t.json()}function X(e){return{...e,cat:e.category||"全部话题",time:e.created_at||e.time||"刚刚",replies:e.replies??0,views:e.views??0,tags:Array.isArray(e.tags)?e.tags:e.tags?JSON.parse(e.tags):[],comments:(e.comments||[]).map(t=>({...t,time:t.created_at||t.time||"刚刚"}))}}function se(e){if(typeof e.metrics=="string")try{e.metrics=JSON.parse(e.metrics)}catch{e.metrics={}}if(typeof e.tags=="string")try{e.tags=JSON.parse(e.tags)}catch{e.tags=[]}return e}const[ie,ae,le,ce,de,pe]=await Promise.all([$(`${w}/universities`).catch(()=>[]),$(`${w}/dimensions`).catch(()=>[]),$(`${w}/programs`).catch(()=>[]),$(`${w}/forum/posts`).catch(()=>[]),$(`${w}/forum/categories`).catch(()=>[]),$(`${w}/forum/hot`).catch(()=>[])]),me=(ie||[]).map(se),ue=ae||[],fe=le||[],ve=(ce||[]).map(X),ge=(de||[]).map(e=>({key:e.key||e.category||"all",label:e.label||e.category||"全部话题",count:e.count||0})),ye=(pe||[]).map(e=>({text:e.text||e.title||"",views:e.views||0}));async function he(){return(await $(`${w}/forum/posts`)||[]).map(X)}const L={COMPARE_ADDED:"✅ 已加入对比列表",COMPARE_LIMIT:"⚠️ 最多同时对比4所高校",COMPARE_MIN:"⚠️ 请至少添加2所高校进行对比",COMPARE_ADD_HINT:"📋 点击高校卡片中的「加入对比」来添加",DEMO_MODE:"👤 演示模式 - 点击即用",NO_DATA:"暂无数据",POST_SENT:"✅ 发帖成功！",POST_EMPTY:"⚠️ 标题和内容不能为空",REPLY_SUCCESS:"✅ 回复成功！",FAVORITED:"⭐ 已收藏",FILTER_EMPTY:"😕 当前筛选条件下没有匹配的高校",FILTER_CLEAR:"清空筛选条件",POST_OPENING:"📖 正在打开帖子",FORM_EMPTY:"⚠️ 请填写内容"},be=[{author:"匿名用户",stars:4,text:"学术氛围很好，科研资源丰富。"},{author:"Sarah K.",stars:5,text:"校园美极了！教授都非常supportive。"},{author:"田中学",stars:4,text:"作为国际生，适应起来需要时间。学校国际学生办公室帮助很大。"}],m={universities:me,ratingDims:ue,programs:fe,forumPosts:ve,forumCategories:ge,hotTopics:ye,regions:["all","北美","欧洲","亚洲","大洋洲"],STR:L,univReviews:{},_defaultReviews:be};let I="discover",R="all",z="",h=[],Q="all",G=null;const S={};function P(e,t){(S[e]||[]).forEach(n=>n(t))}const d={get page(){return I},get region(){return R},get searchQuery(){return z},get compareList(){return[...h]},get forumCat(){return Q},setPage(e){if(e===I)return;document.querySelectorAll(".page").forEach(o=>o.classList.remove("active"));const t=document.getElementById("page-"+e);t&&t.classList.add("active"),document.querySelectorAll("#navLinks button").forEach(o=>{o.classList.remove("active"),o.removeAttribute("aria-current")});const n=document.querySelector(`#navLinks button[data-page="${e}"]`);n&&(n.classList.add("active"),n.setAttribute("aria-current","page")),I=e,P("page",e),x(()=>Promise.resolve().then(()=>E),void 0).then(o=>o.renderPage(e))},setRegion(e){R=e,P("region",e),x(()=>Promise.resolve().then(()=>E),void 0).then(t=>t.renderDiscover())},setSearch(e){clearTimeout(G),z=e,G=setTimeout(()=>{x(()=>Promise.resolve().then(()=>E),void 0).then(t=>t.renderDiscover())},300)},resetFilters(){R="all",z="";const e=document.getElementById("searchInput");e&&(e.value=""),document.querySelectorAll("#regionFilters .filter-tab").forEach(n=>{n.classList.remove("active"),n.setAttribute("aria-checked","false")});const t=document.querySelector('#regionFilters .filter-tab[data-region="all"]');t&&(t.classList.add("active"),t.setAttribute("aria-checked","true")),x(()=>Promise.resolve().then(()=>E),void 0).then(n=>n.renderDiscover())},addCompare(e){return h.includes(e)||h.length>=4?!1:(h.push(e),P("compare",h),!0)},removeCompare(e){const t=h.indexOf(e);t>-1&&h.splice(t,1),P("compare",h)},isCompared(e){return h.includes(e)},clearCompare(){h=[],P("compare",h)},setForumCat(e){Q=e,x(()=>Promise.resolve().then(()=>E),void 0).then(t=>t.renderForum())},on(e,t){S[e]=S[e]||[],S[e].push(t)}};function xe(){window.addEventListener("hashchange",K),K()}function K(){const t=(window.location.hash.slice(2)||"discover").split("/"),n=t[0];if(n==="compare"&&t[1]){we(t[1]);return}["discover","rankings","programs","forum"].includes(n)?F(n,!1):F("discover",!1)}function we(e){d.clearCompare(),e.split(",").map(Number).filter(n=>n>0).forEach(n=>d.addCompare(n)),d.setPage("discover"),x(()=>Promise.resolve().then(()=>_e),void 0).then(n=>n.default.doCompare())}function F(e,t=!0){t&&(window.location.hash="#/"+e),d.setPage(e)}const A={init:xe,navigate:F};function b(e){return document.getElementById(e)}function _(e){return String(e).replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}function Z(){const e=b("compareBar"),t=b("compareCount"),n=b("compareChips"),o=d.compareList;if(t&&(t.textContent=o.length),o.length===0){e&&(e.style.display="none");return}e&&(e.style.display="flex"),n&&(n.innerHTML=o.map(i=>{const s=m.universities.find(r=>r.id===i);return s?`<div class="compare-chip">${_(s.cn)} <span role="button" tabindex="0" aria-label="移除${_(s.cn)}" onclick="window._Compare.removeItem(${i})" onkeydown="if(event.key==='Enter')window._Compare.removeItem(${i})">✕</span></div>`:""}).join(""))}function ee(e){if(d.isCompared(e)){d.removeCompare(e);return}const t=d.addCompare(e);M(t?m.STR.COMPARE_ADDED:m.STR.COMPARE_LIMIT)}function $e(e){ee(e);const t=b("detailCompareBtn");t&&(t.textContent=d.isCompared(e)?"✓ 已加入对比":"🔄 加入对比")}function Ee(e){d.removeCompare(e)}function M(e){const t=b("toast");t&&(t.textContent=e,t.classList.add("show"),clearTimeout(t._t),t._t=setTimeout(()=>t.classList.remove("show"),2500))}async function Le(){const e=d.compareList;if(e.length<2){M(m.STR.COMPARE_MIN);return}const t=e.map(r=>m.universities.find(a=>a.id===r)).filter(Boolean);if(t.length<2)return;const n=b("modalBody"),o=b("modalHero");document.body.classList.add("scroll-locked"),o.innerHTML=`<h3 style="font-family:'Fraunces',serif;font-size:22px">🔄 高校对比</h3>`;const i=`<div class="compare-summary">${t.map(r=>`<div class="compare-summary-item"><div class="uni">${_(r.cn)}</div><div class="score">${_(r.score)}</div><div style="font-size:11px;color:var(--text-soft)">综合评分</div></div>`).join("")}</div>`;let s="";m.ratingDims.forEach(r=>{const a=t.map(v=>v.metrics[r.key]),c=Math.max(...a.filter(v=>v!=null)),p=Math.min(...a.filter(v=>v!=null)),f=c===p;s+=`<tr>
      <td style="padding:10px 14px;border-bottom:1px solid var(--border)">${_(r.label)}</td>
      ${t.map(v=>{const g=v.metrics[r.key];return g==null?`<td style="padding:10px 14px;border-bottom:1px solid var(--border);text-align:center;color:var(--text-soft)">${m.STR.NO_DATA}</td>`:`<td style="padding:10px 14px;border-bottom:1px solid var(--border);text-align:center" class="${g===c&&!f?"best":g===p&&!f?"worst":""}">${g}</td>`}).join("")}
    </tr>`}),n.innerHTML=`
    ${i}
    <div style="overflow-x:auto;margin-top:16px">
    <table class="compare-table">
      <thead><tr><th style="text-align:left">维度</th>${t.map(r=>`<th>${_(r.cn)}</th>`).join("")}</tr></thead>
      <tbody>${s}</tbody>
    </table></div>
    <p style="margin-top:16px;font-size:13px;color:var(--text-soft)">👑 = 该维度最高分 | 红色 = 该维度最低分</p>
    <div style="margin-top:20px;display:flex;gap:8px">
      <button class="btn btn-ghost" id="shareCompareBtn" onclick="window._shareCompare()">🔗 复制分享链接</button>
    </div>`,b("modalOverlay").classList.add("show"),setTimeout(()=>{const r=b("modalClose");r&&r.focus()},100),window.location.replace("#/discover/compare")}window._shareCompare=function(){const e=d.compareList;if(e.length<2)return;const t=window.location.origin+window.location.pathname+"#/compare/"+e.join(",");navigator.clipboard.writeText(t).then(()=>M("🔗 对比链接已复制到剪贴板！")).catch(()=>M("🔗 "+t))};d.on("compare",()=>{Z(),d.page==="discover"&&x(()=>Promise.resolve().then(()=>E),void 0).then(e=>e.renderDiscover())});const k={updateBar:Z,toggleItem:ee,toggleFromDetail:$e,removeItem:Ee,doCompare:Le},_e=Object.freeze(Object.defineProperty({__proto__:null,default:k},Symbol.toStringTag,{value:"Module"}));function u(e){return document.getElementById(e)}function l(e){return String(e).replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}function ke(e){return`<span class="tag ${e.type}">${l(e.text)}</span>`}function H(e){return e==null?'<span class="metric-na" title="暂无数据">--</span>':l(e)}function Te(e){return e==null?"var(--text-soft)":e>=85?"var(--green)":e>=70?"var(--gold)":"var(--red)"}function Ce(e){return e==null?"low":e>=85?"high":e>=70?"mid":"low"}function T(e){const t=u("toast");t&&(t.textContent=e,t.classList.add("show"),clearTimeout(t._t),t._t=setTimeout(()=>t.classList.remove("show"),2500))}function te(e){switch(e){case"discover":B();break;case"rankings":j();break;case"programs":q();break;case"forum":O();break}}function B(){const e=u("uniGrid"),t=u("noResults");if(!e)return;let n=m.universities;d.region!=="all"&&(n=n.filter(s=>s.region===d.region));const o=d.searchQuery.toLowerCase();if(o&&(n=n.filter(s=>s.name.toLowerCase().includes(o)||s.cn.includes(o)||s.loc.includes(o)||s.country.includes(o))),n.length===0){e.innerHTML="",t&&(t.style.display="block");return}t&&(t.style.display="none");const i=document.createDocumentFragment();n.forEach(s=>{const r=document.createElement("div");r.className="uni-card",r.setAttribute("role","button"),r.setAttribute("tabindex","0"),r.setAttribute("aria-label",`${s.cn} - 综合评分 ${s.score} 分`),r.addEventListener("click",()=>C(s.id)),r.addEventListener("keydown",p=>{(p.key==="Enter"||p.key===" ")&&(p.preventDefault(),C(s.id))});const a=d.isCompared(s.id)?" ✓ 已对比":"",c=s.metrics||{};r.innerHTML=`
      <div class="uni-card-header">
        <div class="uni-logo" style="background:${s.logo}" aria-hidden="true">${l(s.initials)}</div>
        <div class="uni-info">
          <h3>${l(s.cn)}${a}</h3>
          <div class="loc">${l(s.loc)}</div>
        </div>
        <div class="uni-rating">
          <span class="score">${l(s.score)}</span>
          <span class="max">/100</span>
        </div>
      </div>
      <div class="uni-tags">
        ${(s.tags||[]).map(ke).join("")}
      </div>
      <div class="uni-metrics">
        <div class="metric"><div class="metric-val">${H(c.academic)}</div><div class="metric-label">学术</div></div>
        <div class="metric"><div class="metric-val">${H(c.campus)}</div><div class="metric-label">校园</div></div>
        <div class="metric"><div class="metric-val">${H(c.career)}</div><div class="metric-label">就业</div></div>
      </div>`,i.appendChild(r)}),e.innerHTML="",e.appendChild(i)}function j(){const e=u("rankList");if(!e)return;const t=[...m.universities].sort((o,i)=>o.rank-i.rank),n=document.createDocumentFragment();t.forEach((o,i)=>{const s=document.createElement("div");s.className="rank-row",s.setAttribute("role","row"),s.setAttribute("tabindex","0"),s.setAttribute("aria-label",`第${o.rank}名 ${o.cn} 综合分${o.score}`),s.addEventListener("click",()=>C(o.id)),s.addEventListener("keydown",c=>{(c.key==="Enter"||c.key===" ")&&(c.preventDefault(),C(o.id))}),s.setAttribute("data-rank",o.rank);const r=o.trend==="up"?"📈":o.trend==="down"?"📉":"➡️",a=o.trend;s.innerHTML=`
      <span class="rank-pos ${i<3?"top":""}" role="cell">#${o.rank}</span>
      <span class="rank-name" role="cell">${l(o.cn)}<span class="sub">${l(o.name)}</span></span>
      <span class="rank-score" role="cell">${l(o.score)}</span>
      <span class="rank-trend ${a}" role="cell">${r} ${l(o.trendV)}</span>
      <span class="rank-country" role="cell">${l(o.country)}</span>
      <span class="rank-stars" role="cell">${"★".repeat(Math.round(o.stars))}${"☆".repeat(5-Math.round(o.stars))} ${o.stars}</span>`,n.appendChild(s)}),e.innerHTML="",e.appendChild(n)}function q(){const e=u("programsGrid");e&&(e.innerHTML=m.programs.map(t=>`
    <div class="prog-card" role="article" aria-label="${l(t.name)}学科排名">
      <h4>${t.icon||""} ${l(t.name)}</h4>
      ${(t.univs||[]).map(n=>`
      <div class="prog-univ">
        <div class="prog-rank ${n.tier||""}" aria-hidden="true">${n.rank}</div>
        <span class="prog-univ-name">${l(n.univ)}</span>
        <span style="font-size:12px;color:var(--text-soft)">#${n.rank}</span>
      </div>`).join("")}
    </div>`).join(""))}function O(){const e=u("forumPosts");if(!e)return;const t=d.forumCat;let n=t==="all"?m.forumPosts:m.forumPosts.filter(o=>o.cat===t);e.innerHTML=n.map(o=>`
    <div class="post-card">
      <div class="post-title">
        <button aria-label="打开帖子：${l(o.title)}" onclick="openForumPost(${o.id})">${l(o.title)}</button>
      </div>
      <div class="post-body" aria-hidden="true">${l((o.content||"").replace(/<[^>]*>/g,"").substring(0,120))}...</div>
      <div class="post-meta">
        <span>👤 ${l(o.author||"匿名用户")}</span>
        <span>🕐 ${l(o.time)}</span>
        <span>💬 ${o.replies||0} 回复</span>
        <span>👁 ${o.views||0} 浏览</span>
        <span class="tag">${l(o.cat||o.category||"")}</span>
        ${(o.tags||[]).slice(0,2).map(i=>`<span class="tag blue">${l(i)}</span>`).join("")}
      </div>
    </div>`).join(""),Pe()}function Pe(){const e=document.querySelector(".forum-hot");!e||e.querySelectorAll(".hot-item").length>0||(m.hotTopics||[]).forEach(n=>{const o=document.createElement("div");o.className="hot-item",o.setAttribute("tabindex","0"),o.innerHTML=`"${l(n.text)}" <span class="views">${l(n.views)} 浏览</span>`,e.appendChild(o)})}function C(e){const t=m.universities.find(a=>a.id===e);if(!t)return;document.body.classList.add("scroll-locked");const n=u("modalHero"),o=u("modalBody"),i=t.metrics||{};n.innerHTML=`
    <div class="detail-hero">
      <div class="detail-logo" style="background:${t.logo}" aria-hidden="true">${l(t.initials)}</div>
      <div>
        <h3 id="modalTitle">${l(t.cn)}</h3>
        <p>${l(t.name)} · ${l(t.loc)}</p>
      </div>
    </div>`;const r=(m.univReviews[t.id]||m._defaultReviews).map(a=>`
    <div class="review">
      <div class="review-author">${l(a.author)} ${"⭐".repeat(a.stars)}</div>
      <div class="review-text">"${l(a.text)}"</div>
    </div>`).join("");o.innerHTML=`
    <p style="margin-bottom:20px">${l(t.description||t.desc||"")}</p>
    <h4 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:12px">📊 多维评分</h4>
    <div class="rating-bars">
      ${(m.ratingDims||[]).map(a=>{const c=i[a.key],p=Ce(c),f=Te(c),v=c??L.NO_DATA,g=c??0;return`
          <div class="rating-bar">
            <span class="rating-label">${l(a.label)} <span style="font-size:10px;color:var(--text-soft)">${a.weight}%</span></span>
            <div class="rating-track"><div class="rating-fill ${p}" style="width:${g}%;background:${f}"></div></div>
            <span class="rating-val">${v}</span>
          </div>`}).join("")}
    </div>
    <div class="review-section">
      <h4>💬 学生评价（${t.reviews||0}条）</h4>
      ${r}
    </div>
    <div style="margin-top:20px;display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-primary" id="detailCompareBtn" onclick="window._toggleCompareFromDetail(${t.id})">
        ${d.isCompared(t.id)?"✓ 已加入对比":"🔄 加入对比"}
      </button>
      <button class="btn btn-ghost" onclick="window._showToast('${L.FAVORITED}「${l(t.cn)}」到你的关注列表')">⭐ 收藏</button>
      <button class="btn btn-ghost" onclick="openMethodology()">📋 评分方法论</button>
    </div>`,u("modalOverlay").classList.add("show"),setTimeout(()=>{const a=u("modalClose");a&&a.focus()},100),window.location.replace("#/"+d.page+"/"+t.rank)}function V(){const e=u("modalHero"),t=u("modalBody");document.body.classList.add("scroll-locked"),e.innerHTML=`<h3 style="font-family:'Fraunces',serif;font-size:22px">📋 UniPulse 评分方法论</h3>`,t.innerHTML=`
    <p style="margin-bottom:20px;color:var(--text-soft);font-size:14px">UniPulse 综合评分基于公开数据和社区反馈，采用加权多维度模型。我们承诺：<strong>透明、公正、可验证</strong>。</p>
    <h4 style="font-size:15px;margin-bottom:12px">🧮 评分权重</h4>
    <div style="margin-bottom:20px">
      ${(m.ratingDims||[]).map(n=>`
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
          <span style="width:90px;text-align:right;font-size:13px">${l(n.label)}</span>
          <div style="flex:1;height:8px;background:var(--bg);border-radius:4px;overflow:hidden"><div style="width:${n.weight*4}%;height:100%;background:var(--gold);border-radius:4px"></div></div>
          <span style="width:36px;font-size:13px;font-weight:600">${n.weight}%</span>
        </div>`).join("")}
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
    <p style="font-size:12px;color:var(--text-soft);padding:12px;background:var(--bg);border-radius:8px">📅 数据更新频率：综合评分每年1月/7月各更新一次。</p>`,u("modalOverlay").classList.add("show"),setTimeout(()=>{const n=u("modalClose");n&&n.focus()},100),window.location.replace("#/"+d.page+"/methodology")}async function U(e){document.body.classList.add("scroll-locked");const t=u("modalHero"),n=u("modalBody");t.innerHTML='<div style="text-align:center;padding:40px"><p>⏳ 加载帖子中...</p></div>',n.innerHTML="",u("modalOverlay").classList.add("show"),window.location.replace("#/forum/"+e);try{const o=await fetch(`/api/forum/posts/${e}`);if(!o.ok)throw new Error(`HTTP ${o.status}`);const i=await o.json(),s=Array.isArray(i.tags)?i.tags:[],r=i.comments||[],a=i.category||i.cat||"",c=r.length;t.innerHTML=`<h3 style="font-family:'Fraunces',serif;font-size:20px">${l(i.title)}</h3>`;const p=r.length>0?r.map(f=>`
      <div class="review" style="border-left:3px solid var(--gold);padding-left:16px;margin-bottom:12px">
        <div class="review-author">${l(f.author||"匿名用户")} <span style="font-size:11px;color:var(--text-soft)">${l(f.created_at||f.time||"刚刚")}</span> <span style="color:var(--gold)">❤ ${f.likes||0}</span></div>
        <div class="review-text">"${l(f.text)}"</div>
      </div>`).join(""):'<p style="color:var(--text-soft);font-size:14px">暂无回复，快来抢沙发！</p>';n.innerHTML=`
      <div class="post-meta" style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid var(--border)">
        <span>👤 ${l(i.author||"匿名用户")}</span>
        <span>🕐 ${l(i.created_at||i.time||"刚刚")}</span>
        <span>💬 ${c} 回复</span>
        <span>👁 ${i.views||0} 浏览</span>
        <span class="tag">${l(a)}</span>
        ${s.map(f=>`<span class="tag blue">${l(f)}</span>`).join("")}
      </div>
      <div class="post-content" style="font-size:14px;line-height:1.8;margin-bottom:24px">${i.content||""}</div>
      <h4 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:12px">💬 回复（${c}条）</h4>
      ${p}
      <div style="margin-top:20px;padding:16px;background:var(--bg);border-radius:8px">
        <p style="font-size:13px;color:var(--text-soft);margin-bottom:8px">✍️ 发表回复</p>
        <textarea id="replyTextArea" placeholder="写下你的观点..." style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px;resize:vertical;min-height:80px;box-sizing:border-box" aria-label="回复内容"></textarea>
        <div style="display:flex;align-items:center;gap:8px;margin-top:8px">
          <input id="replyAuthorInput" placeholder="昵称（选填）" style="flex:1;padding:8px 10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px" aria-label="回复昵称">
          <button class="btn btn-primary" onclick="window._submitReply(${e})">💬 提交回复</button>
        </div>
        <p id="replyStatus" style="font-size:12px;color:var(--green);margin-top:8px;display:none"></p>
      </div>`}catch(o){t.innerHTML="<h3>⚠️ 加载失败</h3>",n.innerHTML=`<p style="color:var(--red)">无法加载帖子：${l(o.message)}</p>`}}window._submitReply=async function(e){const t=document.getElementById("replyTextArea"),n=document.getElementById("replyAuthorInput"),o=document.getElementById("replyStatus"),i=(t?.value||"").trim();if(!i){T(L.FORM_EMPTY);return}const s=document.querySelector('[onclick*="_submitReply"]');s&&(s.disabled=!0,s.textContent="发送中...");try{const r=await fetch(`/api/forum/posts/${e}/comments`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:i,author:(n?.value||"").trim()||"匿名用户"})});if(!r.ok){const a=await r.text();throw new Error(a)}t&&(t.value=""),o&&(o.textContent=L.REPLY_SUCCESS,o.style.display="block",o.style.color="var(--green)"),setTimeout(()=>U(e),800)}catch(r){o&&(o.textContent="❌ 失败: "+l(r.message),o.style.display="block",o.style.color="var(--red)")}finally{s&&(s.disabled=!1,s.textContent="💬 提交回复")}};function D(){document.body.classList.add("scroll-locked");const e=u("modalHero"),t=u("modalBody");e.innerHTML=`<h3 style="font-family:'Fraunces',serif;font-size:20px">✏️ 发布新话题</h3>`;const n=(m.forumCategories||[]).filter(o=>o.key!=="all").map(o=>`<option value="${l(o.key)}">${l(o.label)}</option>`).join("");t.innerHTML=`
    <div style="display:flex;flex-direction:column;gap:12px">
      <input id="newPostTitle" placeholder="标题（必填）" maxlength="100"
        style="padding:10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:14px" aria-label="帖子标题">
      <div style="display:flex;gap:8px">
        <select id="newPostCategory" aria-label="话题分类" style="padding:8px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px">${n}</select>
        <input id="newPostAuthor" placeholder="昵称（选填，默认匿名用户）" maxlength="20" style="flex:1;padding:8px 10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px" aria-label="发帖昵称">
      </div>
      <textarea id="newPostContent" placeholder="内容（必填）..." style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);font-family:inherit;font-size:13px;resize:vertical;min-height:140px;box-sizing:border-box" aria-label="帖子内容"></textarea>
      <p id="newPostStatus" style="font-size:12px;margin:0;display:none"></p>
      <button class="btn btn-primary" onclick="window._submitNewPost()" style="align-self:flex-start">📝 发布</button>
    </div>`,u("modalOverlay").classList.add("show"),setTimeout(()=>{const o=document.getElementById("newPostTitle");o&&o.focus()},150)}window._submitNewPost=async function(){const e=(document.getElementById("newPostTitle")?.value||"").trim(),t=(document.getElementById("newPostContent")?.value||"").trim(),n=document.getElementById("newPostCategory")?.value||"全部话题",o=(document.getElementById("newPostAuthor")?.value||"").trim()||"匿名用户",i=document.getElementById("newPostStatus");if(!e||!t){T(L.POST_EMPTY);return}const s=document.querySelector('[onclick*="_submitNewPost"]');s&&(s.disabled=!0,s.textContent="发布中...");try{const r=await fetch("/api/forum/posts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:e,content:t,category:n,author:o,tags:[]})});if(!r.ok){const a=await r.text();throw new Error(a)}i&&(i.textContent=L.POST_SENT,i.style.display="block",i.style.color="var(--green)"),setTimeout(async()=>{try{const a=await he();a.length>0&&m.forumPosts.splice(0,m.forumPosts.length,...a)}catch{}document.body.classList.remove("scroll-locked"),u("modalOverlay").classList.remove("show"),O(),window.location.replace("#/forum")},1e3)}catch(r){i&&(i.textContent="❌ 失败: "+l(r.message),i.style.display="block",i.style.color="var(--red)")}finally{s&&(s.disabled=!1,s.textContent="📝 发布")}};function oe(e){e&&e.target!==e.currentTarget||(document.body.classList.remove("scroll-locked"),u("modalOverlay").classList.remove("show"),window.location.replace("#/"+d.page))}const Ae={renderPage:te,renderDiscover:B,renderRankings:j,renderPrograms:q,renderForum:O,openDetail:C,openMethodology:V,openForumPost:U,closeModal:oe,showNewPostForm:D};window.openForumPost=U;window.openMethodology=V;window.showNewPostForm=D;const E=Object.freeze(Object.defineProperty({__proto__:null,closeModal:oe,default:Ae,openDetail:C,openMethodology:V,renderDiscover:B,renderForum:O,renderPage:te,renderPrograms:q,renderRankings:j,showNewPostForm:D,showToast:T},Symbol.toStringTag,{value:"Module"}));window.State=d;window._showToast=T;window._toggleCompareFromDetail=function(e){k.toggleFromDetail(e),d.page==="discover"&&x(()=>Promise.resolve().then(()=>E),void 0).then(t=>t.renderDiscover())};window._Compare={removeItem:k.removeItem,doCompare:k.doCompare};function y(e){return document.getElementById(e)}document.addEventListener("DOMContentLoaded",()=>{document.querySelectorAll("#navLinks button").forEach(r=>{r.addEventListener("click",()=>A.navigate(r.dataset.page))});const e=document.querySelector(".logo");e&&(e.addEventListener("click",()=>A.navigate("discover")),e.addEventListener("keydown",r=>{(r.key==="Enter"||r.key===" ")&&(r.preventDefault(),A.navigate("discover"))})),y("regionFilters").addEventListener("click",r=>{const a=r.target.closest(".filter-tab");a&&(document.querySelectorAll("#regionFilters .filter-tab").forEach(c=>{c.classList.remove("active"),c.setAttribute("aria-checked","false")}),a.classList.add("active"),a.setAttribute("aria-checked","true"),d.setRegion(a.dataset.region))}),y("searchInput").addEventListener("input",()=>{d.setSearch(y("searchInput").value)}),y("searchInput").addEventListener("keydown",r=>{r.key==="Enter"&&(r.preventDefault(),d.setSearch(y("searchInput").value))}),y("catList").addEventListener("click",r=>{const a=r.target.closest("li");a&&(document.querySelectorAll("#catList li").forEach(c=>{c.classList.remove("active"),c.setAttribute("aria-selected","false")}),a.classList.add("active"),a.setAttribute("aria-selected","true"),d.setForumCat(a.dataset.cat))}),y("modalOverlay").addEventListener("click",r=>{r.target===y("modalOverlay")&&N(r)}),y("modalClose").addEventListener("click",()=>N()),document.addEventListener("keydown",r=>{r.key==="Escape"&&y("modalOverlay").classList.contains("show")&&N()}),y("compareToggle").addEventListener("click",()=>{if(d.compareList.length===0){T(m.STR.COMPARE_ADD_HINT);return}k.updateBar()}),y("doCompareBtn").addEventListener("click",k.doCompare),y("loginBtn").addEventListener("click",()=>T(m.STR.DEMO_MODE)),y("newPostBtn").addEventListener("click",()=>D());let t=!1;const n=y("hamburger");function o(){document.querySelector(".mobile-nav")?.remove(),document.querySelector(".mobile-nav-overlay")?.remove();const r=document.createElement("div");r.className="mobile-nav-overlay",r.addEventListener("click",s);const a=document.createElement("div");a.className="mobile-nav",document.querySelectorAll("#navLinks button").forEach(c=>{const p=document.createElement("button");p.className="btn btn-ghost",p.textContent=c.textContent,p.addEventListener("click",()=>{A.navigate(c.dataset.page),s()}),a.appendChild(p)}),document.body.appendChild(r),document.body.appendChild(a)}function i(){window.innerWidth>768||(o(),t=!0,n.classList.add("open"),n.setAttribute("aria-expanded","true"))}function s(){t=!1,n.classList.remove("open"),n.setAttribute("aria-expanded","false"),document.querySelector(".mobile-nav-overlay")?.remove(),document.querySelector(".mobile-nav")?.remove(),document.body.classList.remove("scroll-locked")}n.addEventListener("click",()=>{t?s():i()}),window.addEventListener("resize",()=>{window.innerWidth>768&&t&&s()}),A.init()});function N(e){e&&e.target!==e.currentTarget||(document.body.classList.remove("scroll-locked"),y("modalOverlay").classList.remove("show"),window.location.replace("#/"+d.page))}
