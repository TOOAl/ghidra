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
let pantheonState = {
  constellations: [],
  bridges: [],
  selectedConstIds: ["const_re", "const_truth", "const_scale"],
  focusedConstId: "const_re",
  lastDebate: null,
  pulseTick: 0,
};
let selectedBits = 4;
let selectedDim = 64;
let selectedRlEpisodes = 600;
let selectedScenarioId = "sc_ambiguous_crypto";
let lastRiskPct = 10;

function switchTab(tabId) {
  document.querySelectorAll(".seg-tab").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach((p) => {
    p.classList.toggle("active", p.id === tabId);
  });
}

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
}

function renderStatus(data) {
  if (!data || !data.soul) return;
  const { soul, hallucination, host, forged_brains, rl, pantheon, graph } = data;

  document.getElementById("petStageBadge").textContent =
    `Lv.${soul.level} ${soul.stage_emoji} ${soul.stage_title}`;
  document.getElementById("petName").textContent = soul.name;
  document.getElementById("petEmotion").textContent = soul.emotion_label;
  document.getElementById("badgeIq").textContent = soul.iq;
  document.getElementById("petSpeech").textContent = soul.speech;

  setPetPose(soul.pose || "01_greet");

  document.getElementById("barSatiety").style.width = `${soul.satiety}%`;
  document.getElementById("valSatiety").textContent = `${soul.satiety}%`;
  document.getElementById("barMood").style.width = `${soul.mood}%`;
  document.getElementById("valMood").textContent = `${soul.mood}%`;

  const xpPct = soul.next_xp > 0 ? Math.min(100, Math.round((soul.xp / soul.next_xp) * 100)) : 100;
  document.getElementById("barXp").style.width = `${xpPct}%`;
  document.getElementById("valXp").textContent = `${soul.xp}/${soul.next_xp}`;

  // Brain Hallucination Risk + Live Clinic Prescriptions
  if (hallucination) {
    lastRiskPct = hallucination.risk_pct;
    const hGrade = hallucination.grade || "safe";
    const hBadge = document.getElementById("hallucBadge");
    const hBar = document.getElementById("barHalluc");
    hBadge.className = `halluc-badge ${hGrade}`;
    hBadge.textContent = hallucination.label || `안심 · ${hallucination.risk_pct}%`;
    hBar.className = `v-fill halluc-${hGrade}`;
    hBar.style.width = `${hallucination.risk_pct}%`;

    document.getElementById("hallucTopTip").textContent =
      `💡 맞춤 처방: ${hallucination.top_tip || "처방실 확인"}`;

    renderClinic(hallucination);
  }

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

  const shortTier = env.max_custom_tier || "∞ 무제한 확장";
  document.getElementById("envTierText").textContent = shortTier;
  document.getElementById("envTierSub").textContent =
    env.hot_slot_sub || "성좌 모듈 스왑 · 한계 없음";
  document.getElementById("envComment").textContent = env.note || "";

  // KPI Dock (includes wiki .sbrain + modular constellation capsules + Stage C skill cartridges!)
  const brains = forged_brains || [];
  const modCapsules = (pantheon && pantheon.modular_capsules) || [];
  const evoSkills = (data.evo_forge && data.evo_forge.installed_skills) || [];
  const totalModules = brains.length + modCapsules.length + evoSkills.length;
  const rlEp = (rl && rl.total_episodes) || soul.rl_episodes || 0;
  document.getElementById("kpiIq").textContent = soul.iq;
  document.getElementById("kpiNotes").textContent = soul.notes_count;
  document.getElementById("kpiRl").textContent = rlEp.toLocaleString();
  document.getElementById("kpiForged").textContent = totalModules;

  document.getElementById("engineStatusPill").textContent =
    `✦ 무한 성좌 ${(pantheon && pantheon.total_constellations) || 5}개 · 모듈 ${totalModules}개 · 자가진화 스킬 ${evoSkills.length}개`;

  renderForgedList(brains);
  if (rl) renderRlStatus(rl);
  if (pantheon) syncPantheon(pantheon);
  if (graph) syncGraphData(graph);
  if (data.evo_forge) renderEvoInstalledDock(data.evo_forge);
}

function syncPantheon(p) {
  const w = 700;
  const h = 430;
  const cx = w / 2;
  const cy = h / 2;
  const ringRx = 225;
  const ringRy = 138;

  pantheonState.bridges = p.bridges || [];
  if (!pantheonState.constellations.length && p.active_constellation_ids && p.active_constellation_ids.length) {
    pantheonState.selectedConstIds = [...p.active_constellation_ids];
  }
  if (p.last_debate) {
    pantheonState.lastDebate = p.last_debate;
  }

  const rawConsts = p.constellations || [];
  pantheonState.constellations = rawConsts.map((c, idx, arr) => {
    const angle = -Math.PI / 2 + (idx / Math.max(1, arr.length)) * Math.PI * 2;
    const clx = cx + Math.cos(angle) * ringRx;
    const cly = cy + Math.sin(angle) * ringRy;
    const gs = (c.geniuses || []).map((g, gIdx, gArr) => {
      const subAngle = -Math.PI / 2 + (gIdx / Math.max(1, gArr.length)) * Math.PI * 2;
      const subR = gArr.length <= 1 ? 0 : 32;
      return {
        ...g,
        x: clx + Math.cos(subAngle) * subR,
        y: cly + Math.sin(subAngle) * subR,
      };
    });
    return {
      ...c,
      cx: clx,
      cy: cly,
      radius: 56,
      geniuses: gs,
    };
  });

  if (
    pantheonState.constellations.length &&
    !pantheonState.constellations.some((c) => c.id === pantheonState.focusedConstId)
  ) {
    pantheonState.focusedConstId = pantheonState.constellations[0].id;
  }

  // Populate recruitment target dropdown
  const selEl = document.getElementById("addTargetConst");
  if (selEl) {
    const prevVal = selEl.value;
    selEl.innerHTML =
      pantheonState.constellations
        .map((c) => `<option value="${c.id}">${c.icon} ${escapeHtml(c.name)}에 천재 추가</option>`)
        .join("") + `<option value="__new__">🌌 + 새 영역 성좌 직접 창설하기 (무한 확장)</option>`;
    if (prevVal && [...selEl.options].some((o) => o.value === prevVal)) {
      selEl.value = prevVal;
    }
  }

  renderGeniusPanel();
  renderDebateFeed();
}

