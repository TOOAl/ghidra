let lastReport='',lastTask='',currentPath='',cm,allFiles=[];
function toast(m,ms=1800){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),ms)}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function log(msg){const el=document.getElementById('consoleLog');const ts=new Date().toLocaleTimeString();el.textContent+=`\n[${ts}] ${msg}`;el.scrollTop=el.scrollHeight;console.log(msg)}
function setStatus(ok,t){const d=document.getElementById('statusDot'),x=document.getElementById('statusText');d.className='dot '+(ok===true?'ok':ok===false?'bad':ok==='warn'?'warn':'');x.textContent=t}
async function checkHealth(){try{const r=await fetch('/api/status');const j=await r.json();const llm=j.llm||{};if(llm.mode==='real')setStatus(true,'● 서버 + 🧠 ON ('+llm.model+')');else if(llm.mode==='mock')setStatus('warn','● 서버 + ⏸ 모형: '+llm.detail);else setStatus(true,'● 서버 연결됨')}catch{setStatus(false,'● 서버 안 켜짐 — python ui/server.py')}
}
async function loadModels(){try{const r=await fetch('/api/status');const j=await r.json();const s=document.getElementById('model');const hint=document.getElementById('modelHint');const cmodel=document.getElementById('chatModel');s.innerHTML=(j.presets||[]).map(p=>`<option value="${p}" ${p===j.default?'selected':''}>${p}</option>`).join('');const detail=j.llm&&j.llm.detail? (j.llm.mode==='mock'?'⏸ ':'🧠 ')+j.llm.detail : ''; if(hint) hint.textContent=detail; if(cmodel) cmodel.textContent=(j.default||'')+' · '+(j.llm?j.llm.mode:''); s.onchange=async()=>{await fetch('/api/set_model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({preset:s.value})});toast('모델: '+s.value);checkHealth()}}catch(e){setStatus(false,'모델 로드 실패')}
}
function setupChatInput(){
  const ta=document.getElementById('task');
  if(!ta) return;
  ta.addEventListener('keydown', e=>{
    if(e.key==='Enter' && !e.shiftKey){
      e.preventDefault(); run();
    }
  });
  ta.addEventListener('input', ()=>{
    ta.style.height='auto'; ta.style.height=Math.min(100, ta.scrollHeight)+'px';
  });
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
    // 자동 테스트
    if(document.getElementById('autoTest')?.checked){
      log('자동 테스트 실행 중...');
      runTest('verify');
    }
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
  const chatTabs=document.querySelector('.pv-body');
  document.querySelectorAll('.pv-body .panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.chat-tabs button').forEach(b=>b.classList.remove('active'));
  const el=document.getElementById(id);
  if(el) el.classList.add('active');
  const tab=document.querySelector(`[data-tab="${id}"]`);
  if(tab) tab.classList.add('active');
  // show pv-body when blocks/graph requested
  if(id==='blocks' || id==='graph'){
    if(chatTabs) chatTabs.style.display='block';
    document.querySelector('.chat').style.display='none';
  } else {
    if(chatTabs) chatTabs.style.display='none';
  }
  if(id==='blocks')loadBlocks(); if(id==='graph')loadGraph();
}
function showBottom(id){
  document.querySelectorAll('.bpanel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));
  document.getElementById('b-'+id)?.classList.add('active');
  document.querySelector(`[data-btab="${id}"]`)?.classList.add('active');
  if(id==='git') loadGit(); if(id==='test') loadTests();
}
function clearConsole(){document.getElementById('consoleLog').textContent='콘솔 지움 — 다음 로그부터 표시';}
function quick(t){const el=document.getElementById('task'); if(el){el.value=t; el.dispatchEvent(new Event('input')); el.focus()} toast('작업: '+t)}
function quickChat(t){const el=document.getElementById('task'); if(el){el.value=t; el.dispatchEvent(new Event('input')); el.focus()} toast('작업: '+t)}
function clearAll(){document.getElementById('task').value='';document.getElementById('reportBody').innerHTML='';document.getElementById('reportExtras').innerHTML='';const ec=document.getElementById('reportContent'); if(ec) ec.style.display='block'; toast('지웠다')}
function clearChat(){document.getElementById('chatHistory').innerHTML='<div class="chat-empty"><div class="chat-empty-icon">◉</div><h3>무엇을 도와드릴까요?</h3><p>예: <code>C2 찾아줘</code></p></div>'; toast('대화 지움')}
function quickChat(t){document.getElementById('task').value=t; document.getElementById('task').dispatchEvent(new Event('input')); document.getElementById('task').focus()}
function addChat(role, text, meta=''){
  const hist=document.getElementById('chatHistory');
  // remove empty placeholder
  const emp=hist.querySelector('.chat-empty'); if(emp) emp.remove();
  const wrap=document.createElement('div');
  wrap.className='msg '+(role==='user'?'msg-user':'msg-assistant');
  const avatar=role==='user'?'나':'◉';
  // render markdown-lite: ```code``` → pre, ## → bold, - → list
  let html=esc(text);
  html=html.replace(/```(\w+)?\n?([\s\S]*?)```/g,'<pre>$2</pre>');
  html=html.replace(/\n/g,'<br>');
  wrap.innerHTML=`<div class="msg-avatar">${avatar}</div><div><div class="msg-bubble">${html}</div>${meta?'<div class="msg-meta">'+esc(meta)+'</div>':''}</div>`;
  hist.appendChild(wrap);
  hist.scrollTop=hist.scrollHeight;
  return wrap;
}
async function run(){
  const b=document.getElementById('runBtn'),task=document.getElementById('task').value.trim(),binary=document.getElementById('binary').value.trim()||'/bin/ls',preset=document.getElementById('model').value;
  if(!task){toast('메시지를 입력하세요');document.getElementById('task').focus();return}
  lastTask=task;
  // Claude Code style: add user bubble instantly
  addChat('user', task, binary+' · '+preset);
  document.getElementById('task').value='';
  const ta=document.getElementById('task'); if(ta) ta.style.height='36px';
  b.disabled=true; b.textContent='…';
  log(`실행: ${task} | ${binary} | ${preset}`);
  // show typing indicator
  const typing=addChat('assistant','… 생각 중 …', preset);
  try{
    const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task,binary,preset})});
    if(!r.ok) throw new Error('서버 '+r.status);
    const j=await r.json();
    if(j.error&&!j.report) throw new Error(j.error);
    lastReport=j.report||'';
    typing.remove();
    // main report as chat bubble
    const meta=`${j.preset} · ${new Date().toLocaleTimeString()} · ${j.contradiction?j.contradiction.summary:''}`;
    addChat('assistant', j.report||'(보고서 없음)', meta);
    // also update detailed report panel (hidden but for copy/download)
    const body=document.getElementById('reportBody'), extras=document.getElementById('reportExtras'), empty=document.getElementById('reportContent'), actions=document.getElementById('reportActions');
    if(body){
      if(empty) empty.style.display='none';
      body.innerHTML=`<div class="report-card"><div class="report-head"><h3>${esc(task)}</h3><span class="badge ${j.contradiction&&j.contradiction.ok?'badge-green':'badge'}">${j.contradiction?esc(j.contradiction.summary):''}</span></div><pre>${esc(j.report||'')}</pre></div>`;
      let h=''; if(j.reasoning)h+=card('추론',j.reasoning.ok?'ok':'bad',j.reasoning.steps?j.reasoning.steps.join(' → '):j.reasoning.reason); if(j.analysis)h+=card('분석','ok',j.analysis.insight+' '+(j.analysis.pattern||'')); if(j.train)h+=card('학습',j.train.ok?'ok':'bad',j.train.insight+' | 예측:'+j.train.prediction); if(j.team)h+=card('팀 토론',j.team.consensus==='4/4'?'ok':'',j.team.insight+' | 합의 '+j.team.consensus); if(j.ear)h+=card('귀 감성','',j.ear.insight+' (score '+j.ear.score+')'); if(j.contradiction)h+=card('모순',j.contradiction.ok?'ok':'bad',j.contradiction.summary); if(j.llm)h+=card('생각 빌리기',j.llm.mode==='real'?'ok':'',j.llm.mode==='real'? j.llm.provider+'/'+j.llm.model+': '+(j.llm.text||'') : '⏸ 모형: '+(j.llm.reason||''));
      if(extras) extras.innerHTML=`<div class="report-extra">${h}</div>`;
      if(actions) actions.style.display='flex';
      const metaEl=document.getElementById('reportMeta'); if(metaEl) metaEl.textContent=meta;
    }
    toast('완료 — 대화에 응답이 추가됐다'); log(`완료: ${task} → ${j.contradiction.summary} | ${j.llm.mode}`);
  }catch(e){
    typing.remove();
    addChat('assistant','❌ 실패: '+e.message);
    toast('실패: '+e.message,2500); log('실행 실패: '+e.message)
  }
  b.disabled=false; b.textContent='↑';
}
function card(t,k,b){return `<div class="extra-card ${k}"><strong>${t}</strong><p>${esc(b||'')}</p></div>`}
function copyReport(){if(!lastReport) return toast('복사할 보고서 없음'); navigator.clipboard.writeText(lastReport).then(()=>toast('복사 완료'))}
function downloadReport(){if(!lastReport) return toast('다운로드할 보고서 없음'); const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lastReport],{type:'text/markdown'}));a.download=(lastTask||'report').replace(/\s+/g,'_')+'.md';a.click();toast('다운로드 시작')}
async function loadBlocks(){const el=document.getElementById('blocksList');el.innerHTML='<div class="loading"><span class="spinner"></span> 로딩...</div>';try{const r=await fetch('/api/blocks');const j=await r.json();el.innerHTML=(j.blocks||[]).slice(-10).reverse().map(x=>`<div class="block"><small>${esc(x.type)} · ${esc(x.id)}</small><div>${esc(x.content).slice(0,600)}</div></div>`).join('')||'<div class="block">블록 없음</div>'}catch{el.innerHTML='API 연결 안 됨'}}
async function loadGraph(){const c=document.getElementById('c');if(!c) return;const ctx=c.getContext('2d'),dpr=window.devicePixelRatio||1,w=c.clientWidth||600,h=320;c.width=w*dpr;c.height=h*dpr;c.style.width=w+'px';c.style.height=h+'px';ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);try{const [b,d]=await Promise.all([fetch('/api/blocks').then(r=>r.json()),fetch('/api/database').then(r=>r.json())]);const nodes=[...b.blocks.slice(-6).map(x=>({label:x.id.slice(0,6),x:Math.random()*(w-80)+40,y:Math.random()*(h-60)+30,c:'#6366f1'})),...d.results.slice(-6).map(x=>({label:(x.task||'?').slice(0,6),x:Math.random()*(w-80)+40,y:Math.random()*(h-60)+30,c:'#06b6d4'}))];if(!nodes.length){ctx.fillStyle='#64748b';ctx.fillText('데이터 없음 — ▶ 실행하면 연결된다',20,40);return}ctx.strokeStyle='#e2e8f0';for(let i=1;i<nodes.length;i++){ctx.beginPath();ctx.moveTo(nodes[i-1].x,nodes[i-1].y);ctx.lineTo(nodes[i].x,nodes[i].y);ctx.stroke()}nodes.forEach(n=>{ctx.fillStyle=n.c;ctx.beginPath();ctx.arc(n.x,n.y,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.font='bold 9px sans-serif';ctx.textAlign='center';ctx.fillText(n.label[0]||'●',n.x,n.y+3)})}catch{ctx.fillStyle='#f87171';ctx.fillText('API 연결 안 됨',20,40)}}

