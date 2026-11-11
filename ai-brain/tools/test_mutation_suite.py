#!/usr/bin/env python3
"""🧪 변이 스위트 — 불변식 게이트가 원래 결함을 **정말로** 잡는지 기계 재검증해요.

왜 존재하나
    `tools/test_audit_structural.py`(불변식 게이트)는 v7.3.9 에서 만들었어요. 그런데
    **통과하는 게이트는 아무 정보가 없어요.** 원래 결함을 되살렸을 때 정말로
    빨개지는지 확인하지 않으면, 그 게이트가 무엇을 막는지 아무도 보증할 수 없죠.

    실제로 이 검증을 수동으로 돌렸을 때 **새 게이트의 구멍 2개**가 드러났어요:
      · M4b — `__mul__` 을 덧셈으로 바꾼 *침묵 오답* 을 못 잡았어요
              (던더 *존재*만 확인하고 *정확성*은 확인하지 않았음)
      · M10 — 부호 유추를 항상 signed 로 바꿔도 못 잡았어요
              (`_c_signedness` 를 아예 검사하지 않았음)
    둘 다 "게이트는 그린인데 결과는 틀린" 상태였어요. 검사를 추가한 뒤에야 잡혔죠.
    그래서 이 스위트를 **커밋**해요 — 게이트를 고칠 때마다 자동으로 재검증되게.

세 가지 판정 (rc!=0 이면 다 잡은 게 아니에요)
    🟢 CAUGHT   — 게이트가 실패하고, **기대한 그 검사**가 실패 목록에 있어요
    🔴 MISSED   — 게이트가 통과했어요 → **그 결함이 다시 살아도 아무도 모름**
    🟡 CRASHED  — 게이트가 실패하긴 했는데 `❌` 검사 실패가 하나도 없어요
                  → 검사가 잡은 게 아니라 import/예외로 깨진 것(수동 실행 때
                    실제로 겪었어요: `__mul__` 만 지우면 다음 줄 `__rmul__ = __mul__`
                    가 NameError 로 모듈 import 자체가 실패해서 rc=1 이 나왔어요.
                    그건 "결함을 잡은" 게 아니라 "게이트가 부러진" 거예요.)
    ⚠️ ANCHOR   — 변이 앵커 문자열이 파일에 정확히 1번 없어요 → 리팩토링으로
                  앵커가 어긋난 것. **조용히 skip 하지 않고 실패로 보고**해요
                  (skip 하면 커버리지가 소리 없이 사라지므로).
                  실제로 이 스위트가 자기 문서를 고친 직후 M11 앵커가 2건이 되어
                  ANCHOR 를 냈어요 — 산문 앵커는 글을 고칠 때마다 drift 해요.
                  이 판정이 있으니 drift 가 소리 없이 커버리지를 깎지 못해요.

안전장치
    · 각 파일은 변이 전 바이트와 sha256 을 기억하고 `finally` 에서 복원한 뒤
      sha256 으로 **복원을 검증**해요.
    · 프로세스가 죽어도 복원되도록 `atexit` 안전망을 걸어요.
    · 시작 전에 **베이스라인**(변이 없이) 게이트가 통과하는지 확인해요 — 베이스라인이
      이미 실패라면 모든 판정이 무의미하므로 즉시 중단해요.
    · 마지막에 게이트를 다시 돌려 트리가 원상복구됐음을 증명해요.

정직 원칙: 이 스위트는 "게이트가 결함을 잡는다"고 **주장**하지 않고, 매 실행마다
되살려서 **측정**해요. 잡지 못하는 변이가 하나라도 있으면 exit 1 이에요.
"""
from __future__ import annotations

import atexit
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATE = HERE / "test_audit_structural.py"


class Mutation(NamedTuple):
    mid: str            # M1, M2 …
    defect: str         # 되살리는 결함 설명
    path: str           # ROOT 상대 경로
    old: str            # 원래 문자열 (파일에 **정확히 1번** 있어야 해요)
    new: str            # 결함을 되살린 문자열
    expect: str         # 실패해야 하는 검사의 라벨 일부 (`|` 로 여러 후보 허용)
                        # → **맞는 이유**로 잡혔는지 확인해요(우연히 빨개진 것과 구분)