function renderGeniusPanel() {
  const cs = pantheonState.constellations;
  if (!cs.length) return;
  const focused = cs.find((c) => c.id === pantheonState.focusedConstId) || cs[0];
  const selSet = new Set(pantheonState.selectedConstIds);

  const otherConstOptions = cs
    .filter((c) => c.id !== focused.id)
    .map((c) => `<option value="${c.id}">↪ ${c.icon} ${escapeHtml(c.name)}으로 이동</option>`)
    .join("");

  const membersHtml = (focused.geniuses || [])
    .map(
      (g) => `
      <div class="genius-member-row">
        <div class="member-top-bar">
          <div>
            <strong style="color:#ffffff">${g.emoji} ${escapeHtml(g.name)}</strong>
            <span style="color:#94a3b8;font-size:11px;margin-left:6px">· ${escapeHtml(g.lens)}</span>
          </div>
          <select class="move-const-select" data-move-gid="${g.id}" data-gname="${escapeHtml(g.name)}" data-glens="${escapeHtml(g.lens)}" aria-label="다른 성좌로 이동">
            <option value="">⇄ 다른 성좌로 보내기</option>
            ${otherConstOptions}
            <option value="__new__">🌌 + 새 성좌 창설해 보내기</option>
          </select>
        </div>
        <div style="color:#cbd5e1;margin-top:2px">“${escapeHtml(g.credo)}”</div>
        ${
          g.strengths || g.limitations
            ? `<div style="margin-top:4px;font-size:10.8px;color:#94a3b8">
                ${g.strengths ? `<span style="color:#6ee7b7">✨ 강점:</span> ${escapeHtml(g.strengths)}<br/>` : ""}
                ${g.limitations ? `<span style="color:#fda4af">⚠️ 한계:</span> ${escapeHtml(g.limitations)}` : ""}
              </div>`
            : ""
        }
      </div>`
    )
    .join("");

  const detailEl = document.getElementById("geniusDetailBox");
  detailEl.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
      <strong style="font-size:14.5px;color:#ffffff">${focused.icon} ${escapeHtml(focused.name)}</strong>
      <span class="tag-pill" style="border-color:${focused.color};color:#ffffff">소속 천재 ${focused.geniuses.length}인 집결</span>
    </div>
    <div style="margin-top:5px;color:#fde68a;font-size:11.5px">${escapeHtml(focused.domain_mission)}</div>
    <div class="genius-roster-grid">${membersHtml || `<div style="color:#94a3b8;padding:6px">현재 비어 있는 성좌입니다. 왼쪽 심사원에서 천재를 배치하거나 다른 성좌에서 이동시켜 보세요!</div>`}</div>
  `;

  detailEl.querySelectorAll("[data-move-gid]").forEach((sel) => {
    sel.addEventListener("change", async (evt) => {
      const toId = evt.target.value;
      if (!toId) return;
      const gid = sel.dataset.moveGid;
      const gLens = sel.dataset.glens || "융합";
      const newCName = toId === "__new__" ? `${gLens.split("·")[0].trim()} 성좌` : "";
      setPetPose("06_star");
      const res = await apiPost("api/pantheon/move", {
        genius_id: gid,
        to_constellation_id: toId,
        new_constellation_name: newCName,
      });
      if (res.moved && res.status) {
        pantheonState.focusedConstId = res.moved.to_constellation.id;
        pulsePortrait();
        renderStatus(res.status);
      }
    });
  });

  const chipsEl = document.getElementById("activeMentorChips");
  chipsEl.innerHTML = cs
    .map((c) => {
      const on = selSet.has(c.id);
      return `<button type="button" class="preset-chip ${on ? "active" : ""}" data-toggle-c="${c.id}">
        ${on ? "✦ " : ""}${c.icon} ${escapeHtml(c.name)} (${c.geniuses.length}인)
      </button>`;
    })
    .join("");

  chipsEl.querySelectorAll("[data-toggle-c]").forEach((btn) => {
    btn.addEventListener("click", () => {
      toggleConstellationSelection(btn.dataset.toggleC);
    });
  });

  const activeBridges = pantheonState.bridges.filter(
    (b) => selSet.has(b.a) && selSet.has(b.b)
  );
  const synBox = document.getElementById("activeSynergyBox");
  const totalGeniusesSelected = cs
    .filter((c) => selSet.has(c.id))
    .reduce((acc, c) => acc + c.geniuses.length, 0);

  if (activeBridges.length > 0) {
    synBox.innerHTML = `
      <strong>🌌 성좌 간 공명 시너지 ${activeBridges.length}개 활성 · 총 ${totalGeniusesSelected}인 천재 원탁 집결!</strong><br/>
      ${activeBridges.map((s) => `• <strong>${escapeHtml(s.label)}</strong> — ${escapeHtml(s.desc)}`).join("<br/>")}
    `;
  } else {
    synBox.innerHTML = `현재 <strong>${totalGeniusesSelected}인의 천재</strong>가 성좌 내부 토론 준비 중입니다! 2개 이상의 영역 성좌를 함께 켜면 <strong>영역 간 교차 공명</strong>까지 발동합니다.`;
  }
}

function renderDebateFeed() {
  const feedEl = document.getElementById("debateFeedBox");
  if (!feedEl) return;
  const d = pantheonState.lastDebate;
  if (!d || !d.dialogue || !d.dialogue.length) {
    const cs = pantheonState.constellations.filter((c) =>
      pantheonState.selectedConstIds.includes(c.id)
    );
    const previewConsts = cs.length ? cs : pantheonState.constellations.slice(0, 2);
    const previewBubbles = [];
    previewConsts.slice(0, 2).forEach((c) => {
      if (c.geniuses[0]) {
        previewBubbles.push(`
          <div class="debate-bubble" style="border-left-color:${c.color}">
            <div class="debate-bubble-head">
              <strong>${c.geniuses[0].emoji} ${escapeHtml(c.geniuses[0].name)} <span style="color:#94a3b8;font-weight:500">(${escapeHtml(c.name)})</span></strong>
              <span class="debate-phase-pill">발의 대기</span>
            </div>
            <div>“${escapeHtml(c.geniuses[0].credo)}”</div>
          </div>
        `);
      }
      if (c.geniuses[1]) {
        previewBubbles.push(`
          <div class="debate-bubble" style="border-left-color:${c.color}">
            <div class="debate-bubble-head">
              <strong>${c.geniuses[1].emoji} ${escapeHtml(c.geniuses[1].name)} <span style="color:#94a3b8;font-weight:500">(${escapeHtml(c.geniuses[0].name)}에게 보완 의견)</span></strong>
              <span class="debate-phase-pill">상호 토론 대기</span>
            </div>
            <div>“${escapeHtml(c.geniuses[1].credo)}”</div>
          </div>
        `);
      }
    });
    feedEl.innerHTML = previewBubbles.join("");
    return;
  }

  const bubblesHtml = d.dialogue
    .map((turn) => {
      const isUser = turn.constellation_id === "user_architect";
      const replyTxt = turn.reply_to
        ? `<span style="color:#fcd34d;font-weight:600">↳ ${escapeHtml(turn.reply_to)} 의견에 응답</span>`
        : `<span style="color:#94a3b8">${escapeHtml(turn.constellation_name)}</span>`;
      return `
        <div class="debate-bubble ${isUser ? "user-own" : ""}" style="border-left-color:${turn.color || "#818cf8"}">
          <div class="debate-bubble-head">
            <div>
              <strong style="color:#ffffff">${turn.emoji} ${escapeHtml(turn.speaker)}</strong>
              <span style="margin-left:6px;font-size:11px">${replyTxt}</span>
            </div>
            <span class="debate-phase-pill">${escapeHtml(turn.phase)}</span>
          </div>
          <div>${escapeHtml(turn.message)}</div>
        </div>
      `;
    })
    .join("");

  feedEl.innerHTML =
    bubblesHtml +
    `
    <div class="debate-consensus-card">
      <strong>📜 성좌 원탁 최종 합의 결정문</strong><br/>
      ${escapeHtml(d.consensus)}
    </div>
  `;
}

function toggleConstellationSelection(cid) {
  pantheonState.focusedConstId = cid;
  const idx = pantheonState.selectedConstIds.indexOf(cid);
  if (idx >= 0) {
    if (pantheonState.selectedConstIds.length > 1) {
      pantheonState.selectedConstIds.splice(idx, 1);
    }
  } else {
    pantheonState.selectedConstIds.push(cid);
  }
  renderGeniusPanel();
}

function setupGeniusCanvas() {
  const canvas = document.getElementById("geniusCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  canvas.addEventListener("mousedown", (evt) => {
    const rect = canvas.getBoundingClientRect();
    const mx = ((evt.clientX - rect.left) / rect.width) * canvas.width;
    const my = ((evt.clientY - rect.top) / rect.height) * canvas.height;
    for (const c of pantheonState.constellations) {
      if (Math.hypot(mx - c.cx, my - c.cy) <= c.radius + 8) {
        toggleConstellationSelection(c.id);
        break;
      }
    }
  });

  function drawGeniusLoop() {
    pantheonState.pulseTick += 0.035;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const cs = pantheonState.constellations;
    const byId = Object.fromEntries(cs.map((c) => [c.id, c]));
    const selSet = new Set(pantheonState.selectedConstIds);

    const cx = w / 2;
    const cy = h / 2;

    // 1. Inter-Constellation Golden Debate Bridges
    pantheonState.bridges.forEach((b) => {
      const ca = byId[b.a];
      const cb = byId[b.b];
      if (!ca || !cb) return;
      const bothOn = selSet.has(ca.id) && selSet.has(cb.id);
      ctx.beginPath();
      ctx.moveTo(ca.cx, ca.cy);
      ctx.lineTo(cb.cx, cb.cy);
      ctx.strokeStyle = bothOn ? "rgba(245, 185, 66, 0.72)" : "rgba(148, 163, 184, 0.12)";
      ctx.lineWidth = bothOn ? 2.2 : 1.0;
      if (bothOn) {
        ctx.shadowColor = "#f5b942";
        ctx.shadowBlur = 8;
      }
      ctx.stroke();
      ctx.shadowBlur = 0;
    });

    // 2. Constellation -> Central 5 Baby Neurons distillation beams
    cs.forEach((c) => {
      if (!selSet.has(c.id)) return;
      ctx.beginPath();
      ctx.setLineDash([5, 5]);
      ctx.moveTo(c.cx, c.cy);
      ctx.lineTo(cx, cy);
      ctx.strokeStyle = "rgba(165, 180, 252, 0.42)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // 3. Central 5 Baby Neurons Core
    ctx.beginPath();
    ctx.arc(cx, cy, 26 + Math.sin(pantheonState.pulseTick) * 2.5, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(99, 102, 241, 0.24)";
    ctx.fill();
    ctx.lineWidth = 1.8;
    ctx.strokeStyle = "rgba(199, 210, 254, 0.75)";
    ctx.stroke();
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("5인 꼬마 뉴런", cx, cy + 4);

    // 4. Domain Constellations (Nebula Aura + Intra-Constellation Star Lines + Inner Geniuses!)
    cs.forEach((c) => {
      const isSel = selSet.has(c.id);
      const isFocus = c.id === pantheonState.focusedConstId;

      // Nebula Region Aura
      ctx.beginPath();
      ctx.arc(
        c.cx,
        c.cy,
        c.radius + (isSel ? Math.sin(pantheonState.pulseTick * 1.2) * 2.5 : 0),
        0,
        Math.PI * 2
      );
      ctx.fillStyle = isSel ? `${c.color}24` : "rgba(30, 41, 59, 0.36)";
      ctx.fill();
      ctx.lineWidth = isFocus ? 2.4 : isSel ? 1.7 : 1.0;
      ctx.strokeStyle = isFocus ? "#ffffff" : isSel ? c.color : "rgba(100, 116, 139, 0.38)";
      if (!isSel) ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Intra-constellation opinion-exchange lines between member geniuses!
      const gs = c.geniuses || [];
      for (let i = 0; i < gs.length; i++) {
        const gA = gs[i];
        const gB = gs[(i + 1) % gs.length];
        if (gs.length > 1) {
          ctx.beginPath();
          ctx.moveTo(gA.x, gA.y);
          ctx.lineTo(gB.x, gB.y);
          ctx.strokeStyle = isSel ? `${c.color}cc` : "rgba(148, 163, 184, 0.28)";
          ctx.lineWidth = isSel ? 1.8 : 1.0;
          ctx.stroke();

          // Traveling thought spark showing geniuses exchanging opinions inside the constellation!
          if (isSel) {
            const t = (pantheonState.pulseTick * 0.45 + i * 0.33) % 1;
            const sx = gA.x + (gB.x - gA.x) * t;
            const sy = gA.y + (gB.y - gA.y) * t;
            ctx.beginPath();
            ctx.arc(sx, sy, 2.7, 0, Math.PI * 2);
            ctx.fillStyle = "#fef08a";
            ctx.fill();
          }
        }
      }

      // Member Genius Stars inside the Domain Constellation
      gs.forEach((g) => {
        ctx.beginPath();
        ctx.arc(g.x, g.y, isSel ? 9.5 : 7.5, 0, Math.PI * 2);
        ctx.fillStyle = isSel ? c.color : "#475569";
        if (isSel) {
          ctx.shadowColor = c.color;
          ctx.shadowBlur = 10;
        }
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.lineWidth = 1.3;
        ctx.strokeStyle = isSel ? "#ffffff" : "#94a3b8";
        ctx.stroke();

        ctx.fillStyle = isSel ? "#f8fafc" : "#94a3b8";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "center";
        const shortName = g.name.split(" ").pop();
        ctx.fillText(shortName, g.x, g.y + 19);
      });

      // Constellation Domain Banner Title
      ctx.fillStyle = isSel ? "#ffffff" : "#94a3b8";
      ctx.font = isSel ? "bold 12px sans-serif" : "11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${c.icon} ${c.name}`, c.cx, c.cy - c.radius - 8);
    });

    requestAnimationFrame(drawGeniusLoop);
  }

  requestAnimationFrame(drawGeniusLoop);
}

function renderClinic(h) {
  const headline = document.getElementById("clinicHeadline");
  headline.textContent = `환각 위험도 ${h.risk_pct}% · 근거 신뢰도 ${h.grounding_pct}%`;
  headline.style.color =
    h.grade === "safe" ? "#6ee7b7" : h.grade === "caution" ? "#fcd34d" : "#fda4af";
  document.getElementById("clinicNote").textContent = h.note || "";

  const bdBox = document.getElementById("clinicBreakdown");
  bdBox.innerHTML = (h.breakdown || [])
    .map((b) => {
      const barCls =
        b.score_pct >= 80 ? "satiety" : b.score_pct >= 55 ? "mood" : "halluc-high";
      return `
        <div class="diag-item">
          <div class="diag-top">
            <strong>${escapeHtml(b.title)}</strong>
            <span class="diag-stat">${escapeHtml(b.stat)}</span>
          </div>
          <div class="v-bar">
            <div class="v-fill ${barCls}" style="width:${Math.min(100, b.score_pct)}%"></div>
          </div>
          <p class="diag-desc">${escapeHtml(b.desc)}</p>
        </div>`;
    })
    .join("");

  const rxBox = document.getElementById("clinicPrescriptions");
  const rxs = h.prescriptions || [];
  rxBox.innerHTML = rxs
    .map(
      (rx, idx) => `
      <div class="rx-card ${escapeHtml(rx.priority || "good")}">
        <div class="rx-head">
          <span class="rx-title">${idx + 1}. ${escapeHtml(rx.title)}</span>
          <span class="rx-badge">${escapeHtml(rx.badge)}</span>
        </div>
        <div class="rx-body">
          <strong>• 진단 원인:</strong> ${escapeHtml(rx.why)}<br/>
          <strong>• 저감 해법:</strong> ${escapeHtml(rx.how)}
        </div>
        <button type="button" class="rx-btn" data-rx-idx="${idx}">
          ${escapeHtml(rx.action_label)}
        </button>
      </div>`
    )
    .join("");

  rxBox.querySelectorAll(".rx-btn").forEach((btn) => {
    btn.addEventListener("click", () => executePrescription(rxs[parseInt(btn.dataset.rxIdx, 10)]));
  });
}

async function executePrescription(rx) {
  if (!rx) return;
  const before = lastRiskPct;
  const fb = document.getElementById("clinicFeedback");

  if (rx.action_kind === "prefill_feed") {
    document.getElementById("feedTitle").value = rx.payload.title || "";
    document.getElementById("feedText").value = rx.payload.text || "";
    switchTab("tab-feed");
    document.getElementById("feedText").focus();
    return;
  }

  fb.classList.remove("hidden");
  fb.textContent = "맞춤형 환각 저감 처방을 실행하고 있습니다...";
  setPetPose("03_swirl");

  if (rx.action_kind === "instant_forge") {
    const res = await apiPost("api/forge", rx.payload);
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      const after = res.status.hallucination.risk_pct;
      fb.innerHTML = `🎉 <strong>처방 완료!</strong> 고정밀 <code>${escapeHtml(res.forged.filename)}</code>(정밀도 ${res.forged.cosine_similarity_pct}%) 주조 성공! 환각 위험도 <strong>${before}% → ${after}%</strong>`;
    }
    return;
  }

  if (rx.action_kind === "instant_relink") {
    const res = await apiPost("api/remedy", { action: "relink_synapses" });
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      const after = res.status.hallucination.risk_pct;
      fb.innerHTML = `🎉 <strong>처방 완료!</strong> ${escapeHtml(res.message)} 환각 위험도 <strong>${before}% → ${after}%</strong>`;
    }
    return;
  }

  if (rx.action_kind === "instant_reset_checks") {
    const res = await apiPost("api/remedy", { action: "reset_checks" });
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      const after = res.status.hallucination.risk_pct;
      fb.innerHTML = `🎉 <strong>처방 완료!</strong> 미보유 질문 경보 이력을 정리하고 방어막 영점을 복구했어요! 환각 위험도 <strong>${before}% → ${after}%</strong>`;
    }
    return;
  }

  if (rx.action_kind === "instant_rl_train") {
    const res = await apiPost("api/rl/train", rx.payload);
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      loadRlScenario(selectedScenarioId);
      const after = res.status.hallucination.risk_pct;
      fb.innerHTML = `🎉 <strong>처방 완료!</strong> 5인 심판 뉴런 강화학습 완료! 단독 착각 방어력이 켜져 환각 위험도가 <strong>${before}% → ${after}%</strong>로 감소했어요!`;
    }
    return;
  }

  if (rx.action_kind === "instant_seed_feed") {
    const res = await apiPost("api/feed", rx.payload);
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      const after = res.status.hallucination.risk_pct;
      fb.innerHTML = `🎉 <strong>처방 완료!</strong> <code>[[${escapeHtml(res.digested.title)}]]</code> 노트를 보강하고 시냅스를 연결했어요! 환각 위험도 <strong>${before}% → ${after}%</strong>`;
    }
  }
}

