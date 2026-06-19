/**
 * zhipu-api.js — 前端直调智谱API客户端
 * 绕过Render中间层，从用户浏览器直连智谱，延迟从20秒降到2-3秒
 * JWT签名在浏览器端完成，无需后端参与
 */

const ZHIPU_API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions';

// ========== JWT签名（浏览器端实现） ==========
function base64UrlEncode(data) {
  let str = '';
  if (typeof data === 'string') {
    str = btoa(unescape(encodeURIComponent(data)));
  } else {
    str = btoa(String.fromCharCode(...new Uint8Array(data)));
  }
  return str.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function hmacSha256(key, message) {
  const encoder = new TextEncoder();
  const cryptoKey = await crypto.subtle.importKey(
    'raw', encoder.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', cryptoKey, encoder.encode(message));
  return sig;
}

async function generateJwt(apiKey) {
  const [id, secret] = apiKey.split('.');
  if (!id || !secret) throw new Error('API Key格式错误，应为 {id}.{secret}');

  const header = base64UrlEncode(JSON.stringify({ alg: 'HS256', sign_type: 'SIGN' }));
  const now = Math.floor(Date.now() / 1000);
  const payload = base64UrlEncode(JSON.stringify({
    api_key: id,
    exp: now + 3600,
    timestamp: now,
  }));

  const signStr = `${header}.${payload}`;
  const sig = await hmacSha256(secret, signStr);
  const signature = base64UrlEncode(sig);

  return `${signStr}.${signature}`;
}

// ========== API调用 ==========
async function callZhipu(apiKey, messages, temperature = 0.3, maxTokens = 2000) {
  const token = await generateJwt(apiKey);
  const resp = await fetch(ZHIPU_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      model: 'glm-4-flash',
      messages,
      temperature,
      max_tokens: maxTokens,
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`智谱API错误(${resp.status}): ${err.slice(0, 100)}`);
  }

  const data = await resp.json();
  return data.choices[0].message.content;
}

// ========== API Key管理 ==========
function getApiKey() {
  return localStorage.getItem('zhipu_api_key') || '';
}

function setApiKey(key) {
  localStorage.setItem('zhipu_api_key', key);
}

function hasApiKey() {
  const key = getApiKey();
  return key && key.includes('.');
}

// ========== 从AI返回中提取JSON ==========
function extractJson(content) {
  // 尝试提取 ```json ... ``` 代码块
  const codeMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
  if (codeMatch) return JSON.parse(codeMatch[1]);
  // 尝试提取第一个 { ... }
  const start = content.indexOf('{');
  const end = content.lastIndexOf('}') + 1;
  if (start >= 0 && end > start) return JSON.parse(content.slice(start, end));
  throw new Error('无法从AI返回中提取JSON');
}

// ========== 业务API封装 ==========

/**
 * 生成岗位能力图谱（前端直调）
 */
async function directBuildSkillMap(jobName, major, apiKey) {
  const prompt = `你是职业教育专家。为"${major}"专业群的"${jobName}"岗位生成能力图谱。

严格输出JSON（无其他文字）：
\`\`\`json
{
  "job_name": "${jobName}",
  "major": "${major}",
  "skill_tree": {
    "核心能力": [{"name": "名称", "level": "基础/进阶/高级", "description": "描述"}],
    "专业技能": [{"name": "名称", "tools": ["工具"], "proficiency": "程度"}],
    "工具技能": [{"name": "名称", "category": "类别", "importance": "必备/推荐"}],
    "软技能": [{"name": "名称", "scenario": "场景"}]
  },
  "career_path": [{"stage": "阶段", "duration": "时间", "milestones": ["里程碑"]}],
  "related_jobs": ["关联岗位"]
}
\`\`\`
至少8个核心能力、10个专业技能、6个工具技能、5个软技能。`;

  const content = await callZhipu(apiKey, [
    { role: 'system', content: '你是职业教育专家。只输出JSON，不解释。' },
    { role: 'user', content: prompt },
  ], 0.3, 2000);
  return extractJson(content);
}

/**
 * 发现新岗位（前端直调）
 */
async function directDiscoverNewJob(trendKeywords, apiKey) {
  const prompt = `根据技术趋势：${trendKeywords.join(', ')}，发现一个新兴岗位。
输出JSON：{"job_name":"名称","core_responsibility":"职责","required_skills":["技能"],"bonus_skills":["加分"],"scenarios":["场景"],"why_emerging":"原因"}`;

  const content = await callZhipu(apiKey, [
    { role: 'system', content: '你是IT行业分析师。只输出JSON。' },
    { role: 'user', content: prompt },
  ], 0.5, 1000);
  return extractJson(content);
}

/**
 * 智能问答（前端直调）
 */
async function directChat(messages, apiKey) {
  return await callZhipu(apiKey, messages, 0.7, 800);
}

/**
 * 任务转化（前端直调）
 */
async function directTaskConvert(jobName, taskName, taskDesc, apiKey) {
  const descPart = taskDesc ? `\n任务描述：${taskDesc}` : '';
  const prompt = `你是职业教育课程设计专家。将岗位"${jobName}"的典型工作任务"${taskName}"转化为学习型任务。${descPart}

严格输出JSON（无其他文字）：
\`\`\`json
{
  "task_name": "${taskName}",
  "job_name": "${jobName}",
  "description": "转化后的学习型任务描述",
  "mapped_courses": ["对应课程1", "对应课程2"],
  "learning_tasks": [
    {"order": 1, "name": "任务名", "type": "认知/实践/综合", "hours": 8, "description": "详细描述", "deliverable": "交付物", "difficulty": "基础/进阶/高级"}
  ],
  "total_hours": 0,
  "difficulty_progression": "描述难度递进逻辑"
}
\`\`\`
生成4-6个递进式学习型任务，总学时20-40小时，难度从基础到综合递进。`;

  const content = await callZhipu(apiKey, [
    { role: 'system', content: '你是职业教育课程设计专家。只输出JSON，不解释。' },
    { role: 'user', content: prompt },
  ], 0.3, 2000);
  return extractJson(content);
}

/**
 * 学情诊断+学习路径（前端直调）
 */
async function directLearnPath(targetJob, skills, experience, weeks, apiKey) {
  const prompt = `你是职业教育学情诊断专家。

目标岗位：${targetJob}
已掌握技能：${skills}
项目经验：${experience}
学习周期：${weeks}周

执行两步：
1. 学情诊断：分析当前技能与目标岗位的匹配度，找出差距
2. 学习路径规划：设计${weeks}周的学习路径

严格输出JSON（无其他文字）：
\`\`\`json
{
  "diagnosis": {
    "match_score": 65,
    "strengths": ["已掌握的优势"],
    "gaps": ["需要补充的差距"],
    "current_level": "初学者/初中级/中级"
  },
  "path": [
    {"week": "1-2", "topic": "学习主题", "tasks": ["具体任务"], "hours": 20, "goal": "阶段目标"}
  ],
  "trajectory": [
    {"week": 2, "score": 30},
    {"week": 4, "score": 45},
    {"week": 8, "score": 65},
    {"week": 12, "score": 80}
  ],
  "advice": "个性化建议"
}
\`\`\``;

  const content = await callZhipu(apiKey, [
    { role: 'system', content: '你是职业教育学情诊断专家。只输出JSON，不解释。' },
    { role: 'user', content: prompt },
  ], 0.3, 2000);
  return extractJson(content);
}

/**
 * 智能问答（前端直调 - 流式输出）
 */
async function directChatStream(messages, apiKey, onChunk) {
  const token = await generateJwt(apiKey);
  const resp = await fetch(ZHIPU_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      model: 'glm-4-flash',
      messages,
      temperature: 0.7,
      max_tokens: 800,
      stream: true,
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`智谱API错误(${resp.status}): ${err.slice(0, 100)}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const d = line.slice(6);
        if (d === '[DONE]') return fullText;
        try {
          const j = JSON.parse(d);
          const ch = (j.choices?.[0]?.delta?.content) || '';
          if (ch) { fullText += ch; if (onChunk) onChunk(ch); }
        } catch (e) {}
      }
    }
  }
  return fullText;
}

// 导出
window.ZhipuAPI = {
  callZhipu,
  directBuildSkillMap,
  directDiscoverNewJob,
  directChat,
  directChatStream,
  directTaskConvert,
  directLearnPath,
  getApiKey,
  setApiKey,
  hasApiKey,
  extractJson,
};
