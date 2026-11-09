/* Clean Cosmic UI + 8-Pose Synapsemong + Custom Quantization Forge (Relative URLs Only) */

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
    title: "작은 AI 여러 개를 연결할 때 다수결보다 뛰어난 합의 방식",
    text: "단순 다수결 투표는 평범한 평균에 머물지만, 다수가 동의하는 후보 안에서 1등 전문가 두뇌의 선택을 따르게 하면(Poor Voters, Good Judges) 암기만 한 오버피팅 모델을 걸러내고 훨씬 높은 판단 정확도를 얻는다.",
  },
  ghidra: {
    title: "Ghidra analyzeHeadless와 시냅스몽 역공학 해부실 연결 설계",
    text: "Ghidra 헤드리스 모드로 바이너리에서 함수 호출 그래프와 의심 문자열을 추출해 마크다운 위키에 넣으면, 시냅스몽이 인터넷 없이도 암호화 루틴과 핵심 함수를 연결해 기억한다.",
  },
};

let graphState = { nodes: [], edges: [], selectedId: null, dragNode: null };
let manualPoseOverride = null;

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

function pulsePortrait() {
  const frame = document.getElementById("portraitFrame");
  frame.classList.remove("pulse");
  void frame.offsetWidth;
  frame.classList.add("pulse");
}

function setPetPose(poseKey) {
  const valid = poseKey || "01_greet";
  const img = document.getElementById("petImage");
  const targetSrc = `assets/${valid}.jpg`;
  if (!img.getAttribute("src").endsWith(`${valid}.jpg`)) {
    img.setAttribute("src", targetSrc);
  }
  document.querySelectorAll(".pose-dot").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.pose === valid);
  });
}

function renderStatus(data) {
  const { soul, host, forged_brains, graph } = data;
  document.getElementById("petStageBadge").textContent =
    `Lv.${soul.level} ${soul.stage_emoji} ${soul.stage_title}`;
  document.getElementById("petName").textContent = soul.name;
  document.getElementById("petEmotion").textContent = soul.emotion_label;
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
  document.getElementById("valXp").textContent = `${soul.xp} / ${soul.next_xp} XP`;

  // Environment Status Window right underneath Vital Bars
  const env = host.environment || {};
  const envBadge = document.getElementById("envBadge");
  envBadge.className = `env-badge ${env.grade || "optimal"}`;
  envBadge.textContent = `${env.label || "쾌적"} (${env.score || 85}점)`;

  document.getElementById("envRamText").textContent =
    `${host.ram_available_gb} GB 여유 / 총 ${host.ram_total_gb} GB (${env.ram_free_pct || 0}%)`;
  document.getElementById("envRamBar").style.width = `${Math.min(100, env.ram_free_pct || 50)}%`;
  document.getElementById("envCpuText").textContent =
    `${host.cpu_cores}코어 · ${host.accelerator}`;
  document.getElementById("envDiskText").textContent =
    `${host.drive_free_gb} GB 사용 가능`;
  document.getElementById("envTierText").textContent =
    env.max_custom_tier || "INT4 초경량 두뇌 주조 가능";
  document.getElementById("envComment").textContent = env.note || "";

  document.getElementById("kpiIq").textContent = soul.iq;
  document.getElementById("kpiNotes").textContent = soul.notes_count;
  document.getElementById("kpiEdges").textContent = soul.edges_count;
  document.getElementById("kpiForged").textContent = (forged_brains || []).length;

  renderForgedList(forged_brains || []);
  syncGraphData(graph);
}

function renderForgedList(items) {
  const box = document.getElementById("forgedList");
  if (!items.length) {
    box.textContent = "아직 주조된 .sbrain 파일이 없습니다. 위 버튼을 눌러 첫 독자 두뇌를 구워보세요!";
    return;
  }
  box.innerHTML = items
    .map(
      (b) => `
      <div class="forged-item">
        <div>
          <strong>${b.filename}</strong><br/>
          <span style="color:#94a3b8;font-size:11px">어휘 ${b.vocab_size}개 · 파라미터 ${b.total_params.toLocaleString()}개 · 정밀도 ${b.cosine_similarity_pct}%</span>
        </div>
        <div style="text-align:right">
          <strong style="color:#6ee7b7">${b.file_kb} KB</strong><br/>
          <span style="color:#94a3b8;font-size:11px">FP32 대비 -${b.saved_vs_fp32_pct}%</span>
        </div>
      </div>`
    )
    .join("");
}