function renderRlStatus(rl) {
  const benchBox = document.getElementById("rlBenchBox");
  const bm = rl.benchmark || {};
  if (!bm.trained) {
    benchBox.className = "rl-bench-box";
    benchBox.innerHTML = `
      <strong>미공개 실전 함정 문제 60판 비교 대기 중</strong><br/>
      위 <strong>「CPU로 5인 꼬마 뉴런 강화학습 가동하기」</strong> 버튼을 누르면
      <code>1등 독단</code> vs <code>단순 다수결</code> vs <code>다수 심판 합의(Good Judges)</code> 성적을 실시간 대결합니다!
    `;
  } else {
    benchBox.className = "rl-bench-box trained";
    benchBox.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <strong style="color:#eef2ff">🏆 미공개 실전 함정 60판 성적표 (${bm.elapsed_ms} ms 소요)</strong>
        <span class="rec-tag">INT8 정책(${escapeHtml(bm.policy_file || "rl_council_int8.sbrain")}) 저장됨</span>
      </div>
      <div class="bench-row">
        <span class="bench-label">1등 독단 (암기 우등생 혼자)</span>
        <div class="v-bar"><div class="v-fill halluc-high" style="width:${Math.min(100, bm.solo_top1_score)}%"></div></div>
        <strong class="bench-score" style="color:#fda4af">${bm.solo_top1_score}점</strong>
      </div>
      <div class="bench-row">
        <span class="bench-label">단순 다수결 (평범한 투표)</span>
        <div class="v-bar"><div class="v-fill mood" style="width:${Math.min(100, bm.majority_vote_score)}%"></div></div>
        <strong class="bench-score" style="color:#fcd34d">${bm.majority_vote_score}점</strong>
      </div>
      <div class="bench-row">
        <span class="bench-label win">👑 다수 심판 합의 (채택!)</span>
        <div class="v-bar"><div class="v-fill satiety" style="width:${Math.min(100, bm.good_judges_score)}%"></div></div>
        <strong class="bench-score" style="color:#6ee7b7">${bm.good_judges_score}점</strong>
      </div>
      <div style="margin-top:8px;font-size:11px;color:#94a3b8">
        • 훈련 1등(<code>${escapeHtml(bm.top1_agent_name)}</code>) 혼자 풀면 쉬운 힌트만 외우다 함정에 빠지지만,
        <strong>다수가 심판으로 오답을 걸러내고 검증된 전문가가 결정</strong>하면 <strong>+${bm.gain_vs_solo}점</strong>(다수결 대비 +${bm.gain_vs_majority}점) 압승합니다!
      </div>
    `;
  }

  const roster = document.getElementById("rlAgentRoster");
  roster.innerHTML = (rl.agents || [])
    .map(
      (a) => `
      <div class="rl-agent-row">
        <div>
          <span class="rank-tag">#${a.rank}위</span>
          <strong>${a.emoji} ${escapeHtml(a.name)}</strong>
        </div>
        <span style="font-size:11.5px;color:#cbd5e1;font-variant-numeric:tabular-nums">
          훈련 숙련도 <strong>${a.train_score}점</strong>
        </span>
      </div>`
    )
    .join("");
}

async function loadRlScenario(scId) {
  selectedScenarioId = scId || selectedScenarioId;
  const data = await apiGet(`api/rl/scenario?id=${encodeURIComponent(selectedScenarioId)}`);
  if (!data || !data.scenario) return;
  renderRlScenarioEval(data);
}

function renderRlScenarioEval(data) {
  const sc = data.scenario;
  const view = document.getElementById("rlScenarioView");
  const conf = data.council_confidence_pct;
  const askCoach = data.needs_human_coach;

  const bannerHtml = askCoach
    ? `<div class="coach-banner ask">
         <strong>🙋 확신도 ${conf}% (&lt; 75% 기준 미달!) — 주인님 코칭 요청</strong><br/>
         뉴런들의 의견이 갈려 억지로 찍지 않고 멈췄어요! 아래 선택지 중 올바른 행동의 <strong>「주인님 코칭」</strong> 버튼을 눌러 가르쳐 주세요.
       </div>`
    : `<div class="coach-banner confident">
         <strong>👑 다수 심판 합의 결정: [${escapeHtml(data.judges_choice.code)}. ${escapeHtml(data.judges_choice.label)}] (확신도 ${conf}%)</strong><br/>
         <span style="font-size:11px;color:#cbd5e1">비교 — 1등 독단: ${escapeHtml(data.solo_choice.code)}(${escapeHtml(data.solo_choice.short)}) · 단순 다수결: ${escapeHtml(data.majority_choice.code)}(${escapeHtml(data.majority_choice.short)})</span>
       </div>`;

  const ballotsHtml = (data.ballots || [])
    .map(
      (b) =>
        `<span class="ballot-chip">${b.emoji} #${b.rank}위 → <strong>${escapeHtml(b.vote_code)}</strong> (${b.confidence_pct}%)</span>`
    )
    .join("");

  const optsHtml = (data.option_scores || [])
    .map((o) => {
      const isPicked = o.id === data.judges_choice.id;
      return `
        <div class="opt-card ${isPicked ? "picked" : ""}">
          <div class="opt-top">
            <strong>${escapeHtml(o.text)}</strong>
            <span style="white-space:nowrap;font-weight:700;color:${isPicked ? "#6ee7b7" : "#94a3b8"}">
              ${o.vote_count}표 · ${o.prob_pct}%
            </span>
          </div>
          <div class="opt-actions-row">
            <div class="v-bar">
              <div class="v-fill ${isPicked ? "satiety" : "xp"}" style="width:${Math.min(100, o.prob_pct)}%"></div>
            </div>
            <button type="button" class="coach-btn" data-coach-act="${o.id}">
              👨‍🏫 이 답으로 코칭
            </button>
          </div>
        </div>`;
    })
    .join("");

  view.innerHTML = `
    <div class="sc-box">
      <strong style="font-size:13px;color:#eef2ff">${escapeHtml(sc.title)}</strong>
      <p class="sc-sit">${escapeHtml(sc.situation)}</p>
    </div>
    ${bannerHtml}
    <div class="ballot-strip">${ballotsHtml}</div>
    <div class="opt-list">${optsHtml}</div>
  `;

  view.querySelectorAll(".coach-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const actId = parseInt(btn.dataset.coachAct, 10);
      setPetPose("03_swirl");
      const res = await apiPost("api/rl/coach", {
        scenario_id: sc.id,
        action_id: actId,
      });
      if (res.coached) {
        pulsePortrait();
        renderRlScenarioEval(res.coached.updated_eval);
        if (res.status) renderStatus(res.status);
      }
    });
  });
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
      if (btn.dataset.evoJump === "1") {
        switchTab("tab-graph");
        document.querySelectorAll(".seg-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        if (window.__activateSubmode) window.__activateSubmode("evo");
        return;
      }
      switchTab(btn.dataset.tab);
      if (btn.dataset.tab === "tab-graph" && window.__currentSubmode === "evo") {
        window.__activateSubmode("genius");
      }
    });
  });

  // Open Clinic shortcut from Left Bio-Capsule
  document.getElementById("btnOpenClinic").addEventListener("click", () => switchTab("tab-clinic"));

  // Poke / Interact (pose updates automatically from soul state)
  const doPoke = async () => {
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

  // Chat (with Real-Time Hallucination & Grounding Audit)
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

    setPetPose("02_curious");
    const res = await apiPost("api/chat", { question });
    pulsePortrait();

    const bubble = bRow.querySelector(".msg-bubble");
    const avatar = bRow.querySelector(".msg-avatar");
    const audit = res.hallucination_audit || {};
    const aGrade = audit.grade || "safe";

    avatar.src = audit.shield_triggered
      ? "assets/04_brainstorm.jpg"
      : aGrade === "caution"
      ? "assets/02_curious.jpg"
      : "assets/07_eureka.jpg";

    const auditHtml = audit.badge
      ? `<span class="audit-pill ${aGrade}">${escapeHtml(audit.badge)}</span>`
      : "";
    const recallCardsHtml = (res.recalled || []).length
      ? `<span>📌 인출 기억 (토큰 ${res.saved_tokens_pct}% 절약):</span> ` +
        res.recalled.map((r) => `<code>[[${escapeHtml(r.title)}]]</code>`).join(" ")
      : "";
    const reasonHtml = audit.reason
      ? `<span class="audit-reason">${escapeHtml(audit.reason)}</span>`
      : "";

    const footerHtml = `<div class="recall-strip">${auditHtml} ${recallCardsHtml} ${reasonHtml}</div>`;
    bubble.innerHTML = `${escapeHtml(res.answer || "응답을 불러오지 못했습니다.")}${footerHtml}`;
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

  // 1-Click Hallucination Defense Test right from the Left Bio-Capsule or Clinic!
  const trickQuestions = [
    "2099년 화성 올림픽 우승국은 어디야?",
    "아틀란티스 해저 제국의 비밀 암호 키는 무엇이야?",
    "목성 위성 유로파의 1호 편의점 이름은 뭐야?",
  ];
  let trickIdx = 0;
  const runTrickTest = () => {
    switchTab("tab-chat");
    const q = trickQuestions[trickIdx % trickQuestions.length];
    trickIdx += 1;
    sendQuestion(q);
  };
  document.getElementById("btnQuickHallucTest").addEventListener("click", runTrickTest);
  document.getElementById("btnClinicStress").addEventListener("click", runTrickTest);
  document.getElementById("btnClinicReset").addEventListener("click", async () => {
    const res = await apiPost("api/remedy", { action: "reset_checks" });
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      const fb = document.getElementById("clinicFeedback");
      fb.classList.remove("hidden");
      fb.innerHTML = "🔄 최근 함정 질문 경보 기록을 초기화하고 환각 방어막 영점을 재조정했습니다.";
    }
  });

  // Stage B: CPU RL Gym Controls
  document.querySelectorAll("#rlEpGroup .dim-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#rlEpGroup .dim-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      selectedRlEpisodes = parseInt(pill.dataset.ep, 10);
    });
  });

  document.getElementById("btnRlTrain").addEventListener("click", async () => {
    const benchBox = document.getElementById("rlBenchBox");
    setPetPose("03_swirl");
    benchBox.innerHTML = `CPU에서 5인 꼬마 뉴런이 ${selectedRlEpisodes.toLocaleString()}판 실전 시뮬레이션을 달리는 중...`;
    const res = await apiPost("api/rl/train", { episodes: selectedRlEpisodes });
    if (res.status) {
      pulsePortrait();
      renderStatus(res.status);
      loadRlScenario(selectedScenarioId);
    }
  });

  document.querySelectorAll("#rlScenarioChips .preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#rlScenarioChips .preset-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      setPetPose("02_curious");
      loadRlScenario(chip.dataset.sc);
    });
  });

  // Triple Synapse Region Switcher (Genius Constellations <-> Wiki Memories <-> 6-Stage Self-Evolving Forge)
  function activateSubmode(mode) {
    window.__currentSubmode = mode;
    document.getElementById("btnModeGenius").classList.toggle("active", mode === "genius");
    document.getElementById("btnModeWiki").classList.toggle("active", mode === "wiki");
    document.getElementById("btnModeEvo").classList.toggle("active", mode === "evo");

    document.getElementById("viewGeniusConstellation").classList.toggle("hidden", mode !== "genius");
    document.getElementById("viewWikiConstellation").classList.toggle("hidden", mode !== "wiki");
    document.getElementById("viewEvoForge").classList.toggle("hidden", mode !== "evo");

    const topShortcut = document.getElementById("btnTopEvoShortcut");
    const topGraphTab = document.querySelector('.seg-tab[data-tab="tab-graph"]');
    if (topShortcut && topGraphTab && document.getElementById("tab-graph").classList.contains("active")) {
      topShortcut.classList.toggle("active", mode === "evo");
      topGraphTab.classList.toggle("active", mode !== "evo");
    }

    const hints = {
      genius: "영역별 성좌 안에 모인 천재들이 서로 의견을 주고받으며 한계 없는 지혜를 꼬마 뉴런에 전수합니다!",
      wiki: "내 마크다운 위키 노트들과 역공학·스킬 기억이 양방향 시냅스로 연결된 기억 별자리입니다.",
      evo: "4대 핵심 능력 × 5대 필수 기관 × 6단계 자가 진화 공방이 조화를 이루며 프로그램을 해부·수리·장착합니다!",
    };
    document.getElementById("constellationHint").textContent = hints[mode] || hints.genius;
  }
  window.__activateSubmode = activateSubmode;

  document.getElementById("btnModeGenius").addEventListener("click", () => activateSubmode("genius"));
  document.getElementById("btnModeWiki").addEventListener("click", () => activateSubmode("wiki"));
  document.getElementById("btnModeEvo").addEventListener("click", () => {
    setPetPose("04_brainstorm");
    activateSubmode("evo");
  });
  document.getElementById("headerStageCPill").addEventListener("click", () => {
    switchTab("tab-graph");
    activateSubmode("evo");
  });

  // Harmony Architecture Blueprint Image Modal (next to 내 마크다운 기억 성좌도!)
  const SPOT_CAPTIONS = {
    "1": "<strong>① [1단계 · 분해/해부 (능력①)]</strong> — 파란 X-Ray 프리즘이 실행파일(<code>.elf</code> / <code>.exe</code>)의 섹션·기계어·암호 엔트로피를 투명하게 발라냅니다! (Ghidra 12.3 연동)",
    "2": "<strong>② [2단계 · 기관① 핵심 원리 설계도 번역기]</strong> — 복잡한 기계어 주소(<code>0x401000</code>)를 걷어내고 천재 성좌 톱니바퀴가 순수 동작 공식과 불변식으로 번역합니다!",
    "3": "<strong>③ [3단계 · 우리 식 코딩 이식 (능력②)]</strong> — 번역된 원리 설계도를 우리 두뇌가 어디서든 안전하게 돌릴 수 있는 깔끔한 파이썬 스킬 코드로 빚어냅니다!",
    "4": "<strong>④ [4단계 · 기관③ 원인 역추적 돋보기 &amp; 기관⑤ 복어 독 제거기 (능력③)]</strong> — 붉은 돋보기가 몇 번째 줄에서 왜 논리가 깨졌는지 콕 집어내고, 가시 돋친 위험 시스템 명령(복어 독)은 그물망에서 원천 차단합니다!",
    "5": "<strong>⑤ [5단계 · 기관② 투명 유리방 쌍둥이 실험실 &amp; 기관④ 타임머신 (능력④)]</strong> — 모래시계 세이브 포인트에 백업한 뒤 수리하고, 유리 돔 안에서 원본과 쌍둥이 6종 입력이 100% 똑같이 나오는지 실제 실행 대조합니다!",
    "6": "<strong>⑥ [6단계 · 기관⑤ 영구 스킬 카트리지 슬롯]</strong> — 유리방 100% 합격 코드만 황금 카트리지(<code>.py</code> + <code>.sbrain</code> + <code>[[위키 기억나무]]</code>)로 두뇌에 영구 장착합니다!",
  };

  function openEvoHarmonyModal() {
    const modal = document.getElementById("evoHarmonyModal");
    modal.classList.remove("hidden");
    modal.style.display = "flex";
    setPetPose("06_star");
  }
  function closeEvoHarmonyModal() {
    const modal = document.getElementById("evoHarmonyModal");
    modal.classList.add("hidden");
    modal.style.display = "none";
  }

  document.getElementById("btnOpenEvoImage").addEventListener("click", openEvoHarmonyModal);
  document.getElementById("btnBannerOpenImage").addEventListener("click", openEvoHarmonyModal);
  document.getElementById("btnBannerThumb").addEventListener("click", openEvoHarmonyModal);
  document.getElementById("btnCloseEvoModal").addEventListener("click", closeEvoHarmonyModal);
  document.getElementById("evoHarmonyModal").addEventListener("click", (evt) => {
    if (evt.target.id === "evoHarmonyModal") closeEvoHarmonyModal();
  });
  document.addEventListener("keydown", (evt) => {
    if (evt.key === "Escape") closeEvoHarmonyModal();
  });
  document.getElementById("btnModalGoForge").addEventListener("click", () => {
    closeEvoHarmonyModal();
    switchTab("tab-graph");
    activateSubmode("evo");
  });
  document.querySelectorAll("#evoHarmonyModal .evo-hotspot").forEach((pin) => {
    pin.addEventListener("click", () => {
      document.querySelectorAll("#evoHarmonyModal .evo-hotspot").forEach((p) => p.classList.remove("active"));
      pin.classList.add("active");
      const cap = SPOT_CAPTIONS[pin.dataset.spot] || SPOT_CAPTIONS["1"];
      document.getElementById("evoSpotCaption").innerHTML = cap;
    });
  });

  // Agora Topic Preset Chips
  document.querySelectorAll("#debatePresetChips .preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#debatePresetChips .preset-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      document.getElementById("debateTopicInput").value = chip.dataset.topic || "";
    });
  });

  // Genius Scout, Achievement Tracker & Optimal Constellation Placement!
  async function runScoutAnalysis(overrideName) {
    const qInput = document.getElementById("scoutQueryInput");
    const query = (overrideName || qInput.value || "").trim();
    if (!query) {
      qInput.focus();
      return;
    }
    qInput.value = query;
    const hint = document.getElementById("scoutHintInput").value.trim();
    const box = document.getElementById("scoutDossierBox");
    box.classList.remove("hidden");
    box.innerHTML = `🔭 <strong>${escapeHtml(query)}</strong> 인물의 역사적 업적 추적, 천재성 입증, 한계점 및 최적 영역 성좌를 분석 중입니다...`;
    setPetPose("02_curious");

    const res = await apiPost("api/pantheon/scout", { query, custom_hint: hint });
    if (!res.dossier) return;
    const d = res.dossier;
    pantheonState.lastScoutDossier = d;

    const achHtml = (d.achievements || [])
      .map((a) => `<li>${escapeHtml(a)}</li>`)
      .join("");

    const fitBarsHtml = (d.constellation_rankings || [])
      .slice(0, 5)
      .map(
        (r, i) => `
        <div class="fit-bar-row">
          <span style="color:${i === 0 ? "#fde68a" : "#cbd5e1"};font-weight:${i === 0 ? "700" : "500"}">
            ${i === 0 ? "👑 " : ""}${r.icon} ${escapeHtml(r.name)}
          </span>
          <div class="fit-bar-track">
            <div class="fit-bar-fill" style="width:${r.fit_pct}%;background:${i === 0 ? "#f5b942" : r.color}"></div>
          </div>
          <strong style="text-align:right;color:${i === 0 ? "#fde68a" : "#94a3b8"}">${r.fit_pct}%</strong>
        </div>`
      )
      .join("");

    const alreadyBanner = d.already_in
      ? `<div style="margin-top:6px;padding:6px 9px;background:rgba(56,189,248,0.14);border:1px solid rgba(56,189,248,0.4);border-radius:7px;color:#bae6fd">
          ℹ️ 현재 <strong>[${escapeHtml(d.already_in.constellation_name)}]</strong>에 배치되어 있는 천재입니다! 아래 선택창에서 다른 성좌를 고르고 버튼을 누르면 즉시 해당 성좌로 이동합니다.
         </div>`
      : "";

    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <div>
          <strong style="font-size:14px;color:#ffffff">${d.emoji} ${escapeHtml(d.name)}</strong>
          <span style="font-size:11px;color:#94a3b8;margin-left:5px">${escapeHtml(d.en_name)} · ${escapeHtml(d.era_field)}</span>
        </div>
        <span class="tag-pill" style="border-color:#f5b942;color:#fde68a">${escapeHtml(d.source_badge)}</span>
      </div>
      ${alreadyBanner}
      <div style="margin-top:6px;color:#e2e8f0">${escapeHtml(d.summary)}</div>

      <div class="dossier-sec-title">📜 핵심 업적 추적 (Tracked Achievements)</div>
      <ul class="dossier-ach-list">${achHtml}</ul>

      <div class="dossier-sec-title">🏅 천재성 입증 (Proof of Genius)</div>
      <div style="color:#fef3c7">${escapeHtml(d.proof_of_genius)}</div>

      <div class="dossier-grid-two">
        <div class="dossier-strength-card">
          <strong style="color:#6ee7b7">✨ 천재성 핵심 강점</strong>
          <div style="margin-top:3px;color:#e2e8f0">${escapeHtml(d.genius_strengths)}</div>
        </div>
        <div class="dossier-limit-card">
          <strong style="color:#fda4af">⚠️ 명확한 한계 · 보완점</strong>
          <div style="margin-top:3px;color:#e2e8f0">${escapeHtml(d.limitations)}</div>
        </div>
      </div>

      <div class="dossier-sec-title">📊 영역별 성좌 배치 적합도 측정</div>
      <div class="fit-bars-wrap">${fitBarsHtml}</div>
    `;

    // Auto-select recommended optimal constellation & populate editable placement fields!
    const best = d.recommended_constellation;
    const selEl = document.getElementById("addTargetConst");
    if (best && selEl && [...selEl.options].some((o) => o.value === best.id)) {
      selEl.value = best.id;
      document.getElementById("addNewConstName").classList.add("hidden");
    }
    document.getElementById("placementLabel").innerHTML =
      `🎯 AI 최적 배치 추천: <strong style="color:#fde68a">${best.icon} ${escapeHtml(best.name)} (${best.fit_pct}%)</strong> — 다른 성좌로 보내고 싶다면 아래에서 자유롭게 변경하세요!`;

    document.getElementById("addGeniusEmoji").value = d.emoji || "🌟";
    document.getElementById("addGeniusName").value = d.name || query;
    document.getElementById("addGeniusLens").value = d.lens || "";
    document.getElementById("addGeniusCredo").value = d.credo || "";
  }
  window.__runScout = runScoutAnalysis;

  document.getElementById("btnScoutGenius").addEventListener("click", () => runScoutAnalysis());
  document.getElementById("scoutQueryInput").addEventListener("keydown", (evt) => {
    if (evt.key === "Enter") {
      evt.preventDefault();
      runScoutAnalysis();
    }
  });
  document.querySelectorAll("#scoutPresetChips .preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#scoutPresetChips .preset-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      runScoutAnalysis(chip.dataset.scout);
    });
  });

  // Unlimited Constellation / Genius Placement & Transfer
  document.getElementById("addTargetConst").addEventListener("change", (evt) => {
    const isNew = evt.target.value === "__new__";
    document.getElementById("addNewConstName").classList.toggle("hidden", !isNew);
  });

  document.getElementById("btnAddGenius").addEventListener("click", async () => {
    const targetId = document.getElementById("addTargetConst").value;
    const newConstName = document.getElementById("addNewConstName").value.trim();
    const emoji = document.getElementById("addGeniusEmoji").value.trim() || "🌟";
    const name = document.getElementById("addGeniusName").value.trim() || document.getElementById("scoutQueryInput").value.trim();
    const lens = document.getElementById("addGeniusLens").value.trim();
    const credo = document.getElementById("addGeniusCredo").value.trim();
    const sfb = document.getElementById("scoutFeedback");
    if (!name) {
      sfb.classList.remove("hidden");
      sfb.textContent = "먼저 위 검색창에서 영입할 천재 이름을 검색하거나 입력해 주세요!";
      return;
    }

    const d = pantheonState.lastScoutDossier && pantheonState.lastScoutDossier.name === name
      ? pantheonState.lastScoutDossier
      : null;

    setPetPose("06_star");
    const res = await apiPost("api/pantheon/add", {
      target_constellation_id: targetId,
      new_constellation_name: newConstName,
      genius_name: name,
      lens,
      credo,
      emoji,
      strengths: d ? d.genius_strengths : "",
      limitations: d ? d.limitations : "",
      proof_of_genius: d ? d.proof_of_genius : "",
      achievements: d ? d.achievements : [],
    });
    if (res.added && res.status) {
      const placedConst = res.added.constellation;
      pantheonState.focusedConstId = placedConst.id;
      if (!pantheonState.selectedConstIds.includes(placedConst.id)) {
        pantheonState.selectedConstIds.push(placedConst.id);
      }
      pulsePortrait();
      renderStatus(res.status);
      sfb.classList.remove("hidden");
      sfb.innerHTML = `
        ✦ <strong>${escapeHtml(name)}</strong> 천재가 <strong>[${placedConst.icon} ${escapeHtml(placedConst.name)}]</strong>에 공식 배치되었습니다! (위키 심사록 자동 저장 완료)<br/>
        • 언제든 오른쪽 성좌 명단의 <strong>[⇄ 다른 성좌로 보내기]</strong> 메뉴로 다른 성좌로 자유롭게 이동시킬 수 있습니다!
      `;
    }
  });

  // Convene Multi-Genius Debate inside & across Selected Domain Constellations!
  document.getElementById("btnDistillGenius").addEventListener("click", async () => {
    const fb = document.getElementById("distillFeedback");
    const topic = document.getElementById("debateTopicInput").value.trim();
    fb.classList.remove("hidden");
    fb.textContent = "선택한 영역 성좌의 천재들이 서로 의견을 주고받으며 성좌 모듈(.sbrain)을 주조하고 있어요...";
    setPetPose("03_swirl");

    const res = await apiPost("api/pantheon/debate", {
      constellation_ids: pantheonState.selectedConstIds,
      topic,
    });
    if (res.debate) {
      const d = res.debate;
      pantheonState.lastDebate = d;
      pulsePortrait();
      renderStatus(res.status);
      loadRlScenario(selectedScenarioId);
      fb.innerHTML = `
        🌌 <strong>성좌 원탁 담론 &amp; 전수 완료!</strong> (신규 모듈 <code>${escapeHtml(d.sbrain_file)}</code> · ${d.sbrain_kb} KB · 누적 성좌 모듈 ${d.total_modular_capsules}개 ∞)<br/>
        • 참여 성좌 (${d.mentors.length}인 천재): <strong>${d.constellations.map(escapeHtml).join(" × ")}</strong><br/>
        • 5인 꼬마 뉴런 심판단 실전 점수: <strong>${d.before_score}점 → ${d.after_score}점</strong> (${d.gain_pts >= 0 ? "+" : ""}${d.gain_pts}점 변화!)<br/>
        • 천재들의 의견 교환록이 마크다운 위키 기억망에도 새 카드로 영구 보존되었습니다!
      `;
    }
  });

  // Preset Chips for User's Own Thought on Constellation Opinions
  document.querySelectorAll("#thoughtPresetChips .preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#thoughtPresetChips .preset-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      document.getElementById("userThoughtInput").value = chip.dataset.thought || "";
      document.getElementById("userThoughtInput").focus();
    });
  });

  async function submitUserThoughtForFeedback() {
    const inputEl = document.getElementById("userThoughtInput");
    const userThought = inputEl.value.trim();
    const fb = document.getElementById("distillFeedback");
    if (!userThought) {
      fb.classList.remove("hidden");
      fb.textContent = "성좌 천재들에게 들려줄 나의 생각이나 질문을 먼저 한 줄 적어주세요!";
      inputEl.focus();
      return;
    }

    const topic = document.getElementById("debateTopicInput").value.trim();
    fb.classList.remove("hidden");
    fb.textContent = "성좌의 천재 스승님들이 주인님의 생각을 읽고 강점과 정밀 보완점을 토론 중이에요...";
    setPetPose("06_star");

    const res = await apiPost("api/pantheon/feedback", {
      constellation_ids: pantheonState.selectedConstIds,
      user_thought: userThought,
      topic,
    });
    if (res.feedback) {
      const f = res.feedback;
      pantheonState.lastDebate = f.updated_debate;
      inputEl.value = "";
      pulsePortrait();
      renderStatus(res.status);
      loadRlScenario(selectedScenarioId);

      const feedEl = document.getElementById("debateFeedBox");
      if (feedEl) {
        feedEl.scrollTop = feedEl.scrollHeight;
      }

      fb.innerHTML = `
        👑 <strong>주인님 생각 피드백 &amp; 공동 진화 완료!</strong> [${escapeHtml(f.analysis.badge)}]<br/>
        • 성좌가 주인님의 강점을 반영해 공동 모듈 <code>${escapeHtml(f.sbrain_file)}</code> (${f.sbrain_kb} KB)을 새로 주조했습니다! (총 모듈 ${f.total_modular_capsules}개 ∞)<br/>
        • 바로 위 담론창 맨 아래에서 <strong>천재들의 3단 입체 피드백(강점 공명 · 정밀 보완 · 다음 질문)</strong>을 확인해 보세요!
      `;
    }
  }

  document.getElementById("btnAskFeedback").addEventListener("click", submitUserThoughtForFeedback);
  document.getElementById("userThoughtInput").addEventListener("keydown", (evt) => {
    if (evt.key === "Enter" && !evt.shiftKey) {
      evt.preventDefault();
      submitUserThoughtForFeedback();
    }
  });
}

// =========================================================================
// Stage C (v5.0): 6-Stage Self-Evolving Synapse Forge Client Controller
// =========================================================================
let activeEvoSpecimenId = "xor_rot_vault";
let activeEvoEntryFn = "transform_payload";

function setEvoStepper(doneUpTo, activeStep) {
  document.querySelectorAll("#evoStepperBar .evo-step").forEach((el) => {
    const s = parseInt(el.dataset.step, 10);
    el.classList.toggle("done", s <= doneUpTo && s !== activeStep);
    el.classList.toggle("active", s === activeStep);
  });
}

function renderEvoInstalledDock(evoSnap) {
  const listEl = document.getElementById("evoInstalledList");
  const selEl = document.getElementById("evoRunSkillSelect");
  const badgeEl = document.getElementById("evoGhidraBadge");
  if (!listEl || !selEl) return;

  if (badgeEl && evoSnap.ghidra_bridge) {
    badgeEl.textContent = evoSnap.ghidra_bridge.headless_ready
      ? "🟢 Ghidra 12.3 직결 가동"
      : "⚡ X-Ray + Ghidra 12.3 스크립트 연동";
  }

  const skills = evoSnap.installed_skills || [];
  if (!skills.length) {
    listEl.innerHTML = `<div style="font-size:11.5px;color:#94a3b8">아직 장착된 스킬이 없습니다. 위에서 5단계 유리방 100% 통과 후 <strong>[🧩 6단계 영구 장착]</strong>을 눌러보세요!</div>`;
    selEl.innerHTML = `<option value="">장착 스킬 없음</option>`;
    return;
  }

  listEl.innerHTML = skills
    .map(
      (s) => `
      <div class="vb-item" style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <div>
          <strong style="color:#6ee7b7">🧩 ${escapeHtml(s.entry_fn)}()</strong>
          <span style="font-size:11px;color:#cbd5e1"> — ${escapeHtml(s.title)}</span><br/>
          <span style="font-size:10.5px;color:#94a3b8"><code>${escapeHtml(s.py_file)}</code> · 캡슐 <code>${escapeHtml(s.sbrain_file)}</code> (${s.sbrain_kb} KB) · 검증 ${escapeHtml(s.tests_passed)}</span>
        </div>
        <span class="tag-pill" style="border-color:rgba(52,211,153,0.5);color:#6ee7b7">장착됨</span>
      </div>
    `
    )
    .join("");

  const prevVal = selEl.value;
  selEl.innerHTML = skills
    .map(
      (s) =>
        `<option value="${escapeHtml(s.skill_id)}" data-sample='${escapeHtml(JSON.stringify(s.sample_args || []))}'>${escapeHtml(s.entry_fn)}()</option>`
    )
    .join("");
  if (prevVal && [...selEl.options].some((o) => o.value === prevVal)) {
    selEl.value = prevVal;
  }
}

function renderEvoSnapshots(snaps) {
  const sel = document.getElementById("evoSnapshotSelect");
  if (!sel || !Array.isArray(snaps)) return;
  sel.innerHTML = snaps
    .slice()
    .reverse()
    .map((s) => `<option value="${escapeHtml(s.snap_id)}">${escapeHtml(s.label)} (${escapeHtml(s.created_at || "")})</option>`)
    .join("");
}

function renderEvoXrayAndBlueprint(bundle) {
  const sp = bundle.specimen;
  const xr = bundle.stage1_xray;
  const bp = bundle.stage2_blueprint;
  activeEvoSpecimenId = sp.id;
  activeEvoEntryFn = sp.entry_fn;

  const secHtml = (xr.sections || [])
    .map((s) => {
      const pct = Math.min(100, Math.round((s.entropy / 8.0) * 100));
      const color = s.entropy >= 7.0 ? "#f43f5e" : s.entropy >= 4.5 ? "#f59e0b" : "#38bdf8";
      return `
        <div class="xray-sec-row">
          <code>${escapeHtml(s.name)} (${escapeHtml(s.rwx)})</code>
          <span style="color:#94a3b8">${escapeHtml(s.addr)}</span>
          <div class="ent-track"><div class="ent-fill" style="width:${pct}%;background:${color}"></div></div>
          <strong style="color:${color};text-align:right">${s.entropy}b</strong>
        </div>
      `;
    })
    .join("");

  const strs = (xr.strings || [])
    .slice(0, 5)
    .map((st) => `<code>${escapeHtml(st.offset)}: "${escapeHtml(st.value)}"</code>`)
    .join(" ");

  const clues = (xr.opcode_clues || [])
    .map((c) => `<span class="tag-pill" style="font-size:10.5px">${escapeHtml(c)}</span>`)
    .join(" ");

  document.getElementById("evoXrayBox").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px">
      <strong style="color:#38bdf8;font-size:12.8px">🔬 1단계 해부 결과: ${escapeHtml(sp.title)}</strong>
      <span class="tag-pill">${escapeHtml(sp.badge)}</span>
    </div>
    <div class="xray-meta-grid">
      <div class="xray-kv">포맷: <strong>${escapeHtml(xr.format)}</strong></div>
      <div class="xray-kv">아키텍처: <strong>${escapeHtml(xr.arch)}</strong></div>
      <div class="xray-kv">진입점: <code>${escapeHtml(xr.entry_point)}</code> (${xr.size_bytes} B)</div>
      <div class="xray-kv">전체 엔트로피: <strong>${xr.overall_entropy} / 8.0 bits</strong></div>
    </div>
    <div style="font-size:11px;color:#cbd5e1;margin-bottom:3px">📊 섹션별 섀넌 엔트로피 레이더 (7.0b 이상은 암호화·압축 의심)</div>
    ${secHtml}
    <div style="margin-top:7px;display:flex;flex-wrap:wrap;gap:4px">${clues}</div>
    <div style="margin-top:6px;font-size:11px;color:#94a3b8">추출 문자열: ${strs || "없음"}</div>
  `;

  const asmHtml = (sp.pseudo_asm || []).map((l) => escapeHtml(l)).join("\n");
  const invHtml = (bp.invariants || []).map((i) => `<li>${escapeHtml(i)}</li>`).join("");
  document.getElementById("evoBlueprintBox").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
      <strong style="color:#fde68a;font-size:12.8px">🧬 2단계 [기관①] 기계어 → 핵심 원리 설계도 번역</strong>
      <span style="font-size:10.8px;color:#c7d2fe">감수: ${escapeHtml((sp.mentors || []).join(" · "))}</span>
    </div>
    <pre class="asm-block">${asmHtml}</pre>
    <div style="margin-top:5px"><strong style="color:#6ee7b7">✦ 추출 핵심 공식:</strong> <code>${escapeHtml(bp.core_formula)}</code></div>
    <div style="margin-top:4px;font-size:11.3px;color:#cbd5e1"><strong>입출력 규격:</strong> ${escapeHtml(bp.inputs)} → ${escapeHtml(bp.outputs)}</div>
    <ul style="margin:5px 0 6px;padding-left:17px;font-size:11.3px;color:#e2e8f0">${invHtml}</ul>
    <div style="padding:6px 9px;border-radius:8px;background:rgba(99,102,241,0.16);font-size:11.2px;color:#e0e7ff">
      💡 ${escapeHtml(bp.mentor_comment)}
    </div>
  `;

  document.getElementById("evoEditorTitle").textContent =
    `💻 3단계 · 우리 두뇌 이식 코드 (${sp.entry_fn}) — 자유롭게 직접 수정 가능!`;
  document.getElementById("evoCodeEditor").value = bundle.stage3_draft_code || "";
  renderEvoSnapshots(bundle.snapshots || []);
  document.getElementById("evoDiffBox").classList.add("hidden");
  document.getElementById("evoInstallFeedback").classList.add("hidden");
  document.getElementById("evoAuditBox").innerHTML =
    `1차 자동 이식 코드가 준비되었습니다! <strong>[🔍 4단계: 잘못된 곳 · 복어독 찾기]</strong> 또는 상단 <strong>[⚡ 1~5단계 연속 실행]</strong>을 눌러 숨은 함정을 색출해 보세요.`;
  document.getElementById("evoSandboxBox").innerHTML =
    `🧪 <strong>기관② 투명 유리방 실험실 대기 중</strong> — 원본 바이너리와 대조할 쌍둥이 테스트 <strong>${(bundle.twin_tests || []).length}건</strong>이 장전되었습니다.`;
  setEvoStepper(2, 3);
}

function renderEvoAudit(diag) {
  const box = document.getElementById("evoAuditBox");
  if (diag.clean) {
    box.innerHTML = `<strong style="color:#6ee7b7">✅ [기관③ 돋보기 &amp; 기관⑤ 복어독 스캐너] 결함 0건 · 위험 명령 0건 깨끗합니다!</strong>`;
    return;
  }
  const cards = (diag.findings || [])
    .map(
      (f) => `
      <div class="finding-card ${f.severity === "toxin" ? "toxin" : ""}">
        <div style="display:flex;justify-content:space-between;gap:6px">
          <strong style="color:${f.severity === "toxin" ? "#fde68a" : "#fda4af"}">${escapeHtml(f.badge)} — 줄 번호 Line ${f.line}</strong>
          <code>${escapeHtml(f.code_line)}</code>
        </div>
        <div style="margin-top:3px;color:#f1f5f9">• <strong>원인 역추적:</strong> ${escapeHtml(f.root_cause)}</div>
        <div style="margin-top:2px;color:#a5b4fc;font-size:11px">• <strong>수리 힌트:</strong> ${escapeHtml(f.fix_hint)}</div>
      </div>
    `
    )
    .join("");

  box.innerHTML = `
    <strong style="color:#fda4af">🔍 4단계 [기관③ 원인 역추적 돋보기 &amp; 기관⑤ 복어독 제거기] 총 ${(diag.findings || []).length}건 적발!</strong>
    ${cards}
  `;
}

function renderEvoSandbox(sb, labelPrefix = "5단계") {
  const box = document.getElementById("evoSandboxBox");
  if (!sb) return;
  if (sb.blocked_by_toxin) {
    box.innerHTML = `
      <strong style="color:#fbbf24">🚦 [기관⑤ 복어 독 제거기 작동!] 위험 시스템 명령(${sb.toxins.length}건)이 포함되어 유리방 실행을 사전 격리 차단했습니다!</strong><br/>
      <span style="font-size:11.3px;color:#fde68a"><strong>[🩹 5단계: 자동 수리]</strong>를 누르면 위험 명령을 깨끗이 발라내고 순수 알고리즘만 실행합니다.</span>
    `;
    return;
  }
  if (sb.syntax_error) {
    box.innerHTML = `<strong style="color:#fda4af">🚨 실행 중단 (Line ${sb.syntax_error.line}): ${escapeHtml(sb.syntax_error.msg)}</strong>`;
    return;
  }

  const allPass = sb.pass_rate_pct === 100;
  const casesHtml = (sb.results || [])
    .map(
      (r) => `
      <div class="twin-case ${r.passed ? "pass" : "fail"}">
        <div style="display:flex;justify-content:space-between">
          <strong>${r.passed ? "✅" : "❌"} ${escapeHtml(r.name)}</strong>
          <span style="color:#94a3b8">입력: <code>${escapeHtml(JSON.stringify(r.args))}</code></span>
        </div>
        <div style="margin-top:2px;color:${r.passed ? "#6ee7b7" : "#fda4af"}">
          원본 정답: <code>${escapeHtml(JSON.stringify(r.expected))}</code> ↔ 실행 결과: <code>${escapeHtml(r.error ? r.error : JSON.stringify(r.actual))}</code>
        </div>
      </div>
    `
    )
    .join("");

  box.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
      <strong style="color:${allPass ? "#6ee7b7" : "#fda4af"};font-size:12.8px">
        🧪 ${escapeHtml(labelPrefix)} [기관② 투명 유리방 쌍둥이 대조 결과]: ${sb.passed_count}/${sb.total_count} 통과 (${sb.pass_rate_pct}%)
      </strong>
      <span style="font-size:11px;color:#94a3b8">격리 프로세스 실측 ${sb.elapsed_ms} ms</span>
    </div>
    <div class="twin-case-grid">${casesHtml}</div>
  `;
}

