/* Cosmic Bio-Capsule UI v3 — Cache-proof, SSR-hydrated, Relative URLs Only */

const CATEGORY_COLORS = {
  "AI모델·양자화": "#818cf8",
  "강화학습·판단": "#34d399",
  "역공학·보안": "#f472b6",
  "포터블·인프라": "#38bdf8",
  "아이디어·노하우": "#fbbf24",
};

const SNACK_SAMPLES = {
  quant: {
    title: "외부 모델을 해부해 우리만의 4비트 두뇌(.sbrain)로 재주조하는 원리",
    text: "거대 모델을 그대로 내려받아 쓰지 않고, 외부 오픈모델의 GQA 어텐션과 SwiGLU 골격 비율만 참고한 뒤 내 마크다운 위키 어휘와 역공학 지식으로 신경망 가중치를 구성한다. 이후 32개 블록 단위 대칭 스케일링과 니블 패킹(1바이트에 4비트 가중치 2개 저장)을 적용하면 용량이 약 84% 줄어들어 외장하드 어디서든 빠르게 작동한다.",
  },
  rl: {
    title: "작은 AI 여러 개를 연결할 때 다수결보다 뛰어난 심판 합의 방식",
    text: "단순 다수결 투표는 평범한 평균에 머물지만, 다수가 동의하는 후보 안에서 1등 전문가 두뇌의 선택을 따르게 하면(Poor Voters, Good Judges) 암기만 한 오버피팅 모델을 걸러내고 훨씬 높은 판단 정확도를 얻는다.",
  },
  ghidra: {
    title: "Ghidra analyzeHeadless와 시냅스몽 역공학 해부실 연결 설계",
    text: "Ghidra 헤드리스 모드로 바이너리에서 함수 호출 그래프와 의심 문자열을 추출해 마크다운 위키에 넣으면, 시냅스몽이 인터넷 없이도 암호화 루틴과 핵심 함수를 연결해 기억한다.",
  },
};

let graphState = { nodes: [], edges: [], selectedId: null, dragNode: null };
let manualPoseOverride = null;
let selectedBits = 4;
let selectedDim = 64;

async function apiGet(path) {
  const res = await fetch(path, { cache: "no-store" });
  return res.json();
}

async function apiPost(path, payload = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  return res.json();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function pulsePortrait() {
  const frame = document.getElementById("portraitFrame");
  if (!frame) return;
  frame.classList.remove("pulse");
  void frame.offsetWidth;
  frame.classList.add("pulse");
}

function setPetPose(poseKey) {
  const valid = poseKey || "01_greet";
  const img = document.getElementById("petImage");
  if (img && !img.getAttribute("src").endsWith(`${valid}.jpg`)) {
    img.setAttribute("src", `assets/${valid}.jpg`);
  }
  document.querySelectorAll(".pose-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.pose === valid);
  });
}

