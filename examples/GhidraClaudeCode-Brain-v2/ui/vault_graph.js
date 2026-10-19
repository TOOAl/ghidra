// ui/vault_graph.js — Obsidian Graph View 최소 구현 (50줄 canvas force-directed)
async function loadVaultGraph(){
  const c=document.getElementById('vaultCanvas');
  if(!c) return;
  const ctx=c.getContext('2d'), dpr=window.devicePixelRatio||1;
  const w=c.clientWidth||600, h=320;
  c.width=w*dpr; c.height=h*dpr; c.style.width=w+'px'; c.style.height=h+'px';
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
  try{
    const g=await fetch('/api/vault/graph',{headers:{"Cache-Control":"no-cache"}}).then(r=>r.json());
    const nodes=g.nodes||[], edges=g.edges||[];
    if(!nodes.length){ ctx.fillStyle='#64748b'; ctx.font='12px sans-serif'; ctx.fillText('노트 없음 — /api/run 으로 분석하면 생김', 20, 40); return; }
    // 간단 force: 노드를 원형 배치 후 링크당 1회 스프링
    const cx=w/2, cy=h/2, rad=Math.min(w,h)*0.38;
    nodes.forEach((n,i)=>{
      if(n.x==null){ const a=(i/nodes.length)*Math.PI*2; n.x=cx+Math.cos(a)*rad; n.y=cy+Math.sin(a)*rad; }
    });
    // 10회 스프링 완화
    for(let k=0;k<15;k++){
      edges.forEach(e=>{
        const a=nodes.find(n=>n.id===e.from), b=nodes.find(n=>n.id===e.to);
        if(!a||!b) return;
        const dx=b.x-a.x, dy=b.y-a.y, dist=Math.hypot(dx,dy)||1;
        const ideal=80, f=(dist-ideal)*0.05;
        const fx=dx/dist*f, fy=dy/dist*f;
        a.x+=fx; a.y+=fy; b.x-=fx; b.y-=fy;
      });
    }
    // edges
    ctx.strokeStyle='#334155'; ctx.lineWidth=1;
    edges.forEach(e=>{
      const a=nodes.find(n=>n.id===e.from), b=nodes.find(n=>n.id===e.to);
      if(!a||!b) return;
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
    });
    // nodes
    nodes.forEach(n=>{
      const sz=n.size||8, col=n.group==='root'?'#6366f1': n.group==='templates'?'#22c55e':'#06b6d4';
      ctx.fillStyle=col; ctx.beginPath(); ctx.arc(n.x,n.y,sz,0,Math.PI*2); ctx.fill();
      ctx.fillStyle='#fff'; ctx.font='bold 9px sans-serif'; ctx.textAlign='center'; ctx.fillText((n.label||n.id).slice(0,4), n.x, n.y+3);
    });
    // 클릭 → 파일 열기
    c.onclick=(ev)=>{
      const rect=c.getBoundingClientRect(), x=(ev.clientX-rect.left), y=(ev.clientY-rect.top);
      let best=null, bestD=18;
      nodes.forEach(n=>{ const d=Math.hypot(n.x-x, n.y-y); if(d<bestD){bestD=d; best=n;} });
      if(best && typeof openFile==='function') openFile(best.path||best.id);
    };
  }catch(e){ ctx.fillStyle='#f87171'; ctx.fillText('그래프 실패: '+e, 20, 40); }
}
