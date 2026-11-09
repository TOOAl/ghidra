/* Portable Tamagotchi AI Brain Frontend (100% relative API URLs) */

const CATEGORY_COLORS = {
  "AI모델·양자화": "#a78bfa",
  "강화학습·판단": "#34d399",
  "역공학·보안": "#f472b6",
  "포터블·인프라": "#38bdf8",
  "아이디어·노하우": "#fbbf24",
};

const SNACK_SAMPLES = {
  quant: {
    title: "노트북 RAM에서 4비트 GGUF 모델 빠르게 돌리는 비결",
    text: "초소형 언어모델(SLM)을 16비트 그대로 쓰면 무겁지만 Q4_K_M 4비트 양자화를 적용하면 용량이 1/4로 줄어든다. 외장하드에서 처음 모델을 읽어들일 때 OS 파일 캐시에 올라가므로 두 번째 질문부터는 내장 SSD처럼 초고속으로 응답한다.",
  },
  rl: {
    title: "작은 AI 여러 개를 연결할 때 다수결보다 좋은 방법",
    text: "단순 다수결 투표를 하면 평범한 평균 점수가 나오지만, 다수가 동의하는 범위 안에서 1등 전문가 에이전트에게 선택권을 맡기면(Poor Voters, Good Judges) 답만 외운 가짜 1등을 걸러내고 진짜 실력을 발휘할 수 있다. B단계 강화학습 두뇌에 이 규칙을 넣자!",
  },
  ghidra: {
    title: "Ghidra analyzeHeadless로 의심스러운 바이너리 문자열 추적하기",
    text: "기드라 헤드리스 모드로 실행 파일을 임포트한 뒤 심볼 테이블과 참조 문자열을 마크다운 리포트로 뽑아두면, 로컬 AI 두뇌가 인터넷 연결 없이도 암호화 루틴과 네트워크 함수를 찾아 위키 시냅스에 기록할 수 있다.",
  },
};

let graphState = { nodes: [], edges: [], selectedId: null, dragNode: null };

async function apiGet(path) {
  const res = await fetch(path);
  return res.json();
}