function renderStatus(data) {
  if (!data || !data.soul) return;
  const { soul, host, forged_brains, graph } = data;

  document.getElementById("petStageBadge").textContent =
    `Lv.${soul.level} ${soul.stage_emoji} ${soul.stage_title}`;
  document.getElementById("petName").textContent = soul.name;
  document.getElementById("petEmotion").textContent = soul.emotion_label;
  document.getElementById("badgeIq").textContent = soul.iq;
  document.getElementById("petSpeech").textContent = soul.speech;

  if (!manualPoseOverride) {
    setPetPose(soul.pose || "01_greet");
  }

  document.getElementById("barSatiety").style.width = `${soul.satiety}%`;
  document.getElementById("valSatiety").textContent = `${soul.satiety}%`;
  document.getElementById("barMood").style.width = `${soul.mood}%`;
  document.getElementById("valMood").textContent = `${soul.mood}%`;

  const xpPct = soul.next_xp > 0 ? Math.min(100, Math.round((soul.xp / soul.next_xp) * 100)) : 100;
  document.getElementById("barXp").style.width = `${xpPct}%`;
  document.getElementById("valXp").textContent = `${soul.xp}/${soul.next_xp}`;

  // Environment Telemetry Cockpit
  const env = (host && host.environment) || {};
  const envBadge = document.getElementById("envBadge");
  envBadge.className = `env-grade ${env.grade || "optimal"}`;
  envBadge.textContent = `${env.label || "쾌적"} · ${env.score || 80}점`;

  document.getElementById("envRamText").textContent =
    `${host.ram_available_gb} / ${host.ram_total_gb} GB`;
  document.getElementById("envRamBar").style.width =
    `${Math.min(100, env.ram_free_pct || 70)}%`;
  document.getElementById("envCpuText").textContent =
    `${host.cpu_cores}코어 · ${host.accelerator.replace(" Mode", "")}`;
  document.getElementById("envOsText").textContent =
    `${host.os} · 여유 ${env.ram_free_pct || 0}%`;
  document.getElementById("envDiskText").textContent =
    `${host.drive_free_gb} GB 여유`;

  const shortTier = (env.max_custom_tier || "INT4 경량 가능").split(" / ")[0];
  document.getElementById("envTierText").textContent = shortTier;
  document.getElementById("envComment").textContent = env.note || "";

  // KPI Dock
  const brains = forged_brains || [];
  document.getElementById("kpiIq").textContent = soul.iq;
  document.getElementById("kpiNotes").textContent = soul.notes_count;
  document.getElementById("kpiEdges").textContent = soul.edges_count;
  document.getElementById("kpiForged").textContent = brains.length;

  document.getElementById("engineStatusPill").textContent =
    brains.length > 0
      ? `✦ 자체 주조 두뇌 ${brains.length}개 보유 (${brains[0].filename})`
      : "● 위키 기억망 + 자체 양자화 주조소 대기 중";

  renderForgedList(brains);
  if (graph) syncGraphData(graph);
}

function renderForgedList(items) {
  const box = document.getElementById("forgedList");
  if (!items.length) {
    box.innerHTML = `<div class="vb-item" style="color:#94a3b8">아직 주조된 <code>.sbrain</code> 파일이 없습니다. 위 버튼을 눌러 첫 독자 두뇌를 구워보세요!</div>`;
    return;
  }
  box.innerHTML = items
    .map(
      (b) => `
      <div class="vb-item">
        <div>
          <strong style="color:#e0e7ff">${escapeHtml(b.filename)}</strong><br/>
          <span style="font-size:11px;color:#94a3b8">어휘 ${b.vocab_size}개 · 파라미터 ${b.total_params.toLocaleString()}개 · 정밀도 ${b.cosine_similarity_pct}%</span>
        </div>
        <div style="text-align:right">
          <strong style="color:#6ee7b7">${b.file_kb} KB</strong><br/>
          <span style="font-size:10.5px;color:#94a3b8">FP32 대비 -${b.saved_vs_fp32_pct}%</span>
        </div>
      </div>`
    )
    .join("");
}

async function loadAnatomy(bpId) {
  const res = await apiGet(`api/dissect?id=${encodeURIComponent(bpId)}`);
  const a = res.anatomy;
  if (!a) return;
  document.getElementById("anatomyBox").innerHTML = `
    <div style="font-weight:700;font-size:14px;color:#eef2ff">${escapeHtml(a.title)}</div>
    <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">${escapeHtml(a.donor_source)}</div>
    <div class="spec-grid">
      <div class="spec-cell"><span>층수 · 은닉 차원</span><strong>${a.layers}층 · ${a.hidden_size}차원</strong></div>
      <div class="spec-cell"><span>어텐션 방식</span><strong>${escapeHtml(a.attention)}</strong></div>
      <div class="spec-cell"><span>신경망 활성 블록</span><strong>${escapeHtml(a.ffn)}</strong></div>
      <div class="spec-cell"><span>단어 사전 크기</span><strong>${escapeHtml(a.vocab)}</strong></div>
    </div>
    <div class="anat-section keep">
      <strong style="color:#6ee7b7;font-size:12px">✔ 우리 기본 틀로 흡수할 핵심 원리</strong>
      <ul>${a.keep_parts.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
    </div>
    <div class="anat-section strip">
      <strong style="color:#fda4af;font-size:12px">✂ 과감히 덜어내고 직접 재설계할 부분</strong>
      <ul>${a.strip_parts.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
    </div>
  `;
}

