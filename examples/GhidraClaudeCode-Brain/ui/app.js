// 웹 프로그램 — 실행 + 모델 한 글자 진화
function show(id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(event && event.target) event.target.classList.add('active');
  if(id==='blocks') loadBlocks();
  if(id==='database') loadDB();
  if(id==='graph') loadGraph();
  if(id==='queue') loadQueue();
}
async function loadModels(){
  try{
    const r=await fetch('/api/models'); const j=await r.json();
    const sel=document.getElementById('model');
    sel.innerHTML = (j.presets||[]).map(p=>`<option value="${p}" ${p===j.default?'selected':''}>${p}</option>`).join('');
    if(!sel.innerHTML) sel.innerHTML='<option>no presets</option>';
    sel.onchange = async ()=>{
      await fetch('/api/set_model', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({preset: sel.value})});
      alert('한 글자 진화 완료: '+sel.value);
    };
  }catch(e){}
}
async function run(){
  const btn=document.getElementById('runBtn'), task=document.getElementById('task').value, binary=document.getElementById('binary').value, preset=document.getElementById('model').value;
  btn.disabled=true; btn.textContent='⏳ 실행중...';
  const rep=document.getElementById('report'); rep.innerHTML='<p>외부 LLM(무료)에게 물어보고, 로컬 도구 실행 중...</p>';
  try{
    const r=await fetch('/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task,binary,preset})});
    const j=await r.json();
    let extra = '';
    if(j.reasoning) extra += `<p><small>🧠 추론: ${esc(j.reasoning.steps? j.reasoning.steps.join(' → '): j.reasoning.reason||'')}</small></p>`;
    if(j.analysis) extra += `<p><small>📊 분석: ${esc(j.analysis.insight||'')} (${esc(j.analysis.pattern||'')})</small></p>`;
    if(j.train) extra += `<p><small>📚 학습: ${esc(j.train.insight||'')} | 예측: ${esc(j.train.prediction||'')}</small></p>`;
    rep.innerHTML = `<pre>${esc(j.report||j.error||'')}</pre>` + extra + (j.contradiction? `<p><small>모순: ${esc(j.contradiction.summary)}</small></p>`:'');
    show('report');
  }catch(e){ rep.innerHTML='<p>실패: '+esc(e.message)+'</p>'; }
  btn.disabled=false; btn.textContent='▶ 실행';
}
async function loadBlocks(){
  const el=document.getElementById('blocks'); el.innerHTML='<small>로딩...</small>';
  try{ const r=await fetch('/api/blocks'); const j=await r.json(); const b=j.blocks||[];
    el.innerHTML = b.length? b.slice(-20).reverse().map(x=>`<div class="block ${x.type}"><small>${x.type} · ${x.id}</small><div>${esc(x.content)}</div></div>`).join('') : '<p>블록 없음</p>';
  }catch(e){ el.innerHTML='<p>API 연결 안 됨</p>'; }
}
async function loadDB(){
  const el=document.getElementById('database'); el.innerHTML='<small>로딩...</small>';
  try{ const r=await fetch('/api/database'); const j=await r.json(); const rows=j.results||[];
    el.innerHTML = rows.length? '<table><tr><th>task</th><th>preset</th></tr>'+rows.slice(-20).reverse().map(x=>`<tr><td>${esc(x.task||x.type||'')}</td><td>${esc(x.preset||x.model||'')}</td></tr>`).join('')+'</table>' : '<p>세션 없음</p>';
  }catch(e){ el.innerHTML='<p>API 연결 안 됨</p>'; }
}
async function loadQueue(){
  const el=document.getElementById('queue');
  try{ const r=await fetch('/api/queue'); const j=await r.json(); const q=j.queue||[];
    el.innerHTML = q.length? q.map(x=>`<div class="block">${esc(x.task)}<small> ${esc(x.queued||'')}</small></div>`).join('') : '<p>큐 비어있음</p>';
  }catch(e){ el.innerHTML='<p>API 연결 안 됨</p>'; }
}
async function loadGraph(){
  const c=document.getElementById('c'), ctx=c.getContext('2d'); ctx.clearRect(0,0,c.width,c.height);
  try{
    const [b,d]=await Promise.all([fetch('/api/blocks').then(r=>r.json()), fetch('/api/database').then(r=>r.json())]);
    const nodes=[...b.blocks.slice(-8).map(x=>({label:x.id.slice(0,8),x:Math.random()*700+50,y:Math.random()*300+50,c:'#ff6b6b'})), ...d.results.slice(-8).map(x=>({label:(x.task||'').slice(0,8),x:Math.random()*700+50,y:Math.random()*300+50,c:'#4dabf7'}))];
    if(!nodes.length){ ctx.fillText('데이터 없음',20,40); return; }
    ctx.strokeStyle='#ddd'; for(let i=1;i<nodes.length;i++){ ctx.beginPath(); ctx.moveTo(nodes[i-1].x,nodes[i-1].y); ctx.lineTo(nodes[i].x,nodes[i].y); ctx.stroke(); }
    nodes.forEach(n=>{ ctx.fillStyle=n.c; ctx.beginPath(); ctx.arc(n.x,n.y,10,0,Math.PI*2); ctx.fill(); ctx.fillStyle='#222'; ctx.fillText(n.label,n.x-18,n.y-14); });
  }catch(e){ ctx.fillText('API 연결 안 됨',20,40); }
}
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
loadModels(); loadBlocks();
