// ===== 世界杯 2026 - 完整赛事数据 + 逻辑 =====

const DATA = {
  matches: [
    // === 6月11日 A组 ===
    {id:1,date:"2026-06-11",time:"10:00",group:"A",home:"墨西哥",away:"波兰",hf:"🇲🇽",af:"🇵🇱",status:"upcoming",hs:null,as:null,venue:"阿兹特克球场",events:[],prediction:{home:42,draw:28,away:30}},
    {id:2,date:"2026-06-11",time:"14:00",group:"A",home:"阿根廷",away:"沙特",hf:"🇦🇷",af:"🇸🇦",status:"upcoming",hs:null,as:null,venue:"阿兹特克球场",events:[],prediction:{home:55,draw:18,away:27}},
    // === 6月11日 B组 ===
    {id:3,date:"2026-06-11",time:"18:00",group:"B",home:"英格兰",away:"伊朗",hf:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",af:"🇮🇷",status:"upcoming",hs:null,as:null,venue:"大都会人寿",events:[],prediction:{home:48,draw:22,away:30}},
    {id:4,date:"2026-06-11",time:"21:00",group:"B",home:"美国",away:"威尔士",hf:"🇺🇸",af:"🏴󠁧󠁢󠁷󠁬󠁳󠁿",status:"upcoming",hs:null,as:null,venue:"SoFi球场",events:[],prediction:{home:45,draw:25,away:30}},
    // === 6月12日 C组 ===
    {id:5,date:"2026-06-12",time:"10:00",group:"C",home:"法国",away:"澳大利亚",hf:"🇫🇷",af:"🇦🇺",status:"upcoming",hs:null,as:null,venue:"AT&T球场",events:[],prediction:{home:58,draw:20,away:22}},
    {id:6,date:"2026-06-12",time:"14:00",group:"C",home:"丹麦",away:"突尼斯",hf:"🇩🇰",af:"🇹🇳",status:"upcoming",hs:null,as:null,venue:"梅赛德斯奔驰",events:[],prediction:{home:40,draw:30,away:30}},
    // === 6月12日 D组 ===
    {id:7,date:"2026-06-12",time:"18:00",group:"D",home:"巴西",away:"塞尔维亚",hf:"🇧🇷",af:"🇷🇸",status:"upcoming",hs:null,as:null,venue:"硬石球场",events:[],prediction:{home:52,draw:22,away:26}},
    {id:8,date:"2026-06-12",time:"21:00",group:"D",home:"瑞士",away:"喀麦隆",hf:"🇨🇭",af:"🇨🇲",status:"upcoming",hs:null,as:null,venue:"Lumen Field",events:[],prediction:{home:38,draw:28,away:34}},
    // === 6月13日 E组 ===
    {id:9,date:"2026-06-13",time:"10:00",group:"E",home:"西班牙",away:"哥斯达黎加",hf:"🇪🇸",af:"🇨🇷",status:"upcoming",hs:null,as:null,venue:"BMO球场",events:[],prediction:{home:60,draw:20,away:20}},
    {id:10,date:"2026-06-13",time:"14:00",group:"E",home:"德国",away:"日本",hf:"🇩🇪",af:"🇯🇵",status:"upcoming",hs:null,as:null,venue:"BC Place",events:[],prediction:{home:45,draw:25,away:30}},
    // === 6月13日 F组 ===
    {id:11,date:"2026-06-13",time:"18:00",group:"F",home:"比利时",away:"加拿大",hf:"🇧🇪",af:"🇨🇦",status:"upcoming",hs:null,as:null,venue:"NRG球场",events:[],prediction:{home:42,draw:26,away:32}},
    {id:12,date:"2026-06-13",time:"21:00",group:"F",home:"克罗地亚",away:"摩洛哥",hf:"🇭🇷",af:"🇲🇦",status:"upcoming",hs:null,as:null,venue:"Gillette",events:[],prediction:{home:35,draw:30,away:35}},
    // === 6月14日 G组 ===
    {id:13,date:"2026-06-14",time:"10:00",group:"G",home:"葡萄牙",away:"韩国",hf:"🇵🇹",af:"🇰🇷",status:"upcoming",hs:null,as:null,venue:"阿兹特克球场",events:[],prediction:{home:48,draw:24,away:28}},
    {id:14,date:"2026-06-14",time:"14:00",group:"G",home:"乌拉圭",away:"加纳",hf:"🇺🇾",af:"🇬🇭",status:"upcoming",hs:null,as:null,venue:"大都会人寿",events:[],prediction:{home:40,draw:28,away:32}},
    // === 6月14日 H组 ===
    {id:15,date:"2026-06-14",time:"18:00",group:"H",home:"荷兰",away:"塞内加尔",hf:"🇳🇱",af:"🇸🇳",status:"upcoming",hs:null,as:null,venue:"SoFi球场",events:[],prediction:{home:44,draw:26,away:30}},
    {id:16,date:"2026-06-14",time:"21:00",group:"H",home:"厄瓜多尔",away:"卡塔尔",hf:"🇪🇨",af:"🇶🇦",status:"upcoming",hs:null,as:null,venue:"AT&T球场",events:[],prediction:{home:38,draw:28,away:34}},
    // === 已结束 ===
    {id:20,date:"2026-06-10",time:"21:00",group:"A",home:"波兰",away:"沙特",hf:"🇵🇱",af:"🇸🇦",status:"finished",hs:2,as:0,venue:"阿兹特克球场",
     events:[{min:"12'",icon:"⚽",text:"莱万多夫斯基 进球",goal:true,side:"home"},{min:"78'",icon:"⚽",text:"莱万多夫斯基 进球",goal:true,side:"home"}]},
    {id:21,date:"2026-06-10",time:"10:00",group:"A",home:"墨西哥",away:"波兰",hf:"🇲🇽",af:"🇵🇱",status:"finished",hs:1,as:0,venue:"阿兹特克球场",
     events:[{min:"31'",icon:"⚽",text:"哈梅斯·罗德里格斯 进球",goal:true,side:"home"}]},
    // === 今日直播 ===
    {id:17,date:today(),time:"15:00",group:"A",home:"墨西哥",away:"阿根廷",hf:"🇲🇽",af:"🇦🇷",status:"live",hs:1,as:0,venue:"阿兹特克球场",minute:"67'",
     events:[{min:"23'",icon:"⚽",text:"洛萨诺 进球",goal:true,side:"home"},{min:"45'",icon:"🟨",text:"罗梅罗 黄牌",side:"away"},{min:"58'",icon:"🔄",text:"阿根廷换人：迪马利亚 ↑ / 劳塔罗 ↓",side:"away"}],
     prediction:{home:35,draw:20,away:45}},
    // === 今日未开赛 ===
    {id:18,date:today(),time:"18:00",group:"B",home:"英格兰",away:"美国",hf:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",af:"🇺🇸",status:"upcoming",hs:null,as:null,venue:"大都会人寿",events:[],prediction:{home:50,draw:22,away:28}},
    {id:19,date:today(),time:"21:00",group:"C",home:"法国",away:"丹麦",hf:"🇫🇷",af:"🇩🇰",status:"upcoming",hs:null,as:null,venue:"AT&T球场",events:[],prediction:{home:46,draw:24,away:30}},
  ],

  standings: {
    A:[{f:"🇲🇽",t:"墨西哥",p:1,w:1,d:0,l:0,gf:1,ga:0,pt:3},{f:"🇵🇱",t:"波兰",p:1,w:1,d:0,l:0,gf:2,ga:0,pt:3},{f:"🇦🇷",t:"阿根廷",p:1,w:0,d:0,l:1,gf:0,ga:1,pt:0},{f:"🇸🇦",t:"沙特",p:1,w:0,d:0,l:1,gf:0,ga:2,pt:0}],
    B:[{f:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",t:"英格兰",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇺🇸",t:"美国",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🏴󠁧󠁢󠁷󠁬󠁳󠁿",t:"威尔士",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇮🇷",t:"伊朗",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
    C:[{f:"🇫🇷",t:"法国",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇩🇰",t:"丹麦",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇦🇺",t:"澳大利亚",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇹🇳",t:"突尼斯",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
    D:[{f:"🇧🇷",t:"巴西",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇨🇭",t:"瑞士",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇷🇸",t:"塞尔维亚",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇨🇲",t:"喀麦隆",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
    E:[{f:"🇪🇸",t:"西班牙",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇩🇪",t:"德国",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇯🇵",t:"日本",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇨🇷",t:"哥斯达黎加",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
    F:[{f:"🇧🇪",t:"比利时",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇭🇷",t:"克罗地亚",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇨🇦",t:"加拿大",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇲🇦",t:"摩洛哥",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
    G:[{f:"🇵🇹",t:"葡萄牙",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇺🇾",t:"乌拉圭",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇰🇷",t:"韩国",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇬🇭",t:"加纳",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
    H:[{f:"🇳🇱",t:"荷兰",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇸🇳",t:"塞内加尔",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇪🇨",t:"厄瓜多尔",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0},{f:"🇶🇦",t:"卡塔尔",p:0,w:0,d:0,l:0,gf:0,ga:0,pt:0}],
  },

  scorers: [
    {r:1,n:"哈梅斯·罗德里格斯",t:"墨西哥",f:"🇲🇽",g:3},
    {r:2,n:"罗伯特·莱万多夫斯基",t:"波兰",f:"🇵🇱",g:2},
    {r:3,n:"梅西",t:"阿根廷",f:"🇦🇷",g:1},{r:3,n:"姆巴佩",t:"法国",f:"🇫🇷",g:1},
    {r:5,n:"内马尔",t:"巴西",f:"🇧🇷",g:1},{r:5,n:"哈里·凯恩",t:"英格兰",f:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",g:1},
  ],

  news: [
    {t:"2026世界杯6月11日开幕！揭幕战墨西哥vs波兰",tag:"th",tl:"🔥 热点"},
    {t:"梅西确认参加最后一届世界杯：这是我的告别之旅",tag:"tp",tl:"📊 前瞻"},
    {t:"波兰2-0沙特：莱万梅开二度",tag:"tr",tl:"✅ 战报"},
    {t:"英格兰vs美国首发：凯恩领衔三狮军团",tag:"tp",tl:"📋 首发"},
    {t:"墨西哥1-0波兰：哈梅斯一剑封喉",tag:"tr",tl:"✅ 战报"},
  ],

  teams: {
    "墨西哥":{flag:"🇲🇽",coach:"胡安·卡洛斯·奥索里奥",group:"A",city:"墨西哥城",players:["洛萨诺","哈梅斯·罗德里格斯","瓜尔达多","阿尔瓦雷斯","奥乔亚"]},
    "阿根廷":{flag:"🇦🇷",coach:"利昂内尔·斯卡洛尼",group:"A",city:"布宜诺斯艾利斯",players:["梅西","迪马利亚","劳塔罗·马丁内斯","德保罗","马丁内斯"]},
    "波兰":{flag:"🇵🇱",coach:"切斯瓦夫·米赫涅维奇",group:"A",city:"华沙",players:["莱万多夫斯基","泽林斯基","什琴斯尼","米利克","贝雷斯琴斯基"]},
    "沙特":{flag:"🇸🇦",coach:"埃尔韦·勒纳尔",group:"A",city:"利雅得",players:["阿尔道萨里","阿尔谢赫里","阿尔奥瓦伊斯","法拉杰","布莱克"]},
    "英格兰":{flag:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",coach:"加雷斯·索斯盖特",group:"B",city:"伦敦",players:["凯恩","萨卡","贝林厄姆","皮克福德","斯通斯"]},
    "美国":{flag:"🇺🇸",coach:"格雷格·贝尔哈特",group:"B",city:"芝加哥",players:["普利西奇","麦肯尼","雷纳","亚当斯","特纳"]},
    "法国":{flag:"🇫🇷",coach:"迪迪埃·德尚",group:"C",city:"巴黎",players:["姆巴佩","格列兹曼","坎特","瓦拉内","迈尼昂"]},
    "巴西":{flag:"🇧🇷",coach:"多里瓦尔·儒尼奥尔",group:"D",city:"里约热内卢",players:["内马尔","维尼修斯","马尔基尼奥斯","阿利松","卡塞米罗"]},
    "西班牙":{flag:"🇪🇸",coach:"路易斯·德拉富恩特",group:"E",city:"马德里",players:["佩德里","加维","罗德里","莫拉塔","乌奈·西蒙"]},
    "德国":{flag:"🇩🇪",coach:"朱利安·纳格尔斯曼",group:"E",city:"柏林",players:["穆西亚拉","维尔茨","基米希","吕迪格","诺伊尔"]},
    "葡萄牙":{flag:"🇵🇹",coach:"罗伯托·马丁内斯",group:"G",city:"里斯本",players:["B席","莱奥","B费","迪亚斯","科斯塔"]},
    "荷兰":{flag:"🇳🇱",coach:"罗纳德·科曼",group:"H",city:"阿姆斯特丹",players:["范迪克","德容","加克波","西蒙斯","维尔布鲁根"]},
  }
};

// ===== 关注球队（localStorage持久化）=====
let favorites = JSON.parse(localStorage.getItem('wc26_favs')||'["阿根廷","墨西哥","法国","巴西"]');
function saveFavs(){localStorage.setItem('wc26_favs',JSON.stringify(favorites))}
DATA.favorites = favorites;

// ===== 工具函数 =====
function today(){return new Date().toISOString().split('T')[0]}
function fmtDate(s){const d=new Date(s+'T00:00:00');return(d.getMonth()+1)+'月'+d.getDate()+'日 '+['周日','周一','周二','周三','周四','周五','周六'][d.getDay()]}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}

// ===== 倒计时 =====
function startCD(){
  const el=document.getElementById('countdown');
  function upd(){
    const t=new Date('2026-06-11T14:00:00Z'),n=new Date();
    let diff=Math.max(0,Math.floor((t-n)/1000));
    const dd=Math.floor(diff/86400);diff%=86400;
    const hh=Math.floor(diff/3600);diff%=3600;
    const mm=Math.floor(diff/60);const ss=diff%60;
    if(el)el.innerHTML=
      `<div class="cd-b"><div class="cd-n">${String(dd).padStart(2,'0')}</div><div class="cd-u">天</div></div>`+
      `<div class="cd-b"><div class="cd-n">${String(hh).padStart(2,'0')}</div><div class="cd-u">时</div></div>`+
      `<div class="cd-b"><div class="cd-n">${String(mm).padStart(2,'0')}</div><div class="cd-u">分</div></div>`+
      `<div class="cd-b"><div class="cd-n">${String(ss).padStart(2,'0')}</div><div class="cd-u">秒</div></div>`;
  }
  upd();setInterval(upd,1000);
}

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===name));
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.toggle('active',p.id===name));
  if(name==='matches')renderCalendar();
}

// ===== 日历 =====
function renderCalendar(){
  const el=document.getElementById('calendar');if(!el)return;
  const now=new Date(),y=now.getFullYear(),m=now.getMonth();
  const firstDay=new Date(y,m,1).getDay(),daysInMonth=new Date(y,m+1,0).getDate();
  const todayStr=today();
  const matchDays={};DATA.matches.forEach(m=>{matchDays[m.date]=(matchDays[m.date]||0)+1});
  const liveDays=new Set(DATA.matches.filter(m=>m.status==='live').map(m=>m.date));
  let h=`<div class="cal-head"><span>📅 ${['','一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'][m]} ${y}</span></div>`;
  h+=`<div class="cal-week"><div>日</div><div>一</div><div>二</div><div>三</div><div>四</div><div>五</div><div>六</div></div><div class="cal-days">`;
  for(let i=0;i<firstDay;i++)h+='<div class="cal-d dim"></div>';
  for(let d=1;d<=daysInMonth;d++){
    const ds=`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    let cls='cal-d';
    if(ds===todayStr)cls+=' today selected';
    if(matchDays[ds])cls+=' has-match';
    if(liveDays.has(ds))cls+=' has-live';
    h+=`<div class="${cls}" onclick="filterByDate('${ds}')"><div>${d}</div>${matchDays[ds]?`<div class="cal-cnt">${matchDays[ds]}场</div>`:''}</div>`;
  }
  h+='</div>';el.innerHTML=h;
}
function filterByDate(ds){renderMatches(DATA.matches.filter(m=>m.date===ds));document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));document.querySelector('.fbtn[data-g="all"]')?.classList.add('active')}

// ===== 筛选 =====
function filterMatches(g){
  const td=today();
  if(g==='live')return DATA.matches.filter(m=>m.status==='live');
  if(g==='today')return DATA.matches.filter(m=>m.date===td);
  if(g==='upcoming')return DATA.matches.filter(m=>m.status==='upcoming');
  if(g==='finished')return DATA.matches.filter(m=>m.status==='finished');
  if(g==='fav')return DATA.matches.filter(m=>favorites.includes(m.home)||favorites.includes(m.away));
  return DATA.matches;
}

// ===== 关注球队栏 =====
function renderFavBar(){
  const el=document.getElementById('favBar');if(!el)return;
  let h='<div class="fb-title">⭐ 关注球队</div><div class="fav-chips">';
  favorites.forEach(t=>{const tf=DATA.teams[t];h+=`<div class="fav-chip">${tf?tf.flag:'🏳'} ${esc(t)}<span class="fc-rm" onclick="event.stopPropagation();removeFav('${esc(t)}')">✕</span></div>`});
  h+='<div class="fav-add" onclick="addFav()">＋ 添加</div></div>';el.innerHTML=h;
}
function addFav(){
  const avail=Object.keys(DATA.teams).filter(t=>!favorites.includes(t));
  if(!avail.length){alert('已全部关注');return}
  const pick=prompt('输入要关注的球队名：\n'+avail.join('、'));
  if(pick&&avail.includes(pick)){favorites.push(pick);saveFavs();refreshAll()}
}
function removeFav(t){favorites=favorites.filter(x=>x!==t);saveFavs();refreshAll()}
function refreshAll(){renderFavBar();renderMatches(filterMatches(document.querySelector('.fbtn.active')?.dataset.g||'all'));loadStandings(document.getElementById('gsel')?.value||'A')}

// ===== 渲染比赛列表 =====
function renderMatches(list){
  const el=document.getElementById('ml');
  if(!list||!list.length){if(el)el.innerHTML='<div class="empty">暂无比赛数据</div>';return}
  const groups={};list.forEach(m=>{if(!groups[m.date])groups[m.date]=[];groups[m.date].push(m)});
  let h='';
  Object.keys(groups).sort().forEach(d=>{
    const isToday=d===today();
    h+=`<div class="dh${isToday?' today':''}"><span class="dd"></span>${fmtDate(d)}${isToday?'  📅 今日':''}</div>`;
    groups[d].forEach(m=>{
      const lv=m.status==='live',fn=m.status==='finished';
      const tag=lv?'<span class="mc-tag tl">🔴 进行中</span>':fn?'<span class="mc-tag tf">✅ 已结束</span>':'<span class="mc-tag tu">⏳ 未开赛</span>';
      const isFav=favorites.includes(m.home)||favorites.includes(m.away);
      let evHtml='';if(m.events&&m.events.length){evHtml='<div class="mc-evs">';m.events.forEach(e=>{evHtml+=`<div class="mc-ev"><span class="et">${e.min}</span><span class="ei">${e.icon}</span><span class="evt${e.goal?' eg':''}">${esc(e.text)}</span></div>`});evHtml+='</div>'}
      let voteHtml='';if(m.prediction){const p=m.prediction,tot=p.home+p.draw+p.away||1;
        voteHtml=`<div class="mc-vote"><div class="vote-row">
          <div class="vote-opt${p.home>=Math.max(p.draw,p.away)?' voted':''}" onclick="event.stopPropagation();doVote(this,${p.home},${tot},'home',${m.id})"><div class="vote-fill" style="width:${p.home/tot*100}%"></div><div class="vote-label">🏠 ${p.home}%</div></div>
          <div class="vote-opt${p.draw>=Math.max(p.home,p.away)?' voted':''}" onclick="event.stopPropagation();doVote(this,${p.draw},${tot},'draw',${m.id})"><div class="vote-fill" style="width:${p.draw/tot*100}%"></div><div class="vote-label">🤝 ${p.draw}%</div></div>
          <div class="vote-opt${p.away>=Math.max(p.home,p.draw)?' voted':''}" onclick="event.stopPropagation();doVote(this,${p.away},${tot},'away',${m.id})"><div class="vote-fill" style="width:${p.away/tot*100}%"></div><div class="vote-label">🛫 ${p.away}%</div></div>
        </div></div>`}
      const watchHtml=lv?`<div class="wb"><a href="https://www.yangshipin.cn/" target="_blank" class="wc">📺 央视频</a><a href="https://www.miguvideo.com/" target="_blank" class="wm">📱 咪咕</a><a href="https://www.douyin.com/" target="_blank" class="wd">🎵 抖音</a></div>`:
        `<div class="wb"><a href="https://www.yangshipin.cn/" target="_blank" class="wr">⏰ 央视频提醒</a><a href="https://www.miguvideo.com/" target="_blank" class="wr">📱 咪咕预约</a></div>`;
      h+=`<div class="mc${lv?' live':''}${fn?' fin':''}" onclick="openDetail(${m.id})">
        <div class="mc-fav ${isFav?'active':''}" onclick="event.stopPropagation();toggleFavMatch('${esc(m.home)}','${esc(m.away)}')">${isFav?'⭐':''}</div>
        <div class="mc-head"><div class="mc-meta">${m.group}组 · ${m.time} · ${esc(m.venue)}</div>${tag}</div>
        <div class="mc-body">
          <div class="mc-team" onclick="event.stopPropagation();openTeam('${esc(m.home)}')"><div class="mc-flag">${m.hf}</div><div class="mc-name">${esc(m.home)}</div></div>
          ${lv?`<div class="mc-center"><div class="mc-sc">${m.hs} - ${m.as}</div><div class="mc-min">${m.minute||''}</div></div>`:fn?`<div class="mc-center"><div class="mc-sc">${m.hs} - ${m.as}</div></div>`:`<div class="mc-center"><div class="mc-vs">VS</div></div>`}
          <div class="mc-team" onclick="event.stopPropagation();openTeam('${esc(m.away)}')"><div class="mc-flag">${m.af}</div><div class="mc-name">${esc(m.away)}</div></div>
        </div>${evHtml}${voteHtml}${watchHtml}</div>`;
    });
  });
  if(el)el.innerHTML=h;
}
function toggleFavMatch(home,away){const t=favorites.includes(home)?home:(favorites.includes(away)?away:home);if(favorites.includes(t))favorites=favorites.filter(x=>x!==t);else favorites.push(t);saveFavs();refreshAll()}
function doVote(el,current,total,side,mid){const m=DATA.matches.find(x=>x.id===id);const delta=Math.floor(Math.random()*4)+1;m.prediction[side]=Math.min(95,current+delta);const fill=el.querySelector('.vote-fill');if(fill)fill.style.width=(m.prediction[side]/(m.prediction.home+m.prediction.draw+m.prediction.away)*100)+'%';const lbl=el.querySelector('.vote-label');if(lbl)lbl.textContent=(side==='home'?'🏠 ':side==='draw'?'🤝 ':'🛫 ')+m.prediction[side]+'%'}

// ===== 积分榜 =====
function loadStandings(gr){
  const d=DATA.standings[gr],el=document.getElementById('sl');
  if(!d||!el){if(el)el.innerHTML='<div class="empty">暂无数据</div>';return}
  const s=[...d].sort((a,b)=>b.pt-a.pt||(b.gf-b.ga)-(a.gf-a.ga)||b.gf-a.gf);
  let h=`<table class="stt"><thead><tr><th>#</th><th style="text-align:left">球队</th><th>赛</th><th>胜</th><th>平</th><th>负</th><th>进</th><th>失</th><th>净</th><th>分</th></tr></thead><tbody>`;
  s.forEach((t,i)=>{const isFav=favorites.includes(t.t);
    h+=`<tr class="${i<2?'qual':''}" onclick="openTeam('${esc(t.t)}')" style="cursor:pointer"><td>${i+1}${isFav?' ⭐':''}</td><td style="text-align:left"><div class="tm">${t.f} ${esc(t.t)}</div></td><td>${t.p}</td><td>${t.w}</td><td>${t.d}</td><td>${t.l}</td><td>${t.gf}</td><td>${t.ga}</td><td class="gd">${t.gf-t.ga>0?'+':''}${t.gf-t.ga}</td><td><span class="pts">${t.pt}</span></td></tr>`;
  });
  h+=`</tbody></table><div class="st-hint">🟢 前2名晋级淘汰赛 · 点击球队查看详情</div>`;el.innerHTML=h;
}

// ===== 射手榜 =====
function loadScorers(){
  const el=document.getElementById('scl');if(!el)return;
  let h='';DATA.scorers.forEach((s,i)=>{
    h+=`<div class="sr"><div class="rk ${i===0?'g1':i===1?'g2':i===2?'g3':''}">${s.r<=3?['🥇','🥈','🥉'][s.r-1]:s.r}</div><div class="sf">${s.f}</div><div class="si"><div class="sn">${esc(s.n)}</div><div class="st">${esc(s.t)}</div></div><div class="sg">${s.g}<span class="sgl">⚽</span></div></div>`;
  });
  h+='<div style="text-align:center;padding:12px 0;color:var(--dim);font-size:11px">⚽ 进球数 · 模拟数据</div>';el.innerHTML=h;
}

// ===== 资讯 =====
function loadNews(){
  const el=document.getElementById('nl');if(!el)return;
  let h='';DATA.news.forEach(n=>{
    h+=`<div class="nc" onclick="alert('资讯详情开发中...')"><div class="nt ${n.tag}">${n.tl}</div><div class="nn">${esc(n.t)}</div><div class="nm"><span>FIFA官网</span><span>2小时前</span></div></div>`;
  });el.innerHTML=h;
}

// ===== 比赛详情弹窗 =====
function openDetail(id){
  const m=DATA.matches.find(x=>x.id===id);if(!m)return;
  const bg=document.getElementById('modalBg'),md=document.getElementById('modal');
  const lv=m.status==='live',fn=m.status==='finished';
  let evHtml='';if(m.events&&m.events.length){evHtml='<div class="detail-section"><h3>📝 比赛事件</h3>';m.events.forEach(e=>{evHtml+=`<div class="detail-row"><span class="dr-t">${e.min}</span><span>${e.icon}</span><span${e.goal?' style="color:var(--gold);font-weight:600"':''}>${esc(e.text)}</span></div>`});evHtml+='</div>'}
  let predHtml='';if(m.prediction){const p=m.prediction,tot=p.home+p.draw+p.away||1;
    predHtml=`<div class="detail-section"><h3>📊 赛果预测</h3><div style="display:flex;gap:6px;margin-top:6px">
      <div style="flex:1;background:rgba(255,255,255,.05);border-radius:6px;height:24px;position:relative;overflow:hidden"><div style="position:absolute;left:0;top:0;height:100%;width:${p.home/tot*100}%;background:rgba(76,201,240,.2);border-radius:5px"></div><div style="position:relative;display:flex;align-items:center;justify-content:center;height:100%;font-size:10px;font-weight:600">🏠 ${p.home}%</div></div>
      <div style="flex:1;background:rgba(255,255,255,.05);border-radius:6px;height:24px;position:relative;overflow:hidden"><div style="position:absolute;left:0;top:0;height:100%;width:${p.draw/tot*100}%;background:rgba(230,126,34,.15);border-radius:5px"></div><div style="position:relative;display:flex;align-items:center;justify-content:center;height:100%;font-size:10px;font-weight:600">🤝 ${p.draw}%</div></div>
      <div style="flex:1;background:rgba(255,255,255,.05);border-radius:6px;height:24px;position:relative;overflow:hidden"><div style="position:absolute;left:0;top:0;height:100%;width:${p.away/tot*100}%;background:rgba(230,57,70,.15);border-radius:5px"></div><div style="position:relative;display:flex;align-items:center;justify-content:center;height:100%;font-size:10px;font-weight:600">🛫 ${p.away}%</div></div>
    </div></div>`}
  md.innerHTML=`<button class="modal-close" onclick="closeModal(event)">✕</button>
    <h2>比赛详情</h2>
    <div class="detail-teams"><div class="dt"><div class="df">${m.hf}</div><div class="dn">${esc(m.home)}</div></div><div class="dsc">${lv?m.hs+' - '+m.as:(fn?m.hs+' - '+m.as:'VS')}</div><div class="dt"><div class="df">${m.af}</div><div class="dn">${esc(m.away)}</div></div></div>
    <div style="text-align:center;font-size:11px;color:var(--dim);margin-bottom:12px">${m.group}组 · ${m.time} · ${esc(m.venue)}${lv?' · '+m.minute:''}</div>
    ${evHtml}${predHtml}
    ${lv?`<div style="margin-top:14px;display:flex;gap:8px"><a href="https://www.yangshipin.cn/" target="_blank" style="flex:1;padding:10px 0;text-align:center;background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff;border:none;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">📺 央视频直播</a><a href="https://www.miguvideo.com/" target="_blank" style="flex:1;padding:10px 0;text-align:center;background:linear-gradient(135deg,#1a5276,#2980b9);color:#fff;border:none;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">📱 咪咕直播</a></div>`:''}`;
  bg.classList.add('show');
}
function closeModal(e){if(e.target===document.getElementById('modalBg')||e.target.textContent==='✕')document.getElementById('modalBg').classList.remove('show')}

// ===== 球队详情弹窗 =====
function openTeam(name){
  const t=DATA.teams[name];if(!t){alert('球队数据开发中...');return}
  const bg=document.getElementById('modalBg'),md=document.getElementById('modal');
  const tm=DATA.matches.filter(m=>m.home===name||m.away===name).sort((a,b)=>a.date.localeCompare(b.date));
  let matchHtml='';if(tm.length){matchHtml='<div class="detail-section"><h3>📅 赛程</h3>';tm.forEach(m=>{const isH=m.home===name;matchHtml+=`<div class="tm-card"><div class="tm-vs">${m.date.slice(5)} ${m.time}</div><div style="flex:1;text-align:center;font-size:12px;font-weight:600">${isH?esc(m.home)+' <span style="color:var(--dim)">vs</span> '+esc(m.away):esc(m.away)+' <span style="color:var(--dim)">vs</span> '+esc(m.home)}</div><div class="tm-sc">${m.status==='finished'?m.hs+'-'+m.as:(m.status==='live'?'🔴':'⏳')}</div></div>`});matchHtml+='</div>'}
  const playersHtml=t.players.map((p,i)=>`<div class="squad-item"><span class="si-num">${i+1}</span><span>${esc(p)}</span></div>`).join('');
  md.innerHTML=`<button class="modal-close" onclick="closeModal(event)">✕</button>
    <div class="team-header"><div class="th-flag">${t.flag}</div><div class="th-info"><h3 style="font-size:18px;font-weight:800">${esc(name)}</h3><div style="font-size:11px;color:var(--dim);margin-top:3px">主教练：${esc(t.coach)}</div><div style="font-size:11px;color:var(--dim)">${t.group}组 · 主场：${esc(t.city)}</div></div>
    <div style="margin-left:auto;align-self:flex-start">${favorites.includes(name)?`<button onclick="removeFav('${esc(name)}');openTeam('${esc(name)}')" style="background:rgba(255,215,0,.15);border:1px solid rgba(255,215,0,.3);color:var(--gold);padding:4px 10px;border-radius:8px;font-size:11px;cursor:pointer">⭐ 已关注</button>`:`<button onclick="addFavTeam('${esc(name)}')" style="background:var(--card2);border:1px solid var(--border);color:var(--dim);padding:4px 10px;border-radius:8px;font-size:11px;cursor:pointer">＋ 关注</button>`}</div></div>
    <div class="team-squad" style="margin-top:12px"><h4>👥 阵容（部分）</h4><div class="squad-grid">${playersHtml}</div></div>${matchHtml}`;
  bg.classList.add('show');
}
function addFavTeam(name){if(!favorites.includes(name))favorites.push(name);saveFavs();openTeam(name);renderFavBar()}

function scrollToLive(){const el=document.querySelector('.mc.live');if(el)el.scrollIntoView({behavior:'smooth',block:'center'})}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded',()=>{
  startCD();
  document.querySelectorAll('.tab').forEach(tab=>tab.addEventListener('click',()=>switchTab(tab.dataset.tab)));
  document.querySelectorAll('.fbtn').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderMatches(filterMatches(btn.dataset.g))}));
  const gs=document.getElementById('gsel');if(gs)gs.addEventListener('change',e=>loadStandings(e.target.value));
  const lc=DATA.matches.filter(m=>m.status==='live').length;
  const lcel=document.getElementById('lc');if(lcel)lcel.textContent=lc||'';
  renderCalendar();renderFavBar();renderMatches(DATA.matches);loadStandings('A');loadScorers();loadNews();
});


// ============ Event Delegation ============
document.addEventListener("click", function(e) {
  var el = e.target.closest("[data-action]");
  if (!el) return;
  var action = el.dataset.action;
  var args = el.dataset.args || "";
  switch(action) {
    case "closeModal": closeModal(args); break;
    case "scrollToLive": scrollToLive(); break;
    case "switchTab": switchTab(args); break;
  }
});