function formatMarkdownNote(raw) {
  // Strip YAML frontmatter block cleanly for pretty reading
  const stripped = String(raw || "").replace(/^---[\s\S]*?---\s*/, "");
  let html = escapeHtml(stripped);
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^# (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(
    /\[\[([^\]]+)\]\]/g,
    (_, slug) => `<button type="button" class="wiki-link-chip" data-link="${slug}">🔗 ${slug}</button>`
  );
  return html.replace(/\n/g, "<br/>");
}

async function openNoteBySlug(slug) {
  graphState.selectedId = slug;
  const res = await apiGet(`api/note?slug=${encodeURIComponent(slug)}`);
  if (!res.note) return;
  const n = res.note;
  document.getElementById("viewerTitle").textContent = n.title;
  document.getElementById("viewerPath").textContent = `vault/${n.rel_path}`;
  document.getElementById("viewerTags").innerHTML =
    (n.tags || []).map((t) => `<span class="tag-pill">#${escapeHtml(t)}</span>`).join("");

  const bodyEl = document.getElementById("viewerBody");
  bodyEl.innerHTML = formatMarkdownNote(n.body);
  bodyEl.querySelectorAll(".wiki-link-chip").forEach((chip) => {
    chip.addEventListener("click", () => openNoteBySlug(chip.dataset.link));
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
      x: prev ? prev.x : w / 2 + Math.cos(angle) * 145,
      y: prev ? prev.y : h / 2 + Math.sin(angle) * 115,
      vx: prev ? prev.vx : 0,
      vy: prev ? prev.vy : 0,
    };
  });
  graphState.edges = graph.edges || [];

  if (!graphState.selectedId && graphState.nodes.length > 0) {
    openNoteBySlug(graphState.nodes[0].id);
  }
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
      if (Math.hypot(pos.x - n.x, pos.y - n.y) <= 22) {
        graphState.dragNode = n;
        openNoteBySlug(n.id);
        break;
      }
    }
  });

  canvas.addEventListener("mousemove", (evt) => {
    if (!graphState.dragNode) return;
    const pos = getMousePos(evt);
    graphState.dragNode.x = Math.max(40, Math.min(canvas.width - 40, pos.x));
    graphState.dragNode.y = Math.max(40, Math.min(canvas.height - 40, pos.y));
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

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x || 0.1;
        const dy = b.y - a.y || 0.1;
        const dist2 = Math.max(550, dx * dx + dy * dy);
        const force = 3200 / dist2;
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
      const pull = (dist - 155) * 0.013;
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
      n.x = Math.max(52, Math.min(w - 52, n.x + n.vx));
      n.y = Math.max(42, Math.min(h - 42, n.y + n.vy));
    });

    ctx.clearRect(0, 0, w, h);

    edges.forEach((e) => {
      const a = byId[e.source];
      const b = byId[e.target];
      if (!a || !b) return;
      const activeEdge = a.id === graphState.selectedId || b.id === graphState.selectedId;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = activeEdge ? "rgba(165, 180, 252, 0.72)" : "rgba(148, 163, 184, 0.25)";
      ctx.lineWidth = activeEdge ? 2.2 : 1.5;
      ctx.stroke();
    });

    nodes.forEach((n) => {
      const color = CATEGORY_COLORS[n.category] || "#818cf8";
      const isSel = n.id === graphState.selectedId;

      if (isSel) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, 21, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(124, 111, 246, 0.22)";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, isSel ? 14 : 11, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = isSel ? 18 : 8;
      ctx.fill();
      ctx.shadowBlur = 0;

      if (isSel) {
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
      }

      ctx.fillStyle = isSel ? "#ffffff" : "#cbd5e1";
      ctx.font = isSel ? "bold 12px sans-serif" : "11.5px sans-serif";
      ctx.textAlign = "center";
      const label = n.title.length > 20 ? n.title.slice(0, 19) + "…" : n.title;
      ctx.fillText(label, n.x, n.y + 28);
    });

    requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