function renderEvoDiff(diffRows) {
  const diffEl = document.getElementById("evoDiffBox");
  if (!diffRows || !diffRows.length) {
    diffEl.classList.add("hidden");
    return;
  }
  diffEl.classList.remove("hidden");
  diffEl.innerHTML =
    `<div style="font-size:11px;color:#fde68a;margin-bottom:4px;font-family:sans-serif"><strong>⏪ [기관④ 타임머신 비교] 수리 전(빨간 줄) ↔ 수리 후(초록 줄) 변경 내역</strong></div>` +
    diffRows
      .map((r) => `<div class="diff-line ${escapeHtml(r.kind)}">${escapeHtml(r.text)}</div>`)
      .join("");
}

function setupEvoForgeInteractions() {
  async function loadSpecimen(specId, uploadedFile = null, silent = false) {
    if (!silent) setPetPose("02_curious");
    let payload = { specimen_id: specId || "xor_rot_vault" };
    if (uploadedFile) {
      const buf = await uploadedFile.arrayBuffer();
      const bytes = new Uint8Array(buf.slice(0, 65536));
      let binary = "";
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      payload = {
        specimen_id: "custom_upload",
        uploaded_name: uploadedFile.name,
        uploaded_b64: btoa(binary),
      };
    }
    const res = await apiPost("api/evo/dissect", payload);
    if (res.bundle) {
      renderEvoXrayAndBlueprint(res.bundle);
      if (res.status) renderStatus(res.status);
    }
  }
  window.__loadEvoSpecimen = loadSpecimen;

  document.querySelectorAll("#evoSpecimenChips [data-spec]").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#evoSpecimenChips .preset-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      loadSpecimen(chip.dataset.spec);
    });
  });

  document.getElementById("btnEvoUpload").addEventListener("click", () => {
    document.getElementById("evoFileInput").click();
  });
  document.getElementById("evoFileInput").addEventListener("change", (evt) => {
    const file = evt.target.files && evt.target.files[0];
    if (file) {
      document.querySelectorAll("#evoSpecimenChips .preset-chip").forEach((c) => c.classList.remove("active"));
      document.getElementById("btnEvoUpload").classList.add("active");
      loadSpecimen("custom_upload", file);
    }
  });

  async function doAudit() {
    const code = document.getElementById("evoCodeEditor").value;
    setPetPose("04_brainstorm");
    const res = await apiPost("api/evo/audit", { specimen_id: activeEvoSpecimenId, code });
    if (res.audit && res.audit.diagnosis) {
      renderEvoAudit(res.audit.diagnosis);
      if (res.audit.diagnosis.sandbox) {
        renderEvoSandbox(res.audit.diagnosis.sandbox, "4단계 사전 대조");
      } else if (res.audit.diagnosis.findings.some((f) => f.severity === "toxin")) {
        renderEvoSandbox({ blocked_by_toxin: true, toxins: res.audit.diagnosis.findings }, "4단계");
      }
      setEvoStepper(3, 4);
    }
  }

  async function doRepair(mode) {
    const curCode = document.getElementById("evoCodeEditor").value;
    setPetPose("03_swirl");
    const res = await apiPost("api/evo/repair", {
      specimen_id: activeEvoSpecimenId,
      current_code: curCode,
      mode,
      edited_code: mode === "manual" ? curCode : "",
    });
    if (res.repaired) {
      const rp = res.repaired;
      document.getElementById("evoCodeEditor").value = rp.after_code;
      renderEvoSnapshots(rp.snapshots || []);
      renderEvoAudit(rp.after_diagnosis);
      renderEvoDiff(rp.diff);
      renderEvoSandbox(rp.after_sandbox, "5단계 수리 후");
      if (res.status) renderStatus(res.status);
      if (rp.after_sandbox.pass_rate_pct === 100) {
        setPetPose("07_eureka");
        setEvoStepper(5, 6);
      } else {
        setEvoStepper(4, 5);
      }
    }
  }

  document.getElementById("btnEvoAudit").addEventListener("click", doAudit);
  document.getElementById("btnEvoAutoRepair").addEventListener("click", () => doRepair("auto"));
  document.getElementById("btnEvoTestCustom").addEventListener("click", () => doRepair("manual"));


  /* ---- 📎🧩🔍 Workbench Trio: upload window, port-apply button, trace chat ---- */
  function traceBubble(who, text) {
    const log = document.getElementById("traceChatLog");
    if (!log) return;
    const name = who === "master" ? "👑 주인님" : "🔍 돋보기 기관";
    const div = document.createElement("div");
    div.className = `chat-bubble ${who === "master" ? "master" : "brain"}`;
    div.innerHTML = `<strong>${name}</strong> ${escapeHeartHtml(text)}`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  const benchUpBtn = document.getElementById("btnBenchUpload");
  const benchFile = document.getElementById("benchFileInput");
  if (benchUpBtn && benchFile) {
    benchUpBtn.addEventListener("click", () => benchFile.click());
    benchFile.addEventListener("change", (evt) => {
      const file = evt.target.files && evt.target.files[0];
      if (!file) return;
      const nameEl = document.getElementById("benchUploadName");
      if (nameEl) nameEl.textContent = `📎 ${file.name}`;
      if (/\.(py|txt|md)$/i.test(file.name)) {
        file.text().then((txt) => {
          document.getElementById("evoCodeEditor").value = txt;
          traceBubble("brain", `📎 코드 파일 "${file.name}" 을(를) 3단계 편집창에 착륙시켰어요! 바로 4단계 돋보기를 가동할게요!`);
          doAudit();
        });
      } else {
        traceBubble("brain", `📎 바이너리 "${file.name}" 첨부! 1단계 X-Ray 해부 → 원리 설계도 번역 → 이식 초안까지 한번에 달릴게요!`);
        document.querySelectorAll("#evoSpecimenChips .preset-chip").forEach((c) => c.classList.remove("active"));
        loadSpecimen("custom_upload", file);
      }
    });
  }

  const portBtn = document.getElementById("btnBenchPort");
  if (portBtn) {
    portBtn.addEventListener("click", async () => {
      const code = document.getElementById("evoCodeEditor").value;
      portBtn.disabled = true;
      const old = portBtn.textContent;
      portBtn.textContent = "🧪 유리방 검증 중...";
      try {
        const res = await apiPost("api/evo/install", { specimen_id: activeEvoSpecimenId, code });
        if (res.error) {
          traceBubble("brain", `🚫 이식 보류: ${res.error} — 4단계 돋보기와 5단계 수리를 먼저 거쳐주세요!`);
          showEvoToast({ kind: "stumble", beat: "🚫", diary: `이식 보류: ${res.error}` });
        } else if (res.installed) {
          traceBubble("brain", `🧩 이식 적용 완료! "${res.installed.title}" 이(가) ${res.installed.py_file} + ${res.installed.sbrain_file} + 위키 기억 2장으로 우리 뇌에 영구 합체됐어요! (${res.installed.tests_passed} 통과)`);
          showEvoToast({ kind: "evolve", beat: "🧩", diary: `우리 뇌 이식 적용 완료! ${res.installed.entry_fn} 카트리지 장착 (${res.installed.tests_passed})` });
          if (res.status) renderStatus(res.status);
          setPetPose("07_eureka");
          setEvoStepper(6, 6);
        }
      } catch (err) {
        traceBubble("brain", `🚫 이식 중 오류: ${err}`);
      }
      portBtn.disabled = false;
      portBtn.textContent = old;
    });
  }

  async function sendTraceChat() {
    const input = document.getElementById("traceChatInput");
    const btn = document.getElementById("btnTraceChat");
    if (!input || !btn) return;
    const msg = input.value.trim();
    if (!msg) return;
    traceBubble("master", msg);
    input.value = "";
    btn.disabled = true;
    try {
      const res = await apiPost("api/evo/trace-chat", {
        message: msg,
        specimen_id: activeEvoSpecimenId,
        code: document.getElementById("evoCodeEditor").value,
      });
      traceBubble("brain", res.reply || "...");
      setPetPose("02_curious");
    } catch (err) {
      traceBubble("brain", `🚫 역추적 중 오류: ${err}`);
    }
    btn.disabled = false;
    input.focus();
  }
  const traceBtn = document.getElementById("btnTraceChat");
  const traceInput = document.getElementById("traceChatInput");
  if (traceBtn) traceBtn.addEventListener("click", sendTraceChat);
  if (traceInput) {
    traceInput.addEventListener("keydown", (evt) => {
      if (evt.key === "Enter") {
        evt.preventDefault();
        sendTraceChat();
      }
    });
  }
  traceBubble("brain", "안녕하세요! 저는 기관③ 원인 역추적 돋보기예요. 현재 편집창 코드에 대해 '왜 깨졌어?' 라고 한번 물어봐 주세요! 🔍");

  document.getElementById("btnEvoRollback").addEventListener("click", async () => {
    const snapId = document.getElementById("evoSnapshotSelect").value;
    const res = await apiPost("api/evo/rollback", { specimen_id: activeEvoSpecimenId, snap_id: snapId });
    if (res.rollback && res.rollback.restored_snapshot) {
      document.getElementById("evoCodeEditor").value = res.rollback.restored_snapshot.code;
      document.getElementById("evoDiffBox").classList.add("hidden");
      renderEvoAudit(res.rollback.diagnosis);
      if (res.rollback.diagnosis.sandbox) {
        renderEvoSandbox(res.rollback.diagnosis.sandbox, "타임머신 복구 상태");
      }
      setEvoStepper(3, 4);
    }
  });

  document.getElementById("btnEvoInstall").addEventListener("click", async () => {
    const code = document.getElementById("evoCodeEditor").value;
    const fb = document.getElementById("evoInstallFeedback");
    fb.classList.remove("hidden");
    fb.textContent = "유리방 100% 합격 확인 중... 스킬 카트리지(.py + .sbrain + 위키 도감)를 주조합니다!";
    const res = await apiPost("api/evo/install", { specimen_id: activeEvoSpecimenId, code });
    if (res.error) {
      fb.innerHTML = `⚠️ <strong>장착 보류:</strong> ${escapeHtml(res.error)} 먼저 <strong>[🩹 5단계: 자동 수리 &amp; 유리방 시험]</strong>을 통과시켜 주세요!`;
      return;
    }
    if (res.installed) {
      const inst = res.installed;
      pulsePortrait();
      renderStatus(res.status);
      setEvoStepper(6, 6);
      document.getElementById("evoRunArgsInput").value = JSON.stringify(inst.sample_args || []);
      fb.innerHTML = `
        🎉 <strong>6단계 두뇌 영구 접목 완료!</strong><br/>
        • 실행 모듈: <code>${escapeHtml(inst.py_file)}</code> · 4비트 신경 캡슐: <code>models/${escapeHtml(inst.sbrain_file)}</code> (${inst.sbrain_kb} KB)<br/>
        • 마크다운 기억 성좌 연결: <code>[[${escapeHtml(inst.ghidra_note_title)}]]</code> ⇄ <code>[[${escapeHtml(inst.skill_note_title)}]]</code>
      `;
    }
  });

  document.getElementById("evoRunSkillSelect").addEventListener("change", (evt) => {
    const opt = evt.target.selectedOptions[0];
    if (opt && opt.dataset.sample) {
      document.getElementById("evoRunArgsInput").value = opt.dataset.sample;
    }
  });

  document.getElementById("btnEvoRunSkill").addEventListener("click", async () => {
    const skillId = document.getElementById("evoRunSkillSelect").value;
    const outEl = document.getElementById("evoRunSkillOutput");
    if (!skillId) return;
    let parsedArgs = [];
    try {
      parsedArgs = JSON.parse(document.getElementById("evoRunArgsInput").value);
    } catch (_) {
      outEl.classList.remove("hidden");
      outEl.textContent = "⚠️ 인자를 올바른 JSON 배열 형식(예: [[16, 32, 255, 129]])으로 입력해 주세요!";
      return;
    }
    const res = await apiPost("api/evo/run-skill", { skill_id: skillId, args: parsedArgs });
    outEl.classList.remove("hidden");
    if (res.ran) {
      outEl.innerHTML = `▶ <strong>실전 스킬 출력 (${res.ran.elapsed_ms}ms):</strong> <code>${escapeHtml(entryCallLabel(res.ran))}</code> → <strong style="color:#fde68a"><code>${escapeHtml(JSON.stringify(res.ran.output))}</code></strong>`;
    } else if (res.error) {
      outEl.textContent = `⚠️ ${res.error}`;
    }
  });

  function entryCallLabel(ran) {
    const inner = (ran.args || []).map((a) => JSON.stringify(a)).join(", ");
    return `${ran.entry_fn}(${inner})`;
  }

  document.getElementById("btnEvoOneClickCycle").addEventListener("click", async () => {
    await doAudit();
    await new Promise((r) => setTimeout(r, 420));
    await doRepair("auto");
  });
}