# ── 오염 샘플 생성기 ──────────────────────────────────────────────────────
# 게이트의 [5] 문자 오염 검사는 **이 파일도 스캔**해요(스캔 대상에 tools/ 포함).
# 그래서 오염 샘플을 리터럴로 적으면 게이트가 자기 스위트를 잡아서 베이스라인이
# 실패해요 — 실제로 겪었어요. 샘플은 코드포인트로 **조립**해서 만들고, 이 소스에는
# 한글·ASCII 밖의 외국어 문자를 두지 않아요(설명도 코드포인트로 서술).
def _KANA() -> str:
    """일본어 가나: '정직 게이트' 뒤 한글 '이트' 를 가타카나 3자(U+30B2 U+30A4 U+30C8)로 대체."""
    return "정직 게" + "".join(chr(c) for c in (0x30B2, 0x30A4, 0x30C8))


def _PT() -> str:
    """포르투갈어풍: 라틴 다이어크리틱(세디유 U+00E7, 물결 a U+00E3) 주입."""
    return ("절대값 불변식은 표류해요(verifica" + chr(0xE7) + chr(0xE3) + "o)")


def _FR() -> str:
    """프랑스어풍: 라틴 다이어크리틱(에그위트 U+00E9) 주입 — 헤딩 앵커 보존."""
    return ("## \U0001F9EA 변이 v" + chr(0xE9) + "rification — 게이트를 검증하는 게이트")


# ── 변이 목록 ─────────────────────────────────────────────────────────────
# v7.3.8 감사에서 실제 발견된 결함과, 그 결함을 만든 **원인 패턴**을 되살려요.
MUTATIONS: List[Mutation] = [
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
    Mutation("M6", "결함⑧ 고정 프로젝트 캐시 경로 (침묵 staleness)",
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
             "brain_engine/craft_engine.py",
             "q = abs(a) // abs(b)",
             "q = a // b",
             "_tdiv"),
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
    Mutation("M18", "문서 staleness — adc/sbb 미기재 (강화 검사로 실제로 찾았던 것)",
             "brain_engine/x86_cf_emu.py",
             "add/sub/adc/sbb/", "add/sub/",
             "문서에 기재"),
]

# ── 복원 안전망 ───────────────────────────────────────────────────────────
_live: Dict[Path, bytes] = {}


def _restore_all() -> None:
    for path, data in list(_live.items()):
        try:
            if path.read_bytes() != data:
                path.write_bytes(data)
        except Exception:                              # noqa: BLE001
            pass
    _live.clear()


atexit.register(_restore_all)


def _run_gate() -> Tuple[int, str, str]:
    cp = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True,
                        cwd=str(ROOT), timeout=600)
    return cp.returncode, cp.stdout, cp.stderr


def _classify(rc: int, out: str, err: str, expect: str) -> Tuple[str, List[str], bool]:
    """(판정, 실패한 검사 라벨들, 기대한 검사가 그중에 있었는지)."""
    fails = [m.group(1).strip() for m in re.finditer(r"❌ (.+)", out)]
    fails = [f for f in fails if "FAILED —" not in f and "예외:" not in f]
    if rc == 0:
        return "MISSED", fails, False
    if not fails:
        return "CRASHED", fails, False
    alts = [a.strip() for a in expect.split("|") if a.strip()]
    return "CAUGHT", fails, any(a in f for f in fails for a in alts)