function setupInteractions() {
  // Segmented Console Tabs
  document.querySelectorAll(".seg-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg-tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  // 8-Cut Pose Switcher
  document.querySelectorAll(".pose-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      manualPoseOverride = btn.dataset.pose;
      setPetPose(manualPoseOverride);
      pulsePortrait();
    });
  });

  // Poke / Interact
  const doPoke = async () => {
    manualPoseOverride = null;
    pulsePortrait();
    const res = await apiPost("api/poke");
    if (res.status) renderStatus(res.status);
  };
  document.getElementById("btnPoke").addEventListener("click", doPoke);
  document.getElementById("portraitFrame").addEventListener("click", doPoke);

  // Rename
  document.getElementById("btnRename").addEventListener("click", async () => {
    const current = document.getElementById("petName").textContent;
    const next = window.prompt("시냅스몽의 새 이름을 입력해 주세요:", current);
    if (next && next.trim()) {
      manualPoseOverride = null;
      pulsePortrait();
      const res = await apiPost("api/rename", { name: next.trim() });
      if (res.status) renderStatus(res.status);
    }
  });

  // Feed Presets
  document.querySelectorAll("[data-snack]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sample = SNACK_SAMPLES[btn.dataset.snack];
      if (!sample) return;
      document.getElementById("feedTitle").value = sample.title;
      document.getElementById("feedText").value = sample.text;
    });
  });

  // Digest New Memory
  document.getElementById("btnFeed").addEventListener("click", async () => {
    const title = document.getElementById("feedTitle").value.trim();
    const text = document.getElementById("feedText").value.trim();
    const statusEl = document.getElementById("feedStatus");
    if (!text) {
      statusEl.textContent = "먼저 기억시킬 내용을 입력해 주세요.";
      return;
    }
    manualPoseOverride = null;
    setPetPose("03_swirl");
    statusEl.textContent = "소용돌이 시냅스로 소화 중...";
    const res = await apiPost("api/feed", { title, text });
    if (res.digested) {
      pulsePortrait();
      renderStatus(res.status);
      openNoteBySlug(res.digested.slug);
      statusEl.textContent = "저장 및 시냅스 연결 완료!";
      const box = document.getElementById("digestResult");
      box.classList.remove("empty");
      box.innerHTML = `
        <strong style="color:#6ee7b7">✔ 새 마크다운 기억 카드 생성 완료!</strong><br/>
        • 파일 경로: <code>vault/${escapeHtml(res.digested.rel_path)}</code><br/>
        • 자동 분류: <strong>${escapeHtml(res.digested.category)}</strong><br/>
        • 해시태그: ${res.digested.tags.map((t) => `#${escapeHtml(t)}`).join(" ")}<br/>
        • 연결된 시냅스: ${
          res.digested.links.length
            ? res.digested.links.map((l) => `<code>[[${escapeHtml(l)}]]</code>`).join(", ")
            : "독립 씨앗 노트"
        }
      `;
      document.getElementById("feedTitle").value = "";
      document.getElementById("feedText").value = "";
    }
  });

  // Blueprint Dissection Selector
  document.querySelectorAll("[data-bp]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-bp]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      setPetPose("02_curious");
      loadAnatomy(btn.dataset.bp);
    });
  });

  // Custom Quantization Cards (Bits & Dim)
  document.querySelectorAll("#quantBitsGroup .q-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll("#quantBitsGroup .q-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      selectedBits = parseInt(card.dataset.bits, 10);
    });
  });

  document.querySelectorAll("#quantDimGroup .dim-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#quantDimGroup .dim-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      selectedDim = parseInt(pill.dataset.dim, 10);
    });
  });

  // Forge Custom Quantized Brain (.sbrain)
  document.getElementById("btnForge").addEventListener("click", async () => {
    const box = document.getElementById("forgeResult");
    manualPoseOverride = null;
    setPetPose("03_swirl");
    box.classList.remove("hidden");
    box.innerHTML = "내 위키 어휘로 신경망 가중치를 빚고 블록 양자화 눈금으로 깎는 중...";

    const res = await apiPost("api/forge", { bits: selectedBits, hidden_dim: selectedDim });
    if (res.forged) {
      const f = res.forged;
      pulsePortrait();
      renderStatus(res.status);
      box.innerHTML = `
        <strong style="color:#6ee7b7;font-size:13px">🎉 독자 양자화 두뇌 주조 성공! (<code>models/${escapeHtml(f.filename)}</code>)</strong><br/>
        • 학습 어휘 <strong>${f.vocab_size}개</strong> · 파라미터 <strong>${f.total_params.toLocaleString()}개</strong> · 주조 시간 <strong>${f.elapsed_ms} ms</strong><br/>
        • 다이어트 효과: 원본 FP32 <code>${f.fp32_kb} KB</code> → <strong>INT${f.bits} <code>${f.quant_weights_kb} KB</code> (-${f.saved_vs_fp32_pct}% 압축!)</strong><br/>
        • 똑똑함 보존율: <strong>코사인 유사도 ${f.cosine_similarity_pct}%</strong> (오차 RMSE ${f.rmse})<br/>
        • 형성된 대표 연상 시냅스: ${f.sample_synapses.map((s) => `<code>${escapeHtml(s)}</code>`).join(" ")}
      `;
    }
  });

  // Chat
  const sendQuestion = async (qText) => {
    const input = document.getElementById("chatInput");
    const question = (qText || input.value).trim();
    if (!question) return;
    input.value = "";

    const log = document.getElementById("chatLog");
    const uRow = document.createElement("div");
    uRow.className = "msg-row user";
    uRow.innerHTML = `<div class="msg-bubble">${escapeHtml(question)}</div>`;
    log.appendChild(uRow);

    const bRow = document.createElement("div");
    bRow.className = "msg-row bot";
    bRow.innerHTML = `
      <img src="assets/02_curious.jpg" alt="시냅스몽" class="msg-avatar" />
      <div class="msg-bubble">연결된 마크다운 시냅스 노드를 탐색하고 있어요...</div>
    `;
    log.appendChild(bRow);
    log.scrollTop = log.scrollHeight;

    manualPoseOverride = null;
    setPetPose("02_curious");
    const res = await apiPost("api/chat", { question });
    pulsePortrait();

    const bubble = bRow.querySelector(".msg-bubble");
    const avatar = bRow.querySelector(".msg-avatar");
    avatar.src = "assets/06_star.jpg";

    const recalledHtml = (res.recalled || []).length
      ? `<div class="recall-strip">
           <span>📌 인출한 기억 (토큰 ${res.saved_tokens_pct}% 절약):</span>
           ${res.recalled.map((r) => `<code>[[${escapeHtml(r.title)}]]</code>`).join(" ")}
         </div>`
      : "";
    bubble.innerHTML = `${escapeHtml(res.answer || "응답을 불러오지 못했습니다.")}${recalledHtml}`;
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

  // Instant 0ms render from server-injected initial state (never stuck on "측정 중...")
  if (window.__INITIAL_STATUS__) {
    renderStatus(window.__INITIAL_STATUS__);
  }

  const [freshStatus] = await Promise.all([
    apiGet("api/status"),
    loadAnatomy("custom-synapse-seed"),
  ]);
  renderStatus(freshStatus);
}

init();
