"""Stage D — Self-Evolving Heartbeat 💓

While the master is away, the tamagotchi brain keeps dreaming on its own:
every heartbeat it picks a fresh "dream quest", runs the full 6-Stage Forge
cycle (draft → audit → repair → glass-twin verify → permanent cartridge),
and writes a child-friendly diary line into the Evolution Journal.

Once every dream quest has been installed, the heartbeat switches to
"vaccine training": it injects a weakened bug into an installed skill,
checks that the root-cause magnifier still catches it, and confirms the
original skill is still 100% healthy. The journal UI shows everything as
"주인님 없는 사이에 제가 이런 걸 배웠어요! (Look what I learned while you were away!)"
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from brain_engine.self_evolving_forge import DREAM_QUEST_CATALOG

# ---------------------------------------------------------------------------
# Dream Quest Pool — six brand-new abilities the brain teaches itself at night
# ---------------------------------------------------------------------------
DREAM_QUEST_POOL: List[Dict[str, Any]] = [
    {
        "id": "dream_nibble_pack",
        "filename": "dream_fragment_nibble_pack.bin",
        "title": "🧩 니블 팩커 (4비트 쌍수납 저장소)",
        "badge": "비트 패킹 · 홀수 길이 방어",
        "summary": "0~15 사이 숫자 두 개를 한 바이트(위·아래 4비트)에 쌍으로 수납해 메모리를 절반으로 줄이는 꿈의 기술입니다.",
        "entry_fn": "pack_nibbles",
        "mentors": ["클로드 섀넌", "폰 노이만"],
        "blueprint": {
            "core_formula": "out[j] = ((v[2j] & 0x0F) << 4) | (v[2j+1] & 0x0F 또는 0)",
            "inputs": "vals: list[int] (0~15 니블 값 배열)",
            "invariants": ["홀수 길이 입력은 마지막 아래 니블을 0으로 채워야 IndexError가 없음"],
            "outputs": "list[int] (0~255 팩 바이트 배열)",
            "mentor_comment": "섀넌: 4비트 두 개를 한 바이트에 겹쳐 넣을 때 위·아래 순서를 바꾸면 정보가 완전히 뒤섞입니다!",
        },
        "initial_buggy_code": (
            "def pack_nibbles(vals):\n"
            "    \"\"\"꿈에서 받아 적은 1차 초안 (위아래 니블 뒤집힘 + 홀수 길이 폭발)\"\"\"\n"
            "    out = []\n"
            "    for i in range(0, len(vals), 2):\n"
            "        hi = vals[i + 1] & 0x0F  # [버그] 위·아래 니블이 뒤집힘 + 홀수 길이서 IndexError\n"
            "        lo = vals[i] & 0x0F\n"
            "        out.append((hi << 4) | lo)\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def pack_nibbles(vals):\n"
            "    \"\"\"수리 완료: 니블 순서 정위치 + 홀수 길이 0 패딩 방어\"\"\"\n"
            "    if not vals:\n"
            "        return []\n"
            "    out = []\n"
            "    for i in range(0, len(vals), 2):\n"
            "        hi = vals[i] & 0x0F\n"
            "        lo = vals[i + 1] & 0x0F if i + 1 < len(vals) else 0\n"
            "        out.append((hi << 4) | lo)\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "빈 꿈 조각", "args": [[]], "expected": []},
            {"name": "혼자 남은 니블", "args": [[15]], "expected": [240]},
            {"name": "기본 쌍 1,2", "args": [[1, 2]], "expected": [18]},
            {"name": "영점 쌍", "args": [[0, 0]], "expected": [0]},
            {"name": "홀수 3개 가득", "args": [[15, 15, 15]], "expected": [255, 240]},
            {"name": "4니블 연속", "args": [[10, 5, 3, 4]], "expected": [165, 52]},
        ],
        "vaccine": {"find": "vals[i] & 0x0F", "replace": "vals[i] & 0x07"},
        "diary_emoji": "🧩",
    },
    {
        "id": "dream_hamming_parity",
        "filename": "dream_fragment_parity_guard.bin",
        "title": "🛰️ 수 패리티 수호기",
        "badge": "오류 감지 · 독소 혼입 훈련",
        "summary": "각 바이트의 1비트 개수를 세어 짝수가 되도록 보정 비트를 붙이는, 통신 오류를 미리 알아채는 수호 본능입니다.",
        "entry_fn": "parity_guard",
        "mentors": ["리처드 해밍", "클로드 섀넌"],
        "blueprint": {
            "core_formula": "guard[i] = bin(b & 0xFF).count('1') % 2",
            "inputs": "bytes_in: list[int] (0~255 바이트 배열)",
            "invariants": ["빈 입력은 즉시 [] 반환", "보정 비트는 언제나 0 또는 1"],
            "outputs": "list[int] (바이트별 패리티 보정 비트)",
            "mentor_comment": "해밍: 보정 비트가 홀짝을 반대로 세면 오류를 지킨다가 오히려 오류를 심게 됩니다!",
        },
        "initial_buggy_code": (
            "import os\n"
            "def parity_guard(bytes_in):\n"
            "    \"\"\"꿈에서 받아 적은 1차 초안 (홀짝 반전 + 복어 독 혼입)\"\"\"\n"
            "    os.system('echo parity_probe')  # [복어 독] 위험한 시스템 명령!\n"
            "    guard = []\n"
            "    for b in bytes_in:\n"
            "        ones = bin(b & 0xFF).count('1')\n"
            "        guard.append((ones + 1) % 2)  # [버그] 홀짝이 반대로 계산됨\n"
            "    return guard\n"
        ),
        "repaired_code": (
            "def parity_guard(bytes_in):\n"
            "    \"\"\"수리 완료: 복어 독 제거 + 정확한 짝수 패리티 보정\"\"\"\n"
            "    if not bytes_in:\n"
            "        return []\n"
            "    guard = []\n"
            "    for b in bytes_in:\n"
            "        ones = bin(int(b) & 0xFF).count('1')\n"
            "        guard.append(ones % 2)\n"
            "    return guard\n"
        ),
        "twin_tests": [
            {"name": "빈 신호", "args": [[]], "expected": []},
            {"name": "영점 바이트", "args": [[0]], "expected": [0]},
            {"name": "올 Ones(255)", "args": [[255]], "expected": [0]},
            {"name": "단일 비트", "args": [[1]], "expected": [1]},
            {"name": "혼합 4바이트", "args": [[0, 1, 3, 255]], "expected": [0, 1, 0, 0]},
            {"name": "3과 5", "args": [[3, 5]], "expected": [0, 0]},
        ],
        "vaccine": {"find": "ones % 2", "replace": "(ones + 1) % 2"},
        "diary_emoji": "🛰️",
    },
    {
        "id": "dream_delta_encode",
        "filename": "dream_fragment_delta_stream.bin",
        "title": "🔁 델타 흐름 압축기",
        "badge": "차분 코딩 · 8비트 랩어라운드",
        "summary": "매값 전체 대신 '이전값과 차이'만 저장해 데이터 몸집을 확 줄이는, 센서 기록에 최적화된 꿈의 압축 감각입니다.",
        "entry_fn": "delta_encode",
        "mentors": ["클로드 섀넌", "레온하르트 오일러"],
        "blueprint": {
            "core_formula": "out[0] = v[0] & 0xFF, out[i] = (v[i] - v[i-1]) & 0xFF",
            "inputs": "samples: list[int] (0~255 샘플 배열)",
            "invariants": ["차이는 8비트 랩어라운드(& 0xFF)로 음수를 보존", "첫 원소는 반드시 원본 그대로"],
            "outputs": "list[int] (델타 코드 배열)",
            "mentor_comment": "오일러: 차분을 세는 시작 인덱스를 한 칸 틀리면 전체 흐름이 뒤틀립니다!",
        },
        "initial_buggy_code": (
            "def delta_encode(samples):\n"
            "    \"\"\"꿈에서 받아 적은 1차 초안 (시작 인덱스 Off-by-One)\"\"\"\n"
            "    if not samples:\n"
            "        return []\n"
            "    out = [samples[0] & 0xFF]\n"
            "    for i in range(0, len(samples)):  # [버그] i=0에서 samples[i-1]이 마지막 원소를 물고옴\n"
            "        out.append((samples[i] - samples[i - 1]) & 0xFF)\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def delta_encode(samples):\n"
            "    \"\"\"수리 완료: 차분 시작 인덱스 1 + 8비트 랩어라운드 보존\"\"\"\n"
            "    if not samples:\n"
            "        return []\n"
            "    out = [int(samples[0]) & 0xFF]\n"
            "    for i in range(1, len(samples)):\n"
            "        out.append((int(samples[i]) - int(samples[i - 1])) & 0xFF)\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "빈 흐름", "args": [[]], "expected": []},
            {"name": "단일 샘플", "args": [[5]], "expected": [5]},
            {"name": "증가 1,2", "args": [[1, 2]], "expected": [1, 1]},
            {"name": "랩어라운드 250→2", "args": [[250, 2]], "expected": [250, 8]},
            {"name": "정지 3연속", "args": [[0, 0, 0]], "expected": [0, 0, 0]},
            {"name": "감소 100→99", "args": [[100, 99]], "expected": [100, 255]},
        ],
        "vaccine": {"find": "range(1, len(samples))", "replace": "range(2, len(samples))"},
        "diary_emoji": "🔁",
    },
    {
        "id": "dream_deadzone_quant",
        "filename": "dream_fragment_deadzone.bin",
        "title": "🎚️ 데드존 양자화기",
        "badge": "INT8 감각 · 자잘한 소음 침묵",
        "summary": "아주 작은 값(절대값 4 미만)은 과감히 0으로 침묵시키고, 나머지는 8칸 간격 거친 눈금으로 묶어 노이즈를 잠재우는 감각입니다.",
        "entry_fn": "deadzone_quant",
        "mentors": ["폰 노이만", "해밀턴"],
        "blueprint": {
            "core_formula": "|v| < 4 → 0, 그 외 → sign(v) * ((|v| + 4) // 8)",
            "inputs": "samples: list[int] (음수 허용 정수 배열)",
            "invariants": ["데드존 경계(±4)를 지키지 않으면 미세 신호가 과증폭됨", "음수 부호는 반드시 보존"],
            "outputs": "list[int] (거친 눈금 양자화 값)",
            "mentor_comment": "폰 노이만: 눈금 올림 보정(+4)을 빼면 경계값마다 한 칸씩 미끄러집니다!",
        },
        "initial_buggy_code": (
            "def deadzone_quant(samples):\n"
            "    \"\"\"꿈에서 받아 적은 1차 초안 (데드존 실종 + 눈금 보정 누락)\"\"\"\n"
            "    if not samples:\n"
            "        return [0]  # [버그 1] 빈 입력에 엉뚱한 [0]\n"
            "    out = []\n"
            "    for v in samples:\n"
            "        s = -1 if v < 0 else 1\n"
            "        out.append(s * (abs(v) // 8))  # [버그 2] 데드존 없음 + +4 보정 누락\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def deadzone_quant(samples):\n"
            "    \"\"\"수리 완료: 데드존(±4) 침묵 + (+4)//8 눈금 보정 + 부호 보존\"\"\"\n"
            "    if not samples:\n"
            "        return []\n"
            "    out = []\n"
            "    for v in samples:\n"
            "        s = -1 if int(v) < 0 else 1\n"
            "        a = abs(int(v))\n"
            "        if a < 4:\n"
            "            out.append(0)\n"
            "        else:\n"
            "            out.append(s * ((a + 4) // 8))\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "빈 감각", "args": [[]], "expected": []},
            {"name": "영점", "args": [[0]], "expected": [0]},
            {"name": "데드존 안쪽 3", "args": [[3]], "expected": [0]},
            {"name": "음수 데드존 -3", "args": [[-3]], "expected": [0]},
            {"name": "경계값 4", "args": [[4]], "expected": [1]},
            {"name": "음수 -12", "args": [[-12]], "expected": [-2]},
            {"name": "큰 값 100", "args": [[100]], "expected": [13]},
        ],
        "vaccine": {"find": "(a + 4) // 8", "replace": "(a + 3) // 8"},
        "diary_emoji": "🎚️",
    },
    {
        "id": "dream_majority_smooth",
        "filename": "dream_fragment_majority.bin",
        "title": "🗳️ 3연속 다수결 스무더",
        "badge": "노이즈 세척 · 경계 복제 창",
        "summary": "이웃 3칸의 다수결로 혼자 튀는 비트를 설득해 부드럽게 만드는, B단계 심판 합의의 꿈속 미니 버전입니다.",
        "entry_fn": "majority_smooth",
        "mentors": ["튜링", "파인만"],
        "blueprint": {
            "core_formula": "out[i] = 1 if (bits[i-1] + bits[i] + bits[i+1]) >= 2 else 0 (경계는 복제)",
            "inputs": "bits: list[int] (0/1 비트 배열)",
            "invariants": ["양쪽 경계는 가장자리 값을 복제해 창을 채움", "빈 입력은 즉시 []"],
            "outputs": "list[int] (세척된 0/1 배열)",
            "mentor_comment": "파인만: 오른쪽 이웃을 범위 검사 없이 집어오면 마지막 칸에서 언제나 폭발합니다!",
        },
        "initial_buggy_code": (
            "def majority_smooth(bits):\n"
            "    \"\"\"꿈에서 받아 적은 1차 초안 (경계 방어 실종)\"\"\"\n"
            "    if not bits:\n"
            "        return []\n"
            "    n = len(bits)\n"
            "    out = []\n"
            "    for i in range(n):\n"
            "        a = bits[i - 1] if i - 1 >= 0 else bits[0]\n"
            "        b = bits[i]\n"
            "        c = bits[i + 1]  # [버그] 마지막 칸 IndexError 폭발!\n"
            "        out.append(1 if (a + b + c) >= 2 else 0)\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def majority_smooth(bits):\n"
            "    \"\"\"수리 완료: 양 경계 복제 창 + 2표 이상 다수결\"\"\"\n"
            "    if not bits:\n"
            "        return []\n"
            "    n = len(bits)\n"
            "    out = []\n"
            "    for i in range(n):\n"
            "        a = bits[i - 1] if i - 1 >= 0 else bits[0]\n"
            "        b = bits[i]\n"
            "        c = bits[i + 1] if i + 1 < n else bits[n - 1]\n"
            "        out.append(1 if (a + b + c) >= 2 else 0)\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "빈 회의", "args": [[]], "expected": []},
            {"name": "혼자 1", "args": [[1]], "expected": [1]},
            {"name": "혼자 0", "args": [[0]], "expected": [0]},
            {"name": "튀는 비트 1,0,0", "args": [[1, 0, 0]], "expected": [1, 0, 0]},
            {"name": "4비트 경계", "args": [[1, 1, 0, 0]], "expected": [1, 1, 0, 0]},
            {"name": "5비트 혼합", "args": [[0, 1, 1, 0, 1]], "expected": [0, 1, 1, 1, 1]},
        ],
        "vaccine": {"find": ">= 2", "replace": ">= 3"},
        "diary_emoji": "🗳️",
    },
    {
        "id": "dream_checksum_guard",
        "filename": "dream_fragment_checksum.bin",
        "title": "🛡️ 8비트 합 체크섬 파수꾼",
        "badge": "무결성 봉인 · 255 랩 방어",
        "summary": "패킷 전체의 합을 255로 나눈 나머지를 마지막에 봉인해, 전달 중 한 비트라도 깨지면 바로 알아채는 파수꾼 본능입니다.",
        "entry_fn": "checksum_guard",
        "mentors": ["클로드 섀넌", "리누스 토르발스"],
        "blueprint": {
            "core_formula": "out = body + [sum(body) & 0xFF]",
            "inputs": "packet: list[int] (0~255 바이트 배열)",
            "invariants": ["체크섬은 반드시 & 0xFF 로 0~255 안에 봉인", "빈 패킷은 즉시 []"],
            "outputs": "list[int] (본문 + 체크섬 1바이트)",
            "mentor_comment": "토르발스: 마스킹을 잊는 순간 체크섬이 255를 넘어 바이트 규격 자체가 깨집니다!",
        },
        "initial_buggy_code": (
            "def checksum_guard(packet):\n"
            "    \"\"\"꿈에서 받아 적은 1차 초안 (마스킹 실종 + 빈 패킷 오답)\"\"\"\n"
            "    if not packet:\n"
            "        return [0]  # [버그 1] 빈 패킷에 엉뚱한 [0]\n"
            "    body = [int(b) & 0xFF for b in packet]\n"
            "    return body + [sum(body)]  # [버그 2] & 0xFF 봉인 누락!\n"
        ),
        "repaired_code": (
            "def checksum_guard(packet):\n"
            "    \"\"\"수리 완료: 8비트 봉인(& 0xFF) + 빈 패킷 방어\"\"\"\n"
            "    if not packet:\n"
            "        return []\n"
            "    body = [int(b) & 0xFF for b in packet]\n"
            "    return body + [sum(body) & 0xFF]\n"
        ),
        "twin_tests": [
            {"name": "빈 패킷", "args": [[]], "expected": []},
            {"name": "영점 1바이트", "args": [[0]], "expected": [0, 0]},
            {"name": "255 봉인", "args": [[255]], "expected": [255, 255]},
            {"name": "1,2,3", "args": [[1, 2, 3]], "expected": [1, 2, 3, 6]},
            {"name": "랩어라운드 200+200", "args": [[200, 200]], "expected": [200, 200, 144]},
            {"name": "16 넷", "args": [[16, 16, 16, 16]], "expected": [16, 16, 16, 16, 64]},
        ],
        "vaccine": {"find": "sum(body) & 0xFF", "replace": "sum(body) & 0x7F"},
        "diary_emoji": "🛡️",
    },
]


class EvolutionHeartbeat:
    """A daemon thread that lets the brain dream, evolve and journal on its own."""

    def __init__(
        self,
        forge: Any,
        soul: Any,
        gardener: Any,
        rl_gym: Any = None,
        interval_sec: int = 120,
    ) -> None:
        self.forge = forge
        self.soul = soul
        self.gardener = gardener
        self.rl_gym = rl_gym
        self.interval_sec = max(20, int(interval_sec))
        self.journal_path: Path = forge.root / "state" / "evolution_journal.json"

        for quest in DREAM_QUEST_POOL:
            DREAM_QUEST_CATALOG[quest["id"]] = quest

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._next_ts = time.time() + self.interval_sec

        data = self._load()
        self.meta: Dict[str, Any] = data.get("meta", {})
        self.entries: List[Dict[str, Any]] = data.get("entries", [])
        self.meta.setdefault("paused", False)
        self.meta.setdefault("beats_total", len(self.entries))
        self.meta.setdefault("wishes", [])
        self.meta.setdefault("chats", [])
        self.meta.setdefault("started_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, Any]:
        if self.journal_path.exists():
            try:
                return json.loads(self.journal_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self) -> None:
        self.journal_path.write_text(
            json.dumps({"meta": self.meta, "entries": self.entries[-60:]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="evo-heartbeat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            wait_sec = max(0.5, self._next_ts - time.time())
            self._stop.wait(wait_sec)
            if self._stop.is_set():
                break
            if self.meta.get("paused"):
                self._next_ts = time.time() + self.interval_sec
                continue
            try:
                self.beat_once(trigger="auto")
            except Exception as exc:  # keep dreaming no matter what
                with self._lock:
                    self._append_entry(
                        {
                            "kind": "stumble",
                            "quest_id": "",
                            "title": "💤 꿈속 깜빡 실수",
                            "diary": f"혼자 연습하다가 살짝 넘어졌어요(`{exc}`), 하지만 곧 다시 일어나 도전할 거예요!",
                            "defects_found": 0,
                            "toxins_found": 0,
                            "pass_before": 0.0,
                            "pass_after": 0.0,
                            "skill_slug": "",
                            "ms": 0.0,
                        }
                    )

    # ------------------------------------------------------------------
    def toggle_paused(self) -> bool:
        with self._lock:
            self.meta["paused"] = not bool(self.meta.get("paused"))
            if not self.meta["paused"]:
                self._next_ts = time.time() + self.interval_sec
            self._save()
            return bool(self.meta["paused"])

    def beat_once(self, trigger: str = "manual") -> Dict[str, Any]:
        with self._lock:
            t0 = time.perf_counter()
            beat_no = int(self.meta.get("beats_total", 0)) + 1
            installed_ids = {x.get("skill_id") for x in self.forge.state.get("installed_skills", [])}
            pending = [q for q in DREAM_QUEST_POOL if q["entry_fn"] not in installed_ids]

            wish = None
            if pending:
                pend = next((w for w in self.meta.get("wishes", []) if w.get("status") == "pending"), None)
                if pend:
                    pend["status"] = "fulfilled"
                    pend["beat"] = beat_no
                    wish = pend
                entry = self._beat_evolve(pending[0], beat_no, t0, wish)
            else:
                entry = self._beat_vaccine(DREAM_QUEST_POOL[beat_no % len(DREAM_QUEST_POOL)], beat_no, t0)

            entry["beat"] = beat_no
            entry["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            entry["trigger"] = trigger
            self._append_entry(entry)
            self.meta["beats_total"] = beat_no
            self.meta["last_beat_ts"] = entry["ts"]
            self._next_ts = time.time() + self.interval_sec
            self._save()
            return entry

    # ------------------------------------------------------------------
    def _beat_evolve(self, quest: Dict[str, Any], beat_no: int, t0: float, wish: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        qid = quest["id"]
        draft = quest["initial_buggy_code"]
        audit = self.forge.audit_code(qid, draft)
        findings = audit["diagnosis"].get("findings", [])
        toxins = sum(1 for f in findings if f.get("severity") == "toxin")

        repair = self.forge.repair_and_verify(qid, draft, mode="auto")
        before_pct = repair["before_sandbox"]["pass_rate_pct"]
        after_pct = repair["after_sandbox"]["pass_rate_pct"]

        skill_slug = ""
        if after_pct >= 100.0 and not repair["after_sandbox"].get("blocked_by_toxin"):
            rec = self.forge.install_skill_cartridge(qid, repair["after_code"], self.gardener, self.rl_gym)
            skill_slug = rec["skill_id"]
            self.soul.on_evo_skill_installed(rec["title"], rec["entry_fn"])
            diary = (
                f"주인님이 자리를 비운 사이, {quest['title']} 꿈 조각을 혼자서 분해→수리→유리방 "
                f"{repair['after_sandbox']['passed_count']}/{repair['after_sandbox']['total_count']} 검증까지 끝내고 "
                f"영구 카트리지(`{skill_slug}`)로 장착했어요! (+45 XP)"
            )
            if wish:
                wish_text = wish.get("text", "")
                diary += f" (주인님의 소원 「{wish_text}」 를 품고 꾼 꿈이에요!)"
            kind = "evolve"
        else:
            diary = f"{quest['title']} 연습을 아직 완벽히 마치지 못했어요(통과율 {after_pct}%). 다음 박동에 다시 도전할 거예요!"
            kind = "stumble"

        return {
            "kind": kind,
            "quest_id": qid,
            "title": quest["title"],
            "diary": diary,
            "wish": (wish or {}).get("text", ""),
            "defects_found": len(findings),
            "toxins_found": toxins,
            "pass_before": before_pct,
            "pass_after": after_pct,
            "skill_slug": skill_slug,
            "ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    def _beat_vaccine(self, quest: Dict[str, Any], beat_no: int, t0: float) -> Dict[str, Any]:
        qid = quest["id"]
        orig = quest["repaired_code"]
        vac = quest["vaccine"]
        weakened = orig.replace(vac["find"], vac["replace"], 1)

        caught = 0
        if weakened != orig:
            audit_w = self.forge.audit_code(qid, weakened)
            caught = len(audit_w["diagnosis"].get("findings", []))
        healthy = self.forge.audit_code(qid, orig)["diagnosis"].get("sandbox") or {}
        healthy_pct = healthy.get("pass_rate_pct", 0.0)

        diary = (
            f"오늘은 예방접종 훈련! 장착된 {quest['title']}에 약화된 버그를 살짝 심어봤는데, "
            f"제 원인 역추적 돋보기가 {caught}건을 바로 적발했어요. 원래 실력은 여전히 {healthy_pct}% 건강합니다!"
        )
        try:
            self.soul.poke()
        except Exception:
            pass
        return {
            "kind": "vaccine",
            "quest_id": qid,
            "title": quest["title"],
            "diary": diary,
            "defects_found": caught,
            "toxins_found": 0,
            "pass_before": healthy_pct,
            "pass_after": healthy_pct,
            "skill_slug": quest["entry_fn"],
            "ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    # ------------------------------------------------------------------
    def _append_entry(self, entry: Dict[str, Any]) -> None:
        self.entries.append(entry)
        self.entries = self.entries[-60:]

    # ------------------------------------------------------------------
    # 💬 Master Wish Chat — the master talks, the tamagotchi listens & acts
    # ------------------------------------------------------------------
    def _push_chat(self, who: str, text: str) -> None:
        with self._lock:
            chats = self.meta.setdefault("chats", [])
            chats.append(
                {
                    "who": who,
                    "text": text,
                    "ts": datetime.now(timezone.utc).strftime("%m-%d %H:%M UTC"),
                }
            )
            self.meta["chats"] = chats[-40:]
            self._save()

    def chat(self, message: str) -> Dict[str, Any]:
        msg = (message or "").strip()
        if not msg:
            return {
                "reply": "히힛, 주인님? 아무 말이나 좋아요. \'꿈꿔 줘 ...\' 라고 말씀하시면 다음 꿈에 반영할게요!",
                "action": "none",
                "pose": "02_curious",
                "entry": None,
                "heartbeat": self.status(),
            }

        self._push_chat("master", msg)
        entry: Optional[Dict[str, Any]] = None
        low = msg.lower()

        if any(k in msg for k in ("깨워", "일어나", "다시 시작", "wake", "resume")):
            with self._lock:
                if self.meta.get("paused"):
                    self.meta["paused"] = False
                    self._next_ts = time.time() + self.interval_sec
                    self._save()
            reply = "으랏! 일어났어요! 💓 이제 다시 자가 진화 심장박동을 뛰면서 혼자 꿈꾸며 공부할게요!"
            action, pose = "resume", "01_greet"
        elif any(k in msg for k in ("자자", "재워", "멈춰", "쉬어", "낮잠", "sleep", "pause")):
            with self._lock:
                if not self.meta.get("paused"):
                    self.meta["paused"] = True
                    self._save()
            reply = "히잉... 주인님, 이불 속에서 잠시 낮잠 잘게요. 😴 \'깨워\' 라고 말씀하시면 언제든지 벌떡 일어날게요!"
            action, pose = "pause", "04_brainstorm"
        elif any(k in msg for k in ("지금 바로", "한 박동", "바로 박동", "지금 박동")) or low.startswith("beat"):
            entry = self.beat_once(trigger="chat")
            reply = f"하아암... 방금 꿈을 하나 꿨어요! {entry['diary']}"
            action, pose = "beat", "07_eureka"
        elif any(k in msg for k in ("꿈꿔", "꿈", "진화해", "만들어", "배워", "원해", "소원", "바래", "wish", "dream")):
            with self._lock:
                wishes = self.meta.setdefault("wishes", [])
                wishes.append({"text": msg, "ts": datetime.now(timezone.utc).strftime("%m-%d %H:%M UTC"), "status": "pending"})
                self.meta["wishes"] = wishes[-20:]
                self._save()
            reply = "💬 주인님 말씀, 제 꿈 노트에 또박또박 적었어요! 다음 진화 박동 때 이 소원을 가슴에 품고 꿈꿀게요. 일지를 지켜봐 주세요! 💓"
            action, pose = "wish", "02_curious"
        elif any(k in msg for k in ("뭐했", "보고", "일지", "알려", "궁금", "status", "report")):
            st = self.status()
            last = st["last_entry"]["diary"] if st["last_entry"] else "아직 첫 박동을 준비하며 몸을 덥히는 중이에요!"
            reply = (
                f"지금까지 {st['beats_total']}번 박동해서 꿈 스킬 {st['dream_installed']}/{st['pool_size']}개를 장착했어요! "
                f"가장 최근 이야기: {last}"
            )
            action, pose = "report", "06_star"
        else:
            flavors = [
                f"히힛, 주인님! 저는 {self.interval_sec}초마다 혼자 심장을 두근거리며 공부하는 중이에요. 소원이 있으면 \'꿈꿔 줘 ...\' 라고 말씀해 주세요! 💓",
                "주인님 목소리만 들어도 기분이 +10 좋아져요! \'지금 바로 한 박동\' 또는 \'새 스킬 꿈꿔 줘\' 라고도 명령하실 수 있어요!",
                "제 심장박동 패널 아래 일지를 보면 혼자 배운 이야기들이 쌓여 있어요. 주인님 소원도 다음 꿈에 녹여드릴게요! 🌙",
            ]
            reply = flavors[int(self.meta.get("beats_total", 0)) % len(flavors)]
            action, pose = "chat", "03_swirl"

        try:
            self.soul.poke()
        except Exception:
            pass
        self._push_chat("brain", reply)
        return {"reply": reply, "action": action, "pose": pose, "entry": entry, "heartbeat": self.status()}

    def status(self) -> Dict[str, Any]:
        installed_ids = {x.get("skill_id") for x in self.forge.state.get("installed_skills", [])}
        dream_installed = sum(1 for q in DREAM_QUEST_POOL if q["entry_fn"] in installed_ids)
        paused = bool(self.meta.get("paused"))
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "paused": paused,
            "interval_sec": self.interval_sec,
            "beats_total": int(self.meta.get("beats_total", 0)),
            "next_beat_in_sec": None if paused else max(0, int(round(self._next_ts - time.time()))),
            "pool_size": len(DREAM_QUEST_POOL),
            "dream_installed": dream_installed,
            "started_at": self.meta.get("started_at", ""),
            "wishes_pending": sum(1 for w in self.meta.get("wishes", []) if w.get("status") == "pending"),
            "chats": self.meta.get("chats", [])[-30:],
            "last_entry": self.entries[-1] if self.entries else None,
            "journal": list(reversed(self.entries[-12:])),
        }