def main() -> int:
    print("🧪 변이 스위트 — 불변식 게이트가 원래 결함을 정말로 잡는지 재검증\n")
    if not GATE.exists():
        print(f"  ❌ 게이트가 없어요: {GATE.name}")
        return 1

    # ── 베이스라인: 변이 없이 게이트가 통과해야 모든 판정이 의미 있어요 ──
    rc, out, err = _run_gate()
    base = re.search(r"(\d+) passed / (\d+) failed", out)
    if rc != 0:
        print("  ❌ 베이스라인이 이미 실패 — 변이 판정이 무의미하므로 중단해요")
        print("     먼저 test_audit_structural.py 를 그린으로 만드세요.")
        for line in re.findall(r"❌ (.+)", out)[:5]:
            print(f"       · {line[:100]}")
        return 1
    print(f"  ✅ 베이스라인 그린 ({base.group(0) if base else '?'}) — "
          f"변이 {len(MUTATIONS)}종을 시작해요\n")

    caught = missed = crashed = anchored = wrongreason = 0
    rows: List[str] = []
    print(f"  {'ID':<5} {'판정':<12} {'되살린 결함'}")
    print("  " + "-" * 104)
    for mut in MUTATIONS:
        path = ROOT / mut.path
        if not path.exists():
            print(f"  {mut.mid:<5} {'⚠️ ANCHOR':<12} {mut.defect[:60]}  (파일 없음)")
            anchored += 1
            continue
        orig = path.read_bytes()
        sha = hashlib.sha256(orig).hexdigest()
        text = orig.decode("utf-8")
        n = text.count(mut.old)
        if n != 1:
            # 조용히 skip 하면 커버리지가 소리 없이 사라져요 → **실패로 보고**
            print(f"  {mut.mid:<5} {'⚠️ ANCHOR':<12} {mut.defect[:56]}  "
                  f"(앵커 {n}건, 기대 1건 — 리팩토링으로 어긋남)")
            anchored += 1
            continue
        _live[path] = orig
        try:
            path.write_text(text.replace(mut.old, mut.new, 1), encoding="utf-8")
            rc, out, err = _run_gate()
            verdict, fails, right = _classify(rc, out, err, mut.expect)
        finally:
            path.write_bytes(orig)
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                print(f"  {mut.mid:<5} 💥 복원 실패 — {mut.path} 를 확인하세요!")
                _restore_all()
                return 1
            _live.pop(path, None)

        if verdict == "CAUGHT":
            caught += 1
            if not right:
                wrongreason += 1
                tag = "🟠 딴 이유"
            else:
                tag = "🟢 CAUGHT"
        elif verdict == "MISSED":
            missed += 1
            tag = "🔴 MISSED"
        else:
            crashed += 1
            tag = "🟡 CRASHED"
        print(f"  {mut.mid:<5} {tag:<12} {mut.defect[:76]}")
        if verdict != "CAUGHT" or not right:
            detail = "; ".join(f[:70] for f in fails[:2]) or (err.strip()[-90:] or "-")
            print(f"        → 기대 검사 `{mut.expect}` · 실제: {detail}")
        rows.append(f"{mut.mid}={verdict}{'' if right or verdict != 'CAUGHT' else '(딴이유)'}")

    # ── 트리가 원상복구됐음을 게이트 재실행으로 증명 ──
    _restore_all()
    rc, out, _e = _run_gate()
    print("  " + "-" * 104)
    print(f"  복원 후 게이트 재실행: {'✅ 그린(트리 원상복구 증명)' if rc == 0 else '❌ 여전히 실패'}")

    total = len(MUTATIONS)
    print(f"\n  판정: 🟢 CAUGHT {caught} · 🔴 MISSED {missed} · 🟡 CRASHED {crashed} "
          f"· ⚠️ ANCHOR {anchored} / {total}종")
    print(f"        ({', '.join(rows)})")
    print("=" * 72)
    bad = missed + crashed + anchored + wrongreason + (0 if rc == 0 else 1)
    if bad:
        print(f"❌ MUTATION SUITE FAILED — {total - bad}/{total} 만 올바르게 검출")
        if missed:
            print(f"   🔴 MISSED {missed}종: 이 결함들이 다시 살아도 게이트가 몰라요 "
                  f"→ 검사를 추가하세요.")
        if crashed:
            print(f"   🟡 CRASHED {crashed}종: 검사가 아니라 예외로 깨진 것 "
                  f"→ 게이트를 고치세요.")
        if anchored:
            print(f"   ⚠️ ANCHOR {anchored}종: 앵커 문자열이 어긋남 "
                  f"→ MUTATIONS 의 old 를 현재 코드에 맞게 갱신하세요.")
        if wrongreason:
            print(f"   🟠 딴 이유 {wrongreason}종: 실패하긴 했지만 기대한 검사가 아니에요 "
                  f"→ 우연히 잡힌 것일 수 있어요.")
        return 1
    print(f"✅ MUTATION SUITE PASSED — 변이 {total}종 전부 **기대한 검사로** 검출")
    print("   게이트가 그린인 이유가 우연이 아니라는 것이 매 실행마다 재측정돼요.")
    print("   게이트를 고칠 때 이 스위트가 같이 돌므로, 검사를 약화시키면 여기서 드러나요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
