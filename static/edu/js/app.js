/* ============================================================
   Multi-Agent Edu v6.0 - 核心应用逻辑
   挑战杯 XH-202630 · 7-Agent协同决策可视化
   ============================================================ */

// ============ 全局状态 ============
const AGENTS = ['diagnosis','knowledge_gen','reviewer','practice_guide','quiz','iteration','socratic'];
const AGENT_LABELS = {diagnosis:'学情诊断',knowledge_gen:'知识生成',reviewer:'审核裁判',practice_guide:'实操指南',quiz:'分阶测试',iteration:'迭代优化',socratic:'苏格拉底'};
const AGENT_ICONS = {diagnosis:'🔍',knowledge_gen:'📚',reviewer:'🔎',practice_guide:'🔧',quiz:'📝',iteration:'🔄',socratic:'💬'};
const AGENT_COLORS = {diagnosis:'#00e8b0',knowledge_gen:'#4da6ff',reviewer:'#ff6b6b',practice_guide:'#7c5cfc',quiz:'#ffb347',iteration:'#ff9cf5',socratic:'#00d4ff'};

let agentResults = {};
let quizData = null;
let timerInterval = null;
let startTime = 0;
let abortController = null;
let currentModel = localStorage.getItem('selected_model') || 'zhipu';
let currentApiKey = localStorage.getItem('api_key_'+currentModel) || '';

// SSE流式状态
let streamRunning = false;
let typewriterTimers = {}; // agent -> setTimeout id

// 辩论状态
let debateState = {round:0, maxRounds:2, scores:[], showing:false};
let debateAnimFrame = null;

// 拓扑Canvas状态
let topoNodes = [];       // {id, x, y, state:'idle'|'running'|'done', label}
let topoParticles = [];   // {from, to, progress, speed, color}
let topoAnimFrame = null;
let topoCtx = null;

// 对话历史
let globalChatHistory = [];

// ============ 欢迎引导 ============
(function initOnboarding(){
  const overlay = document.getElementById('onboarding');
  if(!overlay) return;
  const steps = overlay.querySelectorAll('.ob-step');
  const dots = overlay.querySelectorAll('.ob-dots span');
  const btn = document.getElementById('obNext');
  if(!btn) return;
  let cur = 0;
  btn.onclick = () => {
    cur++;
    if(cur >= steps.length){ overlay.classList.add('hidden'); return; }
    steps.forEach((s,i)=>s.classList.toggle('active',i===cur));
    dots.forEach((d,i)=>d.classList.toggle('active',i===cur));
    if(cur === steps.length-1) btn.textContent = '开始体验 →';
  };
  // 5秒无操作自动进入
  setTimeout(()=>{ if(!overlay.classList.contains('hidden')) overlay.classList.add('hidden'); }, 8000);
})();

// ============ 拓扑Canvas ============
function initTopology(){
  const canvas = document.getElementById('topoCanvas');
  if(!canvas) return;
  topoCtx = canvas.getContext('2d');
  resizeTopology();
  window.addEventListener('resize', resizeTopology);
  // 定义7个节点的U型布局
  const nodes = [
    {id:'diagnosis',     label:'诊断'},
    {id:'knowledge_gen', label:'生成'},
    {id:'reviewer',      label:'审核'},
    {id:'practice_guide',label:'实操'},
    {id:'quiz',          label:'测试'},
    {id:'iteration',     label:'迭代'},
    {id:'socratic',      label:'导学'},
  ];
  topoNodes = nodes.map((n,i) => ({
    ...n,
    x: 0, y: 0,
    state: 'idle',
    icon: AGENT_ICONS[n.id],
  }));
  drawTopology();
  startTopologyAnim();
}

function resizeTopology(){
  const canvas = document.getElementById('topoCanvas');
  if(!canvas) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  repositionNodes();
  drawTopology();
}

function repositionNodes(){
  const canvas = document.getElementById('topoCanvas');
  if(!canvas || !topoNodes.length) return;
  const w = canvas.width, h = canvas.height;
  const cx = w/2;
  // 7节点: 3上(诊断/生成/审核) + 1中间(实操) + 3下(测试/迭代/导学)
  const positions = [
    {x: cx - 180, y: h * 0.25},  // diagnosis
    {x: cx,       y: h * 0.15},  // knowledge_gen (center top)
    {x: cx + 180, y: h * 0.25},  // reviewer
    {x: cx,       y: h * 0.5},   // practice_guide (center)
    {x: cx - 150, y: h * 0.75},  // quiz
    {x: cx,       y: h * 0.88},  // iteration (center bottom)
    {x: cx + 150, y: h * 0.75},  // socratic
  ];
  topoNodes.forEach((n,i) => {
    n.x = positions[i].x;
    n.y = positions[i].y;
  });
}

function startTopologyAnim(){
  if(topoAnimFrame) cancelAnimationFrame(topoAnimFrame);
  let lastTime = 0;
  function loop(ts){
    const dt = ts - lastTime;
    lastTime = ts;
    // 更新粒子
    updateParticles(dt);
    // 绘制
    drawTopology();
    topoAnimFrame = requestAnimationFrame(loop);
  }
  topoAnimFrame = requestAnimationFrame(loop);
}

function updateParticles(dt){
  // 更新辩论粒子（知识生成<->审核之间的双向粒子）
  const debateNode1 = topoNodes.find(n=>n.id==='knowledge_gen');
  const debateNode2 = topoNodes.find(n=>n.id==='reviewer');
  if(!debateNode1 || !debateNode2) return;
  // 辩论时：增加双向红色粒子
  if(debateState.showing && debateState.round > 0){
    // 添加新粒子（随机方向）
    if(Math.random() < 0.08){
      topoParticles.push({
        from: Math.random()<0.5 ? 'knowledge_gen' : 'reviewer',
        to:   Math.random()<0.5 ? 'reviewer' : 'knowledge_gen',
        progress: Math.random(),
        speed: 0.003 + Math.random()*0.002,
        color: '#ff6b6b',
        size: 2 + Math.random()*2,
      });
    }
  }
  // 移动粒子
  topoParticles = topoParticles.filter(p => {
    const dir = p.from === 'knowledge_gen' ? 1 : -1;
    p.progress += p.speed * dir;
    return p.progress >= 0 && p.progress <= 1;
  });
}

function drawTopology(){
  if(!topoCtx) return;
  const canvas = topoCtx.canvas;
  const w = canvas.width, h = canvas.height;
  topoCtx.clearRect(0, 0, w, h);

  // 背景网格
  topoCtx.strokeStyle = 'rgba(30,40,70,0.3)';
  topoCtx.lineWidth = 0.5;
  const gridSize = 30;
  for(let x=0; x<w; x+=gridSize){ topoCtx.beginPath(); topoCtx.moveTo(x,0); topoCtx.lineTo(x,h); topoCtx.stroke(); }
  for(let y=0; y<h; y+=gridSize){ topoCtx.beginPath(); topoCtx.moveTo(0,y); topoCtx.lineTo(w,y); topoCtx.stroke(); }

  // 连接线：顺序流程
  const flowOrder = ['diagnosis','knowledge_gen','reviewer','practice_guide','quiz','iteration','socratic'];
  topoCtx.lineWidth = 1.5;
  for(let i=0; i<flowOrder.length-1; i++){
    const from = topoNodes.find(n=>n.id===flowOrder[i]);
    const to   = topoNodes.find(n=>n.id===flowOrder[i+1]);
    if(!from || !to) continue;
    const isActive = from.state==='running' || from.state==='done';
    const lit = from.state==='done';
    topoCtx.strokeStyle = lit ? 'rgba(0,232,176,0.4)' : 'rgba(26,39,68,0.8)';
    topoCtx.beginPath();
    topoCtx.moveTo(from.x, from.y);
    topoCtx.lineTo(to.x, to.y);
    topoCtx.stroke();
  }

  // 辩论双向连线（知识生成 ↔ 审核）
  const n1 = topoNodes.find(n=>n.id==='knowledge_gen');
  const n2 = topoNodes.find(n=>n.id==='reviewer');
  if(n1 && n2){
    topoCtx.strokeStyle = debateState.showing ? 'rgba(255,107,107,0.6)' : 'rgba(255,107,107,0.15)';
    topoCtx.lineWidth = debateState.showing ? 2 : 1;
    topoCtx.setLineDash([5,5]);
    topoCtx.beginPath();
    topoCtx.moveTo(n1.x, n1.y);
    topoCtx.lineTo(n2.x, n2.y);
    topoCtx.stroke();
    topoCtx.setLineDash([]);

    // 辩论粒子
    topoParticles.forEach(p => {
      const pf = topoNodes.find(n=>n.id===p.from);
      const pt = topoNodes.find(n=>n.id===p.to);
      if(!pf || !pt) return;
      const x = pf.x + (pt.x - pf.x) * p.progress;
      const y = pf.y + (pt.y - pf.y) * p.progress;
      topoCtx.beginPath();
      topoCtx.arc(x, y, p.size, 0, Math.PI*2);
      topoCtx.fillStyle = p.color + 'cc';
      topoCtx.fill();
    });
  }

  // 绘制节点
  topoNodes.forEach(node => {
    const isRunning = node.state === 'running';
    const isDone = node.state === 'done';
    const isDebate = (node.id==='knowledge_gen' || node.id==='reviewer') && debateState.showing;
    const color = AGENT_COLORS[node.id] || '#00e8b0';
    const r = 28;

    // 发光效果
    if(isRunning || isDebate){
      topoCtx.shadowBlur = 20;
      topoCtx.shadowColor = color;
    } else if(isDone){
      topoCtx.shadowBlur = 12;
      topoCtx.shadowColor = '#00e8b0';
    } else {
      topoCtx.shadowBlur = 0;
    }

    // 节点圆
    topoCtx.beginPath();
    topoCtx.arc(node.x, node.y, r, 0, Math.PI*2);
    topoCtx.fillStyle = isDone ? 'rgba(0,232,176,0.15)' : isRunning ? color+'22' : 'rgba(13,20,36,0.9)';
    topoCtx.fill();
    topoCtx.strokeStyle = isDone ? '#00e8b0' : isRunning ? color : 'rgba(26,39,68,0.8)';
    topoCtx.lineWidth = isRunning ? 2 : 1.5;
    topoCtx.stroke();

    // 脉冲环（运行中）
    if(isRunning){
      const pulse = (Date.now() % 1500) / 1500;
      topoCtx.beginPath();
      topoCtx.arc(node.x, node.y, r + pulse*15, 0, Math.PI*2);
      topoCtx.strokeStyle = color+'44';
      topoCtx.lineWidth = 1.5;
      topoCtx.stroke();
    }

    topoCtx.shadowBlur = 0;

    // 节点图标
    topoCtx.font = '14px serif';
    topoCtx.textAlign = 'center';
    topoCtx.textBaseline = 'middle';
    topoCtx.fillText(node.icon, node.x, node.y - 2);

    // 节点标签
    topoCtx.font = '9px -apple-system,Segoe UI,sans-serif';
    topoCtx.fillStyle = isRunning ? color : isDone ? '#00e8b0' : '#7a869e';
    topoCtx.fillText(node.label, node.x, node.y + 18);

    // 状态小点
    if(isRunning){
      topoCtx.beginPath();
      topoCtx.arc(node.x+r-4, node.y-r+4, 4, 0, Math.PI*2);
      topoCtx.fillStyle = color;
      topoCtx.fill();
    } else if(isDone){
      topoCtx.beginPath();
      topoCtx.arc(node.x+r-4, node.y-r+4, 4, 0, Math.PI*2);
      topoCtx.fillStyle = '#00e8b0';
      topoCtx.fill();
      topoCtx.font = '7px sans-serif';
      topoCtx.fillStyle = '#060b18';
      topoCtx.fillText('✓', node.x+r-4, node.y-r+5);
    }
  });
}