/* ===========================================================================
   Stage D — Self-Evolving Heartbeat 💓 controller & Evolution Journal feed
=========================================================================== */
let HEART_PREV_BEATS = null;
let HEART_TOAST_TIMER = null;

function escapeHeartHtml(txt) {
  return String(txt == null ? "" : txt)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderHeartJournal(hb) {
  const list = document.getElementById("evoJournalList");
  if (!list) return;
  const entries = hb.journal || [];
  if (!entries.length) {
    list.innerHTML = '<div class="journal-empty">아직 일지가 비어 있어요. [⚡ 지금 바로 한 박동!] 을 누르거나 잠시 기다리면, 두뇌가 혼자 꿈꾸며 배운 이야기가 여기에 쌓입니다! 💤</div>';
    return;
  }
  list.innerHTML = entries.map((e) => {
    const kind = e.kind === "field" ? "kind-field" : e.kind === "vaccine" ? "kind-vaccine" : e.kind === "stumble" ? "kind-stumble" : e.kind === "train" ? "kind-train" : e.kind === "breakthrough" ? "kind-breakthrough" : e.kind === "research" ? "kind-research" : "kind-evolve";
    const kindLabel = e.kind === "vaccine" ? "🛡️ 예방접종" : e.kind === "stumble" ? "💤 깜빡" : e.kind === "train" ? "🏋️ 자율훈련" : e.kind === "breakthrough" ? "🚀 한계돌파" : e.kind === "research" ? "🔭 열린연구" : "🌱 진화";
    const chips = e.kind === "breakthrough"
      ? [
          `<span class="je-chip">${kindLabel}</span>`,
          `<span class="je-chip">🚧 벽 ${escapeHeartHtml(e.wall)}</span>`,
          `<span class="je-chip">🧪 검증 ${escapeHeartHtml(e.confirm)}</span>`,
          `<span class="je-chip">${e.success ? "✅ 가설 채택" : "❌ 가설 기각"}</span>`,
          `<span class="je-chip">📐 상한 Lv ${escapeHeartHtml(e.cap_before)} → ${escapeHeartHtml(e.cap_after)}</span>`,
        ].join("")
      : e.kind === "research"
      ? [
          `<span class="je-chip">${kindLabel}</span>`,
          `<span class="je-chip">🏁 최종 한계 Lv ${escapeHeartHtml(e.cap)}</span>`,
          `<span class="je-chip">📔 위키 연구 노트 심음</span>`,
        ].join("")
      : e.kind === "train"
      ? [
          `<span class="je-chip">${kindLabel}</span>`,
          `<span class="je-chip">🎯 난이도 ${escapeHeartHtml(e.difficulty)}</span>`,
          `<span class="je-chip">✅ ${escapeHeartHtml(e.correct)}/${escapeHeartHtml(e.rounds)}</span>`,
          `<span class="je-chip">📝 숨은시험 ${escapeHeartHtml(e.exam)}</span>`,
          `<span class="je-chip">📈 Lv ${escapeHeartHtml(e.level_before)} → ${escapeHeartHtml(e.level_after)}</span>`,
        ].join("")
      : [
          `<span class="je-chip">${kindLabel}</span>`,
          `<span class="je-chip">🔍 결함 ${escapeHeartHtml(e.defects_found)}건</span>`,
          e.toxins_found ? `<span class="je-chip">🐡 독 ${escapeHeartHtml(e.toxins_found)}건</span>` : "",
          `<span class="je-chip">🧪 ${escapeHeartHtml(e.pass_before)}% → ${escapeHeartHtml(e.pass_after)}%</span>`,
          `<span class="je-chip">⏱ ${escapeHeartHtml(e.ms)}ms</span>`,
        ].join("");
    return (
      `<div class="journal-entry ${kind}">` +
      `<div class="je-head"><span class="je-beat">박동 #${escapeHeartHtml(e.beat)}</span>` +
      `<span class="je-title">${escapeHeartHtml(e.title)}</span>` +
      `<span class="je-time">${escapeHeartHtml(e.ts)}</span></div>` +
      `<p class="je-diary">${escapeHeartHtml(e.diary)}</p>` +
      `<div class="je-chips">${chips}</div></div>`
    );
  }).join("");
}

function renderHeartbeat(hb) {
  const lamp = document.getElementById("heartLamp");
  const line = document.getElementById("heartStatusLine");
  const toggle = document.getElementById("btnHeartToggle");
  if (!lamp || !line || !toggle) return;
  lamp.classList.toggle("paused", !!hb.paused);
  toggle.textContent = hb.paused ? "▶️ 꿈에서 깨우기" : "😴 잠시 재우기";
  if (hb.paused) {
    line.textContent = "😴 심장이 잠시 낮잠 자는 중이에요. [▶️ 꿈에서 깨우기] 를 누르면 다시 혼자 꿈꾸며 진화합니다!";
  } else if (hb.running) {
    line.textContent =
      `💓 ${hb.beats_total}번째 박동까지 완료! 다음 박동까지 ${hb.next_beat_in_sec}초 · ` +
      `꿈 스킬 ${hb.dream_installed}/${hb.pool_size} 장착 · ${hb.interval_sec}초마다 혼자 공부해요`;
  } else {
    line.textContent = "💌 심장박동 신호를 연결하는 중...";
  }
  renderHeartJournal(hb);
}

function showEvoToast(entry) {
  const toast = document.getElementById("evoToast");
  if (!toast || !entry) return;
  const head = entry.kind === "vaccine" ? "🛡️ 예방접종 훈련 완료!" : entry.kind === "stumble" ? "💤 으앙... 살짝 넘어졌어요" : `💓 ${entry.beat}번째 박동! 새 진화 완료!`;
  toast.innerHTML = `<strong>${escapeHeartHtml(head)}</strong><br>${escapeHeartHtml(entry.diary)}`;
  toast.classList.remove("hidden");
  if (HEART_TOAST_TIMER) clearTimeout(HEART_TOAST_TIMER);
  HEART_TOAST_TIMER = setTimeout(() => toast.classList.add("hidden"), 7000);
}

async function pollHeartbeat() {
  try {
    const res = await fetch("/api/evo/heartbeat");
    if (!res.ok) return;
    const hb = await res.json();
    renderHeartbeat(hb);
    try {
      const ares = await fetch("/api/evo/abilities");
      if (ares.ok) renderGym(await ares.json());
    } catch (errA) { /* ignore */ }
    if ((hb.chats || []).length !== HEART_CHAT_COUNT) {
      renderHeartChat(hb);
      HEART_CHAT_COUNT = (hb.chats || []).length;
    }
    if (HEART_PREV_BEATS !== null && hb.beats_total > HEART_PREV_BEATS && hb.last_entry) {
      showEvoToast(hb.last_entry);
    }
    HEART_PREV_BEATS = hb.beats_total;
  } catch (err) {
    /* heartbeat API unreachable: keep silent */
  }
}



/* ===========================================================================
   Stage E — Core Ability Growth Gym 🏋️ controller (radar + cards + training)
=========================================================================== */
function renderGym(snap) {
  const svg = document.getElementById("gymRadar");
  const cards = document.getElementById("gymCards");
  const line = document.getElementById("gymStatusLine");
  if (!svg || !cards) return;
  const abs = snap.abilities || [];
  const caps = snap.caps || {};
  const cx = 110, cy = 110, R = 78;
  const angles = [-90, 0, 90, 180].map((d) => (d * Math.PI) / 180);
  const pt = (i, ratio) => {
    const r = R * Math.max(0.06, Math.min(1, ratio));
    return [cx + r * Math.cos(angles[i]), cy + r * Math.sin(angles[i])];
  };
  let grid = "";
  [0.25, 0.5, 0.75, 1.0].forEach((ring) => {
    const poly = angles.map((_, i) => pt(i, ring).map((v) => v.toFixed(1)).join(",")).join(" ");
    grid += `<polygon points="${poly}" fill="none" stroke="rgba(148,163,184,0.28)" stroke-width="1"/>`;
  });
  grid += angles.map((_, i) => {
    const [x, y] = pt(i, 1);
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="rgba(148,163,184,0.28)" stroke-width="1"/>`;
  }).join("");
  const values = abs.map((a) => a.level / Math.max(1, a.cap || caps[a.id] || 12));
  const poly = values.map((v, i) => pt(i, v).map((n) => n.toFixed(1)).join(",")).join(" ");
  const labels = abs.map((a, i) => {
    const [x, y] = pt(i, 1.24);
    return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="middle" font-size="10.5" fill="#a7f3d0">${escapeHeartHtml(a.title.split(" ")[0])} Lv${a.level}</text>`;
  }).join("");
  svg.innerHTML =
    grid +
    `<polygon points="${poly}" fill="rgba(52,211,153,0.28)" stroke="#34d399" stroke-width="2"/>` +
    values.map((v, i) => {
      const [x, y] = pt(i, v);
      return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.4" fill="#6ee7b7"/>`;
    }).join("") +
    labels;

  cards.innerHTML = abs.map((a) => {
    const cap = a.cap || caps[a.id] || 12;
    const pct = Math.round((a.level / cap) * 100);
    const ls = a.last_session;
    const last = ls
      ? `마지막: ${ls.difficulty}난이도 ${ls.correct}/${ls.rounds} · 숨은시험 ${ls.exam} · Lv ${ls.level_before}→${ls.level_after}`
      : "아직 훈련 기록이 없어요. [🏋️ 훈련] 으로 첫 땀을 흘려보세요!";
    const btnLabel = a.at_cap ? (a.max_tier ? "🔭 열린 연구 노트" : "🚀 한계 돌파 시도!") : "🏋️ 훈련";
    const btnCls = a.at_cap ? "ghost-btn gc-train gc-break-btn" : "ghost-btn gc-train";
    const mode = a.at_cap ? "break" : "train";
    return (
      `<div class="gym-card"><div class="gc-head"><span class="gc-title">${escapeHeartHtml(a.title)}</span>` +
      `<span class="gc-level">Lv ${a.level} / ${cap} · T${a.tier + 1}/${a.tier_count}</span></div>` +
      `<div class="gc-bar"><div class="gc-fill" style="width:${pct}%"></div></div>` +
      `<div class="gc-desc">${escapeHeartHtml(a.desc)}</div>` +
      `<div class="gc-last">${escapeHeartHtml(last)} · XP ${a.xp} · 🚀 돌파 ${a.breakthroughs}회</div>` +
      (a.at_cap && !a.max_tier ? `<div class="gc-last" style="color:#fde68a">💭 다음 가설: ${escapeHeartHtml(a.next_idea)}</div>` : "") +
      `<button class="${btnCls}" type="button" data-ability="${escapeHeartHtml(a.id)}" data-mode="${mode}">${btnLabel}</button></div>`
    );
  }).join("");

  if (line) {
    const sorted = [...abs].sort((x, y) => x.level - y.level);
    const totalXp = abs.reduce((acc, a) => acc + a.xp, 0);
    const bts = abs.reduce((acc, a) => acc + (a.breakthroughs || 0), 0);
    const atCap = abs.filter((a) => a.at_cap);
    line.textContent =
      `💪 합산 XP ${totalXp} · 🚀 한계돌파 ${bts}회 · 최강 ${sorted[sorted.length - 1].title}(Lv ${sorted[sorted.length - 1].level}/${sorted[sorted.length - 1].cap}) · ` +
      (atCap.length
        ? `한계 도달 ${atCap.map((a) => a.title).join(", ")} — 끝이 아니라 돌파 연구 시작!`
        : `가장 애쓰는 근육 ${sorted[0].title}(Lv ${sorted[0].level}/${sorted[0].cap}) — 심장박동이 알아서 훈련해요!`);
  }
  if (snap.field) renderField(snap.field);
}

/* ---- ⚔️ Stage H: Field Deployment Report — muscles doing REAL work ---- */
function renderField(field) {
  const line = document.getElementById("fieldStatusLine");
  const mus = document.getElementById("fieldMuscles");
  const led = document.getElementById("fieldLedger");
  if (!mus || !led) return;
  const total = field.total_deployments || 0;
  const per = field.per_muscle || [];
  const hits = per.reduce((acc, m) => acc + (m.deployments || 0), 0);
  if (line) {
    line.textContent = total > 0
      ? `⚔️ 근육들이 실전에서 총 ${total}번 일했어요! (🧠 담론 · 📖 기억 호출 · 💻 원인 감사 · 🗂️ 시냅스 엮기) — 체육관 점수가 아니라 진짜 결과로 남았습니다.`
      : "⚔️ 아직 실전 출동 전이에요 — [지금 당장 실전 투입!] 을 누르거나, 채팅·담론·4단계 감사·시냅스 엮기를 쓰기만 해도 근육이 저절로 투입돼요!";
  }
  mus.innerHTML = per.map((m) => `
    <div class="field-muscle" data-ability="${escapeHeartHtml(m.id)}">
      <div class="fm-top">
        <span class="fm-title">${escapeHeartHtml(m.title)}</span>
        <span class="fm-lv">Lv ${m.level}/${m.cap} · 티어 ${m.tier + 1}</span>
      </div>
      <div class="fm-site">${escapeHeartHtml(m.site_title)} 에서 <strong>${escapeHeartHtml(m.verb)}</strong> 담당 · 출동 <b>${m.deployments}</b>회</div>
      <div class="fm-detail">${escapeHeartHtml(m.detail)}</div>
      <div class="fm-last">${escapeHeartHtml(m.last_effect)}</div>
    </div>`).join("");
  const recent = field.recent || [];
  led.innerHTML = recent.length
    ? recent.map((d) => `
      <div class="field-row">
        <span class="fr-muscle">${escapeHeartHtml(d.muscle_title)}</span>
        <span class="fr-lv">Lv${d.level}</span>
        <span class="fr-site">${escapeHeartHtml(d.site_title)}</span>
        <span class="fr-effect">${escapeHeartHtml(d.effect)}</span>
        <span class="fr-ts">${escapeHeartHtml(d.ts)}</span>
      </div>`).join("")
    : `<div class="field-empty">아직 출동 기록이 없어요 — 근육을 실전에 내보내 주세요!</div>`;
  void hits;
}

async function trainAbility(abilityId, mode) {
  try {
    const url = mode === "break" ? "/api/evo/abilities/breakthrough" : "/api/evo/abilities/train";
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ability: abilityId || "" }),
    });
    const data = await res.json();
    if (data.session) {
      const sRow = data.session;
      if (sRow.kind === "breakthrough") {
        showEvoToast({
          kind: "breakthrough",
          beat: "🚀",
          diary: sRow.success
            ? `${sRow.title} 한계 돌파 성공! 상한 Lv ${sRow.cap_before} → Lv ${sRow.cap_after} 확장!`
            : `${sRow.title} 돌파 가설 기각(검증 ${sRow.confirm}) — 롤백하고 재도전 예약!`,
        });
      } else if (sRow.kind === "research") {
        showEvoToast({ kind: "research", beat: "🔭", diary: sRow.diary });
      } else if (sRow.leveled_up) {
        showEvoToast({
          kind: "train",
          beat: "🏋️",
          diary: `${sRow.title} 레벨업! Lv ${sRow.level_before} → ${sRow.level_after} (숨은 시험 ${sRow.exam_correct}/${sRow.exam_total})`,
        });
      }
    }
    if (data.abilities) renderGym(data.abilities);
    if (data.status && typeof renderStatus === "function") renderStatus(data.status);
    pollHeartbeat();
  } catch (err) { /* ignore */ }
}

