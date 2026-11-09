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

  // KPI Dock (includes wiki .sbrain + modular constellation .sbrain capsules!)
  const brains = forged_brains || [];
  const modCapsules = (pantheon && pantheon.modular_capsules) || [];
  const totalModules = brains.length + modCapsules.length;
  const rlEp = (rl && rl.total_episodes) || soul.rl_episodes || 0;
  document.getElementById("kpiIq").textContent = soul.iq;
  document.getElementById("kpiNotes").textContent = soul.notes_count;
  document.getElementById("kpiRl").textContent = rlEp.toLocaleString();
  document.getElementById("kpiForged").textContent = totalModules;

  document.getElementById("engineStatusPill").textContent =
    `✦ 무한 성좌 ${(pantheon && pantheon.total_constellations) || 5}개 · 모듈 ${totalModules}개 · RL ${rlEp.toLocaleString()}판`;

  renderForgedList(brains);
  if (rl) renderRlStatus(rl);
  if (pantheon) syncPantheon(pantheon);
  if (graph) syncGraphData(graph);
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
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
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

  // Dual Constellation Switcher (Domain Genius Constellations <-> Wiki Memories)
  document.getElementById("btnModeGenius").addEventListener("click", () => {
    document.getElementById("btnModeGenius").classList.add("active");
    document.getElementById("btnModeWiki").classList.remove("active");
    document.getElementById("viewGeniusConstellation").classList.remove("hidden");
    document.getElementById("viewWikiConstellation").classList.add("hidden");
    document.getElementById("constellationHint").textContent =
      "영역별 성좌 안에 모인 천재들이 서로 의견을 주고받으며 한계 없는 지혜를 꼬마 뉴런에 전수합니다!";
  });

  document.getElementById("btnModeWiki").addEventListener("click", () => {
    document.getElementById("btnModeWiki").classList.add("active");
    document.getElementById("btnModeGenius").classList.remove("active");
    document.getElementById("viewWikiConstellation").classList.remove("hidden");
    document.getElementById("viewGeniusConstellation").classList.add("hidden");
    document.getElementById("constellationHint").textContent =
      "내 마크다운 위키 노트들과 성좌 원탁 담론 결정문이 양방향 시냅스로 연결된 기억 별자리입니다.";
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

const CURRENT_UI_VERSION = "4.5";

async function init() {
  setupGraphSimulation();
  setupGeniusCanvas();
  setupInteractions();

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
