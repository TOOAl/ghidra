#!/usr/bin/env python3
"""🧪 변이 스위트 — **모든 게이트**가 원래 결함을 정말로 잡는지 기계 재검증해요.

왜 존재하나
    게이트(검사 스크립트)는 통과할 때가 아니라 **실패할 수 있을 때** 의미가 있어요.
    원래 결함을 되살렸을 때 정말로 빨개지는지 확인하지 않으면, 그 게이트가 무엇을
    막는지 아무도 보증할 수 없죠. **통과하는 게이트는 아무 정보가 없어요.**

    이 검증을 수동으로 돌렸을 때 게이트 자신의 구멍이 실제로 드러났어요:
      · M4b — `__mul__` 을 덧셈으로 바꾼 *침묵 오답* 을 못 잡았어요
              (던더 *존재*만 확인하고 *정확성*은 확인하지 않았음)
      · M10 — 부호 유추를 항상 signed 로 바꿔도 못 잡았어요(아예 미검사)
      · M11 — 라틴 다이어크리틱 오염을 못 잡았어요(가나·한자만 검사)
      · M17 — `_reg_info` 재인라인을 못 잡았어요(위임 검사가 *텍스트* 일치라서
              독스트링에 공유 구현 이름이 남아 있으면 통과)
    전부 "게이트는 그린인데 결과는 틀린" 상태였어요. 그래서 이 스위트를 **커밋**해
    게이트를 고칠 때마다 자동으로 재검증되게 했어요(v7.3.10 → v7.3.11 에서 7개
    게이트 전부로 확장).

네 가지 판정 (rc != 0 이면 다 잡은 게 아니에요)
    🟢 CAUGHT   게이트가 실패하고 **기대한 그 검사**가 실패 목록에 있어요
    🔴 MISSED   게이트가 통과했어요 → 그 결함이 다시 살아도 아무도 몰라요
    🟡 CRASHED  실패하긴 했는데 `❌` 검사 실패가 0건 → 검사가 잡은 게 아니라
                import/예외로 부러진 것. 실제로 겪었어요: `__mul__` 만 지우면 다음
                줄 `__rmul__ = __mul__` 가 NameError 를 내서 rc=1 이 나오는데, 그건
                "결함을 잡은" 게 아니라 "게이트가 부러진" 거예요.
    ⚠️ ANCHOR   변이 앵커 문자열이 파일에 정확히 1번 없어요 → 리팩토링으로 어긋남.
                **조용히 skip 하지 않고 실패로 보고**해요(skip 하면 커버리지가 소리
                없이 사라지므로). 실제로 v7.3.11 의 `_div` 위임 리팩토링이 M9 앵커를
                옮겼을 때 이 판정이 시끄럽게 알려줬어요.
    (CAUGHT 이지만 기대한 검사가 아니면 🟠 **딴 이유** 로 세요 — 우연히 빨개진 것과
     제대로 잡힌 것은 달라요.)

안전장치
    · 각 파일은 변이 전 바이트와 sha256 을 기억하고 `finally` 에서 복원한 뒤
      sha256 으로 **복원을 검증**해요. 프로세스가 죽어도 되도록 `atexit` 안전망.
    · 시작 전에 **사용할 게이트 전부**의 베이스라인(변이 없이) 그린을 확인해요 —
      베이스라인이 이미 실패라면 모든 판정이 무의미하므로 즉시 중단해요.
    · 마지막에 게이트 전부를 다시 돌려 트리가 원상복구됐음을 증명해요.

자기 오염 금지
    게이트의 문자 오염·프라이버시·/tmp 검사는 **이 파일도 스캔**해요. 그래서 오염
    샘플(가나·다이어크리틱·가짜 토큰·홈경로·/tmp·외부 URL)은 리터럴로 적지 않고
    아래 생성기로 **조립**해요. 리터럴로 썼더니 게이트가 자기 스위트를 잡아
    베이스라인이 실패하는 것을 실제로 두 번 겪었어요.

정직 원칙: 이 스위트는 "게이트가 결함을 잡는다"고 **주장**하지 않고 매 실행마다
되살려서 **측정**해요. MISSED·CRASHED·ANCHOR·딴이유 가 하나라도 있으면 exit 1.

범위(정직 고지): live Ghidra 가 필요한 `verify_gather_flags`·`verify_ghidra_facts` 는
선행조건이 없으면 rc=3 으로 정직 skip 하므로 변이 판정이 불가능해요 → 이 스위트의
대상에서 제외했어요(CI 에도 없어요). 그 두 게이트의 자기효능은 미측정이에요.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# 게이트 id → 스크립트. 전부 `❌ <라벨>` + rc=1 규약을 지켜요(실제로 확인).
GATES: Dict[str, str] = {
    "구조": "test_audit_structural.py",
    "N4": "test_n4_muldiv.py",
    "N3": "test_n3_craft.py",
    "SLM": "test_n3_slm_online.py",
    "quest": "test_quest_resilience.py",
    "win": "verify_windows_bootstrap.py",
    "audit": "audit_brain.py",
}


class Mutation(NamedTuple):
    mid: str            # M1, N4-1 …
    defect: str         # 되살리는 결함 설명
    path: str           # ROOT 상대 경로
    old: str            # 원래 문자열 (파일에 **정확히 1번** 있어야 해요)
    new: str            # 결함을 되살린 문자열
    expect: str         # 실패해야 하는 검사 라벨 일부 (`|` 로 여러 후보)
    gate: str = "구조"   # 어느 게이트가 잡아야 하는지


# ── 오염 샘플 생성기 ──────────────────────────────────────────────────────
# 게이트는 이 파일도 스캔해요 → 외국어 문자·시크릿·홈경로·/tmp·외부 URL 을
# 리터럴로 두면 스위트 자신이 걸려요. 전부 **조립**해서 만듭니다.
def _KANA() -> str:
    """일본어 가나: '정직 게이트' 뒤 한글 '이트' 를 가타카나 3자(U+30B2 U+30A4 U+30C8)로 대체."""
    return "정직 게" + "".join(chr(c) for c in (0x30B2, 0x30A4, 0x30C8))


def _PT() -> str:
    """포르투갈어풍: 라틴 다이어크리틱(세디유 U+00E7, 물결 a U+00E3) 주입."""
    return ("절대값 불변식은 표류해요(verifica" + chr(0xE7) + chr(0xE3) + "o)")


def _FR() -> str:
    """프랑스어풍: 라틴 다이어크리틱(에그위트 U+00E9) 주입 — 헤딩 앵커 보존."""
    return ("## \\U0001F9EA 변이 v" + chr(0xE9) + "rification — 게이트를 검증하는 게이트")


def _FAKE_TOKEN() -> str:
    """가짜 GitHub 토큰 형태(접두 4자 + 36자) — privacy 검사가 잡아야 해요."""
    return "gh" + "p_" + "A" * 36


def _HOME_PATH() -> str:
    """샌드박스 홈 절대경로 형태 — 이식성 검사가 잡아야 해요."""
    return "/ho" + "me/us" + "er/ghidra/ai-brain"


def _TMP_LINE() -> str:
    """하드코딩 /tmp 런타임 경로 형태(`= "<경로>"`) — tempfile 을 써야 해요."""
    return 'STATE_DIR = "/t' + 'mp/brain_state"'


def _EXT_URL() -> str:
    """비-localhost 유료 API URL 형태 — dormant 다운로더 밖이면 안 돼요."""
    return "ht" + "tps://api.ope" + "nai.com/v1/chat"


# ── 변이 목록 ─────────────────────────────────────────────────────────────
MUTATIONS: List[Mutation] = [
    # ═══ 구조 게이트 (test_audit_structural.py) ═══
    Mutation("M1", "결함① 바이트 레지스터 오투영 (bl→rbp·dl→rdi, 침묵 오답)",
             "brain_engine/x86_cf_emu.py",
             '_ALIASES[_core + "l"] = (_b, 8)',
             '_ALIASES[_core[0] + "l"] = (_b, 8)',
             "참조 표"),
    Mutation("M2", "결함①′ 별칭 표 복제 (한쪽만 고치면 갈라짐)",
             "brain_engine/craft_engine.py",
             "_ALIASES = x86_cf_emu._ALIASES",
             "_ALIASES = dict(x86_cf_emu._ALIASES)",
             "동일 객체"),
    Mutation("M3", "결함② 절단된 스트림의 침묵 완주 (trunc:no-ret 제거)",
             "brain_engine/x86_cf_emu.py",
             'unsupported.append("trunc:no-ret")',
             "pass",
             "절단"),
    Mutation("M4a", "결함④ `_W.__mul__`/`__rmul__` 제거 (*/가 전부 TypeError)",
             "brain_engine/craft_engine.py",
             "    def __mul__(self, o): return self._n(self._sv() * self._o(o))\n"
             "    __rmul__ = __mul__\n",
             "",
             "던더"),
    Mutation("M4b", "결함④ `__mul__` 을 덧셈으로 — **침묵 오답** (게이트 구멍이었음)",
             "brain_engine/craft_engine.py",
             "def __mul__(self, o): return self._n(self._sv() * self._o(o))",
             "def __mul__(self, o): return self._n(self._sv() + self._o(o))",
             "독립 참조와 일치"),
    Mutation("M5", "결함⑤ 익명 슬라이스 캡 [:24] (잘림이 데이터에 안 드러남)",
             "tools/ghidra_facts_pyghidra.py",
             'dec = "\\n".join(dlines[:_DEC_LINE_CAP])',
             'dec = "\\n".join(dlines[:24])',
             "익명 슬라이스"),
    Mutation("M6", "결함⑨ 고정 프로젝트 캐시 경로 (침묵 staleness)",
             "tools/ghidra_facts_pyghidra.py",
             '_proj = os.path.join(tempfile.gettempdir(), facts["project_key"])',
             '_proj = os.path.join(tempfile.gettempdir(), "ghidra_pyproj")',
             "캐시 키"),
    Mutation("M7", "결함⑥ 일본어 가나 오염 주입",
             "vault/20_Skills/skill_craft_muldiv_n4.md",
             "정직 게이트", _KANA(),
             "가나"),
    Mutation("M8", "결함⑥ 문서 staleness — 지원하는데 미기재 (cdq 삭제)",
             "brain_engine/x86_cf_emu.py",
             "`cdq`/`cqo`/`cwd`", "`cqo`/`cwd`",
             "문서 기재|문서에 기재"),
    Mutation("M9", "C truncation 파괴 — 파이썬 바닥 나눗셈으로 (-7/3=-3)",
             "brain_engine/c_synthesize.py",
             "q = abs(a) // abs(b)",
             "q = a // b",
             "독립 참조와 일치|_tdiv|truncation"),
    Mutation("M10", "부호 유추를 항상 signed 로 (unsigned 오분류, 게이트 구멍이었음)",
             "brain_engine/craft_engine.py",
             "return not bool(_UNSIGNED_TY.search(m.group(1)))\n    # 표현식 안의 캐스트",
             "return True\n    # 표현식 안의 캐스트",
             "_c_signedness"),
    Mutation("M11", "포르투갈어 주입 (라틴 다이어크리틱)",
             "vault/20_Skills/skill_audit_invariants_mutation.md",
             "절대값 불변식은 표류해요",
             _PT(),
             "다이어크리틱"),
    Mutation("M12", "프랑스어 주입 (라틴 다이어크리틱)",
             "vault/20_Skills/skill_audit_invariants_mutation.md",
             "## 🧪 변이 테스트 — 게이트를 검증하는 게이트",
             _FR(),
             "다이어크리틱"),
    Mutation("M13", "완전성 플래그 제거 (캡 잘림이 데이터에 안 남음)",
             "tools/ghidra_facts_pyghidra.py",
             '                "insns_complete": guard < _INSN_CAP,\n'
             '                "decompile_truncated": dec_trunc,\n',
             "",
             "insns_complete|decompile_truncated"),
    Mutation("M14", "익명 guard 캡 (`guard < 16` — 결함③의 실제 원인)",
             "tools/ghidra_facts_pyghidra.py",
             "guard < _INSN_CAP:",
             "guard < 16:",
             "guard"),
    Mutation("M15", "기록 정직성 완화 (100% 가 아니어도 vault 에 기록)",
             "brain_engine/craft_engine.py",
             'if c["match_pct"] != 100.0:',
             'if c["match_pct"] < 99.0:',
             "기록"),
    Mutation("M16", "문서의 **거짓 주장** — 미지원 cmovl 을 지원한다고 기재",
             "brain_engine/x86_cf_emu.py",
             "· **imul**(2-operand)",
             "· **imul**(2-operand) · **cmovl**",
             "거짓 주장"),
    Mutation("M17", "`_reg_info` 재인라인 — **동작은 같지만** 단일 출처가 깨짐(구멍이었음)",
             "brain_engine/craft_engine.py",
             "_reg_info = x86_cf_emu.reg_info",
             'def _reg_info(name: str):\n'
             '    """이름 → (base, shift, width). x86_cf_emu.reg_info 와 단일 출처예요."""\n'
             "    hit = _ALIASES.get(name.strip().lower())\n"
             "    if not hit:\n"
             "        return None\n"
             "    _b, _w = hit\n"
             '    return (_b, 8, 8) if name.strip().lower() in ("ah", "bh", "ch", "dh") '
             "else (_b, 0, _w)",
             "동일 객체"),
    Mutation("M18", "문서 staleness — adc/sbb 미기재 (실제로 지원됨)",
             "brain_engine/x86_cf_emu.py",
             "add/sub/adc/sbb/", "add/sub/",
             "문서에 기재|문서 기재"),
    Mutation("M19", "C truncation 나눗셈 **복제 부활** (_div 를 다시 인라인으로)",
             "brain_engine/craft_engine.py",
             "            return self._n(c_synthesize._tmod(a, b) if mod\n"
             "                           else c_synthesize._tdiv(a, b))",
             "            q = abs(a) // abs(b)\n"
             "            if (a < 0) != (b < 0):\n"
             "                q = -q\n"
             "            return self._n(a - q * b if mod else q)",
             "실제 호출"),

    # ═══ N4 게이트 (test_n4_muldiv.py) ═══
    Mutation("N4-1", "C 나머지 → 파이썬 `%`(음수에서 부호 틀림)",
             "brain_engine/c_synthesize.py",
             "return a - _tdiv(a, b) * b",
             "return a % b",
             "truncation|절삭|ground|native|일치", "N4"),
    Mutation("N4-2", "C 나눗셈 부호 규칙 제거 (항상 양의 몫)",
             "brain_engine/c_synthesize.py",
             "return q if (a < 0) == (b < 0) else -q",
             "return q",
             "truncation|절삭|ground|native|일치", "N4"),
    Mutation("N4-3", "LLP64 혼동 — `long` 폭을 32 로 (Linux LP64 는 64)",
             "brain_engine/c_synthesize.py",
             '"long": 64, "ulong": 64,',
             '"long": 32, "ulong": 32,',
             "폭|width|long|ground|native|일치", "N4"),
    Mutation("N4-4", "#DE 몫 오버플로 정직 bail 제거 (좁은 폭에서 침묵 오답)",
             "brain_engine/x86_cf_emu.py",
             "if q >= (1 << (w - 1)) or q < -(1 << (w - 1)):",
             "if False:",
             "div|오버플로|of|honesty|정직", "N4"),
    Mutation("N4-5", "**게이트 픽스처 오염** — magic reciprocal 상수 1 깨짐",
             "tools/test_n4_muldiv.py",
             "0x55555556",
             "0x55555557",
             "oracle|native|ground|일치", "N4"),

    # ═══ N3 게이트 (test_n3_craft.py) ═══
    Mutation("N3-1", "LLM 소스 검증에서 import 금지 해제 (임의 모듈 실행 허용)",
             "brain_engine/slm_bridge.py",
             "        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):\n"
             "            return False",
             "        if isinstance(node, (ast.Global, ast.Nonlocal)):\n"
             "            return False",
             "safe_synth|안전|import|검증", "N3"),
    Mutation("N3-2", "코드펜스 추출 파괴 (LLM 응답에서 소스를 못 찾음)",
             "brain_engine/slm_bridge.py",
             '    m = _CODE_FENCE.search(reply or "")',
             "    m = None",
             "펜스|추출|fallback|grounded|safe", "N3"),

    # ═══ SLM 온라인 게이트 (test_n3_slm_online.py) ═══
    Mutation("SLM-1", "**환각 통과** — 안전/형식 검증 없이 LLM 출력 수용",
             "brain_engine/slm_bridge.py",
             "if safe_synth_source(src):",
             "if src:",
             "환각|검증|safe|거부|reject", "SLM"),

    # ═══ quest 게이트 (test_quest_resilience.py) ═══
    Mutation("Q-1", "훼손 원장을 격리하지 않고 **파기** (증거 소실)",
             "brain_engine/quest_ledger.py",
             "os.replace(self.path, dest)",
             "self.path.unlink()",
             "격리|quarantine|corrupt", "quest"),
    Mutation("Q-2", "크래시가 남긴 orphan tmp 방치 (kill -9 흔적 누적)",
             "brain_engine/quest_ledger.py",
             "self.tmp.unlink()",
             "pass",
             "orphan|tmp", "quest"),
    Mutation("Q-3", "저장 실패를 **침묵** (SaveError 를 삼킴 = 정직 위반)",
             "brain_engine/quest_ledger.py",
             "raise SaveError(self.last_save_error) from exc",
             "pass",
             "SaveError|저장|disk|실패|표면", "quest"),

    # ═══ Windows 부트스트랩 게이트 (verify_windows_bootstrap.py) ═══
    Mutation("W-1", "오프라인 설치 해제 — `--no-index` 제거(인터넷 의존)",
             "tools/fetch_ghidra_dist.ps1",
             "& $VenvPip install -q --no-index --find-links $Vendor jdk4py pyghidra jpype1 2>$null",
             "& $VenvPip install -q --find-links $Vendor jdk4py pyghidra jpype1 2>$null",
             "no-index|오프라인|offline", "win"),

    Mutation("W-2", "**실제 사고 재현** — pipefail + `grep -q` 로 수리 조건 되돌리기",
             "tools/fetch_ghidra_dist.sh",
             '_LDD_OUT="$(ldd "$DECOMP" 2>&1 || true)"\n'
             "_NEEDS_REBUILD=0\n"
             'if [ -x "$DECOMP" ]; then\n'
             '  case "$_LDD_OUT" in *"not found"*) _NEEDS_REBUILD=1 ;; esac\n'
             "fi\n"
             'if [ "$_NEEDS_REBUILD" = 1 ]; then',
             'if [ -x "$DECOMP" ] && ldd "$DECOMP" 2>&1 | grep -q "not found"; then',
             "grep -q|SIGPIPE|파이프", "win"),

    # ═══ 두뇌 자가감사 게이트 (audit_brain.py) ═══
    Mutation("A-1", "개인정보 — 하드 시크릿(토큰 형태) 유출",
             "brain_engine/craft_engine.py",
             "from brain_engine import re_analyzer",
             "from brain_engine import re_analyzer  # key: " + _FAKE_TOKEN(),
             "시크릿|secret", "audit"),
    Mutation("A-2", "이식성 — 샌드박스 홈 절대경로 하드코딩",
             "brain_engine/craft_engine.py",
             "from brain_engine import re_analyzer",
             'from brain_engine import re_analyzer  # ROOT = "' + _HOME_PATH() + '"',
             "홈경로|절대경로|home", "audit"),
    Mutation("A-3", "이식성 — 하드코딩 /tmp 런타임 경로 (tempfile 미사용)",
             "brain_engine/craft_engine.py",
             "from brain_engine import re_analyzer",
             "from brain_engine import re_analyzer\n" + _TMP_LINE(),
             "/tmp|런타임 경로|이식성", "audit"),
    Mutation("A-4", "정직 — 환각 방어 자기기술 문구 삭제",
             "brain_engine/slm_bridge.py",
             "지어내는 대신",
             "만드는 대신",
             "환각|정직|honesty", "audit"),
    Mutation("A-6", "정직 — 좀비 대신 `failed` 기록 계약을 `done` 으로 위조",
             "brain_engine/quest_ledger.py",
             'self.complete(qid, proof={"error": error}, status="failed")',
             'self.complete(qid, proof={"error": error}, status="done")',
             "failed|정직|quest", "audit"),
    Mutation("A-5", "무료 — dormant 다운로더 밖의 비-localhost 유료 API URL",
             "brain_engine/craft_engine.py",
             "from brain_engine import re_analyzer",
             'from brain_engine import re_analyzer  # fallback: "' + _EXT_URL() + '"',
             "비-localhost|URL|무료|huggingface", "audit"),
]

# ── 복원 안전망 ───────────────────────────────────────────────────────────
_live: Dict[Path, bytes] = {}


def _restore_all() -> None:
    for path, data in list(_live.items()):
        try:
            if path.read_bytes() != data:
                path.write_bytes(data)
        except Exception:                                    # noqa: BLE001
            pass
    _live.clear()


atexit.register(_restore_all)


def _run_gate(script: str) -> Tuple[int, str, str]:
    """게이트를 **바이트코드 캐시가 격리된** 상태로 돌려요.

    왜(실측으로 확인한 함정): 파이썬의 .pyc 무효화 기준은 `mtime(초 단위) + 파일
    크기` 예요. 그래서 **크기가 같은 변이**(예: `*` → `+`)를 되돌리는 것이 같은 초
    안에 일어나면, 캐시가 "변경 없음"으로 판단되어 **복원된 소스가 아니라 변이된
    바이트코드가 실행**돼요 — 14/14 재현했어요. 그러면 복원 뒤에도 이전 변이가
    살아 있어서 판정이 양방향으로 오염돼요(없던 검출이 생기기도, 있던 검출이
    사라지기도 해요). `PYTHONPYCACHEPREFIX` 를 실행마다 **새** 임시 디렉터리로
    주면 읽어올 캐시가 없으므로 매번 소스에서 컴파일해요.
    """
    cache = tempfile.mkdtemp(prefix="mut_pyc_")
    try:
        env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
        cp = subprocess.run([sys.executable, str(HERE / script)], capture_output=True,
                            text=True, cwd=str(ROOT), timeout=900, env=env)
        return cp.returncode, cp.stdout, cp.stderr
    finally:
        shutil.rmtree(cache, ignore_errors=True)


def _behavior_probe() -> List[str]:
    """복원이 **소스만이 아니라 실행 결과로도** 맞는지 확인해요.

    sha256 은 디스크 바이트만 봐요. 바이트코드 캐시 오염은 그걸 통과하면서도
    잘못된 동작을 남길 수 있으므로(위 `_run_gate` 참조), 알려진 정답 몇 개를
    새 프로세스에서 실제로 계산해 대조해요.
    """
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from brain_engine import craft_engine as C;"
        "from brain_engine import c_synthesize as S;"
        "from brain_engine import x86_cf_emu as E;"
        "print(C._W(7, 32, True).__mul__(C._W(3, 32, True)).v,"
        " S._tdiv(-7, 3), S._tmod(-7, 3),"
        " E.reg_info('bl'), C._reg_info is E.reg_info,"
        " C._ALIASES is E._ALIASES)"
    )
    cache = tempfile.mkdtemp(prefix="mut_probe_")
    try:
        env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
        cp = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            text=True, cwd=str(ROOT), timeout=120, env=env)
    finally:
        shutil.rmtree(cache, ignore_errors=True)
    got = cp.stdout.strip()
    want = "21 -2 -1 ('rbx', 0, 8) True True"   # print 는 공백 구분이에요
    return [] if got == want else [f"행동 프로브 got={got or cp.stderr.strip()[-80:]} want={want}"]


def _classify(rc: int, out: str, expect: str) -> Tuple[str, List[str], bool]:
    """(판정, 실패한 검사 라벨들, 기대한 검사로 잡혔는지)."""
    fails = [m.group(1).strip() for m in re.finditer(r"❌ (.+)", out)]
    fails = [f for f in fails if "FAILED" not in f and "예외:" not in f]
    if rc == 0:
        return "MISSED", fails, False
    if not fails:
        return "CRASHED", fails, False
    alts = [a.strip() for a in expect.split("|") if a.strip()]
    return "CAUGHT", fails, any(a in f for f in fails for a in alts)


def main() -> int:
    verbose = bool(os.environ.get("MUT_VERBOSE"))
    print("🧪 변이 스위트 — 게이트가 원래 결함을 정말로 잡는지 재검증\n")

    used = sorted({m.gate for m in MUTATIONS}, key=list(GATES).index)
    missing = [s for g in used for s in (GATES[g],) if not (HERE / s).exists()]
    if missing:
        print(f"  ❌ 게이트 스크립트가 없어요: {', '.join(missing)}")
        return 1

    # ── 베이스라인: 사용할 게이트 전부가 변이 없이 그린이어야 판정이 의미 있어요 ──
    print("  [베이스라인] 변이 없이 게이트 전부를 먼저 돌려요")
    base_bad: List[str] = []
    for g in used:
        rc, out, err = _run_gate(GATES[g])
        tail = re.search(r"(\d+ passed / \d+ failed|\d+/\d+ 통과)", out)
        mark = "✅" if rc == 0 else "❌"
        print(f"    {mark} {g:<6} {GATES[g]:<28} {tail.group(0) if tail else f'rc={rc}'}")
        if rc != 0:
            base_bad.append(g)
    if base_bad:
        print("\n  ❌ 베이스라인이 이미 실패 — 변이 판정이 무의미하므로 중단해요")
        print(f"     먼저 그린으로 만드세요: {', '.join(base_bad)}")
        return 1
    print(f"\n  변이 {len(MUTATIONS)}종을 시작해요 "
          f"(게이트 {len(used)}개: {', '.join(used)})\n")

    counts = {"CAUGHT": 0, "MISSED": 0, "CRASHED": 0, "ANCHOR": 0}
    wrongreason: List[str] = []
    cur_gate = None
    for mut in MUTATIONS:
        if mut.gate != cur_gate:
            cur_gate = mut.gate
            print(f"  ── 게이트: {cur_gate} ({GATES[cur_gate]}) "
                  f"── {sum(1 for m in MUTATIONS if m.gate == cur_gate)}종")
        path = ROOT / mut.path
        if not path.exists():
            print(f"    {mut.mid:<6} ⚠️ ANCHOR   {mut.defect[:58]}  (파일 없음)")
            counts["ANCHOR"] += 1
            continue
        orig = path.read_bytes()
        sha = hashlib.sha256(orig).hexdigest()
        text = orig.decode("utf-8")
        n = text.count(mut.old)
        if n != 1:
            print(f"    {mut.mid:<6} ⚠️ ANCHOR   {mut.defect[:52]}  "
                  f"(앵커 {n}건, 기대 1건 — 리팩토링으로 어긋남)")
            counts["ANCHOR"] += 1
            continue
        _live[path] = orig
        try:
            path.write_text(text.replace(mut.old, mut.new, 1), encoding="utf-8")
            rc, out, err = _run_gate(GATES[mut.gate])
            verdict, fails, right = _classify(rc, out, mut.expect)
        finally:
            path.write_bytes(orig)
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                print(f"    {mut.mid:<6} 💥 복원 실패 — {mut.path} 를 확인하세요!")
                _restore_all()
                return 1
            _live.pop(path, None)

        if verdict == "CAUGHT":
            counts["CAUGHT"] += 1
            tag = "🟢 CAUGHT " if right else "🟠 딴 이유"
            if not right:
                wrongreason.append(mut.mid)
        else:
            counts[verdict] += 1
            tag = {"MISSED": "🔴 MISSED ", "CRASHED": "🟡 CRASHED"}[verdict]
        print(f"    {mut.mid:<6} {tag}  {mut.defect[:66]}")
        if verbose or verdict != "CAUGHT" or not right:
            detail = "; ".join(f[:64] for f in fails[:3]) or (err.strip()[-80:] or "-")
            print(f"           → 기대 `{mut.expect.split('|')[0]}` · 실제: {detail}")

    # ── 트리가 원상복구됐음을 게이트 전부 재실행으로 증명 ──
    _restore_all()
    print("\n  [복원 검증] 게이트 전부를 다시 돌려요")
    restore_bad: List[str] = _behavior_probe()
    for m in restore_bad:
        print(f"    ❌ {m}")
    if not restore_bad:
        print("    ✅ 행동 프로브: _W(7)*_W(3)=21 · _tdiv(-7,3)=-2 · _tmod(-7,3)=-1 ·"
              " bl→rbx · 동일 객체 2건")
    for g in used:
        rc, _o, _e = _run_gate(GATES[g])
        if rc != 0:
            restore_bad.append(g)
        print(f"    {'✅' if rc == 0 else '❌'} {g:<6} {GATES[g]}")

    total = len(MUTATIONS)
    print("\n  " + "=" * 78)
    print(f"  판정: 🟢 CAUGHT {counts['CAUGHT']} · 🔴 MISSED {counts['MISSED']} · "
          f"🟡 CRASHED {counts['CRASHED']} · ⚠️ ANCHOR {counts['ANCHOR']} / {total}종")
    per_gate: Dict[str, List[str]] = {}
    for m in MUTATIONS:
        per_gate.setdefault(m.gate, []).append(m.mid)
    for g, ids in per_gate.items():
        print(f"    · {g:<6} {len(ids):>2}종 ({ids[0]}~{ids[-1]})")
    if wrongreason:
        print(f"  🟠 딴 이유 {len(wrongreason)}종: {', '.join(wrongreason)}")
    print("=" * 78)
    bad = counts["MISSED"] + counts["CRASHED"] + counts["ANCHOR"] + len(wrongreason)
    bad += len(restore_bad)
    if bad:
        print(f"❌ MUTATION SUITE FAILED — {total - bad}/{total} 만 올바르게 검출")
        if counts["MISSED"]:
            print(f"   🔴 MISSED {counts['MISSED']}종: 이 결함들이 다시 살아도 게이트가 "
                  f"몰라요 → 검사를 추가하세요(게이트 구멍).")
        if counts["CRASHED"]:
            print(f"   🟡 CRASHED {counts['CRASHED']}종: 검사가 아니라 예외로 깨진 것 "
                  f"→ 게이트를 고치세요.")
        if counts["ANCHOR"]:
            print(f"   ⚠️ ANCHOR {counts['ANCHOR']}종: 앵커가 어긋남 → MUTATIONS 의 old 를 "
                  f"현재 코드에 맞게 갱신하세요(커버리지가 사라지기 전에).")
        if wrongreason:
            print(f"   🟠 딴 이유 {len(wrongreason)}종: 실패하긴 했지만 기대한 검사가 "
                  f"아니에요 → 우연히 잡힌 것일 수 있어요.")
        if restore_bad:
            print(f"   💥 복원 실패: {', '.join(restore_bad)} — 트리가 오염됐어요!")
        return 1
    print(f"✅ MUTATION SUITE PASSED — 변이 {total}종 전부 **기대한 검사로** 검출")
    print(f"   게이트 {len(used)}개 전부의 자기효능이 매 실행마다 재측정돼요.")
    print("   게이트를 고치거나 검사를 약화시키면 여기서 드러나요.")
    print("   정직 범위: live Ghidra 게이트 2종(verify_gather_flags·verify_ghidra_facts)은")
    print("   rc=3 정직 skip 이라 변이 판정이 불가 → 대상에서 제외(미측정).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