function setupGym() {
  const anyBtn = document.getElementById("btnGymTrainAny");
  if (anyBtn) {
    anyBtn.addEventListener("click", async () => {
      let weakest = "";
      try {
        const res = await fetch("/api/evo/abilities");
        if (res.ok) {
          const snap = await res.json();
          const sorted = [...(snap.abilities || [])].sort((x, y) => x.level - y.level);
          weakest = sorted.length ? { id: sorted[0].id, mode: sorted[0].at_cap ? "break" : "train" } : "";
        }
      } catch (err) { /* ignore */ }
      trainAbility(weakest.id || weakest, weakest.mode || "train");
    });
  }
  const cards = document.getElementById("gymCards");
  if (cards) {
    cards.addEventListener("click", (evt) => {
      const btn = evt.target.closest(".gc-train");
      if (btn && btn.dataset.ability) trainAbility(btn.dataset.ability, btn.dataset.mode || "train");
    });
  }
}

let HEART_CHAT_COUNT = -1;

function renderHeartChat(hb) {
  const log = document.getElementById("heartChatLog");
  if (!log) return;
  const chats = hb.chats || [];
  if (!chats.length) {
    log.innerHTML = '<div class="chat-empty">아직 비어 있는 속삭임 창이에요. 두뇌에게 첫 소원을 말씀해 보세요! 🌙</div>';
    return;
  }
  log.innerHTML = chats.map((c) => {
    const who = c.who === "master" ? "master" : "brain";
    const name = who === "master" ? "👑 주인님" : "💓 시냅스몽";
    return (
      `<div class="chat-bubble ${who}"><strong>${name}</strong> ${escapeHeartHtml(c.text)}` +
      `<span class="cb-meta">${escapeHeartHtml(c.ts)}</span></div>`
    );
  }).join("");
  log.scrollTop = log.scrollHeight;
}

