// ui/app.js — Notion(블록/DB) + Obsidian(그래프) 최소 UI
// 데이터는 /api/* 에서 가져옴 (ui/server.py가 memory/*.jsonl을 읽어 제공)

function show(id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
  if(id==='blocks') loadBlocks();
  if(id==='database') loadDB();
  if(id==='graph') loadGraph();
  if(id==='queue') loadQueue();
}

async function loadBlocks(){
  const el=document.getElementById('blocks');
  el.innerHTML='<small>로딩...</small>';
  try{
    const r=await fetch('/api/blocks'); const j=await r.json();
    if(!j.blocks.length){ el.innerHTML='<p>블록 없음 — notion/blocks.py --add 로 추가</p>'; return; }
    el.innerHTML = j.blocks.map(b=>`<div class="block ${b.type}"><small>${b.type} · ${b.id} · ${b.created||''}</small><div>${esc(b.content)}</div></div>`).join('');
  }catch(e){ el.innerHTML='<p>API 연결 안 됨 — python ui/server.py 실행 필요</p>'; }
}
async function loadDB(){
  const el=document.getElementById('database');
  el.innerHTML='<small>로딩...</small>';
  try{
    const r=await fetch('/api/database'); const j=await r.json();
    const rows=j.results||[];
    if(!rows.length){ el.innerHTML='<p>세션 없음</p>'; return; }
    el.innerHTML='<table><tr><th>task</th><th>model</th><th>date</th></tr>'+rows.map(x=>`<tr><td>${esc(x.task||x.type||'')}</td><td>${esc(x.model||'')}</td><td>${esc((x.created||'').slice(0,10))}</td></tr>`).join('')+'</table>';
  }catch(e){ el.innerHTML='<p>API 연결 안 됨</p>'; }
}
async function loadQueue(){
  const el=document.getElementById('queue');
  try{
    const r=await fetch('/api/queue'); const j=await r.json();
    const q=j.queue||[];
    el.innerHTML=q.length? q.map(x=>`<div class="block">${esc(x.task)} <small>${esc(x.queued||'')}</small></div>`).join('') : '<p>큐 비어있음</p>';
  }catch(e){ el.innerHTML='<p>API 연결 안 됨</p>'; }
}
async function loadGraph(){
  // Obsidian 그래프: 블록/세션을 노드로, 간단 캔버스
  const c=document.getElementById('c'), ctx=c.getContext('2d');
  ctx.clearRect(0,0,c.width,c.height);
  try{
    const [b,d]=await Promise.all([fetch('/api/blocks').then(r=>r.json()), fetch('/api/database').then(r=>r.json())]);
    const nodes=[...b.blocks.slice(-8).map(x=>({label:x.id, x:Math.random()*700+50, y:Math.random()*300+50, c:'#ff6b6b'})),
                 ...d.results.slice(-8).map(x=>({label:(x.task||'').slice(0,10), x:Math.random()*700+50, y:Math.random()*300+50, c:'#4dabf7'}))];
    if(!nodes.length){ ctx.fillText('데이터 없음 — 분석을 한 번 돌리세요', 20, 40); return; }
    // 간선
    ctx.strokeStyle='#ddd';
    for(let i=1;i<nodes.length;i++){ ctx.beginPath(); ctx.moveTo(nodes[i-1].x,nodes[i-1].y); ctx.lineTo(nodes[i].x,nodes[i].y); ctx.stroke(); }
    // 노드
    nodes.forEach(n=>{ ctx.fillStyle=n.c; ctx.beginPath(); ctx.arc(n.x,n.y,12,0,Math.PI*2); ctx.fill(); ctx.fillStyle='#333'; ctx.fillText(n.label, n.x-20, n.y-16); });
  }catch(e){ ctx.fillText('API 연결 안 됨', 20, 40); }
}
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadBlocks();
