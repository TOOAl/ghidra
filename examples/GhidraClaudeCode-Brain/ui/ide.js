let lastReport='',lastTask='',currentPath='',cm,allFiles=[];
function toast(m,ms=1800){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),ms)}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function log(msg){const el=document.getElementById('consoleLog');const ts=new Date().toLocaleTimeString();el.textContent+=`\n[${ts}] ${msg}`;el.scrollTop=el.scrollHeight;console.log(msg)}
function setStatus(ok,t){const d=document.getElementById('statusDot'),x=document.getElementById('statusText');d.className='dot '+(ok===true?'ok':ok===false?'bad':ok==='warn'?'warn':'');x.textContent=t}
async function checkHealth(){try{const r=await fetch('/api/status');const j=await r.json();const llm=j.llm||{};if(llm.mode==='real')setStatus(true,'● 서버 + 🧠 ON ('+llm.model+')');else if(llm.mode==='mock')setStatus('warn','● 서버 + ⏸ 모형: '+llm.detail);else setStatus(true,'● 서버 연결됨')}catch{setStatus(false,'● 서버 안 켜짐 — python ui/server.py')}
}
async function loadModels(){try{const r=await fetch('/api/status');const j=await r.json();const s=document.getElementById('model');const hint=document.getElementById('modelHint');s.innerHTML=(j.presets||[]).map(p=>`<option value="${p}" ${p===j.default?'selected':''}>${p}</option>`).join('');if(j.llm&&j.llm.detail)hint.textContent=(j.llm.mode==='mock'?'⏸ ':'🧠 ')+j.llm.detail; s.onchange=async()=>{await fetch('/api/set_model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({preset:s.value})});toast('모델: '+s.value);checkHealth()}}catch(e){setStatus(false,'모델 로드 실패')}
}

// File tree
async function refreshFiles(){
  try{
    const r=await fetch('/api/files');const j=await r.json();allFiles=j.files||[];
    renderFiles(allFiles);
    log(`파일 ${allFiles.length}개 로드`)
  }catch(e){document.getElementById('fileTree').textContent='로드 실패: '+e;log('파일 목록 실패: '+e)}
}
function renderFiles(files){
  const el=document.getElementById('fileTree');
  const groups={}; files.forEach(f=>{ (groups[f.dir]=groups[f.dir]||[]).push(f)});
  el.innerHTML=Object.keys(groups).sort().map(dir=>`
    <div class="file-group">
      <div class="file-group-title">📂 ${esc(dir)} (${groups[dir].length})</div>
      ${groups[dir].map(f=>`<div class="file-item ${f.path===currentPath?'active':''}" onclick="openFile('${f.path}')" title="${f.path}">${esc(f.name)} <small>${f.size}B</small></div>`).join('')}
    </div>`).join('') || '<div class="file-item">파일 없음</div>';
}
function filterFiles(){
  const q=document.getElementById('fileSearch').value.toLowerCase();
  const filtered=!q? allFiles : allFiles.filter(f=> f.path.toLowerCase().includes(q) || f.name.toLowerCase().includes(q));
  renderFiles(filtered);
}
let dirty=false;
function setDirty(v){
  dirty=v;
  const s=document.getElementById('saveStatus');
  s.textContent=v?'● 저장 안 됨':'저장됨';
  s.className='save-status '+(v?'dirty':'');
}
async function openFile(path){
  try{
    const r=await fetch('/api/file?path='+encodeURIComponent(path));
    const j=await r.json();
    if(!j.ok) throw new Error(j.error);
    currentPath=path;
    document.getElementById('currentFile').textContent=path;
    if(cm){
      cm.setValue(j.content);
      cm.clearHistory();
      setDirty(false);
      setTimeout(()=>cm.refresh(),50);
    } else {
      document.getElementById('codeArea').value=j.content;
    }
    document.getElementById('fileInfo').textContent=j.size+'B · '+path.split('.').pop();
    refreshFiles();
    log(`열기: ${path} (${j.size}B)`);
    // update cursor
  }catch(e){toast('열기 실패: '+e,2500);log('열기 실패 '+path+': '+e)}
}
async function saveFile(){
  if(!currentPath) return toast('파일을 먼저 선택해');
  const content=cm? cm.getValue() : document.getElementById('codeArea').value;
  document.getElementById('saveBtn').textContent='⏳ 저장 중...';
  try{
    const r=await fetch('/api/file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:currentPath, content})});
    const j=await r.json();
    if(!j.ok) throw new Error(j.error + (j.line? ' (줄 '+j.line+')':''));
    setDirty(false);
    toast('저장 완료: '+currentPath);
    log(`저장: ${currentPath} (${j.size}B)`);
    refreshFiles();
  }catch(e){toast('저장 실패: '+e,3000);log('저장 실패: '+e)}
  document.getElementById('saveBtn').textContent='💾 저장 Ctrl+S';
}
async function runFromEditor(){ await saveFile(); run(); }

// Editor init
function initEditor(){
  const ta=document.getElementById('codeArea');
  if(typeof CodeMirror!=='undefined'){
    cm=CodeMirror.fromTextArea(ta,{
      lineNumbers:true, mode:'python', theme:'dracula',
      matchBrackets:true, autoCloseBrackets:true, lineWrapping:true,
      indentUnit:4, tabSize:4
    });
    cm.on('change',()=>{ setDirty(true); updateCursor() });
    cm.on('cursorActivity', updateCursor);
    log('에디터 준비 (CodeMirror dracula) — Ctrl+S 저장, Ctrl+Enter 실행');
  } else {
    ta.addEventListener('input',()=>setDirty(true));
    log('에디터 준비 (textarea) — CDN 실패 시 대체 모드');
  }
}
function updateCursor(){
  const pos=cm? cm.getCursor() : null;
  if(pos) document.getElementById('cursorPos').textContent=`Ln ${pos.line+1}, Col ${pos.ch+1}`;
}

// Preview (reuse app.js logic)
function showTab(id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.preview-tabs button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.querySelector(`[data-tab="${id}"]`).classList.add('active');
  if(id==='blocks')loadBlocks(); if(id==='graph')loadGraph();
}
function clearConsole(){document.getElementById('consoleLog').textContent='콘솔 지움 — 다음 로그부터 표시';}
function quick(t){document.getElementById('task').value=t;toast('작업: '+t)}
function clearAll(){document.getElementById('task').value='';document.getElementById('reportBody').innerHTML='';document.getElementById('reportExtras').innerHTML='';document.getElementById('reportContent').style.display='block';toast('지웠다')}
async function run(){
  const b=document.getElementById('runBtn'),task=document.getElementById('task').value.trim(),binary=document.getElementById('binary').value.trim()||'/bin/ls',preset=document.getElementById('model').value;
  if(!task){toast('작업 칸에 써봐');document.getElementById('task').focus();return}
  lastTask=task; b.disabled=true; b.textContent='⏳ 실행 중...';
  const body=document.getElementById('reportBody'),extras=document.getElementById('reportExtras'),empty=document.getElementById('reportContent'),actions=document.getElementById('reportActions');
  empty.style.display='none'; body.innerHTML='<div class="loading"><span class="spinner"></span> 외부 LLM에 물어보고 로컬 4개 도구 실행 중...</div>'; extras.innerHTML=''; actions.style.display='none'; showTab('report');
  log(`실행: ${task} | ${binary} | ${preset}`);
  try{
    const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task,binary,preset})});
    if(!r.ok) throw new Error('서버 '+r.status);
    const j=await r.json();
    if(j.error&&!j.report) throw new Error(j.error);
    lastReport=j.report||'';
    body.innerHTML=`<div class="report-card"><div class="report-head"><h3>📝 ${esc(task)}</h3><span class="badge ${j.contradiction&&j.contradiction.ok?'badge-green':'badge'}">${j.contradiction?esc(j.contradiction.summary):''}</span></div><pre>${esc(j.report||'')}</pre></div>`+(j.ok?'<div class="success-banner">✅ 보고서 저장 — 왼쪽 코드와 오른쪽 결과가 연결됐다</div>':'');
    let h=''; if(j.reasoning)h+=card('🧠 추론',j.reasoning.ok?'ok':'bad',j.reasoning.steps?j.reasoning.steps.join(' → '):j.reasoning.reason); if(j.analysis)h+=card('📊 분석','ok',j.analysis.insight+' '+(j.analysis.pattern||'')); if(j.train)h+=card('📚 학습',j.train.ok?'ok':'bad',j.train.insight+' | 예측:'+j.train.prediction); if(j.team)h+=card('👥 팀 토론',j.team.consensus==='4/4'?'ok':'',j.team.insight+' | 합의 '+j.team.consensus); if(j.ear)h+=card('👂 귀 감성','',j.ear.insight+' (score '+j.ear.score+')'); if(j.contradiction)h+=card('✅ 모순',j.contradiction.ok?'ok':'bad',j.contradiction.summary); if(j.llm)h+=card('🧠 생각 빌리기',j.llm.mode==='real'?'ok':'',j.llm.mode==='real'? j.llm.provider+'/'+j.llm.model+': '+(j.llm.text||'') : '⏸ 모형: '+(j.llm.reason||''));
    extras.innerHTML=`<div class="report-extra">${h}</div>`; actions.style.display='flex'; document.getElementById('reportMeta').textContent=`${j.preset} · ${new Date().toLocaleTimeString()}`;
    toast('완료 — 오른쪽에 6섹션 떴다!'); log(`완료: ${task} → 모순 ${j.contradiction.summary} | LLM ${j.llm.mode}`);
  }catch(e){body.innerHTML=`<div class="extra-card bad"><strong>❌ 실패</strong><p>${esc(e.message)}</p></div>`; toast('실패: '+e.message,2500); log('실행 실패: '+e.message)}
  b.disabled=false; b.textContent='▶ 실행 Ctrl+Enter';
}
function card(t,k,b){return `<div class="extra-card ${k}"><strong>${t}</strong><p>${esc(b||'')}</p></div>`}
function copyReport(){if(!lastReport) return toast('복사할 보고서 없음'); navigator.clipboard.writeText(lastReport).then(()=>toast('복사 완료'))}
function downloadReport(){if(!lastReport) return toast('다운로드할 보고서 없음'); const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lastReport],{type:'text/markdown'}));a.download=(lastTask||'report').replace(/\s+/g,'_')+'.md';a.click();toast('다운로드 시작')}
async function loadBlocks(){const el=document.getElementById('blocksList');el.innerHTML='<div class="loading"><span class="spinner"></span> 로딩...</div>';try{const r=await fetch('/api/blocks');const j=await r.json();el.innerHTML=(j.blocks||[]).slice(-10).reverse().map(x=>`<div class="block"><small>${esc(x.type)} · ${esc(x.id)}</small><div>${esc(x.content).slice(0,600)}</div></div>`).join('')||'<div class="block">블록 없음</div>'}catch{el.innerHTML='API 연결 안 됨'}}
async function loadGraph(){const c=document.getElementById('c');if(!c) return;const ctx=c.getContext('2d'),dpr=window.devicePixelRatio||1,w=c.clientWidth||600,h=320;c.width=w*dpr;c.height=h*dpr;c.style.width=w+'px';c.style.height=h+'px';ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);try{const [b,d]=await Promise.all([fetch('/api/blocks').then(r=>r.json()),fetch('/api/database').then(r=>r.json())]);const nodes=[...b.blocks.slice(-6).map(x=>({label:x.id.slice(0,6),x:Math.random()*(w-80)+40,y:Math.random()*(h-60)+30,c:'#6366f1'})),...d.results.slice(-6).map(x=>({label:(x.task||'?').slice(0,6),x:Math.random()*(w-80)+40,y:Math.random()*(h-60)+30,c:'#06b6d4'}))];if(!nodes.length){ctx.fillStyle='#64748b';ctx.fillText('데이터 없음 — ▶ 실행하면 연결된다',20,40);return}ctx.strokeStyle='#e2e8f0';for(let i=1;i<nodes.length;i++){ctx.beginPath();ctx.moveTo(nodes[i-1].x,nodes[i-1].y);ctx.lineTo(nodes[i].x,nodes[i].y);ctx.stroke()}nodes.forEach(n=>{ctx.fillStyle=n.c;ctx.beginPath();ctx.arc(n.x,n.y,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.font='bold 9px sans-serif';ctx.textAlign='center';ctx.fillText(n.label[0]||'●',n.x,n.y+3)})}catch{ctx.fillStyle='#f87171';ctx.fillText('API 연결 안 됨',20,40)}}