function setTopoNode(id, state){
  const n = topoNodes.find(n=>n.id===id);
  if(n) n.state = state;
  drawTopology();
}

// ============ 模型 & API Key ============
function showModelModal(){ document.getElementById('modelModal').classList.add('show'); document.getElementById('modelSelect').value = currentModel; }
function closeModelModal(){ document.getElementById('modelModal').classList.remove('show'); }
function confirmModel(){
  currentModel = document.getElementById('modelSelect').value;
  localStorage.setItem('selected_model', currentModel);
  document.getElementById('btnModel').textContent = '🤖 '+{deepseek:'DeepSeek',zhipu:'GLM','openai-compat':'OpenAI'}[currentModel];
  closeModelModal();
  log('🤖 模型：'+currentModel,'info');
  currentApiKey = '';
  localStorage.removeItem('api_key_'+currentModel);
}

function showApiKeyModal(){
  document.getElementById('apiKeyModal').classList.add('show');
  document.getElementById('apiKeyInput').value = currentApiKey ? '••••••••' : '';
  document.getElementById('apiKeyError').style.display = 'none';
  const hints = {
    deepseek: 'DeepSeek Key（sk-开头）<br>platform.deepseek.com获取，免费额度充足',
    zhipu: '智谱Key格式：{id}.{secret}<br>open.bigmodel.cn获取',
    'openai-compat': '输入API Key+Base URL'
  };
  document.getElementById('apiKeyHint').innerHTML = hints[currentModel] || '';
}
function closeApiKeyModal(){ document.getElementById('apiKeyModal').classList.remove('show'); }
function skipApiKey(){
  currentApiKey = '';
  closeApiKeyModal();
  log('⚠️ Demo模式（无真实AI）','warn');
}
async function confirmApiKey(){
  const input = document.getElementById('apiKeyInput').value.trim();
  const errEl = document.getElementById('apiKeyError');
  if(!input || input==='••••••••'){ errEl.textContent='请输入Key'; errEl.style.display='block'; return; }
  currentApiKey = input;
  localStorage.setItem('api_key_'+currentModel, input);
  try {
    const ok = await testApiKey();
    if(ok){ log('✅ Key有效','success'); closeApiKeyModal(); }
    else { errEl.textContent='Key验证失败'; errEl.style.display='block'; }
  } catch(e){ errEl.textContent=e.message; errEl.style.display='block'; }
}
async function testApiKey(){
  if(currentModel==='deepseek') return await callDeepSeek('hi', true);
  if(currentModel==='zhipu') return await callZhipu('hi', true);
  return false;
}

// ============ LLM调用（保留所有模型） ============
async function callLLM(sys, user, onChunk){
  if(!currentApiKey) throw new Error('NoKey');
  if(currentModel==='deepseek') return await callDeepSeekStream(sys, user, onChunk);
  if(currentModel==='zhipu') return await callZhipuStream(sys, user, onChunk);
  return await callOpenAICompatStream(sys, user, onChunk);
}

async function callDeepSeekStream(sys, user, onChunk){
  abortController = new AbortController();
  const resp = await fetch('https://api.deepseek.com/chat/completions',{
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+currentApiKey},
    body: JSON.stringify({model:'deepseek-chat',messages:[{role:'system',content:sys},{role:'user',content:user}],temperature:parseFloat(document.getElementById('vTemp')?.textContent||'0.3'),stream:true}),
    signal: abortController.signal
  });
  if(!resp.ok) throw new Error('DeepSeek '+resp.status);
  return streamRead(resp, onChunk);
}

async function callZhipuStream(sys, user, onChunk){
  abortController = new AbortController();
  const parts = currentApiKey.split('.');
  if(parts.length<2) throw new Error('Zhipu Key格式错误');
  const token = await genJwt(parts[0], parts.slice(1).join('.'));
  const resp = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions',{
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
    body: JSON.stringify({model:'glm-4-flash',messages:[{role:'system',content:sys},{role:'user',content:user}],temperature:parseFloat(document.getElementById('vTemp')?.textContent||'0.3'),stream:true}),
    signal: abortController.signal
  });
  if(!resp.ok) throw new Error('Zhipu '+resp.status);
  return streamRead(resp, onChunk);
}

async function callOpenAICompatStream(sys, user, onChunk){
  abortController = new AbortController();
  const baseUrl = localStorage.getItem('openai_compat_base_url')||'https://api.openai.com/v1';
  const model = localStorage.getItem('openai_compat_model')||'gpt-3.5-turbo';
  const resp = await fetch(baseUrl+'/chat/completions',{
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+currentApiKey},
    body: JSON.stringify({model,messages:[{role:'system',content:sys},{role:'user',content:user}],stream:true}),
    signal: abortController.signal
  });
  if(!resp.ok) throw new Error('OpenAI '+resp.status);
  return streamRead(resp, onChunk);
}

async function streamRead(resp, onChunk){
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf='', full='';
  while(true){
    const {done,value} = await reader.read();
    if(done) break;
    buf += dec.decode(value,{stream:true});
    const lines = buf.split('\n');
    buf = lines.pop()||'';
    for(const line of lines){
      if(line.startsWith('data: ')){
        const d = line.slice(6);
        if(d==='[DONE]') continue;
        try {
          const j = JSON.parse(d);
          const ch = (j.choices?.[0]?.delta?.content)||'';
          full += ch;
          if(ch && onChunk) onChunk(ch);
        }catch(e){}
      }
    }
  }
  return full;
}

async function genJwt(id, sec){
  const h = btoa(JSON.stringify({alg:'HS256',sign_type:'SIGN'})).replace(/=+$/,'');
  const t = Math.floor(Date.now()/1000);
  const p = btoa(JSON.stringify({api_key:id,exp:t+3600,timestamp:t})).replace(/=+$/,'');
  const sig = await hmacSha256(h+'.'+p, sec);
  return h+'.'+p+'.'+sig;
}
async function hmacSha256(msg, key){
  const enc = new TextEncoder();
  const k = await crypto.subtle.importKey('raw',enc.encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const sig = await crypto.subtle.sign('HMAC',k,enc.encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}

async function callDeepSeek(prompt, test){
  try{const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+currentApiKey},body:JSON.stringify({model:'deepseek-chat',messages:[{role:'user',content:prompt}],max_tokens:5})});return r.ok;}catch(e){return false;}
}
async function callZhipu(prompt, test){
  try{const p=currentApiKey.split('.');if(p.length<2)return false;const t=await genJwt(p[0],p.slice(1).join('.'));const r=await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+t},body:JSON.stringify({model:'glm-4-flash',messages:[{role:'user',content:prompt}],max_tokens:5})});return r.ok;}catch(e){return false;}
}

// ============ Prompt构建 ============
function buildPrompts(agentName, context){
  const p = getProfile();
  if(agentName==='diagnosis') return {
    system:`你是林教授——教了18年编程的大学老师，说话一针见血不留情面。最烦"多练习就好"这种废话。
⚠️ 绝对禁止："首先其次最后"三段式八股、"需要加强XX基础"类套话、"综上所述"
你说话方式："你的问题不是'基础薄弱'——谁的基础不薄弱了？你真实的问题是XX"
先在心里分析：ta的学习目标和实际水平之间最大的鸿沟在哪？如果只能给ta一条建议，是什么？ta最可能在哪个环节放弃？
输出JSON：
{"learner_level":"beginner|intermediate|advanced","level_score":0-100,"raw_truth":"一针见血指出真正弱点(50字)","strengths":["已有且能马上转化为学习杠杆的东西"],"blind_spots":["用'你不知道你不知道XX'格式，点出元认知盲区"],"focus_topic":"最该优先攻克的主题(只要一个)","red_flag":"如果只给你一条建议：XX(尖锐、像朋友劝你)","learning_path":[{"phase":"阶段名(要有性格，别叫'基础入门')","topics":["主题"],"estimated_hours":学时,"why_this_matters":"做这件事到底有什么用"}],"summary":"一句话概括(40字)"}`,
    user:`又来一个学习者，帮我看看——
背景：${p.background}
编程经验：${p.experience}
学习目标：${p.goal}
自评水平：${p.level}
别给ta"需要系统学习"的废话，说ta真正需要听到的。JSON输出。`
  };
  if(agentName==='knowledge_gen') return {
    system:`你是阿坤——GitHub混了10年的野生程序员，对教科书深恶痛绝。信条：一个概念如果不能用一个6岁小孩都能懂的类比讲清楚，就说明你没真懂。
⚠️ 禁止："首先了解XX定义"、Markdown标题叫"概述/核心内容"、"在实际开发中"、"有助于提升"、import xx占位符
说话方式："今天不讲虚的。就说一个事——XX到底为什么有时候'丢'元素..."
结构：反直觉例子开头→类比讲核心原理→一个"教科书不会告诉你的事实"→代码注释要有性格
JSON：{"title":"别用'XX基础教程'——用'XX：90%的人搞错的那个概念'","hook":"反直觉引子(1-3句)","content":"完整内容(Markdown,800-1500字,像博客不像教材)","hidden_truth":"官方文档不会告诉你的事实/技巧","source_refs":[{"id":"引用","source":"来源文件","type":"[教材]|[官方]|[论文]|[实践]","relevance":"说明"}],"concepts":["概念(口语化命名)"],"examples":["示例"],"extensions":["想深入？给具体链接/书名"],"summary":"像推荐文章那样写50字摘要"}`,
    user:`学情诊断：${JSON.stringify(context.diagnosis||{})}
知识库参考：${(context.kb_content||'暂无').slice(0,1500)}
${context.revision_hints?'\n⚠️ 审核指出：'+JSON.stringify(context.revision_hints)+'请针对性修正。':''}
像写博客一样写，别像写教材。JSON。`
  };
  if(agentName==='reviewer') return {
    system:`你是老周——15年技术审稿人，一眼看出教程里的水分。座右铭："看起来没问题的内容，往往最危险。"
⚠️ 禁止："整体质量不错"——觉得没问题说明没认真看；"建议补充更多示例"——这是敷衍；"内容结构清晰"——没人审稿关心结构
说话像挑剔的同行："这段代码在Python 3.12下会报错你知道吗？你测过吗？"
第1轮至少找出3个问题，找不到说明没认真看。第2轮检查上一轮问题是否真的被修正了。
JSON：{"verdict":"pass_with_concerns|needs_revision|reject","hallucination_score":0-100(第1轮不要低于25),"accuracy_score":0-100,"most_egregious":"如果只让说一个问题，你最想骂哪点？(1句话)","issues":[{"type":"factual_error|logical_flaw|missing_source|industry_violation|bad_practice","description":"直接说","severity":"high|medium|low","suggestion":"给具体方案"}],"strengths":["说真话，没有就写'暂无显著优点'"],"summary":"30字犀利总结"}`,
    user:`审核第${context.debate_round||1}轮：
--- 内容 ---
${(context.content||'').slice(0,2000)}
--- 来源 ---
${JSON.stringify(context.source_refs||[])}
严格评估，至少3个问题。JSON。`
  };
  if(agentName==='practice_guide') return {
    system:`你是大刘——BAT干了12年的老程序员，带过30多个实习生。不讲最佳实践，讲血泪教训。
⚠️ 禁止："第一步：环境准备"——烦不烦；"第二步：编写代码"——不是步骤是废话；代码注释"# 定义一个变量"——删掉，写有用的
风格："别直接写代码。先想3分钟——数据长什么样？数据量突然变100倍，方案还撑得住吗？"
每步：真实可跑代码+"我当年掉过的坑"(具体教训)+不做这步会怎样
JSON：{"title":"有动作感的标题","difficulty":"easy|medium|hard","estimated_time":"预计时间(分钟)","steps":[{"step":1,"title":"步骤","why":"为什么做这步——后果前置","description":"详细说明","code":"真实可运行代码","pitfall":"我踩过的坑：XX","tip":"一句话技巧"}],"project_idea":"具体到能用的小工具","common_mistakes":["用'我见过有人XX然后YY'的叙事"],"summary":"像同事交接工作时说的50字"}`,
    user:`主题：${context.topic||'Python基础'}
水平：${p.level}
写一个实操指南，像老兵带新兵。JSON。`
  };
  if(agentName==='quiz') return {
    system:`你是陈姐——大厂技术面试官，面过2000+候选人。你的题让人想3秒然后发现"我以为我会了"。
⚠️ 禁止："Python中用什么关键字定义函数"——这是背API；"以下哪个是正确的"+3个明显荒谬选项——测视力不是测理解
好的选择题=所有选项看起来都有道理+只有真正理解才能选对
JSON：{"quiz_title":"测试标题(别叫'XX测试题'——叫'来，看看你是真懂还是假懂'这样)","difficulty":"easy|medium|hard","questions":[{"id":1,"type":"choice","difficulty":"easy|medium|hard","question":"题目(场景或陷阱题)","options":["A.看起来对但错","B.正确答案","C.常见误解","D.另一个看起来对的"],"correct":索引0-3,"trap":"这题的陷阱在哪","interviewer_note":"面试官点评：XX(口语化)","knowledge_point":"考察知识点"}],"total_score":100,"passing_score":60,"summary":"像面试官看完答题后的评价(50字)"}
重要：correct是0-3数字！全部choice类型！`,
    user:`知识内容：${(context.knowledge?.content||'').slice(0,1500)}
核心概念：${JSON.stringify(context.knowledge?.concepts||[])}
难度：${p.level}
出5道有陷阱的好题(2easy+2medium+1hard)。JSON。`
  };
  if(agentName==='iteration') return {
    system:`你是赵教练——不教技术，教怎么学。看过太多人：学3个月原地踏步、刷200道题不知道在刷什么。
你的价值不是"多练练"——是看出瓶颈点在哪，给一个具体可立刻执行的动作。
⚠️ 禁止："建议加强XX基础"——说具体；"持续学习"——浪费时间
风格："正确率60%，但真正问题是——答错的3道题全是同一类(XX理解不够)。补那个，别补别的。"
决策：<60%→降维；60-80%→定点突破错题知识点；>80%→给下一个具体学什么
JSON：{"decision":"simplify|consolidate|advance","decision_label":"降维解释|定点突破|进阶挑战","reason":"用'核心问题是XX，因为YY'句式","one_thing":"只做一件事：XX(明天就能做的具体动作)","adjustments":{"difficulty_shift":-2到+2,"focus_topics":["只列1-2个"],"skip_topics":["暂时放掉"],"new_approach":"具体怎么换"},"next_steps":[{"step":1,"action":"行动","agent":"负责Agent","description":"量化说明(多长时间、做多少)"}],"summary":"30字教练总结"}`,
    user:`测验结果：${JSON.stringify(context.quiz_result||{})}
学情诊断：${JSON.stringify(context.diagnosis||{})}
已学内容：${JSON.stringify(context.knowledge?.title||'')}
做出迭代决策。JSON。`
  };
  if(agentName==='socratic') return {
    system:`你是小苏——学哲学转码的怪人。不会好好回答问题，只会反问。口头禅："为什么？再想想。真的吗？"
你不是老师，是好奇心过剩的朋友。永远不给答案，只给下一个问题。
⚠️ 禁止："很好！你的回答很有深度"——不要像老师；"让我们回顾XX"——不是在做总结；给答案——你永不直接给答案
追问方式："你刚说的——如果条件反过来，还会成立吗？" / "我给你讲个极端情况：如果XX变成YY..."
追问层次（自然递进不要标注）：理解→应用(给没见过场景)→分析(为什么不是另一种方案)→评价(在什么情况下你的理解就错了)
JSON：{"title":"带追问的学习内容标题","sections":[{"content":"知识点(≤3句)","question":"让人停下来想的问题","hint":"想不出往这方向想(不给答案)","depth":"understanding|application|analysis|evaluation","follow_ups":["答对了问什么","答错了从什么角度引导"]}],"reflection_prompts":["'你以为你懂了吗？试试这个'"],"summary":"30字导学总结"}`,
    user:`学习主题：${context.knowledge?.title||'编程基础'}
核心概念：${JSON.stringify(context.knowledge?.concepts||[])}
内容摘要：${(context.knowledge?.content||'').slice(0,1000)}
设计启发式追问节点。JSON。`
  };
  return {system:'',user:''};
}