async function apiPost(path, payload = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

function triggerPetBounce() {
  const svg = document.getElementById("petSvg");
  svg.classList.remove("bounce");
  void svg.offsetWidth;
  svg.classList.add("bounce");
}

function renderStatus(data) {
  const { soul, host, engine, graph } = data;
  document.getElementById("petStageBadge").textContent = `Lv.${soul.level} ${soul.stage_emoji} ${soul.stage_title}`;
  document.getElementById("petName").textContent = soul.name;
  document.getElementById("petEmotion").textContent = soul.emotion_label;
  document.getElementById("petSpeech").textContent = soul.speech;

  const mouth = document.getElementById("petMouth");
  if (soul.emotion === "hungry") {
    mouth.setAttribute("d", "M100,121 Q110,113 120,121");
  } else {
    mouth.setAttribute("d", "M99,115 Q110,126 121,115");
  }

  document.getElementById("barSatiety").style.width = `${soul.satiety}%`;
  document.getElementById("valSatiety").textContent = `${soul.satiety}%`;
  document.getElementById("barMood").style.width = `${soul.mood}%`;
  document.getElementById("valMood").textContent = `${soul.mood}%`;

  const xpPct = soul.next_xp > 0 ? Math.min(100, Math.round((soul.xp / soul.next_xp) * 100)) : 100;
  document.getElementById("barXp").style.width = `${xpPct}%`;
  document.getElementById("valXp").textContent = `${soul.xp}/${soul.next_xp}`;

  document.getElementById("kpiIq").textContent = soul.iq;
  document.getElementById("kpiNotes").textContent = soul.notes_count;
  document.getElementById("kpiEdges").textContent = soul.edges_count;

  document.getElementById("hostChip").textContent =
    `🔌 숙주: ${host.cpu_cores}코어 · 여유 RAM ${host.ram_available_gb}GB`;

  const engineBanner = document.getElementById("engineBanner");
  if (engine.online) {
    engineBanner.innerHTML = `🟢 <strong>로컬 양자화 엔진 연결됨:</strong> ${engine.engine_name} (<code>${engine.active_model}</code>)`;
  } else {
    engineBanner.innerHTML = `🔵 <strong>${engine.engine_name}</strong><br/><span style="font-size:11px;opacity:0.85">외장하드 models/ 에 GGUF 모델 추가 시 자동 전환</span>`;
  }

  const eventList = document.getElementById("eventList");
  eventList.innerHTML = "";
  (soul.recent_events || []).slice(0, 8).forEach((ev) => {
    const li = document.createElement("li");
    const shortTime = (ev.time || "").slice(11, 16);
    li.textContent = `[${shortTime}] ${ev.text}`;
    eventList.appendChild(li);
  });

  renderHostScanner(host);
  syncGraphData(graph);
}

function renderHostScanner(host) {
  const specs = document.getElementById("hostSpecs");
  specs.innerHTML = `
    <div class="spec-tile"><span>운영체제 / 아키텍처</span><strong>${host.os} (${host.arch})</strong></div>
    <div class="spec-tile"><span>숙주 CPU</span><strong>${host.cpu_cores}코어 · ${host.cpu_name.slice(0, 28)}</strong></div>
    <div class="spec-tile"><span>현재 사용 가능 RAM</span><strong>${host.ram_available_gb} GB / 총 ${host.ram_total_gb} GB</strong></div>
    <div class="spec-tile"><span>가속기 모드</span><strong>${host.accelerator}</strong></div>
    <div class="spec-tile"><span>서식지(외장하드) 여유 공간</span><strong>${host.drive_free_gb} GB 여유</strong></div>
    <div class="spec-tile"><span>추천 최적 두뇌</span><strong>⭐ ${host.best_slm.name}</strong></div>
  `;

  const tbody = document.getElementById("slmTableBody");
  tbody.innerHTML = "";
  (host.slm_matrix || []).forEach((m) => {
    const tr = document.createElement("tr");
    const cls = m.fit === "optimal" ? "fit-optimal" : m.fit === "tight" ? "fit-tight" : "fit-heavy";
    tr.innerHTML = `
      <td><strong>${m.name}</strong><br/><span style="font-size:11.5px;color:#94a3b8">${m.role}</span></td>
      <td>${(m.fp16_mb / 1000).toFixed(1)} GB</td>
      <td><strong>${m.file_mb} MB</strong></td>
      <td>-${m.saved_pct}% 압축</td>
      <td>${m.ram_needed_gb} GB</td>
      <td class="${cls}">${m.fit_label}</td>
    `;
    tbody.appendChild(tr);
  });
}

function syncGraphData(graph) {
  const canvas = document.getElementById("graphCanvas");
  const w = canvas.width;
  const h = canvas.height;
  const oldPos = {};
  graphState.nodes.forEach((n) => {
    oldPos[n.id] = { x: n.x, y: n.y, vx: n.vx, vy: n.vy };
  });

  graphState.nodes = (graph.nodes || []).map((n, idx) => {
    const prev = oldPos[n.id];
    const angle = (idx / Math.max(1, graph.nodes.length)) * Math.PI * 2;
    return {
      ...n,
      x: prev ? prev.x : w / 2 + Math.cos(angle) * 120,
      y: prev ? prev.y : h / 2 + Math.sin(angle) * 95,
      vx: prev ? prev.vx : 0,
      vy: prev ? prev.vy : 0,
    };
  });
  graphState.edges = graph.edges || [];

  if (!graphState.selectedId && graphState.nodes.length > 0) {
    openNoteBySlug(graphState.nodes[0].id);
  }
}

async function openNoteBySlug(slug) {
  graphState.selectedId = slug;
  const res = await apiGet(`api/note?slug=${encodeURIComponent(slug)}`);
  if (!res.note) return;
  const n = res.note;
  document.getElementById("viewerTitle").textContent = `📄 ${n.title}`;
  document.getElementById("viewerPath").textContent = `vault/${n.rel_path}`;
  const tagBox = document.getElementById("viewerTags");
  tagBox.innerHTML = "";
  (n.tags || []).forEach((t) => {
    const span = document.createElement("span");
    span.className = "tag-chip";
    span.textContent = `#${t}`;
    tagBox.appendChild(span);
  });
  document.getElementById("viewerBody").textContent = n.body;
}

function setupGraphSimulation() {
  const canvas = document.getElementById("graphCanvas");
  const ctx = canvas.getContext("2d");

  function getMousePos(evt) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((evt.clientX - rect.left) / rect.width) * canvas.width,
      y: ((evt.clientY - rect.top) / rect.height) * canvas.height,
    };
  }

  canvas.addEventListener("mousedown", (evt) => {
    const pos = getMousePos(evt);
    for (const n of graphState.nodes) {
      const dx = pos.x - n.x;
      const dy = pos.y - n.y;
      if (Math.hypot(dx, dy) <= 22) {
        graphState.dragNode = n;
        openNoteBySlug(n.id);
        break;
      }
    }
  });

  canvas.addEventListener("mousemove", (evt) => {
    if (!graphState.dragNode) return;
    const pos = getMousePos(evt);
    graphState.dragNode.x = Math.max(30, Math.min(canvas.width - 30, pos.x));
    graphState.dragNode.y = Math.max(30, Math.min(canvas.height - 30, pos.y));
    graphState.dragNode.vx = 0;
    graphState.dragNode.vy = 0;
  });

  window.addEventListener("mouseup", () => {
    graphState.dragNode = null;
  });

  function step() {
    const nodes = graphState.nodes;
    const edges = graphState.edges;
    const w = canvas.width;
    const h = canvas.height;

    // Force layout
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = b.x - a.x || 0.1;
        let dy = b.y - a.y || 0.1;
        const dist2 = Math.max(400, dx * dx + dy * dy);
        const force = 2600 / dist2;
        const dist = Math.sqrt(dist2);
        a.vx -= (dx / dist) * force;
        a.vy -= (dy / dist) * force;
        b.vx += (dx / dist) * force;
        b.vy += (dy / dist) * force;
      }
    }

    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    edges.forEach((e) => {
      const a = byId[e.source];
      const b = byId[e.target];
      if (!a || !b) return;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(1, Math.hypot(dx, dy));
      const pull = (dist - 135) * 0.012;
      a.vx += (dx / dist) * pull;
      a.vy += (dy / dist) * pull;
      b.vx -= (dx / dist) * pull;
      b.vy -= (dy / dist) * pull;
    });

    nodes.forEach((n) => {
      if (n === graphState.dragNode) return;
      n.vx += (w / 2 - n.x) * 0.0025;
      n.vy += (h / 2 - n.y) * 0.0025;
      n.vx *= 0.84;
      n.vy *= 0.84;
      n.x = Math.max(42, Math.min(w - 42, n.x + n.vx));
      n.y = Math.max(36, Math.min(h - 36, n.y + n.vy));
    });

    // Render
    ctx.clearRect(0, 0, w, h);
    edges.forEach((e) => {
      const a = byId[e.source];
      const b = byId[e.target];
      if (!a || !b) return;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = "rgba(167, 139, 250, 0.42)";
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    nodes.forEach((n) => {
      const color = CATEGORY_COLORS[n.category] || "#a78bfa";
      const isSel = n.id === graphState.selectedId;
      ctx.beginPath();
      ctx.arc(n.x, n.y, isSel ? 17 : 13, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = isSel ? 18 : 8;
      ctx.fill();
      ctx.shadowBlur = 0;
      if (isSel) {
        ctx.lineWidth = 3;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
      }
      ctx.fillStyle = "#e2e8f0";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      const label = n.title.length > 18 ? n.title.slice(0, 17) + "…" : n.title;
      ctx.fillText(label, n.x, n.y + 29);
    });

    requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

function setupInteractions() {
  // Tabs
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  // Poke
  const doPoke = async () => {
    triggerPetBounce();
    const res = await apiPost("api/poke");
    if (res.status) renderStatus(res.status);
  };
  document.getElementById("btnPoke").addEventListener("click", doPoke);
  document.getElementById("petSvg").addEventListener("click", doPoke);

  // Rename
  document.getElementById("btnRename").addEventListener("click", async () => {
    const current = document.getElementById("petName").textContent;
    const next = window.prompt("다마고치 AI 두뇌의 새 이름을 지어주세요!", current);
    if (next && next.trim()) {
      triggerPetBounce();
      const res = await apiPost("api/rename", { name: next.trim() });
      if (res.status) renderStatus(res.status);
    }
  });

  // Sample snacks
  document.querySelectorAll("[data-snack]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sample = SNACK_SAMPLES[btn.dataset.snack];
      if (!sample) return;
      document.getElementById("feedTitle").value = sample.title;
      document.getElementById("feedText").value = sample.text;
    });
  });

  // Feed memory
  document.getElementById("btnFeed").addEventListener("click", async () => {
    const title = document.getElementById("feedTitle").value.trim();
    const text = document.getElementById("feedText").value.trim();
    const statusEl = document.getElementById("feedStatus");
    if (!text) {
      statusEl.textContent = "⚠️ 먼저 먹일 메모 내용을 적어주세요!";
      return;
    }
    statusEl.textContent = "⏳ 정원사가 마크다운 카드로 소화시키는 중...";
    const res = await apiPost("api/feed", { title, text });
    if (res.digested) {
      triggerPetBounce();
      renderStatus(res.status);
      openNoteBySlug(res.digested.slug);
      statusEl.textContent = "✅ 소화 완료! 시냅스 지도에 새 노드가 생겼어요!";
      const box = document.getElementById("digestResult");
      box.classList.remove("hidden");
      box.innerHTML = `
        <strong>🎉 새 마크다운 기억 카드 생성 완료!</strong><br/>
        • 파일: <code>vault/${res.digested.rel_path}</code><br/>
        • 분류: <strong>${res.digested.category}</strong> | 태그: ${res.digested.tags.map((t) => "#" + t).join(" ")}<br/>
        • 자동 연결된 기존 기억: ${
          res.digested.links.length
            ? res.digested.links.map((l) => `<code>[[${l}]]</code>`).join(", ")
            : "첫 독립 씨앗 노드"
        }
      `;
      document.getElementById("feedTitle").value = "";
      document.getElementById("feedText").value = "";
    }
  });

  // Quick questions & Chat
  const sendQuestion = async (qText) => {
    const input = document.getElementById("chatInput");
    const question = (qText || input.value).trim();
    if (!question) return;
    input.value = "";
    const log = document.getElementById("chatLog");
    const uDiv = document.createElement("div");
    uDiv.className = "msg user";
    uDiv.textContent = `🙋 주인님: ${question}`;
    log.appendChild(uDiv);

    const bDiv = document.createElement("div");
    bDiv.className = "msg bot";
    bDiv.textContent = "🧠 시냅스 그물망을 더듬어 기억을 꺼내는 중...";
    log.appendChild(bDiv);
    log.scrollTop = log.scrollHeight;

    const res = await apiPost("api/chat", { question });
    triggerPetBounce();
    bDiv.textContent = res.answer || "응답을 불러오지 못했어요.";
    log.scrollTop = log.scrollHeight;
    if (res.status) renderStatus(res.status);
  };

  document.getElementById("btnChat").addEventListener("click", () => sendQuestion());
  document.getElementById("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendQuestion();
  });
  document.querySelectorAll("[data-q]").forEach((btn) => {
    btn.addEventListener("click", () => sendQuestion(btn.dataset.q));
  });
}

async function init() {
  setupGraphSimulation();
  setupInteractions();
  const data = await apiGet("api/status");
  renderStatus(data);
}

init();