async function loadAnatomy(bpId) {
  const res = await apiGet(`api/dissect?id=${encodeURIComponent(bpId)}`);
  const a = res.anatomy;
  if (!a) return;
  const box = document.getElementById("anatomyBox");
  box.innerHTML = `
    <div style="font-weight:700;font-size:14px;color:#e0e7ff">${a.title}</div>
    <div style="font-size:11.5px;color:#94a3b8;margin-top:2px">${a.donor_source}</div>
    <div class="anatomy-grid">
      <div class="anat-item"><span>층수 / 은닉 차원</span><strong>${a.layers}층 · ${a.hidden_size}차원</strong></div>
      <div class="anat-item"><span>어텐션 메커니즘</span><strong>${a.attention}</strong></div>
      <div class="anat-item"><span>신경망 활성 블록</span><strong>${a.ffn}</strong></div>
      <div class="anat-item"><span>단어 사전 구조</span><strong>${a.vocab}</strong></div>
    </div>
    <strong style="color:#6ee7b7">✔ 우리 두뇌 기본 틀로 흡수할 핵심 원리</strong>
    <ul class="anat-list">${a.keep_parts.map((x) => `<li>${x}</li>`).join("")}</ul>
    <strong style="color:#fca5a5">✂ 과감히 덜어내고 재설계할 부분</strong>
    <ul class="anat-list" style="margin-bottom:0">${a.strip_parts.map((x) => `<li>${x}</li>`).join("")}</ul>
  `;
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
      x: prev ? prev.x : w / 2 + Math.cos(angle) * 130,
      y: prev ? prev.y : h / 2 + Math.sin(angle) * 105,
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
  document.getElementById("viewerTitle").textContent = n.title;
  document.getElementById("viewerPath").textContent = `vault/${n.rel_path}`;
  const tagBox = document.getElementById("viewerTags");
  tagBox.innerHTML = (n.tags || []).map((t) => `<span class="tag-chip">#${t}</span>`).join("");
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
    graphState.dragNode.x = Math.max(36, Math.min(canvas.width - 36, pos.x));
    graphState.dragNode.y = Math.max(36, Math.min(canvas.height - 36, pos.y));
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
        const dist2 = Math.max(500, dx * dx + dy * dy);
        const force = 2900 / dist2;
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
      const pull = (dist - 145) * 0.012;
      a.vx += (dx / dist) * pull;
      a.vy += (dy / dist) * pull;
      b.vx -= (dx / dist) * pull;
      b.vy -= (dy / dist) * pull;
    });

    nodes.forEach((n) => {
      if (n === graphState.dragNode) return;
      n.vx += (w / 2 - n.x) * 0.0024;
      n.vy += (h / 2 - n.y) * 0.0024;
      n.vx *= 0.84;
      n.vy *= 0.84;
      n.x = Math.max(46, Math.min(w - 46, n.x + n.vx));
      n.y = Math.max(38, Math.min(h - 38, n.y + n.vy));
    });

    ctx.clearRect(0, 0, w, h);
    edges.forEach((e) => {
      const a = byId[e.source];
      const b = byId[e.target];
      if (!a || !b) return;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = "rgba(165, 180, 252, 0.34)";
      ctx.lineWidth = 1.8;
      ctx.stroke();
    });

    nodes.forEach((n) => {
      const color = CATEGORY_COLORS[n.category] || "#818cf8";
      const isSel = n.id === graphState.selectedId;
      ctx.beginPath();
      ctx.arc(n.x, n.y, isSel ? 15 : 11.5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = isSel ? 16 : 7;
      ctx.fill();
      ctx.shadowBlur = 0;
      if (isSel) {
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
      }
      ctx.fillStyle = "#cbd5e1";
      ctx.font = "11.5px sans-serif";
      ctx.textAlign = "center";
      const label = n.title.length > 19 ? n.title.slice(0, 18) + "…" : n.title;
      ctx.fillText(label, n.x, n.y + 27);
    });

    requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

function setupInteractions() {
  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  // Manual Pose Preview Strip
  document.querySelectorAll(".pose-dot").forEach((btn) => {
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

  // Sample snacks
  document.querySelectorAll("[data-snack]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sample = SNACK_SAMPLES[btn.dataset.snack];
      if (!sample) return;
      document.getElementById("feedTitle").value = sample.title;
      document.getElementById("feedText").value = sample.text;
    });
  });

  // Feed memory (shows 03_swirl while digesting -> switches to 06_star / 05_drop!)
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
    statusEl.textContent = "시냅스 소용돌이로 지식을 소화하는 중...";
    const res = await apiPost("api/feed", { title, text });
    if (res.digested) {
      pulsePortrait();
      renderStatus(res.status);
      openNoteBySlug(res.digested.slug);
      statusEl.textContent = "위키 저장 및 시냅스 연결 완료!";
      const box = document.getElementById("digestResult");
      box.classList.remove("hidden");
      box.innerHTML = `
        <strong>새 마크다운 기억 카드 생성 완료</strong><br/>
        • 저장 경로: <code>vault/${res.digested.rel_path}</code><br/>
        • 분류: <strong>${res.digested.category}</strong> · 태그: ${res.digested.tags.map((t) => "#" + t).join(" ")}<br/>
        • 연결된 시냅스: ${
          res.digested.links.length
            ? res.digested.links.map((l) => `<code>[[${l}]]</code>`).join(", ")
            : "독립 씨앗 노트"
        }
      `;
      document.getElementById("feedTitle").value = "";
      document.getElementById("feedText").value = "";
    }
  });

  // Blueprint Dissector selector
  document.querySelectorAll("[data-bp]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-bp]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      setPetPose("02_curious");
      loadAnatomy(btn.dataset.bp);
    });
  });

  // Custom Quantization Forge
  document.getElementById("btnForge").addEventListener("click", async () => {
    const bits = parseInt(document.getElementById("forgeBits").value, 10);
    const hidden_dim = parseInt(document.getElementById("forgeDim").value, 10);
    const box = document.getElementById("forgeResult");
    manualPoseOverride = null;
    setPetPose("03_swirl");
    box.classList.remove("hidden");
    box.innerHTML = "신경망 가중치를 조립하고 블록 양자화 눈금으로 깎는 중...";

    const res = await apiPost("api/forge", { bits, hidden_dim });
    if (res.forged) {
      const f = res.forged;
      pulsePortrait();
      renderStatus(res.status);
      box.innerHTML = `
        <strong>우리만의 독자 양자화 두뇌 주조 완료! (<code>models/${f.filename}</code>)</strong><br/>
        • 학습 어휘: <strong>${f.vocab_size}개</strong> · 총 파라미터: <strong>${f.total_params.toLocaleString()}개</strong> (${f.elapsed_ms} ms 소요)<br/>
        • 용량 압축: 원본 FP32 <code>${f.fp32_kb} KB</code> → <strong>INT${f.bits} <code>${f.quant_weights_kb} KB</code> (-${f.saved_vs_fp32_pct}% 절감 / FP16 대비 -${f.saved_vs_fp16_pct}%)</strong><br/>
        • 양자화 정밀도 보존율: <strong>코사인 유사도 ${f.cosine_similarity_pct}%</strong> (오차 RMSE ${f.rmse})<br/>
        • 형성된 대표 연상 시냅스: ${f.sample_synapses.map((s) => `<code>${s}</code>`).join(" · ")}
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
    const uDiv = document.createElement("div");
    uDiv.className = "bubble user";
    uDiv.textContent = question;
    log.appendChild(uDiv);

    const bDiv = document.createElement("div");
    bDiv.className = "bubble bot";
    bDiv.textContent = "관련 시냅스 기억 카드를 탐색하고 있어요...";
    log.appendChild(bDiv);
    log.scrollTop = log.scrollHeight;

    manualPoseOverride = null;
    setPetPose("02_curious");
    const res = await apiPost("api/chat", { question });
    pulsePortrait();
    bDiv.textContent = res.answer || "응답을 불러오지 못했습니다.";
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
  const [statusData] = await Promise.all([
    apiGet("api/status"),
    loadAnatomy("custom-synapse-seed"),
  ]);
  renderStatus(statusData);
}

init();