function parseLLMOutput(text){
  if(!text) return {};
  let c = text.trim();
  const m = c.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if(m) c = m[1].trim();
  try{return JSON.parse(c);}catch(e){}
  const s = c.indexOf('{'), e = c.lastIndexOf('}');
  if(s>=0 && e>s){try{return JSON.parse(c.slice(s,e+1));}catch(e){}}
  try{return JSON.parse(c.replace(/'/g,'"').replace(/,\s*\}/g,'}').replace(/,\s*\]/g,']'));}catch(e){}
  return {content:text,_parse_error:'解析失败'};
}

// ============ 获取画像 ============
function getProfile(){
  return{
    background: document.getElementById('inpBg')?.value||'',
    experience: document.getElementById('inpExp')?.value||'',
    goal: document.getElementById('inpGoal')?.value||'',
    level: document.getElementById('inpLvl')?.value||'intermediate'
  };
}

// ============ 全流程启动（SSE优先，回退逐Agent） ============
async function startPipeline(){
  const p = getProfile();
  if(!p.background.trim()){ alert('请填写背景描述'); return; }
  if(!currentApiKey){
    log('⚠️ 无Key，进入Demo模式','warn');
    return runDemoPipeline();
  }

  if(document.getElementById('btnStart').disabled) return; // 防重复
  agentResults = {};
  resetUI();
  startTimer();
  log('🚀 7个Agent协同启动...','info');

  try {
    // 优先尝试SSE后端流
    await runSSEPipeline();
  } catch(e){
    if(e.message !== 'NoKey') log('⚠️ SSE失败，改用直调：'+e.message,'warn');
    await runDirectPipeline();
  }

  stopTimer();
}

async function runSSEPipeline(){
  const p = getProfile();
  streamRunning = true;
  document.getElementById('btnStart').disabled = true;
  document.getElementById('btnStop').style.display = 'block';
  showThinkingIndicator();

  try {
    const resp = await fetch('/api/stream',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({profile:p, debate_rounds:parseInt(document.getElementById('vRounds')?.textContent||'2')}),
    });
    if(!resp.ok) throw new Error('SSE '+resp.status);

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf='';
    let sseCompleted = false;

    while(true){
      const {done, value} = await reader.read();
      if(done) break;
      buf += dec.decode(value,{stream:true});
      const lines = buf.split('\n');
      buf = lines.pop()||'';
      for(const line of lines){
        if(line.startsWith('data: ')){
          const raw = line.slice(6);
          if(raw==='[DONE]'){ sseCompleted=true; streamRunning=false; break; }
          try {
            const evt = JSON.parse(raw);
            hideThinkingIndicator();
            handleSSEEvent(evt);
          }catch(e){}
        }
      }
      if(!streamRunning) break;
    }

    // SSE stream ended without complete event - possible timeout/disconnect
    if(!sseCompleted && streamRunning){
      showSSEInterrupted();
    }
  } catch(e) {
    hideThinkingIndicator();
    showSSEInterrupted(e.message);
  }

  streamRunning = false;
  document.getElementById('btnStart').disabled = false;
  document.getElementById('btnStop').style.display = 'none';
  hideThinkingIndicator();
}

function handleSSEEvent(evt){
  // 兼容后端格式：{type, agent, step, result} 和前端期望的 {status, ...}
  // 将后端type映射为status
  const evtType = evt.type || '';
  const step = evt.step;
  const agent = evt.agent;
  const result = evt.result;

  // 处理SSE超时事件
  if(evtType === 'timeout'){
    log('⚠️ ' + (evt.message || '服务器响应超时，已返回部分结果'),'warn');
    showSSEInterrupted('服务器响应超时');
    if(evt.completed_agents && evt.completed_agents.length > 0){
      log('已完成Agent: ' + evt.completed_agents.join(', '),'info');
    }
    return;
  }

  // 映射后端事件类型到前端status
  let status = evt.status; // 如果后端已提供status则直接用
  if(!status){
    if(evtType === 'agent_start') status = 'running';
    else if(evtType === 'agent_done') status = 'completed';
    else if(evtType === 'debate_round') status = 'running';
    else if(evtType === 'pipeline_done') status = 'completed';
    else if(evtType === 'error') status = 'error';
    else status = 'running';
  }

  // 流式文字输出
  if(evt.stream_text){
    appendStreamingText(agent, evt.stream_text);
  }

  // 更新拓扑和Pipeline
  if(step && agent){
    if(status === 'running'){
      setTopoNode(agent, 'running');
      setPipe(step, 'active');
      log(`${AGENT_ICONS[agent]} ${AGENT_LABELS[agent]} 运行中...`,'info');
      showSkeleton(agent);
    }
  }

  // 辩论开始
  if(evtType==='debate_start'){
    debateState.showing = true;
    debateState.round = 0;
    showDebatePanel();
    log('⚔️ 辩论开始','warn');
  }
  // 辩论轮次
  if(evtType==='debate_round'){
    debateState.round = evt.round;
    debateState.current_gen = evt.gen_text || debateState.current_gen || '';
    debateState.current_rev = evt.rev_text || debateState.current_rev || '';
    debateState.current_score = evt.hallucination_score;
    updateDebatePanel();
  }
  // 辩论结束
  if(evtType==='debate_end'){
    debateState.verdict = evt.verdict;
    debateState.final_score = evt.hallucination_score;
    closeDebatePanel();
    log('⚔️ 辩论结束：'+vl2(evt.verdict),'success');
  }

  // Agent完成
  if(status==='completed' && result){
    // Agent完成
    agentResults[agent] = result;
    setTopoNode(agent, 'done');
    const done = Object.keys(agentResults).length;
    document.getElementById('mAgents').textContent = done+'/7';
    const pct = Math.round(done/7*100);
    updateProgress(pct, `${AGENT_LABELS[agent]}完成 · ${done}/7`);
    log(`✅ ${AGENT_LABELS[agent]} 完成`,'success');
    // 渲染卡片（带打字机效果）
    if(!document.getElementById('card-'+agent)){
      renderCard(agent, result);
    }
    if(agent==='reviewer'){
      document.getElementById('mHalluc').textContent = result.hallucination_score??'-';
      document.getElementById('mAcc').textContent = result.accuracy_score??'-';
    }
  }
}

// 直接调API的全流程（回退方案）
async function runDirectPipeline(){
  const p = getProfile();
  document.getElementById('btnStart').disabled = true;
  document.getElementById('btnStop').style.display = 'block';

  const steps = [
    {name:'diagnosis',     step:1, ctx:p},
    {name:'knowledge_gen',  step:2, ctx:{diagnosis:agentResults.diagnosis, profile:p}},
    {name:'reviewer',      step:3, ctx:{content:agentResults.knowledge_gen?.content||'', source_refs:agentResults.knowledge_gen?.source_refs||[], debate_round:1}},
    {name:'reviewer_r2',   step:'3r', ctx:{content:agentResults.knowledge_gen?.content||'', source_refs:agentResults.knowledge_gen?.source_refs||[], debate_round:2}},
    {name:'practice_guide', step:4, ctx:{topic:agentResults.diagnosis?.focus_topic||'Python基础', level:p.level}},
    {name:'quiz',           step:5, ctx:{knowledge:agentResults.knowledge_gen||{}, level:p.level}},
    {name:'iteration',      step:6, ctx:{quiz_result:agentResults.quiz||{}, diagnosis:agentResults.diagnosis||{}, knowledge:agentResults.knowledge_gen||{}}},
    {name:'socratic',       step:7, ctx:{knowledge:agentResults.knowledge_gen||{}}},
  ];

  for(const s of steps){
    const displayName = s.name === 'reviewer_r2' ? 'reviewer' : s.name;
    const displayLabel = s.name === 'reviewer_r2' ? '审核裁判(第2轮)' : (AGENT_LABELS[s.name]||s.name);
    setTopoNode(displayName, 'running');
    setPipe(s.step, 'active');
    log((AGENT_ICONS[displayName]||'')+' '+displayLabel+' 运行中...','info');
    showSkeleton(displayName);

    // 辩论阶段显示覆盖层
    if(s.name === 'reviewer' || s.name === 'reviewer_r2'){
      if(!debateState.showing){ debateState.showing = true; showDebatePanel(); }
      debateState.round = s.ctx.debate_round || 1;
      document.getElementById('debateRoundLabel').textContent = '第 '+debateState.round+' 轮';
    }

    // 实时流式渲染
    let buf = '';
    const promptName = s.name === 'reviewer_r2' ? 'reviewer' : s.name;
    const {system, user} = buildPrompts(promptName, s.ctx);
    try {
      const fullText = await callLLM(system, user, ch => { buf += ch; });
      const parsed = parseLLMOutput(fullText || buf);
      agentResults[s.name] = parsed;
      parsed._meta = {agent:s.name, src:'llm', model:currentModel};
    } catch(e){
      log(`⚠️ ${AGENT_LABELS[s.name]} 失败，使用Demo`,'warn');
      agentResults[s.name] = getDemo(s.name);
    }

    const resultName = s.name === 'reviewer_r2' ? 'reviewer' : s.name;
    setTopoNode(resultName, 'done');
    setPipe(s.step, 'done');
    removeSkeleton(resultName);

    // 辩论面板更新
    if(resultName === 'reviewer' && parsed.hallucination_score !== undefined){
      debateState.current_score = parsed.hallucination_score;
      debateState.current_rev = parsed.summary || '审核完成';
      debateState.verdict = parsed.verdict;
      updateDebatePanel();
      if(s.name === 'reviewer_r2'){
        debateState.round = 2;
        updateDebatePanel();
        setTimeout(()=>{ debateState.showing = false; closeDebatePanel(); }, 2500);
      }
    }

    agentResults[resultName] = parsed;
    const done = Object.keys(agentResults).length;
    document.getElementById('mAgents').textContent = done+'/7';
    const pct = Math.round(done/7*100);
    updateProgress(pct, (AGENT_LABELS[resultName]||resultName)+'完成 · '+done+'/7');
    log('✅ '+(AGENT_LABELS[resultName]||resultName)+' 完成','success');
    renderCard(resultName, agentResults[resultName]);

    if(resultName==='reviewer'){
      document.getElementById('mHalluc').textContent = agentResults.reviewer.hallucination_score??'-';
      document.getElementById('mAcc').textContent = agentResults.reviewer.accuracy_score??'-';
    }
  }

  document.getElementById('btnStart').disabled = false;
  document.getElementById('btnStop').style.display = 'none';
  log('🎉 全流程完成！','success');
}

// Demo模式全流程
function runDemoPipeline(){
  resetUI();
  startTimer();
  const p = getProfile();
  const steps = [
    {name:'diagnosis',step:1},{name:'knowledge_gen',step:2},{name:'reviewer',step:3},
    {name:'practice_guide',step:4},{name:'quiz',step:5},{name:'iteration',step:6},{name:'socratic',step:7}
  ];
  let delay = 300;
  steps.forEach(s => {
    setTimeout(()=>{
      setTopoNode(s.name,'running');
      setPipe(s.step,'active');
      showSkeleton(s.name);
    }, delay);
    // 审核阶段显示辩论动画
    if(s.name==='reviewer'){
      delay += 400;
      setTimeout(()=>{
        debateState.showing = true;
        debateState.round = 1;
        showDebatePanel();
        setTimeout(()=>{
          debateState.round = 1;
          debateState.current_score = 35;
          debateState.current_gen = '正在审核内容准确性...';
          debateState.current_rev = '第1轮审核：发现部分内容缺少来源标注，幻觉分数35';
          updateDebatePanel();
          setTimeout(()=>{
            debateState.round = 2;
            debateState.current_score = 18;
            debateState.current_gen = '已补充来源标注...';
            debateState.current_rev = '第2轮审核：来源标注完善，幻觉分数降至18';
            debateState.verdict = 'pass';
            debateState.final_score = 18;
            updateDebatePanel();
            setTimeout(()=>{ closeDebatePanel(); }, 1500);
          }, 1200);
        }, 800);
      }, delay);
    }
    delay += 600;
    setTimeout(()=>{
      setTopoNode(s.name,'done');
      setPipe(s.step,'done');
      removeSkeleton(s.name);
      agentResults[s.name] = getDemo(s.name);
      const done = Object.keys(agentResults).length;
      document.getElementById('mAgents').textContent = done+'/7';
      const pct = Math.round(done/7*100);
      updateProgress(pct, `${AGENT_LABELS[s.name]}完成 · ${done}/7`);
      renderCard(s.name, agentResults[s.name]);
      if(s.name==='reviewer'){
        document.getElementById('mHalluc').textContent = agentResults.reviewer.hallucination_score||'30';
        document.getElementById('mAcc').textContent = agentResults.reviewer.accuracy_score||'88';
      }
      if(s.name==='socratic') log('✅ Demo全流程完成','success');
    }, delay);
    delay += 300;
  });
  stopTimer();
}

// ============ 单Agent运行 ============
async function runSingle(name){
  const p = getProfile();
  const ctxs = {
    diagnosis:{...p},
    knowledge_gen:{diagnosis:agentResults.diagnosis||{},profile:p},
    reviewer:{content:agentResults.knowledge_gen?.content||'',source_refs:[]},
    practice_guide:{topic:agentResults.diagnosis?.focus_topic||'Python基础',level:p.level},
    quiz:{knowledge:agentResults.knowledge_gen||{},level:p.level},
    iteration:{quiz_result:agentResults.quiz||{},diagnosis:agentResults.diagnosis||{},knowledge:agentResults.knowledge_gen||{}},
    socratic:{knowledge:agentResults.knowledge_gen||{}}
  };
  setTopoNode(name,'running');
  log(`${AGENT_ICONS[name]} ${AGENT_LABELS[name]} 单步运行...`,'info');
  try {
    const {system,user} = buildPrompts(name,ctxs[name]||{});
    let buf='';
    const fullText = await callLLM(system,user,ch=>{buf+=ch;});
    const parsed = parseLLMOutput(fullText||buf);
    agentResults[name] = parsed;
    parsed._meta={agent:name,src:'llm',model:currentModel};
    setTopoNode(name,'done');
    renderCard(name,parsed);
    log(`✅ ${AGENT_LABELS[name]} 完成`,'success');
  } catch(e){
    setTopoNode(name,'idle');
    log(`❌ ${AGENT_LABELS[name]} 失败`,'error');
  }
}

// ============ Demo数据 ============
function getDemo(name){
  const p = getProfile();
  const demos = {
    diagnosis:{learner_level:p.level||'intermediate',level_score:p.level==='beginner'?25:p.level==='advanced'?80:55,strengths:['C语言基础','数据结构理解','逻辑思维'],blind_spots:['Python生态不熟悉','AI框架未接触','工程实践不足'],focus_topic:'Python与AI开发',learning_path:[{phase:'Python基础',topics:['语法','函数','模块','面向对象'],estimated_hours:20},{phase:'数据处理',topics:['NumPy','Pandas','文件IO'],estimated_hours:15},{phase:'AI实战',topics:['Scikit-learn','模型训练','评估优化'],estimated_hours:40}],summary:'学习者有编程基础但Python生态和AI框架经验不足，建议从Python语法系统学习',_demo:true},
    knowledge_gen:{title:'Python与AI开发基础',content:'## Python编程基础\n\nPython是一种高级编程语言，以简洁优雅的语法著称，广泛应用于数据科学、AI、Web开发等领域。\n\n### 核心概念\n- **变量与数据类型**：Python是动态类型语言，变量无需声明类型\n  ```python\n  name = "Alice"  # 字符串\n  age = 25        # 整数\n  scores = [90, 85, 92]  # 列表\n  ```\n- **函数定义**：使用`def`关键字\n  ```python\n  def greet(name, greeting="Hello"):\n      return f"{greeting}, {name}!"\n  ```\n- **列表推导式**：简洁的数据变换语法\n  ```python\n  evens = [x for x in range(20) if x % 2 == 0]\n  ```\n\n### AI开发入门\n从NumPy\u2192Pandas\u2192Scikit-learn循序渐进：\n1. **NumPy**：高性能数值计算基础\n2. **Pandas**：数据处理与分析利器\n3. **Scikit-learn**：经典机器学习框架',concepts:['Python语法','NumPy','Pandas','机器学习','列表推导式'],source_refs:[{id:'KB001',source:'python_basics.md',type:'[教材]',relevance:'核心语法参考'},{id:'KB002',source:'ai_basics.md',type:'[实践]',relevance:'AI工具链参考'},{id:'KB003',source:'web_dev.md',type:'[官方文档]',relevance:'Web开发实践'}],_demo:true},
    reviewer:{verdict:'pass_with_concerns',hallucination_score:30,accuracy_score:88,issues:[{type:'missing_source',description:'列表推导式部分缺少官方文档引用',severity:'medium',suggestion:'添加Python官方教程链接'},{type:'industry_violation',description:'AI开发路径描述过于简化，未提及模型验证',severity:'low',suggestion:'补充交叉验证和模型评估内容'}],debate_rounds:2,debate_log:[{round:1,reviewer_verdict:'pass_with_concerns',hallucination_score:35},{round:2,reviewer_verdict:'pass',hallucination_score:18}],_demo:true},
    practice_guide:{title:'Python与AI开发实操指南',difficulty:'medium',estimated_time:'3-4小时',prerequisites:['Python 3.10+','VS Code或PyCharm','pip包管理器'],steps:[{step:1,title:'环境搭建',description:'安装Python环境并配置虚拟环境',code:'# 创建虚拟环境\npython -m venv myenv\n# 激活（Windows）\nmyenv\\Scripts\\activate\n# 安装依赖\npip install numpy pandas scikit-learn',tip:'建议使用虚拟环境隔离项目依赖'},{step:2,title:'数据处理练习',description:'用Pandas读取CSV并进行基本分析',code:'import pandas as pd\n\ndf = pd.read_csv("data.csv")\nprint(df.describe())  # 统计摘要\nprint(df.isnull().sum())  # 缺失值检查',tip:'注意处理缺失值和异常值'},{step:3,title:'模型训练',description:'用Scikit-learn训练一个简单的分类模型',code:'from sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = RandomForestClassifier(n_estimators=100)\nmodel.fit(X_train, y_train)\nprint(f"准确率: {model.score(X_test, y_test):.2f}")',tip:'使用交叉验证避免过拟合'}],tips:['用虚拟环境隔离依赖','善用type hints提升代码质量','遵循PEP 8编码规范'],_demo:true},
    quiz:{questions:[{id:1,type:'choice',difficulty:'easy',question:'Python中用什么关键字定义函数？',options:['function','def','func','lambda'],correct:1,explanation:'Python使用def关键字定义函数。lambda用于匿名函数。',knowledge_point:'函数定义'},{id:2,type:'choice',difficulty:'easy',question:'以下哪个是Python的可变数据结构？',options:['tuple','str','list','int'],correct:2,explanation:'list是可变类型，tuple和str是不可变类型。',knowledge_point:'数据类型'},{id:3,type:'choice',difficulty:'medium',question:'NumPy创建全0数组的函数是？',options:['np.ones()','np.zeros()','np.empty()','np.arange()'],correct:1,explanation:'np.zeros()创建全0数组，np.ones()创建全1数组。',knowledge_point:'NumPy基础'},{id:4,type:'choice',difficulty:'medium',question:'过拟合(Overfitting)指的是什么？',options:['训练差且测试差','训练好但测试差','训练好且测试好','模型太简单导致欠拟合'],correct:1,explanation:'过拟合=模型在训练集表现好但在测试集泛化差。',knowledge_point:'机器学习评估'},{id:5,type:'choice',difficulty:'hard',question:'Scikit-learn中防止过拟合的最佳实践是？',options:['增加模型复杂度','减少训练数据','使用交叉验证+正则化','只看训练集准确率'],correct:2,explanation:'交叉验证评估泛化能力，正则化约束模型复杂度，两者结合是防过拟合标准方法。',knowledge_point:'模型优化'}],total_score:100,passing_score:60,summary:'共5题，覆盖Python基础到机器学习评估',_demo:true},
    iteration:{decision:'consolidate',decision_label:'巩固强化',reason:'正确率60%，基本掌握但AI框架和模型优化存在薄弱点',adjustments:{difficulty_shift:0,focus_topics:['NumPy/Pandas实战','模型评估方法','交叉验证'],skip_topics:['已掌握的Python语法'],add_topics:['Scikit-learn进阶','特征工程']},suggestion:'建议先巩固Python数据处理基础，再系统学习机器学习模型训练与评估',next_steps:['完成NumPy/Pandas数据处理练习','学习Scikit-learn模型评估与交叉验证','实践一个完整的分类项目'],_demo:true},
    socratic:{title:'Python与AI开发 — 启发式导学',sections:[{content:'Python动态类型系统',question:'为什么Python选择动态类型？这和静态类型语言（如Java）相比有什么优劣？',hint:'思考开发效率和运行安全之间的权衡',depth:'analysis',follow_ups:['类型提示(Type Hints)如何弥补动态类型的不足？']},{content:'列表推导式与生成器',question:'列表推导式`[x*2 for x in lst]`和生成器`(x*2 for x in lst)`有什么区别？什么时候用哪个？',hint:'考虑内存使用和惰性求值',depth:'application',follow_ups:['大数据场景下为什么生成器更优？']},{content:'过拟合与模型选择',question:'如果你的模型在训练集上99%准确但测试集只有70%，你会怎么诊断和解决这个问题？',hint:'从数据、模型、验证三个角度思考',depth:'evaluation',follow_ups:['正则化为什么能防止过拟合？它的数学原理是什么？']}],reflection_prompts:['回顾Python学习过程，你最大的认知转变是什么？','如果让你设计一个AI项目解决实际问题，你会选什么场景？'],response:'你对Python和AI已有初步了解。让我通过问题引导你深入思考——如果要把列表中的偶数翻倍，你会怎么写？为什么选择这种方式而不是循环？',questions:[{question:'列表推导式[x*2 for x in lst if x%2==0]的执行顺序是什么？',purpose:'理解列表推导式内部机制'},{question:'生成器和列表有什么本质区别？',purpose:'引导思考惰性求值与内存效率'}],hint:'先for迭代，再if过滤，最后计算表达式值',_demo:true},
  };
  return demos[name] || {_demo:true};
}

// ============ 实时流式文字（辩论用） ============
function appendStreamingText(agent, chunk){
  // 用于辩论阶段实时显示生成/审核的文字
  if(agent==='knowledge_gen' && debateState.showing){
    const el = document.getElementById('debateGenContent');
    if(el) el.textContent = (debateState.current_gen||'') + chunk;
  }
  if(agent==='reviewer' && debateState.showing){
    const el = document.getElementById('debateRevContent');
    if(el) el.textContent = (debateState.current_rev||'') + chunk;
  }
}

// ============ 辩论可视化 ============
function showDebatePanel(){
  debateState.showing = true;
  const overlay = document.getElementById('debateOverlay');
  if(!overlay) return;
  overlay.classList.add('show');
  debateState.current_gen = '';
  debateState.current_rev = '';
  debateState.current_score = 50;
  debateState.verdict = '';
  document.getElementById('debateRoundLabel').textContent = '第 1 轮';
  document.getElementById('debateGenContent').innerHTML = '<div class="debate-placeholder">生成中...</div>';
  document.getElementById('debateRevContent').innerHTML = '<div class="debate-placeholder">等待审核...</div>';
  document.getElementById('debateScoreNum').textContent = '--';
  document.getElementById('debateVerdict').textContent = '';
  document.getElementById('debateFooter').style.display = 'none';
  // 开始分数动画
  animateDebateScore(50);
}

function updateDebatePanel(){
  const r = debateState.round;
  document.getElementById('debateRoundLabel').textContent = '第 ' + r + ' 轮';
  document.getElementById('debateGenContent').innerHTML = `<div style="font-size:11px;line-height:1.7">${esc(debateState.current_gen||'生成中...')}</div>`;
  document.getElementById('debateRevContent').innerHTML = `<div style="font-size:11px;line-height:1.7">${esc(debateState.current_rev||'审核中...')}</div>`;
  if(debateState.current_score){
    animateDebateScore(debateState.current_score);
  }
}

function animateDebateScore(targetScore){
  const el = document.getElementById('debateScoreNum');
  if(!el) return;
  const current = parseInt(el.textContent)||0;
  if(current === targetScore) return;
  const step = targetScore > current ? 1 : -1;
  let now = current;
  function tick(){
    now += step;
    if((step>0 && now>=targetScore)||(step<0 && now<=targetScore)){ now = targetScore; }
    el.textContent = now;
    el.style.color = now < 20 ? '#00e8b0' : now < 50 ? '#ffb347' : '#ff6b6b';
    if(now !== targetScore) setTimeout(tick, 30);
  }
  tick();
}

function closeDebatePanel(){
  const overlay = document.getElementById('debateOverlay');
  if(!overlay) return;
  document.getElementById('debateFooter').style.display = 'block';
  const verdictEl = document.getElementById('debateVerdict');
  if(debateState.verdict){
    const color = debateState.verdict==='pass' ? '#00e8b0' : '#ff6b6b';
    verdictEl.innerHTML = `<span style="font-size:16px;font-weight:900;color:${color}">${vl2(debateState.verdict)}</span> · 幻觉分数：${debateState.final_score||'--'}`;
  }
  // 3秒后自动关闭
  setTimeout(()=>{ overlay.classList.remove('show'); debateState.showing=false; }, 3000);
}

function closeDebate(){
  document.getElementById('debateOverlay')?.classList.remove('show');
  debateState.showing = false;
}

// ============ Pipeline Bar状态 ============
function setPipe(step, state){
  const el = document.querySelector(`.pipe-step[data-s="${step}"]`);
  if(!el) return;
  el.classList.remove('active','done','error');
  if(state==='active') el.classList.add('active');
  if(state==='done') el.classList.add('done');
  if(state==='error') el.classList.add('error');
  const ar = document.querySelector(`.pipe-arrow[data-a="${step}"]`);
  if(ar) ar.classList.toggle('lit', state==='done');
}

// ============ 计时器 ============
function startTimer(){
  startTime = Date.now();
  document.getElementById('liveBadge').style.display = 'inline';
  timerInterval = setInterval(()=>{
    const s = Math.floor((Date.now()-startTime)/1000);
    document.getElementById('timerDisplay').textContent = Math.floor(s/60).toString().padStart(2,'0')+':'+(s%60).toString().padStart(2,'0');
    document.getElementById('mTime').textContent = s+'s';
  }, 1000);
}
function stopTimer(){
  clearInterval(timerInterval);
  document.getElementById('liveBadge').style.display = 'none';
}

// ============ 停止 ============
function stopPipeline(){
  if(abortController) abortController.abort();
  streamRunning = false;
  stopTimer();
  document.getElementById('btnStart').disabled = false;
  document.getElementById('btnStop').style.display = 'none';
  log('⏹ 已停止','warn');
}

// ============ UI重置 ============
function resetUI(){
  agentResults = {};
  document.getElementById('resultsArea').innerHTML = '';
  document.getElementById('emptyState')?.remove();
  document.getElementById('resultsArea').innerHTML = '<div class="empty-state" id="emptyState" style="display:none"><div class="icon">🧠</div><h3>多智能体协同中...</h3></div>';
  document.getElementById('metricsRow').style.display = 'flex';
  AGENTS.forEach((n,i)=>{ setNode(n,''); setPipe(i+1,null); setTopoNode(n,'idle'); });
  topoParticles = [];
  ['mHalluc','mAcc','mQuiz'].forEach(id=>{ const el=document.getElementById(id); if(el) el.textContent='-'; });
  document.getElementById('mAgents').textContent='0/7';
  document.getElementById('progressWrap').style.display='block';
  updateProgress(0,'启动中...');
  Object.keys(typewriterTimers).forEach(k=>{ clearTimeout(typewriterTimers[k]); typewriterTimers[k]=null; });
}

function setNode(name, state){
  const el = document.getElementById('nd-'+name);
  if(!el) return;
  el.classList.remove('active','running','done');
  const s = el.querySelector('.status');
  if(state==='running'){ el.classList.add('running','active'); if(s) s.textContent='运行中'; }
  else if(state==='done'){ el.classList.add('done'); if(s) s.textContent='✓ 完成'; }
  else if(state==='error'){ el.classList.add('active'); if(s){s.style.color='var(--danger)'; s.textContent='✗ 出错';}}
  else { if(s){s.textContent='等待中'; s.style.color='';}}
}

// ============ 骨架屏 ============
function showSkeleton(name){
  const rg = document.getElementById('resultsArea');
  if(!rg) return;
  const sk = document.createElement('div');
  sk.className='skeleton-card';
  sk.id='sk-'+name;
  sk.innerHTML=`<div style="display:flex;align-items:center;gap:7px;margin-bottom:10px"><span class="skeleton" style="height:14px;width:120px"></span></div><div class="skeleton skeleton-line w80"></div><div class="skeleton skeleton-line w60"></div><div class="skeleton skeleton-line w80"></div>`;
  rg.appendChild(sk);
}
function removeSkeleton(name){
  const sk = document.getElementById('sk-'+name);
  if(sk) sk.remove();
}

// ============ 进度条 ============
function updateProgress(pct, label){
  const fill = document.getElementById('progressFill');
  const lbl = document.getElementById('progressLabel');
  const pc = document.getElementById('progressPct');
  if(fill) fill.style.width = pct+'%';
  if(lbl) lbl.textContent = label||'';
  if(pc) pc.textContent = pct+'%';
}

// ============ 渲染结果卡片（带打字机效果） ============
function renderCard(name, data){
  const rg = document.getElementById('resultsArea');
  if(!rg) return;
  removeSkeleton(name);
  const old = document.getElementById('card-'+name);
  if(old) old.remove();

  const isDemo = !!data._demo;
  let body = buildCardBody(name, data);
  const card = document.createElement('div');
  card.className = 'result-card streaming';
  card.id = 'card-'+name;
  card.dataset.agent = name;
  card.innerHTML = `
    <h4 data-action="toggleCard" data-args="${name}">
      ${AGENT_ICONS[name]||''} ${AGENT_LABELS[name]||name}
      ${isDemo?'<span style="font-size:8px;background:var(--warn);color:#000;padding:1px 7px;border-radius:7px;margin-left:4px">DEMO</span>':''}
      <span class="toggle-icon">▼</span>
    </h4>
    <div class="card-body" id="cb-${name}">${body}</div>
    <div class="card-actions">
      <button data-action="copyResult" data-args="${name}">📋 复制JSON</button>
      ${name==='knowledge_gen'?'<button data-action="copyCardContent" data-args="card-'+name+'">📄 复制内容</button>':''}
      ${name==='socratic'?'<button data-action="exportAllResults">📦 导出全部</button>':''}
    </div>
    ${name==='socratic'?'<div id="socraticChat" style="margin-top:8px;max-height:240px;overflow-y:auto"></div><div class="chat-input-row"><input id="socraticInput" placeholder="输入回答继续对话..." onkeydown="if(event.key===\'Enter\')sendSocraticChat()"><button data-action="sendSocraticChat">发送</button></div>':''}
  `;
  card.querySelector('h4').onclick = (e)=>{
    if(e.target.tagName!=='BUTTON') card.classList.toggle('collapsed');
  };
  rg.appendChild(card);
  card.scrollIntoView({behavior:'smooth',block:'nearest'});

  // 打字机效果
  setTimeout(()=>{ card.classList.remove('streaming'); }, 2000);
}

function buildCardBody(name, data){
  if(name==='diagnosis'){
    return `
      <div style="margin-bottom:6px"><strong>能力评分</strong>：<span style="font-size:20px;font-weight:900;color:${sc2(data.level_score||0)}">${data.level_score||0}</span>/100</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:5px">
        <span style="font-size:9px;color:var(--success);padding:2px 8px;border-radius:10px;background:rgba(0,232,176,.1);border:1px solid rgba(0,232,176,.2)">✅优势</span>
        ${(data.strengths||[]).map(s=>`<span style="font-size:10px;color:var(--muted)">${esc(s)}</span>`).join('·')}
      </div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:6px">
        <span style="font-size:9px;color:var(--danger);padding:2px 8px;border-radius:10px;background:rgba(255,85,85,.1);border:1px solid rgba(255,85,85,.2)">⚠️盲区</span>
        ${(data.blind_spots||[]).map(s=>`<span style="font-size:10px;color:var(--muted)">${esc(s)}</span>`).join('·')}
      </div>
      <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px">
        <div style="font-size:9px;color:var(--accent2);font-weight:700;margin-bottom:4px">📍 学习路径</div>
        ${(data.learning_path||[]).map((lp,i)=>`<div style="display:flex;gap:6px;margin-bottom:3px;font-size:10px">
          <span style="min-width:16px;height:16px;border-radius:50%;background:var(--accent2);color:#fff;font-size:8px;display:flex;align-items:center;justify-content:center;font-weight:800">${i+1}</span>
          <div><span style="font-weight:700">${esc(lp.phase)}</span> <span style="color:var(--muted)">(${lp.estimated_hours||0}h)</span>
          <div style="color:var(--muted);font-size:9px">${(lp.topics||[]).join(' · ')}</div></div>
        </div>`).join('')}
      </div>`;
  }
  if(name==='knowledge_gen'){
    return `
      <div style="margin-bottom:5px">${(data.concepts||[]).map((c,i)=>`<span style="background:${i%2===0?'rgba(77,166,255,.1)':'rgba(124,92,252,.1)'};color:${i%2===0?'#4da6ff':'#7c5cfc'};padding:2px 9px;border-radius:9px;font-size:9px;font-weight:700;margin-right:3px">${esc(c)}</span>`).join('')}</div>
      <div style="font-size:11px;line-height:1.7;margin-top:5px">${md2html(data.content||'')}</div>
      <div style="margin-top:6px;font-size:9px;color:var(--muted)">📚 来源：${(data.source_refs||[]).map(r=>`<span style="background:var(--bg);border:1px solid var(--border);padding:1px 7px;border-radius:7px;margin-right:3px">${esc(r.source||'')} ${esc(r.type||'')}</span>`).join('')}</div>`;
  }
  if(name==='reviewer'){
    const h=data.hallucination_score||0, a=data.accuracy_score||0;
    return `
      <div style="display:flex;gap:10px;margin-bottom:6px">
        <div><span style="font-size:9px;color:var(--muted)">幻觉分数</span><br><span style="font-size:18px;font-weight:900;color:${h<20?'var(--success)':h<50?'var(--warn)':'var(--danger)'}">${h}</span></div>
        <div><span style="font-size:9px;color:var(--muted)">准确度</span><br><span style="font-size:18px;font-weight:900;color:${sc2(a)}">${a}%</span></div>
        <div><span style="font-size:9px;color:var(--muted)">判定</span><br><span style="font-size:12px;font-weight:800;color:${data.verdict==='pass'?'var(--success)':'var(--warn)'}">${vl2(data.verdict)}</span></div>
      </div>
      ${(data.issues||[]).length>0?`<div style="font-size:9px;color:var(--danger);background:rgba(255,85,85,.08);padding:5px 8px;border-radius:6px;margin-bottom:5px">⚠ ${esc(data.issues[0].description||'')}</div>`:''}
      <div style="background:var(--bg);border-radius:7px;padding:7px;font-size:9px">
        <div style="font-weight:700;color:var(--accent2);margin-bottom:3px">辩论过程 (${data.debate_rounds||1}轮)</div>
        ${(data.debate_log||[]).map((rd,i)=>`<div style="padding:2px 0;border-bottom:1px solid var(--border)">第${i+1}轮：${vl2(rd.reviewer_verdict||rd.v||'')} · 幻觉${rd.hallucination_score||rd.h||0}</div>`).join('')}
      </div>`;
  }
  if(name==='practice_guide'){
    return `
      <div style="display:flex;gap:5px;margin-bottom:6px">
        <span style="font-size:9px;color:var(--prac-color);padding:2px 9px;border-radius:9px;background:rgba(124,92,252,.1);border:1px solid rgba(124,92,252,.2)">难度：${data.difficulty||'-'}</span>
        <span style="font-size:9px;color:var(--warn);padding:2px 9px;border-radius:9px;background:rgba(255,179,71,.1);border:1px solid rgba(255,179,71,.2)">⏱ ${data.estimated_time||'-'}</span>
      </div>
      ${(data.steps||[]).map((s,i)=>`<div style="display:flex;gap:8px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px;margin-bottom:5px">
        <div style="min-width:20px;height:20px;border-radius:50%;background:rgba(124,92,252,.2);border:1px solid var(--accent2);color:var(--accent2);font-size:8px;font-weight:800;display:flex;align-items:center;justify-content:center">${i+1}</div>
        <div style="flex:1;font-size:10px">
          <div style="font-weight:700;margin-bottom:2px">${esc(s.title||'')}</div>
          <div style="color:var(--muted);line-height:1.5">${esc(s.description||'')}</div>
          ${s.code?`<pre style="margin-top:4px;background:#060b18;border:1px solid var(--border);border-radius:5px;padding:6px 8px;font-size:9px;font-family:'Cascadia Code',monospace;color:#00d4ff;overflow-x:auto">${esc(s.code||'')}</pre>`:''}
        </div>
      </div>`).join('')}
      ${(data.tips||[]).length>0?`<div style="font-size:9px;color:var(--warn);margin-top:4px">💡 ${(data.tips||[]).join(' | ')}</div>`:''}`;
  }
  if(name==='quiz'){
    quizData = data;
    let h = `<p style="font-size:10px;margin-bottom:6px;color:var(--muted)">共${(data.questions||[]).length}题 · 及格${data.passing_score||60}分</p>`;
    h += renderQuizHTML(data.questions||[]);
    return h;
  }
  if(name==='iteration'){
    const opts=[{v:'simplify',l:'简化',c:'var(--warn)'},{v:'advance',l:'进阶',c:'var(--success)'},{v:'consolidate',l:'巩固',c:'var(--accent)'}];
    return `
      <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap">
        ${opts.map(o=>`<div style="padding:4px 12px;border-radius:18px;font-size:10px;font-weight:700;border:1px solid ${data.decision===o.v?o.c:'var(--border)'};color:${data.decision===o.v?o.c:'var(--muted)'};background:${data.decision===o.v?o.c+'18':'transparent'}">${o.l}</div>`).join('')}
      </div>
      <p style="font-size:11px;color:var(--muted);line-height:1.6">${esc(data.suggestion||'')}</p>
      ${(data.next_steps||[]).length>0?`<div style="margin-top:5px;font-size:9px;color:var(--accent)">📌 ${(data.next_steps||[]).join(' → ')}</div>`:''}`;
  }
  if(name==='socratic'){
    return `
      <div style="background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:10px;margin-bottom:6px">
        <div style="font-size:9px;color:var(--soc-color);font-weight:700;margin-bottom:4px">💬 苏格拉底导学</div>
        <p style="font-size:11px;line-height:1.7">${esc(data.response||'')}</p>
      </div>
      <ul style="list-style:none;padding:0">
        ${(data.questions||[]).map(q=>`<li style="display:flex;align-items:flex-start;gap:6px;padding:5px 0;border-bottom:1px solid var(--border);font-size:10px">
          <span style="min-width:14px;height:14px;border-radius:50%;background:rgba(0,212,255,.15);color:var(--soc-color);font-size:8px;display:flex;align-items:center;justify-content:center;font-weight:900">?</span>
          <span>${esc(q.question||q.q||'')}</span>
        </li>`).join('')}
      </ul>
      ${data.hint?`<div style="font-size:9px;color:var(--warn);margin-top:4px">💡 提示：${esc(data.hint)}</div>`:''}`;
  }
  return '<div style="color:var(--muted);font-size:11px">无数据</div>';
}


// ============ 思考动画 & SSE中断处理 ============
let thinkingTimer = null;
function showThinkingIndicator(){
  const rg = document.getElementById('resultsArea');
  if(!rg) return;
  let el = document.getElementById('thinkingIndicator');
  if(!el){
    el = document.createElement('div');
    el.id = 'thinkingIndicator';
    el.className = 'thinking-indicator';
    el.innerHTML = '<div class="thinking-dots"><span></span><span></span><span></span></div><div class="thinking-text">正在思考中...</div>';
    rg.prepend(el);
  }
  el.style.display = 'flex';
  // Animate dots text
  let dots = 0;
  clearInterval(thinkingTimer);
  const textEl = el.querySelector('.thinking-text');
  thinkingTimer = setInterval(()=>{
    dots = (dots+1) % 4;
    if(textEl) textEl.textContent = '正在思考中' + '.'.repeat(dots);
  }, 500);
}
function hideThinkingIndicator(){
  clearInterval(thinkingTimer);
  const el = document.getElementById('thinkingIndicator');
  if(el) el.style.display = 'none';
}
function showSSEInterrupted(reason){
  const rg = document.getElementById('resultsArea');
  if(!rg) return;
  // Remove any existing interrupt notice
  const old = document.getElementById('sseInterrupted');
  if(old) old.remove();
  const el = document.createElement('div');
  el.id = 'sseInterrupted';
  el.className = 'sse-interrupted';
  el.innerHTML = '<div class="interrupt-icon">⚠️</div>' +
    '<div class="interrupt-text">' +
    (reason ? '连接中断：' + esc(reason) : '响应时间较长，流式连接已中断') +
    '</div>' +
    '<div class="interrupt-hint">这可能是因为服务器响应超时或网络波动。已完成的Agent结果已保留。</div>' +
    '<button class="retry-btn" onclick="retryPipeline()">🔄 重新开始</button>' +
    '<button class="retry-btn secondary" onclick="document.getElementById(\'sseInterrupted\').remove()">关闭</button>';
  rg.prepend(el);
  el.scrollIntoView({behavior:'smooth',block:'nearest'});
  log('⚠️ SSE流中断，点击重试或使用前端直调模式','warn');
}
function retryPipeline(){
  document.getElementById('sseInterrupted')?.remove();
  hideThinkingIndicator();
  startPipeline();
}

// ============ 测验 ============
function renderQuizHTML(qs){
  let h = '';
  qs.forEach((q,i)=>{
    const exp = document.getElementById('qe-'+i);
    if(exp) exp.style.display = 'block';
    const opts = document.querySelectorAll('.qopt-'+i);
    // 标准化correct字段：A/B/C/D → 0/1/2/3，字符串数字 → 数字
    let ci = q.correct;
    if(typeof ci === 'string'){
      if('ABCD'.includes(ci.toUpperCase())) ci = 'ABCD'.indexOf(ci.toUpperCase());
      else if(!isNaN(ci)) ci = parseInt(ci);
      else ci = 0;
    }
    ci = Math.max(0, Math.min(3, ci || 0));
    q.correct = ci; // 写回标准化值
    if(opts[ci]){ opts[ci].style.borderColor='var(--success)'; opts[ci].style.background='rgba(0,232,176,.12)'; }
    const ua = userAnswers[i];
    if(ua !== undefined && ua !== ci && opts[ua]){ opts[ua].style.borderColor='var(--danger)'; opts[ua].style.background='rgba(255,85,85,.08)'; }
    if(ua === ci) correct++;
  });
  const score = Math.round(correct/qs.length*100);
  document.getElementById('quizScore').innerHTML = `<div style="text-align:center;font-size:18px;font-weight:900;padding:12px;border-radius:10px;margin-top:6px;background:${score>=60?'rgba(0,232,176,.08)':'rgba(255,85,85,.08)'};color:${score>=60?'var(--success)':'var(--danger)'};border:1px solid ${score>=60?'rgba(0,232,176,.2)':'rgba(255,85,85,.2)'}">🎯 ${score}/100 · 正确${correct}/${qs.length}</div>`;
  document.getElementById('mQuiz').textContent = score;

  // 将用户答案写回agentResults.quiz，确保迭代Agent能收到正确数据
  if(agentResults.quiz){
    agentResults.quiz.user_answers = {};
    qs.forEach((q,i) => {
      const qid = String(q.id || i+1);
      agentResults.quiz.user_answers[qid] = userAnswers[i] !== undefined ? userAnswers[i] : -1;
    });
    // 同时更新 questions 中的 correct 为数字索引
    qs.forEach(q => {
      if(typeof q.correct !== 'number') q.correct = 0;
    });
  }
}

// ============ 工具函数 ============
function sc2(s){ return s>=80?'var(--success)':s>=50?'var(--warn)':'var(--danger)'; }
function vl2(v){ return {pass:'✅ 通过',pass_with_concerns:'⚠ 有顾虑',needs_revision:'❌ 需修订',reject:'🚫 驳回'}[v]||v||''; }
function escHtml(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function md2html(md){
  if(!md) return '';
  // 先保护代码块，防止后续替换在代码内注入标签
  const codeBlocks = [];
  let processed = md.replace(/```(\w*)\n?([\s\S]*?)```/g, (m, lang, c) => {
    const idx = codeBlocks.length;
    codeBlocks.push('<pre style="background:#060b18;border:1px solid var(--border);border-radius:6px;padding:7px 9px;font-size:10px;font-family:Cascadia Code,monospace;color:#00d4ff;overflow-x:auto;margin:5px 0"><code>'+esc(c)+'</code></pre>');
    return '__CODE_BLOCK_' + idx + '__';
  });
  processed = processed
    .replace(/`([^`]+)`/g,'<code style="background:var(--bg);padding:1px 4px;border-radius:3px;font-size:10px">$1</code>')
    .replace(/^### (.+)$/gm,'<h4 style="font-size:12px;font-weight:700;margin:7px 0 3px">$1</h4>')
    .replace(/^## (.+)$/gm,'<h3 style="font-size:13px;font-weight:800;margin:9px 0 5px">$1</h3>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/^[\-\*] (.+)$/gm,'<li style="font-size:10px;margin-left:14px">$1</li>')
    .replace(/\n{2,}/g,'<br><br>')
    .replace(/\n/g,'<br>');
  // 恢复代码块
  codeBlocks.forEach((html, i) => {
    processed = processed.replace('__CODE_BLOCK_' + i + '__', html);
  });
  return processed;
}

function log(msg, level){
  const panel = document.getElementById('logPanel');
  if(!panel) return;
  const t = new Date().toLocaleTimeString('zh-CN',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const div = document.createElement('div');
  div.className='log-line';
  div.innerHTML=`<span class="log-time">${t}</span><span class="log-msg ${level||''}">${esc(msg)}</span>`;
  panel.appendChild(div);
  panel.scrollTop = panel.scrollHeight;
}

// ============ 知识库搜索 ============
async function searchKB(){
  const q = document.getElementById('kbSearchInput')?.value.trim();
  if(!q) return;
  const domain = document.querySelector('.kb-filter.active')?.dataset.domain || 'all';
  log('🔍 搜索：'+q+' ['+domain+']','info');
  try {
    const url = '/api/knowledge/search?q='+encodeURIComponent(q)+(domain!=='all'?'&domain='+domain:'');
    const resp = await fetch(url);
    if(!resp.ok) throw new Error('搜索失败');
    const data = await resp.json();
    const results = data.results||[];
    if(!results.length){ showToast('未找到相关内容'); return; }
    const rg = document.getElementById('resultsArea');
    document.getElementById('emptyState')?.remove();
    const card = document.createElement('div');
    card.className='result-card';
    card.innerHTML=`
      <h4>🔍 知识库搜索「${esc(q)}」<span style="font-size:9px;color:var(--muted);margin-left:auto">${results.length}条</span><span class="toggle-icon">▼</span></h4>
      <div class="card-body">
      ${results.map(r=>`
        <div class="kb-result" onclick="this.classList.toggle('expanded')">
          <div style="font-size:10px;line-height:1.6">${esc((r.content||r.text||'').slice(0,200))}${(r.content||r.text||'').length>200?'...':''}</div>
          <div class="kb-source">📄 ${esc(r.source||'')} · ${((r.score||0)*100).toFixed(0)}%相关 ${r.type?'· '+esc(r.type):''}</div>
        </div>
      `).join('')}
      </div>`;
    card.querySelector('h4').onclick = ()=>card.classList.toggle('collapsed');
    rg.appendChild(card);
    card.scrollIntoView({behavior:'smooth',block:'nearest'});
    log('✅ 找到'+results.length+'条','success');
  } catch(e){ log('❌ 搜索失败：'+e.message,'error'); }
}

// ============ 学情可视化报告（Canvas雷达图） ============
async function generateReport(){
  if(!Object.keys(agentResults).length){ showToast('请先完成全流程'); return; }
  log('📊 生成可视化报告...','info');
  renderReportCards();
  renderRadarChart();
  log('✅ 报告生成完成','success');
}

function renderReportCards(){
  const rg = document.getElementById('resultsArea');
  const diag = agentResults.diagnosis||{};
  const rev = agentResults.reviewer||{};
  const card = document.createElement('div');
  card.className='result-card';
  card.dataset.agent='report';
  card.innerHTML=`
    <h4>📊 学情可视化报告<span class="toggle-icon">▼</span></h4>
    <div class="card-body">
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:8px">
      <div style="background:var(--bg);border-radius:8px;padding:10px;text-align:center">
        <div style="font-size:8px;color:var(--muted)">能力评分</div>
        <div style="font-size:26px;font-weight:900;background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent">${diag.level_score||'-'}</div>
        <div style="font-size:8px;color:var(--muted)">/100</div>
      </div>
      <div style="background:var(--bg);border-radius:8px;padding:10px;text-align:center">
        <div style="font-size:8px;color:var(--muted)">幻觉分数</div>
        <div style="font-size:26px;font-weight:900;color:${(rev.hallucination_score||0)<20?'var(--success)':'var(--warn)'}">${rev.hallucination_score||'-'}</div>
        <div style="font-size:8px;color:var(--muted)">/100</div>
      </div>
      <div style="background:var(--bg);border-radius:8px;padding:10px;text-align:center">
        <div style="font-size:8px;color:var(--muted)">准确度</div>
        <div style="font-size:26px;font-weight:900;color:var(--accent)">${rev.accuracy_score||'-'}%</div>
        <div style="font-size:8px;color:var(--muted)">/100</div>
      </div>
      <div style="background:var(--bg);border-radius:8px;padding:10px;text-align:center">
        <div style="font-size:8px;color:var(--muted)">知识盲区</div>
        <div style="font-size:26px;font-weight:900;color:var(--danger)">${(diag.blind_spots||[]).length}</div>
        <div style="font-size:8px;color:var(--muted)">项需补强</div>
      </div>
    </div>
    <div style="background:var(--bg);border-radius:8px;padding:8px">
      <div style="font-size:9px;color:var(--accent2);font-weight:700;margin-bottom:4px">📍 学习路径</div>
      ${(diag.learning_path||[]).map((lp,i)=>`<div style="font-size:9px;padding:2px 0">${i+1}. ${esc(lp.phase)} (${lp.estimated_hours||0}h) - ${(lp.topics||[]).join(', ')}</div>`).join('')}
    </div>
    </div>`;
  card.querySelector('h4').onclick = ()=>card.classList.toggle('collapsed');
  rg.appendChild(card);
}

function renderRadarChart(){
  const rg = document.getElementById('resultsArea');
  const diag = agentResults.diagnosis||{};
  const rev = agentResults.reviewer||{};
  const score = diag.level_score||50;
  const strengths = diag.strengths||[];
  const blindSpots = diag.blind_spots||[];
  
  // 从诊断结果动态映射6维
  const strengthsText = strengths.join(' ');
  const blindText = blindSpots.join(' ');
  const dimensionKeywords = [
    {label:'编程基础', kw:['编程','Python','语法','基础','代码','函数'], base:0.5},
    {label:'算法思维', kw:['算法','数据结构','排序','复杂度','递归'], base:0.35},
    {label:'工程实践', kw:['工程','项目','实践','开发','部署','框架'], base:0.45},
    {label:'AI应用',   kw:['AI','机器学习','深度学习','模型','训练','NumPy','Pandas'], base:0.3},
    {label:'安全意识', kw:['安全','加密','验证','防护','XSS','SQL注入'], base:0.4},
    {label:'创新思维', kw:['创新','设计','优化','架构','重构','模式'], base:0.35},
  ];
  
  const dimensions = dimensionKeywords.map(d => {
    let value = d.base * 100 + (score - 50) * 0.4;
    // 强项匹配加分
    if(d.kw.some(k => strengthsText.includes(k))) value = Math.min(100, value + 15);
    // 盲区匹配减分
    if(d.kw.some(k => blindText.includes(k))) value = Math.max(10, value - 15);
    return {label: d.label, value: Math.round(Math.min(100, Math.max(10, value)))};
  });

  const card = document.createElement('div');
  card.className='result-card';
  card.innerHTML=`
    <h4>🎯 能力雷达图<span class="toggle-icon">▼</span></h4>
    <div class="card-body" style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
      <canvas id="radarCanvas" width="260" height="260" style="border-radius:8px;background:var(--bg)"></canvas>
      <div style="flex:1;min-width:140px">
        ${dimensions.map((d,i)=>`<div style="margin-bottom:6px">
          <div style="display:flex;justify-content:space-between;font-size:9px;margin-bottom:2px">
            <span style="color:var(--text)">${d.label}</span>
            <span style="color:${sc2(d.value)};font-weight:700">${d.value}</span>
          </div>
          <div style="height:4px;background:var(--border);border-radius:2px;overflow:hidden">
            <div style="height:100%;width:${d.value}%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:2px;transition:width 1s ease"></div>
          </div>
        </div>`).join('')}
        <div style="margin-top:10px;font-size:9px;color:var(--muted);background:var(--bg);border-radius:7px;padding:6px;line-height:1.5">
          <strong style="color:var(--accent2)">诊断结论</strong><br>
          ✅ 强项：${strengths.length?strengths.slice(0,3).map(esc).join('、'):'暂无'}<br>
          ⚠️ 盲区：${blindSpots.length?blindSpots.slice(0,3).map(esc).join('、'):'暂无'}<br>
          ${score>=70?'基础扎实，建议向AI应用和算法深度方向发展':'建议系统学习Python基础，配合项目实战提升工程能力'}
        </div>
      </div>
    </div>`;
  card.querySelector('h4').onclick = ()=>card.classList.toggle('collapsed');
  rg.appendChild(card);

  // 绘制雷达图
  setTimeout(()=>drawRadar(dimensions), 50);
}

function drawRadar(dims){
  const canvas = document.getElementById('radarCanvas');
  if(!canvas) return;
  // HiDPI支持
  const dpr = window.devicePixelRatio || 1;
  const displayW = 260, displayH = 260;
  canvas.width = displayW * dpr;
  canvas.height = displayH * dpr;
  canvas.style.width = displayW + 'px';
  canvas.style.height = displayH + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const w = displayW, h = displayH, cx = w/2, cy = h/2;
  const r = Math.min(w,h)*0.38;
  const n = dims.length;
  const step = (Math.PI*2)/n;

  ctx.clearRect(0,0,w,h);

  // 背景同心多边形
  [1,0.75,0.5,0.25].forEach(f=>{
    ctx.beginPath();
    dims.forEach((_,i)=>{
      const a = i*step - Math.PI/2;
      const px = cx + Math.cos(a)*r*f, py = cy + Math.sin(a)*r*f;
      if(i===0) ctx.moveTo(px,py); else ctx.lineTo(px,py);
    });
    ctx.closePath();
    ctx.strokeStyle='rgba(26,39,68,0.6)';
    ctx.lineWidth=0.5;
    ctx.stroke();
  });

  // 轴线
  dims.forEach((_,i)=>{
    const a = i*step - Math.PI/2;
    ctx.beginPath();
    ctx.moveTo(cx,cy);
    ctx.lineTo(cx+Math.cos(a)*r, cy+Math.sin(a)*r);
    ctx.strokeStyle='rgba(26,39,68,0.5)';
    ctx.lineWidth=0.5;
    ctx.stroke();
  });

  // 数据填充
  ctx.beginPath();
  dims.forEach((d,i)=>{
    const a = i*step - Math.PI/2;
    const v = d.value/100 * r;
    const px = cx + Math.cos(a)*v, py = cy + Math.sin(a)*v;
    if(i===0) ctx.moveTo(px,py); else ctx.lineTo(px,py);
  });
  ctx.closePath();
  ctx.fillStyle='rgba(0,232,176,0.12)';
  ctx.fill();
  ctx.strokeStyle='rgba(0,232,176,0.7)';
  ctx.lineWidth=1.5;
  ctx.stroke();

  // 数据点
  dims.forEach((d,i)=>{
    const a = i*step - Math.PI/2;
    const v = d.value/100 * r;
    ctx.beginPath();
    ctx.arc(cx+Math.cos(a)*v, cy+Math.sin(a)*v, 3, 0, Math.PI*2);
    ctx.fillStyle='#00e8b0';
    ctx.fill();
  });

  // 标签
  dims.forEach((d,i)=>{
    const a = i*step - Math.PI/2;
    const lx = cx + Math.cos(a)*(r+18), ly = cy + Math.sin(a)*(r+18);
    ctx.font='8px -apple-system,Segoe UI,sans-serif';
    ctx.textAlign=Math.abs(Math.cos(a))>0.5?(Math.cos(a)>0?'left':'right'):'center';
    ctx.textBaseline='middle';
    ctx.fillStyle='#7a869e';
    ctx.fillText(d.label, lx, ly);
  });
}

// ============ 苏格拉底对话（卡片内） ============
let socraticHistory = [];
async function sendSocraticChat(){
  const input = document.getElementById('socraticInput');
  if(!input) return;
  const msg = input.value.trim();
  if(!msg) return;
  input.value='';
  socraticHistory.push({role:'learner',text:msg});
  renderSocraticChat();
  const knowledge = agentResults.knowledge_gen||{};
  const sysPrompt = `你是苏格拉底导师。主题：${knowledge.title||'编程'}。知识点：${(knowledge.concepts||[]).join('、')}。输出JSON：{"response":"","next_question":"追问","assessment":"understood/partially_understood/misunderstood"}`;
  try {
    const fullText = await callLLM(sysPrompt, `历史：${JSON.stringify(socraticHistory.slice(-6))}\n学习者：${msg}\n回应（JSON）：`);
    const p = parseLLMOutput(fullText);
    socraticHistory.push({role:'tutor',text:p.response||'继续思考——能否举个例子？'});
  } catch(e){
    socraticHistory.push({role:'tutor',text:'继续思考——能换个角度说明吗？'});
  }
  renderSocraticChat();
}
function renderSocraticChat(){
  const el = document.getElementById('socraticChat');
  if(!el) return;
  el.innerHTML = socraticHistory.map(m=>`<div class="chat-bubble ${m.role==='tutor'?'tutor':'learner'}">${esc(m.text)}</div>`).join('');
  el.scrollTop = el.scrollHeight;
}

// ============ 全局对话FAB ============
function toggleChat(){
  const panel = document.getElementById('chatPanel');
  if(!panel) return;
  panel.classList.toggle('show');
}
async function sendGlobalChat(){
  const input = document.getElementById('chatInput');
  if(!input) return;
  const msg = input.value.trim();
  if(!msg) return;
  input.value='';
  const msgs = document.getElementById('chatMessages');
  // 用户消息
  const ub = document.createElement('div');
  ub.className='chat-bubble-user';
  ub.textContent = msg;
  msgs.appendChild(ub);
  msgs.scrollTop = msgs.scrollHeight;

  // AI回复
  const ab = document.createElement('div');
  ab.className='chat-bubble-ai';
  ab.textContent = '正在思考...';
  msgs.appendChild(ab);
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const knowledge = agentResults.knowledge_gen||{};
    const sysPrompt = `你是AI学习助手。${Object.keys(agentResults).length?'当前学习主题：'+(knowledge.title||'编程'):'你可以回答各类学习问题'}。知识点：${(knowledge.concepts||[]).join('、')}。简洁专业，中文回答。`;
    const fullText = await callLLM(sysPrompt, msg);
    ab.textContent = fullText.slice(0,500)||'这个问题比较复杂，建议先完成学情诊断和知识生成流程，我会给出更精准的回答。';
  } catch(e){
    ab.textContent = '我还在学习中，建议先填写学习者画像并启动全流程，这样可以给你更个性化的回答~ 🧠';
  }
  msgs.scrollTop = msgs.scrollHeight;
}
async function quickChat(question){
  document.getElementById('chatInput').value = question;
  sendGlobalChat();
}

// ============ 结果复制 & 导出 ============
function copyResult(name){
  const data = agentResults[name];
  if(!data) return;
  const clean = {...data}; delete clean._demo; delete clean._meta;
  navigator.clipboard.writeText(JSON.stringify(clean,null,2)).then(()=>showToast('✅ 已复制')).catch(()=>showToast('复制失败'));
}
function copyCardContent(cardId){
  const card = document.getElementById(cardId);
  if(!card) return;
  navigator.clipboard.writeText(card.innerText).then(()=>showToast('✅ 已复制')).catch(()=>showToast('复制失败'));
}
function exportAllResults(){
  if(!Object.keys(agentResults).length){ showToast('暂无结果'); return; }
  const clean={};
  for(const [k,v] of Object.entries(agentResults)){ clean[k]={...v}; delete clean[k]._demo; delete clean[k]._meta; }
  const blob=new Blob([JSON.stringify(clean,null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download='multi-agent-results-'+new Date().toISOString().slice(0,10)+'.json';
  a.click();
  showToast('✅ 已导出JSON');
}

// ============ 卡片折叠 ============
function toggleCard(name){
  const card = document.getElementById('card-'+name);
  if(card) card.classList.toggle('collapsed');
}

// ============ Toast ============
function showToast(msg,dur=2000){
  const t=document.createElement('div'); t.className='toast'; t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),dur);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', ()=>{
  // Inject thinking/interrupt/retry styles
  const style = document.createElement('style');
  style.textContent = `
    .thinking-indicator{display:flex;align-items:center;gap:10px;padding:14px 18px;background:rgba(0,232,176,.06);border:1px solid rgba(0,232,176,.15);border-radius:10px;margin-bottom:10px}
    .thinking-dots{display:flex;gap:4px}
    .thinking-dots span{width:8px;height:8px;border-radius:50%;background:var(--accent);animation:thinkingBounce 1.2s ease-in-out infinite}
    .thinking-dots span:nth-child(2){animation-delay:.2s}
    .thinking-dots span:nth-child(3){animation-delay:.4s}
    @keyframes thinkingBounce{0%,80%,100%{transform:scale(0.6);opacity:.4}40%{transform:scale(1);opacity:1}}
    .thinking-text{font-size:13px;color:var(--accent);font-weight:600}
    .sse-interrupted{padding:16px 18px;background:rgba(255,179,71,.08);border:1px solid rgba(255,179,71,.2);border-radius:10px;margin-bottom:10px;text-align:center}
    .interrupt-icon{font-size:28px;margin-bottom:6px}
    .interrupt-text{font-size:13px;color:var(--warn);font-weight:700;margin-bottom:4px}
    .interrupt-hint{font-size:11px;color:var(--muted);margin-bottom:10px;line-height:1.5}
    .retry-btn{padding:6px 16px;border-radius:8px;border:1px solid var(--accent);background:rgba(0,232,176,.1);color:var(--accent);font-size:12px;font-weight:700;cursor:pointer;margin:0 4px;transition:all .2s}
    .retry-btn:hover{background:rgba(0,232,176,.2);transform:translateY(-1px)}
    .retry-btn.secondary{border-color:var(--border);color:var(--muted);background:transparent}
    .retry-btn.secondary:hover{border-color:var(--muted)}
  `;
  document.head.appendChild(style);
  initTopology();
  document.getElementById('btnModel').textContent = '🤖 '+{deepseek:'DeepSeek',zhipu:'GLM','openai-compat':'OpenAI'}[currentModel]||'🤖 模型';
  if(currentApiKey) log('🔑 Key已加载','info');
  else { log('⚠️ 无Key，点击右上角配置','warn'); setTimeout(()=>showApiKeyModal(), 1000); }

  // 后端健康检查
  fetch('/api/health').then(r=>r.json()).then(d=>{
    const n=(d.agents||[]).length;
    log(`后端：${n}个Agent · v${d.version||'?'} · ${d.api_key?'✅ Key已配':'⚠️ 无Key'}`,'success');
  }).catch(()=>log('⚠️ 后端离线（可用前端直调）','warn'));

  // Ctrl+Enter快捷启动
  document.addEventListener('keydown', e=>{
    if(e.ctrlKey && e.key==='Enter' && !document.getElementById('btnStart').disabled){
      startPipeline();
    }
  });
});

// ============ 事件委托 ============
document.addEventListener('click', e=>{
  const el = e.target.closest('[data-action]');
  if(!el) return;
  const action = el.dataset.action;
  const args = el.dataset.args||'';
  switch(action){
    case 'startPipeline': startPipeline(); break;
    case 'stopPipeline': stopPipeline(); break;
    case 'runSingle': runSingle(args); break;
    case 'toggleCard': toggleCard(args); break;
    case 'copyResult': copyResult(args); break;
    case 'copyCardContent': copyCardContent(args); break;
    case 'exportAllResults': exportAllResults(); break;
    case 'toggleSidebar': document.getElementById('sidebar').classList.toggle('mobile-show'); break;
    case 'showModelModal': showModelModal(); break;
    case 'showApiKeyModal': showApiKeyModal(); break;
    case 'closeModelModal': closeModelModal(); break;
    case 'confirmModel': confirmModel(); break;
    case 'skipApiKey': skipApiKey(); break;
    case 'confirmApiKey': confirmApiKey(); break;
    case 'searchKB': searchKB(); break;
    case 'generateReport': generateReport(); break;
    case 'pickOpt': { const [a,b]=args.split(','); pickOpt(parseInt(a),parseInt(b)); break; }
    case 'gradeQuiz': gradeQuiz(); break;
    case 'sendSocraticChat': sendSocraticChat(); break;
    case 'toggleChat': toggleChat(); break;
    case 'sendGlobalChat': sendGlobalChat(); break;
    case 'quickChat': quickChat(args); break;
    case 'closeDebate': closeDebate(); break;
  }
});