// Terminal
async function runTerminal(){
  const inp=document.getElementById('termInput'), out=document.getElementById('termOutput');
  const cmd=inp.value.trim(); if(!cmd) return toast('명령을 써봐');
  out.textContent+=`\n$ ${cmd}\n... 실행 중 ...`;
  log(`터미널: $ ${cmd}`);
  try{
    const r=await fetch('/api/terminal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd})});
    const j=await r.json();
    out.textContent+=`\n${j.output||j.error||''}\n[exit ${j.exit}]`;
    out.scrollTop=out.scrollHeight;
    log(`터미널 완료 exit=${j.exit}`);
  }catch(e){ out.textContent+=`\n실패: ${e}`; toast('터미널 실패: '+e)}
}
function termQuick(cmd){document.getElementById('termInput').value=cmd;runTerminal()}
function clearTerminal(){document.getElementById('termOutput').textContent='터미널 지움 — 새 명령을 써봐';}

// Git
async function loadGit(){
  const s=document.getElementById('gitStatus'), lg=document.getElementById('gitLog'), br=document.getElementById('gitBranch');
  s.textContent='로딩...'; lg.textContent='로딩...';
  try{
    const [st, log] = await Promise.all([fetch('/api/git/status').then(r=>r.json()), fetch('/api/git/log').then(r=>r.json())]);
    s.textContent=st.status||st.error||''; br.textContent=st.branch? `(${st.branch})`:''; lg.textContent=log.log||log.error||'';
    loadGitDiff();
  }catch(e){s.textContent='로드 실패: '+e}
}
async function loadGitDiff(){
  const el=document.getElementById('gitDiff'); el.textContent='diff 로딩...';
  try{
    const r=await fetch('/api/git/diff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    const j=await r.json();
    el.textContent=j.diff||j.error||'(변경 없음)';
    // 파일 클릭 시 해당 diff
    // 색상 하이라이트는 CSS로 .add/.del 처리하려면 줄별 span 필요하지만 pre로 간단 처리
  }catch(e){el.textContent='diff 실패: '+e}
}
function gitDiffForFile(path){
  fetch('/api/git/diff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})})
    .then(r=>r.json()).then(j=>{document.getElementById('gitDiff').textContent=j.diff||j.error; showTab('git')});
}
async function gitCommitPrompt(){
  const msg=prompt('커밋 메시지 (3자 이상):','IDE에서 수정 — 자동 커밋');
  if(!msg) return;
  const el=document.getElementById('gitDiff');
  el.textContent='커밋 중...';
  try{
    const r=await fetch('/api/git/commit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const j=await r.json();
    el.textContent=j.output||j.error||JSON.stringify(j);
    toast(j.ok?'커밋 완료':'커밋 실패: '+(j.output||j.error));
    loadGit();
  }catch(e){el.textContent='커밋 실패: '+e}
}

// Test
async function loadTests(){
  try{
    const r=await fetch('/api/test/list'); const j=await r.json();
    const el=document.getElementById('testList');
    el.innerHTML=(j.tests||[]).map(t=>`<button class="test-item" onclick="runTest('${t.path}')" title="${t.path}">${esc(t.id)} <small>${t.type}</small></button>`).join('') || '테스트 없음';
  }catch(e){document.getElementById('testList').textContent='로드 실패: '+e}
}
async function runTest(target){
  const out=document.getElementById('testOutput');
  out.textContent=`▶ ${target} 실행 중...\n`;
  log(`테스트: ${target}`);
  showTab('test');
  try{
    const r=await fetch('/api/test/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target})});
    const j=await r.json();
    out.textContent=`$ ${j.cmd||target}\n${j.output||j.error||''}\n[exit ${j.exit}] ${j.ok?'✅ PASS':'❌ FAIL'}`;
    out.scrollTop=out.scrollHeight;
    toast(j.ok?'✅ 테스트 PASS':'❌ 테스트 FAIL — 콘솔 확인');
    log(`테스트 ${j.ok?'PASS':'FAIL'}: ${target}`);
  }catch(e){out.textContent='테스트 실패: '+e}
}
function toggleAutoTest(){const v=document.getElementById('autoTest').checked; toast(v?'자동 테스트 ON — 저장 시 verify 실행':'자동 테스트 OFF'); log(`자동 테스트 ${v?'ON':'OFF}`)}

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
document.addEventListener('DOMContentLoaded',()=>{
  initEditor();initSplitter();refreshFiles();loadModels();checkHealth();setInterval(checkHealth,8000);
  setupChatInput();
  log('IDE 준비 — 왼쪽 파일 선택 → 코딩 → Ctrl+S → Enter(대화)');
  // binary Enter도 대화 전송
  const bin=document.getElementById('binary');
  if(bin) bin.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); run() }})
});