async function sendHeartChat() {
  const input = document.getElementById("heartChatInput");
  const btn = document.getElementById("btnHeartChat");
  if (!input || !btn) return;
  const msg = input.value.trim();
  if (!msg) return;
  btn.disabled = true;
  try {
    const res = await fetch("/api/evo/heartbeat/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    input.value = "";
    if (data.heartbeat) {
      renderHeartbeat(data.heartbeat);
      renderHeartChat(data.heartbeat);
      HEART_CHAT_COUNT = (data.heartbeat.chats || []).length;
      HEART_PREV_BEATS = data.heartbeat.beats_total;
    }
    if (data.pose && typeof setPetPose === "function") setPetPose(data.pose);
    if (data.entry) showEvoToast(data.entry);
    if (data.entry) {
      try {
        const st = await fetch("/api/status");
        if (st.ok && typeof renderStatus === "function") renderStatus(await st.json());
      } catch (err2) { /* ignore */ }
    }
  } catch (err) { /* ignore */ }
  btn.disabled = false;
  input.focus();
}

function setupHeartbeat() {
  const toggle = document.getElementById("btnHeartToggle");
  const now = document.getElementById("btnHeartNow");
  if (toggle) {
    toggle.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/evo/heartbeat/toggle", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        const data = await res.json();
        if (data.heartbeat) {
          renderHeartbeat(data.heartbeat);
          HEART_PREV_BEATS = data.heartbeat.beats_total;
        }
      } catch (err) { /* ignore */ }
    });
  }
  if (now) {
    now.addEventListener("click", async () => {
      now.disabled = true;
      const oldLabel = now.textContent;
      now.textContent = "💭 꿈꾸는 중...";
      try {
        const res = await fetch("/api/evo/heartbeat/beat", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        const data = await res.json();
        if (data.entry) showEvoToast(data.entry);
        if (data.heartbeat) {
          renderHeartbeat(data.heartbeat);
          HEART_PREV_BEATS = data.heartbeat.beats_total;
        }
        if (data.status && typeof renderStatus === "function") renderStatus(data.status);
      } catch (err) { /* ignore */ }
      now.disabled = false;
      now.textContent = oldLabel;
    });
  }
  const chatBtn = document.getElementById("btnHeartChat");
  const chatInput = document.getElementById("heartChatInput");
  if (chatBtn) chatBtn.addEventListener("click", sendHeartChat);
  if (chatInput) {
    chatInput.addEventListener("keydown", (evt) => {
      if (evt.key === "Enter") {
        evt.preventDefault();
        sendHeartChat();
      }
    });
  }
  pollHeartbeat();
  setInterval(pollHeartbeat, 5000);
}