// Splitter
function initSplitter(){
  const s=document.getElementById('splitter'),left=document.getElementById('paneLeft');
  let dragging=false;
  s.addEventListener('mousedown',e=>{dragging=true;document.body.style.cursor='col-resize';e.preventDefault()});
  document.addEventListener('mousemove',e=>{
    if(!dragging) return;
    const total=document.querySelector('.ide-layout').clientWidth;
    let pct=(e.clientX/total)*100;
    pct=Math.max(22,Math.min(68,pct));
    left.style.flex=`0 0 ${pct}%`;
    if(cm) setTimeout(()=>cm.refresh(),30);
  });
  document.addEventListener('mouseup',()=>{if(dragging){dragging=false;document.body.style.cursor=''; if(cm) cm.refresh()}});
}

// Keys
document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==='s'){ e.preventDefault(); saveFile() }
  if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){ e.preventDefault(); run() }
  if(e.key==='Escape'&&!e.ctrlKey) clearAll();
});

// Init
document.addEventListener('DOMContentLoaded',()=>{initEditor();initSplitter();refreshFiles();loadModels();checkHealth();setInterval(checkHealth,8000);log('IDE 준비 — 왼쪽 파일 선택 → 코딩 → Ctrl+S → Ctrl+Enter')});
// Ctrl+Enter on inputs
document.addEventListener('DOMContentLoaded',()=>{
  ['task','binary'].forEach(id=>{
    const el=document.getElementById(id);
    if(el) el.addEventListener('keydown',e=>{ if(e.key==='Enter'&&!e.ctrlKey){ e.preventDefault(); run() }})
  });
});