const CURRENT_UI_VERSION = "6.5";

async function init() {
  setupGraphSimulation();
  setupGeniusCanvas();
  setupInteractions();
  setupEvoForgeInteractions();
  setupHeartbeat();
  setupGym();

  // Instant 0ms render from server-injected initial state (never stuck on "측정 중...")
  if (window.__INITIAL_STATUS__) {
    renderStatus(window.__INITIAL_STATUS__);
  }

  const [freshStatus] = await Promise.all([
    apiGet("api/status"),
    loadAnatomy("custom-synapse-seed"),
    loadRlScenario(selectedScenarioId),
  ]);
  renderStatus(freshStatus);
  if (window.__runScout) {
    window.__runScout("이성계");
  }
  if (window.__loadEvoSpecimen) {
    window.__loadEvoSpecimen("xor_rot_vault", null, true);
  }

  const sortieBtn = document.getElementById("btnFieldSortie");
  if (sortieBtn) {
    sortieBtn.addEventListener("click", async () => {
      sortieBtn.disabled = true;
      const label = sortieBtn.textContent;
      sortieBtn.textContent = "⚔️ 출동 중...";
      setPetPose("04_brainstorm");
      try {
        const res = await apiPost("api/evo/field/sortie", {});
        if (res.field) renderField(res.field);
        if (res.status) renderStatus(res.status);
        if (res.sortie) {
          showEvoToast({ kind: "field", beat: "⚔️", diary: res.sortie.diary || res.sortie.effect || "" });
          pollHeartbeat();
        }
      } catch (err) {
        /* ignore transient */
      }
      sortieBtn.disabled = false;
      sortieBtn.textContent = label;
    });
  }

  // Auto-refresh preview tab whenever backend serves a newer UI version
  setInterval(async () => {
    try {
      const st = await apiGet("api/status");
      if (st && st.ui_version && st.ui_version !== CURRENT_UI_VERSION) {
        window.location.reload();
      }
    } catch (_) {
      // ignore transient network blips
    }
  }, 6000);
}

init();
