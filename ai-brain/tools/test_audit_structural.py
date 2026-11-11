"""🩺 구조 감사 게이트 — 결함의 **종류**를 기계적으로 막아요 (v7.3.8 감사의 자동화).

왜 존재하나
    N4 감사(v7.3.8)에서 결함 7종을 찾았어요. 그런데 그중 ①②④⑥ 은 **패턴 검사로
    미리 잡을 수 있었던** 것들이에요. 기존 게이트(test_n3_craft·test_n4_muldiv·…)는
    "이 함수들이 맞게 craft 되는가"라는 **기능**만 봤고, "구조가 이런 실수를 허용하는가"
    는 보지 않았어요. 그래서 게이트 6개가 전부 그린인데도 침묵 오답이 살아 있었죠.
    이 게이트는 기능이 아니라 **불변식(invariant)** 을 검사해요.

검사하는 불변식
  1) 레지스터 모델 **단일 출처** — 별칭 표가 두 벌이면 같은 결함이 두 곳에 생겨요
     (실제로 그랬음). 객체 동일성(`is`) + 소스에서 중복 구성 금지 + x86 아키텍처
     명명 규칙으로 **독립적으로** 만든 참조 표와 전수 대조.
  2) **절단 = 침묵 완주 금지** — 알려진 모든 픽스처 함수를 *모든* 절단점에서 잘라
     `unsupported` 가 비어 있으면 안 돼요(한 함수의 끝 몇 개만 보던 것을 일반화).
  3) **캡은 흔적을 남긴다** — 채집기의 모든 한도는 이름있는 상수여야 하고, 잘림
     여부를 말하는 플래그가 레코드에 있어야 해요. 익명 숫자 캡(`[:24]`·`guard < 16`)
     은 금지.
  4) **문서-코드 일치(행동 기반)** — 독스트링이 주장하는 명령은 실제로 `unsupported`
     없이 실행돼야 하고(거짓 주장 금지), 픽스처에서 실제로 깨끗이 실행되는 명령은
     독스트링에 기재돼 있어야 해요(staleness 금지). 텍스트 대조가 아니라 **실행**으로.
  5) **문자 오염** — 한글 산문·주석에 일본어 가나, 또는 한글을 **대체**한 한자가
     있으면 안 돼요. 단 정당한 국어 한자 병기(`무패(無敗)`)는 허용.
  6) **두 oracle 경로 일관성** — 직선경로 `_W` 와 cf경로 `_tdiv`/`_tmod`, 그리고
     **게이트가 독립 유도체 참조**가 삼방으로 같은 C truncation semantics 여야 하고,
     `_W` 가 산술 던더를 **갖고 있어야** 해요(하나라도 사라지면 결함④ 재발).
     참조를 `SYN._tdiv` 호출로 쓰면 위임 리팩토링 후 tautology 가 돼요(변이 M9 실측).
  7) **정직 불변식** — `record` 는 match 100% 만 저장해요(99.99% 도 안 됨).

정직 원칙: 이 게이트 자체도 짐작하지 않아요. 검사할 수 없는 것(예: live Ghidra
재채집)은 여기서 다루지 않고 `tools/verify_ghidra_facts.py` 에 맡겨요.
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from brain_engine import x86_cf_emu as EMU          # noqa: E402
from brain_engine import craft_engine as CE          # noqa: E402
from brain_engine import c_synthesize as SYN         # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, label: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ✅ {label}")
    else:
        _FAIL += 1
        print(f"  ❌ {label}" + (f"\n       → {detail}" if detail else ""))


def _load_fixture_module(name: str) -> Any:
    """형제 게이트의 픽스처를 **재사용**해요(복사하면 또 다른 복제 결함이 돼요)."""
    path = _HERE / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


# ── x86 아키텍처 명명 규칙으로 **독립적으로** 만든 참조 표 ─────────────────────
# 에뮬레이터의 표를 베끼지 않아요. 베끼면 결함① 같은 오매핑을 함께 베껴서
# 검사가 아무 의미 없어져요(Intel/AMD 의 공개 레지스터 명명 규칙에서 직접 유도).
def _reference_alias_table() -> Dict[str, Tuple[str, int, int]]:
    """이름 → (base, shift, width). shift 는 그 이름이 base 의 몇 비트째부터인지."""
    legacy = [("rax", "ax", "eax", "al", "ah"), ("rbx", "bx", "ebx", "bl", "bh"),
              ("rcx", "cx", "ecx", "cl", "ch"), ("rdx", "dx", "edx", "dl", "dh"),
              ("rsi", "si", "esi", "sil", None), ("rdi", "di", "edi", "dil", None),
              ("rbp", "bp", "ebp", "bpl", None), ("rsp", "sp", "esp", "spl", None)]
    ref: Dict[str, Tuple[str, int, int]] = {}
    for base, w16, w32, lo8, hi8 in legacy:
        ref[base] = (base, 0, 64)
        ref[w16] = (base, 0, 16)
        ref[w32] = (base, 0, 32)
        ref[lo8] = (base, 0, 8)
        if hi8:                                  # ah/bh/ch/dh 는 bits 8..15 (고바이트)
            ref[hi8] = (base, 8, 8)
    for i in range(8, 16):                       # r8..r15 는 REX 접미사 규칙
        base = f"r{i}"
        ref[base] = (base, 0, 64)
        ref[base + "d"] = (base, 0, 32)
        ref[base + "w"] = (base, 0, 16)
        ref[base + "b"] = (base, 0, 8)
    return ref


REF_ALIASES = _reference_alias_table()


def test_single_source_register_model() -> None:
    print("\n[1] 레지스터 모델 단일 출처 + 독립 참조 표 전수 대조")
    # (a) 객체 **동일성** — 값이 같은 사본도 안 돼요(한쪽만 고쳐서 갈라지므로)
    check(CE._ALIASES is EMU._ALIASES, "craft_engine._ALIASES 는 x86_cf_emu 와 동일 객체")
    check(CE._BASES is EMU._BASES, "craft_engine._BASES 는 동일 객체")
    check(CE._WIDTHS is EMU._WIDTHS, "craft_engine._WIDTHS 는 동일 객체")

    # (b) 소스 수준: x86_cf_emu 이외의 모듈이 별칭 표를 **구성**하면 안 돼요
    offenders = []
    for py in sorted((_ROOT / "brain_engine").glob("*.py")):
        if py.name == "x86_cf_emu.py":
            continue
        txt = py.read_text(encoding="utf-8")
        if re.search(r"^\s*_ALIASES\[", txt, re.M) or re.search(
                r"^\s*_BASES\s*=\s*\[", txt, re.M):
            offenders.append(py.name)
    check(not offenders, "다른 모듈이 별칭 표를 독자 구성하지 않음(복제 금지)",
          ", ".join(offenders))

    # (c) 단일 출처: `_reg_info` 는 **동일 객체**여야 해요.
    #     예전엔 "본문에 `x86_cf_emu.reg_info` 라는 글자가 있는가"로 검사했는데, 변이
    #     스위트 M17 이 그 구멍을 찾았어요 — 함수를 다시 인라인으로 펼쳐도 *독스트링*에
    #     그 이름이 남아 있으면 통과했어요. `is` 는 위조할 수 없어요.
    check(CE._reg_info is EMU.reg_info,
          "craft_engine._reg_info 는 x86_cf_emu.reg_info 와 동일 객체(재인라인 불가)")

    # (d) 독립 참조 표와 **전수** 대조 — 결함①(bl→rbp, dl→rdi, sil/dil 누락) 재발 방지
    bad: List[str] = []
    for name, (base, shift, width) in sorted(REF_ALIASES.items()):
        got = EMU.reg_info(name)
        if got != (base, shift, width):
            bad.append(f"{name}: got={got} want={(base, shift, width)}")
        got2 = CE._reg_info(name)
        if got2 != got:
            bad.append(f"{name}: 두 oracle 불일치 {got2} vs {got}")
    check(not bad, f"독립 참조 표 {len(REF_ALIASES)}개 이름 전수 일치(두 oracle 동일)",
          "; ".join(bad[:5]))

    # (e) 참조 표에 **없는** 이름을 에뮬레이터가 알아보면 그것도 결함이에요
    #     (결함①의 허위 별칭 "sl" 이 정확히 이 경우였어요)
    extra = sorted(set(EMU._ALIASES) - set(REF_ALIASES))
    check(not extra, "허위 별칭 없음(참조 표에 없는 이름을 알아보면 안 됨)",
          ", ".join(extra[:8]))

    # (f) 결함①의 **원인 패턴**이 다시 생기면 안 돼요: `_core[0] + "l"` 은
    #     rax..rdx(_i<4) 에서만 유효해요. 할당문의 **가장 가까운 상위 if** 가
    #     `_i < 4` 가드인지 들여쓰기로 확인해요(옛 결함은 `_i < 8` 아래 직행).
    src_lines = (_ROOT / "brain_engine" / "x86_cf_emu.py").read_text(
        encoding="utf-8").split("\n")
    risky: List[str] = []
    for i, line in enumerate(src_lines):
        if not re.search(r"_core\[0\]\s*\+\s*['\"]l['\"]", line):
            continue
        if line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        guard = "?"
        for j in range(i - 1, -1, -1):
            prev = src_lines[j]
            if not prev.strip() or prev.strip().startswith("#"):
                continue
            if (len(prev) - len(prev.lstrip())) < indent:
                guard = prev.strip()
                break
        if "_i < 4" not in guard:
            risky.append(f"L{i + 1} 상위 if = {guard[:40]!r}")
    check(not risky, "`_core[0]+\"l\"`(al/bl/cl/dl 전용) 은 `_i < 4` 가드 안에서만 쓰임",
          "; ".join(risky))

    # (g) C truncation 나눗셈의 단일 출처를 **행동**으로 확인해요.
    #     `_W._div` 는 `c_synthesize._tdiv`/`_tmod` 를 *실제로 호출*해야 해요.
    #     왜 텍스트가 아닌가 → M17 교훈: "본문에 그 이름이 있는가"는 독스트링
    #     언급에 속아요. 호출 계수는 이름만 적어두는 것으로 위조할 수 없어요.
    import brain_engine.c_synthesize as SYN

    hits = {"tdiv": 0, "tmod": 0}
    orig_div, orig_mod = SYN._tdiv, SYN._tmod

    def _probe_div(a: int, b: int) -> int:
        hits["tdiv"] += 1
        return orig_div(a, b)

    def _probe_mod(a: int, b: int) -> int:
        hits["tmod"] += 1
        return orig_mod(a, b)

    SYN._tdiv, SYN._tmod = _probe_div, _probe_mod
    try:
        _ = CE._W(-7, 32, True) / CE._W(3, 32, True)
        _ = CE._W(-7, 32, True) % CE._W(3, 32, True)
    finally:
        SYN._tdiv, SYN._tmod = orig_div, orig_mod   # 되돌리지 않으면 오염돼요
    check(hits["tdiv"] > 0 and hits["tmod"] > 0,
          "craft_engine 의 signed 나눗셈·나머지는 c_synthesize._tdiv/_tmod 를 실제 호출",
          f"호출 횟수 {hits} — 0 이면 로직을 다시 인라인으로 펼친 거예요(복제 부활)")


def test_truncation_never_silent() -> None:
    print("\n[2] 절단 = 침묵 완주 금지 (모든 픽스처 × 모든 절단점)")
    mods = []
    for name in ("test_n3_craft", "test_n4_muldiv"):
        try:
            mods.append((name, _load_fixture_module(name)))
        except Exception as exc:                    # noqa: BLE001
            check(False, f"{name} 픽스처 로드", f"{type(exc).__name__}: {exc}")
    total_funcs = 0
    total_cuts = 0
    silent: List[str] = []
    no_ret: List[str] = []
    for name, mod in mods:
        funcs: Dict[str, Any] = getattr(mod, "FUNCS", {})
        for fname, fx in funcs.items():
            insns = fx.get("insns") or []
            if not insns:
                continue
            total_funcs += 1
            # 전제: 완전체는 RET 로 끝나야 해요(아니면 픽스처 자체가 결함③)
            tail = insns[-1].split(":", 1)[-1].strip().lower()
            if not tail.startswith("ret"):
                no_ret.append(f"{name}:{fname}(끝={tail})")
            # **모든** 절단점에서 침묵 완주가 없는지
            for cut in range(1, len(insns)):
                total_cuts += 1
                _o, _w, uns = EMU.run(insns[:cut], 0)
                if not uns:
                    silent.append(f"{name}:{fname}[:{cut}]")
    check(not no_ret, f"픽스처 {total_funcs}개 함수 전부 RET 로 종결(결함③ 재발 방지)",
          ", ".join(no_ret[:6]))
    check(not silent,
          f"{total_cuts}개 절단 전부 정직 bail(침묵 완주 0건, 결함② 재발 방지)",
          ", ".join(silent[:6]))

    # 직선경로 oracle 도 같은 성질을 지켜야 해요(별도 에뮬레이터라 따로 검사)
    straight_silent = []
    for name, mod in mods:
        for fname, fx in getattr(mod, "FUNCS", {}).items():
            insns = fx.get("insns") or []
            for cut in range(1, len(insns)):
                try:
                    _o, _w, uns = CE.emulate(insns[:cut], 0)
                except Exception:                    # noqa: BLE001
                    continue
                # 직선경로는 RET 을 무시하므로 "RET 이전 접두사"는 정상 완주일 수 있어요.
                # 그래서 RET 를 **포함**한 접두사만 검사해요(그 이후는 잘린 것이므로).
                joined = " ".join(insns[:cut]).lower()
                if "ret" in joined and not uns:
                    straight_silent.append(f"{name}:{fname}[:{cut}]")
    check(not straight_silent,
          "직선경로 oracle 도 RET 이후 절단에서 침묵 완주 없음",
          ", ".join(straight_silent[:6]))


def test_caps_leave_traces() -> None:
    print("\n[3] 캡은 흔적을 남긴다 — 채집기 한도/완전성 플래그 불변식")
    gpath = _HERE / "ghidra_facts_pyghidra.py"
    src = gpath.read_text(encoding="utf-8")

    # (a) 한도는 **이름있는 상수**여야 해요
    caps = dict(re.findall(r"^(_[A-Z_]*CAP)\s*=\s*(\d+)", src, re.M))
    check("INSN" in " ".join(caps) and "DEC" in " ".join(caps),
          f"캡 상수 선언됨: {caps}", str(caps))

    # (b) 익명 숫자 캡 금지 — `[:24]`·`guard < 16` 같은 형태가 남아 있으면
    #     잘림이 데이터에 드러나지 않아요(결함⑤의 실제 형태)
    # 단, **채집 데이터**의 캡만 문제예요. 해시 접두사(`_digest[:16]` = 캐시 키
    # 길이)는 데이터 잘림이 아니므로 제외해요(오탐 방지).
    anon_slice = [m.group(0) + " @" + src[:m.start()].split("\n")[-1].strip()[:40]
                  for m in re.finditer(r"\[:\s*\d+\s*\]", src)
                  if not re.search(r"(digest|sha|hex|hash)\w*\s*$",
                                   src[:m.start()].split("[")[-1].strip())]
    anon_guard = re.findall(r"guard\s*<\s*\d+", src)
    check(not anon_slice, "채집 데이터에 익명 슬라이스 캡 0건 (`[:N]`)",
          " | ".join(anon_slice[:4]))
    check(not anon_guard, "익명 guard 캡 0건 (`guard < N`)", ", ".join(anon_guard[:5]))

    # (c) 잘림을 말하는 플래그가 레코드에 **실제로** 쓰여야 해요
    check("insns_complete" in src, "레코드에 `insns_complete` 플래그 기록")
    check("decompile_truncated" in src, "레코드에 `decompile_truncated` 플래그 기록")
    # 플래그가 상수를 참조해야 해요(숫자를 다시 쓰면 상수와 갈라져요).
    # `"flag": var` 형태는 var 의 대입문까지 한 단계 따라가요.
    def _flag_uses_cap(flag: str, cap: str) -> Tuple[bool, str]:
        m = re.search(r"[\"']" + flag + r"[\"']\s*:\s*([^\n,]+)", src)
        if not m:
            return False, "플래그 없음"
        expr = m.group(1).strip()
        if cap in expr:
            return True, expr[:60]
        if re.fullmatch(r"[A-Za-z_]\w*", expr):
            for am in re.finditer(r"^\s*" + expr + r"\s*=\s*(.+)$", src, re.M):
                if cap in am.group(1):
                    return True, f"{expr} = {am.group(1).strip()[:48]}"
        return False, expr[:60]

    for flag, cap in (("insns_complete", "_INSN_CAP"),
                      ("decompile_truncated", "_DEC_LINE_CAP")):
        ok, how = _flag_uses_cap(flag, cap)
        check(ok, f"`{flag}` 가 상수 `{cap}` 을 참조(갈라짐 방지)", how)

    # (c2) 프로젝트 캐시 키는 **내용 해시**에서 파생해야 해요 — 고정 경로면
    #      내용이 바뀐 바이너리를 같은 이름으로 다시 채집할 때 이전 분석을
    #      침묵 재사용해요(live 검증에서 실제로 겪은 오염).
    fixed_proj = re.search(r"gettempdir\(\)\s*,\s*[\"']ghidra_pyproj[\"']\s*\)", src)
    check(not fixed_proj, "프로젝트 캐시 키가 고정 리터럴이 아님(staleness 금지)")
    check("sha256" in src and "project_key" in src,
          "캐시 키가 sha256 으로 파생되고 facts 에 기록됨")
    for key in ("source_sha256", "source_size", "project_key", "insn_cap"):
        check(f'"{key}"' in src, f"facts 가 `{key}` 를 스스로 기록(데이터 자기기술)")

    # (d) 채집 루프의 guard 도 상수를 써야 해요
    m = re.search(r"while\s+.*guard\s*<\s*(\w+)", src)
    check(bool(m) and m.group(1) == "_INSN_CAP",
          "채집 루프 guard 가 `_INSN_CAP` 사용", m.group(1) if m else "없음")


def _probe_insns() -> Dict[str, List[str]]:
    """문서 주장 검증을 위한 대표 명령 형태(각 mnem → RET 로 끝나는 최소 스트림)."""
    P = ["0:\tPUSH RBP", "1:\tMOV RBP,RSP"]
    load = ["4:\tMOV EAX,EDI", "6:\tMOV ECX,0x3", "b:\tXOR EDX,EDX"]
    return {
        "mov": ["0:\tMOV EAX,EDI", "2:\tRET"],
        "movzx": ["0:\tMOVZX EAX,DIL", "4:\tRET"],
        "movsx": ["0:\tMOVSX EAX,DI", "3:\tRET"],
        "movsxd": ["0:\tMOVSXD RDX,EDI", "3:\tRET"],
        "lea": ["0:\tLEA EAX,[RDI*0x8]", "3:\tRET"],
        "push": P + ["4:\tRET"],
        "pop": P + ["4:\tPOP RBP", "5:\tRET"],
        "add": ["0:\tMOV EAX,EDI", "2:\tADD EAX,0x3", "5:\tRET"],
        "sub": ["0:\tMOV EAX,EDI", "2:\tSUB EAX,0x3", "5:\tRET"],
        "and": ["0:\tMOV EAX,EDI", "2:\tAND EAX,0x7", "5:\tRET"],
        "or": ["0:\tMOV EAX,EDI", "2:\tOR EAX,0x3", "5:\tRET"],
        "xor": ["0:\tMOV EAX,EDI", "2:\tXOR EAX,0x5a", "5:\tRET"],
        "shl": ["0:\tMOV EAX,EDI", "2:\tSHL EAX,0x2", "5:\tRET"],
        "shr": ["0:\tMOV EAX,EDI", "2:\tSHR EAX,0x2", "5:\tRET"],
        "sal": ["0:\tMOV EAX,EDI", "2:\tSAL EAX,0x2", "5:\tRET"],
        "sar": ["0:\tMOV EAX,EDI", "2:\tSAR EAX,0x2", "5:\tRET"],
        "rol": ["0:\tMOV EAX,EDI", "2:\tROL EAX,0x3", "5:\tRET"],
        "ror": ["0:\tMOV EAX,EDI", "2:\tROR EAX,0x3", "5:\tRET"],
        "not": ["0:\tMOV EAX,EDI", "2:\tNOT EAX", "4:\tRET"],
        "neg": ["0:\tMOV EAX,EDI", "2:\tNEG EAX", "4:\tRET"],
        "inc": ["0:\tMOV EAX,EDI", "2:\tINC EAX", "4:\tRET"],
        "dec": ["0:\tMOV EAX,EDI", "2:\tDEC EAX", "4:\tRET"],
        "cmp": ["0:\tMOV EAX,EDI", "2:\tCMP EAX,0x3", "5:\tRET"],
        "test": ["0:\tMOV EAX,EDI", "2:\tTEST EAX,EAX", "4:\tRET"],
        "ret": ["0:\tMOV EAX,EDI", "2:\tRET"],
        "leave": P + ["4:\tLEAVE", "5:\tRET"],
        "nop": ["0:\tNOP", "1:\tMOV EAX,EDI", "3:\tRET"],
        "imul": ["0:\tMOV EAX,EDI", "2:\tIMUL EAX,EDI", "4:\tRET"],
        "mul": ["0:\tMOV EAX,EDI", "2:\tMUL ECX", "4:\tRET"],
        "div": ["0:\tMOV EAX,EDI", "2:\tMOV ECX,0x3", "7:\tXOR EDX,EDX",
                "9:\tDIV ECX", "b:\tRET"],
        "idiv": ["0:\tMOV EAX,EDI", "2:\tMOV ECX,0x3", "7:\tCDQ", "9:\tIDIV ECX",
                 "b:\tRET"],
        "cdq": ["0:\tMOV EAX,EDI", "2:\tCDQ", "3:\tMOV EAX,EDX", "5:\tRET"],
        "cqo": ["0:\tMOV RAX,RDI", "3:\tCQO", "4:\tRET"],
        "cwd": ["0:\tMOV AX,DI", "3:\tCWD", "4:\tRET"],
        "cdqe": ["0:\tMOV EAX,EDI", "2:\tCDQE", "3:\tRET"],
        "cwde": ["0:\tMOV AX,DI", "3:\tCWDE", "4:\tRET"],
        "cbw": ["0:\tMOV AL,DIL", "3:\tCBW", "4:\tRET"],
        # **미지원** 명령들도 probe 에 넣어요 — 문서가 이걸 지원한다고 *주장*하면
        # (a) 검사가 거짓 주장으로 잡아내야 해요(반대 방향 검증).
        "cmovl": ["0:\tMOV EAX,EDI", "2:\tMOV ECX,0x3", "7:\tCMP EAX,0x0",
                  "a:\tCMOVL EAX,ECX", "d:\tRET"],
        "sete": ["0:\tMOV EAX,EDI", "2:\tCMP EAX,0x0", "5:\tSETE AL", "7:\tRET"],
        "bswap": ["0:\tMOV EAX,EDI", "2:\tBSWAP EAX", "4:\tRET"],
        "adc": ["0:\tMOV EAX,EDI", "2:\tADC EAX,0x1", "5:\tRET"],
        "sbb": ["0:\tMOV EAX,EDI", "2:\tSBB EAX,0x1", "5:\tRET"],
    }


def test_docstring_matches_behavior() -> None:
    print("\n[4] 문서-코드 일치 — **행동 기반**(텍스트 대조 아님)")
    doc = (EMU.__doc__ or "")
    m = re.search(r"지원 명령.*?(?=\n메모리:|\n입력:)", doc, re.S)
    if not m:
        check(False, "독스트링에 `지원 명령` 섹션이 있음", "섹션을 찾지 못함")
        return
    block = m.group(0)
    probes = _probe_insns()

    # (a) 문서가 **주장**하는 명령 → 실제로 unsupported 없이 실행돼야 해요(거짓 주장 금지)
    claimed = {k for k in probes if re.search(r"(?<![a-z])" + k + r"(?![a-z])", block)}
    check(len(claimed) >= 25, f"독스트링이 {len(claimed)}개 명령을 주장(추출 검증)",
          str(sorted(claimed)))
    lied: List[str] = []
    for mnem in sorted(claimed):
        _o, _w, uns = EMU.run(probes[mnem], 0)
        if uns:
            lied.append(f"{mnem}: unsupported={uns}")
    check(not lied, f"주장한 {len(claimed)}개 명령 전부 실제 실행 가능(거짓 주장 0)",
          "; ".join(lied[:5]))

    # (b) 실제로 **지원하는데** 문서에 없는 명령 → staleness(결함④/⑥의 실제 형태)
    #   ⚠ 후보를 probe 표에서만 뽑으면 표에 없는 명령이 **숨어요**. 실제로
    #     `adc`·`sbb` 가 지원되는데 문서에 없고 probe 표에도 없어 이 검사를
    #     통과했었어요. 그래서 후보를 **소스에서 기계적으로 유도**해요
    #     (ARITH·SHIFT 집합 + `mnem ==`/`mnem in (...)` 리터럴 + startswith 접두).
    esrc = (_ROOT / "brain_engine" / "x86_cf_emu.py").read_text(encoding="utf-8")
    cands: Set[str] = set(probes)
    for cname in ("ARITH", "SHIFT"):
        m = re.search(rf"^{cname}\s*=\s*[{{(]([^)}}]*)[)}}]", esrc, re.M | re.S)
        if m:
            cands |= set(re.findall(r"\"([a-z0-9]+)\"", m.group(1)))
    cands |= set(re.findall(r'mnem\s*==\s*\"([a-z0-9]+)\"', esrc))
    for grp in re.findall(r'mnem\s+in\s+\(([^)]*)\)', esrc):
        cands |= set(re.findall(r'\"([a-z0-9]+)\"', grp))
    for pre in set(re.findall(r'mnem\.startswith\(\"([a-z]+)\"\)', esrc)):
        cands |= {pre, pre + "x"}                  # movs→movsd, movz→movzx 류 대표형
    # `call`/`callq` 는 지원이 아니라 **bail 처리**로 등장해요(문서에도 bail 로 기재)
    cands -= {"call", "callq", "j", "jmpq"}

    # 동의어·노프 계열은 **근거를 명시하고** 정규 이름으로 환원해요(그냥 제외하면
    # 언젠가 진짜 미기재 명령이 이 목록에 숨어요).
    SYNONYM = {"retq": "ret", "callq": "call"}      # 어셈블러 표기 차이(동일 명령)
    NOP_FAMILY = {"endbr64", "endbr32"}             # CET 노프 — `nop` 과 함께 처리
    doc_tokens = set(re.findall(r"[a-z][a-z0-9]{1,9}", block))

    def _documented(m: str) -> bool:
        if m in doc_tokens:
            return True
        if SYNONYM.get(m, "") in doc_tokens:
            return True
        if m in NOP_FAMILY and "nop" in doc_tokens:
            return True
        # startswith 접두 가족: 문서에 `movs` 로 시작하는 실제 명령(movsx·movsxd)이
        # 있으면 그 가족은 기재된 셈이에요.
        return any(d.startswith(m) and len(d) > len(m) for d in doc_tokens)

    undocumented: List[str] = []
    for mnem in sorted(cands):
        forms = [[f"0:\tMOV EAX,EDI", f"2:\t{mnem.upper()} EAX,0x1", "5:\tRET"],
                 [f"0:\tMOV EAX,EDI", f"2:\t{mnem.upper()} EAX", "4:\tRET"],
                 [f"0:\tMOV EAX,EDI", f"2:\t{mnem.upper()}", "3:\tRET"]]
        supported = any(not EMU.run(f, 0)[2] for f in forms)
        if not supported:
            continue
        if not _documented(mnem):
            undocumented.append(mnem)
    check(not undocumented,
          f"실제 지원 명령은 전부 문서에 기재(소스 유도 후보 {len(cands)}개, staleness 0)",
          ", ".join(undocumented))

    # (c) 픽스처에서 실제로 깨끗이 실행되는 mnem 도 문서에 있어야 해요(독립 경로)
    fixture_mnems: Set[str] = set()
    clean_mnems: Set[str] = set()
    for name in ("test_n3_craft", "test_n4_muldiv"):
        try:
            mod = _load_fixture_module(name)
        except Exception:                            # noqa: BLE001
            continue
        for fx in getattr(mod, "FUNCS", {}).values():
            insns = fx.get("insns") or []
            mn = {i.split(":", 1)[-1].strip().split(None, 1)[0].lower()
                  for i in insns if ":" in i}
            fixture_mnems |= mn
            _o, _w, uns = EMU.run(insns, 0)
            if not uns:
                clean_mnems |= mn
    # 독스트링이 `jcc` 로 한꺼번에 표기하면 j-패밀리 전체가 기재된 셈이에요.
    jcc_covered = bool(re.search(r"(?<![a-z])jcc(?![a-z])", block))
    skip = {"retq", "endbr64", "endbr32"}          # 동의어/노프 계열(문서 표기 차이)
    missing = sorted(m for m in clean_mnems
                     if m not in skip
                     and not (jcc_covered and m.startswith("j"))
                     and not re.search(r"(?<![a-z])" + re.escape(m) + r"(?![a-z])", block))
    check(not missing,
          f"픽스처에서 깨끗이 실행되는 {len(clean_mnems)}개 mnem 전부 문서 기재",
          ", ".join(missing))

    # (d) bail 조건도 문서에 명시돼 있어야 해요(정직성 고지)
    for needle, what in (("trunc", "RET 없이 끝남 bail"), ("#DE", "0 나눔/오버플로 bail")):
        check(needle.lower() in doc.lower(), f"독스트링이 `{what}` 을 명시", needle)


def test_no_foreign_script_contamination() -> None:
    print("\n[5] 문자 오염 — 가나·한자 대체·라틴 다이어크리틱 금지(병기·수학기호 허용)")
    kana = re.compile(r"[\u3040-\u30ff]")
    # 라틴 **문자**의 다이어크리틱(U+00C0..U+024F, U+1E00..U+1EFF) — 한국어 산문에
    # 섞이면 외래어 오염이에요. 이 게이트를 쓰다가 포르투갈어 단어가 실제로 새어
    # 들어온 걸 발견해서 추가했어요(예시는 아래 백틱 안에서 인용만 해요).
    # 단 수학 기호 × (U+00D7)·÷ (U+00F7) 는 **정당한 용례**라 범위에서 제외해요
    # (vault 전반에 78건이 있고 전부 `6 함수 × 91 입력` 같은 수식 표기예요).
    latin = re.compile(r"[\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u024f\u1e00-\u1eff]")
    han = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
    # 정당한 국어 한자 병기: 한글 바로 뒤 `(...)` 안의 한자 — 예: 무패(無敗), 세 적(敵)
    annotated = re.compile(r"[가-힣]\s*\([^()]*[\u4e00-\u9fff]+[^()]*\)")

    kana_hits: List[str] = []
    han_hits: List[str] = []
    latin_hits: List[str] = []
    scanned = 0
    for path in sorted(_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in (".md", ".py"):
            continue
        if any(part in ("vendor", "__pycache__", ".git") for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:                            # noqa: BLE001
            continue
        scanned += 1
        rel = path.relative_to(_ROOT)
        for lineno, line in enumerate(text.split("\n"), 1):
            if kana.search(line):
                # 이 게이트·부채원장이 **결함을 인용**한 것은 예외(백틱 안)
                if re.search(r"`[^`]*[\u3040-\u30ff]+[^`]*`", line):
                    continue
                kana_hits.append(f"{rel}:{lineno}")
            if latin.search(line):
                if re.search(r"`[^`]*[\u00c0-\u024f]+[^`]*`", line):
                    continue                        # 백틱 안의 인용(결함 예시)은 허용
                latin_hits.append(f"{rel}:{lineno}")
            stripped = annotated.sub("", line)        # 병기 표식을 지우고 남은 한자만
            if han.search(stripped):
                if re.search(r"`[^`]*[\u4e00-\u9fff]+[^`]*`", line):
                    continue
                han_hits.append(f"{rel}:{lineno}")
    check(not kana_hits, f"일본어 가나 오염 0건 ({scanned}파일 스캔)",
          ", ".join(kana_hits[:6]))
    check(not han_hits, "한글을 대체한 한자 0건(정당한 병기는 허용)",
          ", ".join(han_hits[:6]))
    check(not latin_hits,
          "라틴 다이어크리틱 오염 0건(× · ÷ 등 수학 기호는 허용)",
          ", ".join(latin_hits[:6]))


def _ref_c_div(a: int, b: int) -> int:
    """C99 6.5.5 몫 — **게이트 안에서 독립 유도**한 참조예요.

    ⚠ 여기서 `SYN._tdiv` 를 호출하면 비교가 **tautology** 가 돼요. v7.3.11 에서
    `_W._div` 를 단일 출처로 `SYN._tdiv` 에 위임시켰더니, (b) 검사의 양쪽이 같은
    함수가 되어 `_tdiv` 를 바닥나눗셈으로 바꾸는 변이(M9)가 **조용히 통과**했어요.
    알고리즘은 C 표준이 유일하게 결정하므로 구현 텍스트가 같을 수밖에 없어요 —
    중요한 것은 **호출 관계가 없어서 한쪽만 변이된다**는 거예요.
    """
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _ref_c_mod(a: int, b: int) -> int:
    """C99 나머지 — `a == (a/b)*b + a%b` 이고 부호는 피제수를 따라요(독립 유도)."""
    return a - _ref_c_div(a, b) * b


def test_two_oracle_paths_agree() -> None:
    print("\n[6] 두 oracle 경로 일관성 — 직선 `_W` · cf `_tdiv`/`_tmod` · **독립 참조** 삼방")
    # (a) `_W` 가 산술 던더를 **갖고 있어야** 해요(사라지면 결함④ 재발)
    need = ["__mul__", "__rmul__", "__truediv__", "__rtruediv__", "__floordiv__",
            "__mod__", "__rmod__", "__neg__", "__invert__", "__eq__", "__lt__",
            "__lshift__", "__rshift__"]
    missing = [d for d in need if not hasattr(CE._W, d)]
    check(not missing, f"`_W` 산술 던더 {len(need)}개 전부 존재(결함④ 재발 방지)",
          ", ".join(missing))

    # (b) **삼방 대조** — 직선 경로(`_W`), cf 경로(`SYN._tdiv`/`_tmod`), 그리고
    #     게이트가 독립 유도체 참조를 서로 대조해요.
    #     예전엔 직선 vs `SYN._tdiv` 였는데, `_W._div` 를 `_tdiv` 에 위임시킨 뒤로는
    #     양쪽이 같은 함수라 **무조건 통과하는 tautology** 였어요(변이 M9 가 실측으로
    #     드러냄). 참조를 독립 유도체로 바꾸고 `_tdiv` 자체도 직접 대조해요.
    M32 = (1 << 32) - 1
    bad: List[str] = []
    pairs = 0
    for a in (0, 1, -1, 7, -7, 3, -3, 2 ** 31, -(2 ** 31), 12345, -12345, 1000000007):
        for b in (1, 2, 3, -3, 4, 5, -5, 7, 8, -8, 100):
            sa = a & M32
            sa = sa - (1 << 32) if sa >= (1 << 31) else sa
            pairs += 1
            rq, rm = _ref_c_div(sa, b) & M32, _ref_c_mod(sa, b) & M32
            wq = CE.build_python(f"x / {b}", 32, True)(a) & M32
            wm = CE.build_python(f"x % {b}", 32, True)(a) & M32
            if wq != rq:
                bad.append(f"직선 {a}/{b} q={wq} want={rq}")
            if wm != rm:
                bad.append(f"직선 {a}%{b} m={wm} want={rm}")
            if (SYN._tdiv(sa, b) & M32) != rq:
                bad.append(f"cf _tdiv({a},{b})={SYN._tdiv(sa, b) & M32} want={rq}")
            if (SYN._tmod(sa, b) & M32) != rm:
                bad.append(f"cf _tmod({a},{b})={SYN._tmod(sa, b) & M32} want={rm}")
    check(not bad,
          f"직선 `_W` · cf `_tdiv`/`_tmod` · 독립 참조 삼방 일치 ({pairs}쌍 × 4대조)",
          "; ".join(bad[:4]))

    # (b2) `_W` 산술 **전부**를 독립 참조(파이썬 int + 폭 마스킹)와 대조해요.
    #   던더가 "존재"하는지만 보면 __mul__ 이 덧셈을 하는 **침묵 오답**이어도
    #   통과해요(변이 테스트 M4b 가 이 구멍을 실제로 드러냈어요).
    M32 = (1 << 32) - 1
    xs = [0, 1, -1, 7, -7, 3, 2 ** 31, -(2 ** 31), 2 ** 32 - 1, 12345, -12345]
    arith_bad: List[str] = []
    n_arith = 0
    for a in xs:
        ua = a & M32
        sa = ua - (1 << 32) if ua >= (1 << 31) else ua
        for b in (0, 1, 3, -3, 7, 16):
            cases = [
                (f"x + {b}",  (ua + b) & M32),
                (f"x - {b}",  (ua - b) & M32),
                (f"x * {b}",  (ua * b) & M32),          # ← M4b 가 노리는 지점
                (f"x & {b}",  ua & (b & M32)),
                (f"x | {b}",  ua | (b & M32)),
                (f"x ^ {b}",  ua ^ (b & M32)),
                (f"{b} * x",  (b * ua) & M32),
                ("-x",        (-sa) & M32),
                ("~x",        (~ua) & M32),
            ]
            if b >= 0 and b < 32:
                cases += [(f"x << {b}", (ua << b) & M32)]
            if b:                       # 0 나눔은 (d) 에서 separately 다뤄요
                # ⚠ 이 두 줄이 없었어요 — 나눗셈·나머지는 (b) 만이 재고 있었는데 그
                #   (b) 가 위임 리팩토링 후 tautology 가 되면서 **C truncation 파괴가
                #   게이트 전체에서 안 잡히는 상태**였어요(변이 M9 가 실측으로 노출).
                cases += [(f"x / {b}", _ref_c_div(sa, b) & M32),
                          (f"x % {b}", _ref_c_mod(sa, b) & M32)]
            for expr, want in cases:
                n_arith += 1
                try:
                    got = CE.build_python(expr, 32, True)(a) & M32
                except Exception as exc:                  # noqa: BLE001
                    arith_bad.append(f"{expr}@{a}:EXC {type(exc).__name__}")
                    continue
                if got != want:
                    arith_bad.append(f"{expr}@{a}: got={got} want={want}")
    check(not arith_bad,
          f"`_W` 산술 {n_arith}건 전부 독립 참조와 일치(침묵 오답 0)",
          "; ".join(arith_bad[:4]))

    # (c) signed 와 unsigned 가 **실제로** 달라야 해요(같다면 부호 유추가 무의미)
    diff = sum(1 for a in (2 ** 31, 2 ** 32 - 1, -(2 ** 31))
               for b in (3, 7)
               if (CE.build_python(f"x / {b}", 32, True)(a) & M32)
               != (CE.build_python(f"x / {b}", 32, False)(a) & M32))
    check(diff >= 4, f"signed/unsigned 절삭이 실제로 다름({diff}/6 조합)", f"diff={diff}")

    # (d) 0 나눔은 **짐작하지 않고** 예외 → 게이트가 실패로 집계
    raised = False
    try:
        CE.build_python("x / (x & 0)", 32, True)(5)
    except ZeroDivisionError:
        raised = True
    except Exception:                                # noqa: BLE001
        raised = True
    check(raised, "0 나눔 → 예외(침묵 오답 아님)")


def test_record_only_perfect() -> None:
    print("\n[7] 정직 불변식 — record 는 match 100% 만 저장")
    import shutil
    import tempfile
    # 엔트리를 **손으로 만들지 않고** 실제 파이프라인(synth_for → differential →
    # craft_function)으로 만들어요. 손으로 만든 dict 는 스키마가 코드와 갈라지면
    # KeyError 로 터져서 검사가 "정직성"이 아니라 "내 dict 모양"을 재게 돼요.
    dec = "int good_fn(int param_1)\n\n{\n  return param_1 ^ 0x5a;\n}"
    insns = ["0:\tMOV EAX,EDI", "2:\tXOR EAX,0x5a", "5:\tRET"]
    entry, why = CE.craft_function({"name": "good_fn", "decompile": dec,
                                    "insns": insns}, False)
    if entry is None:
        check(False, "기준 함수가 실제로 craft 됨(100%)", why or "entry=None")
        return
    check(entry["match_pct"] == 100.0,
          f"기준 함수 good_fn 이 실제로 100% craft 됨(via={entry.get('via')})",
          f"match={entry['match_pct']} why={why}")

    tmp = Path(tempfile.mkdtemp(prefix="audit_rec_"))
    try:
        # 100% 원본 + match_pct 만 조작한 두 변형(99.99%·49.61%)
        near = dict(entry, name="near_fn", match_pct=99.99, mismatches=[12345])
        half = dict(entry, name="half_fn", match_pct=49.61, mismatches=[1, 2, 3])
        rep = {"binary": "inv.o", "backend": "analyzeHeadless",
               "crafted": [entry, near, half]}
        notes = CE.record(rep, tmp)
        names = {q.name for q in notes}
        check(len(notes) == 1, "3개 중 1개만 기록(99.99%·49.61% 는 거부)", str(names))
        check(any("good_fn" in n for n in names), "100% 인 good_fn 만 기록됨", str(names))
        check(not any(("near_fn" in n) or ("half_fn" in n) for n in names),
              "99.99%·49.61% 는 기록 안 됨(거짓 기록 구조적 불가)", str(names))
        # 기록된 노트가 실제로 내용을 담고 있는지(빈 파일 금지)
        if notes:
            body = notes[0].read_text(encoding="utf-8")
            check(len(body) > 100 and "good_fn" in body and "100" in body,
                  f"기록 노트에 실질 내용 있음({len(body)}자)", body[:80])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_signedness_inference() -> None:
    print("\n[8] 부호 유추 — `_c_signedness` 정확성 + 오분류 시 정직 거부")
    # 구조 게이트가 이걸 검사하지 않으면 "항상 signed" 로 바뀌어도 조용히 통과해요
    # (변이 테스트 M10 이 실제로 드러낸 구멍).
    sigs = [("uint f(uint param_1)", "param_1", False),
            ("int f(int param_1)", "param_1", True),
            ("undefined4 f(undefined4 param_1)", "param_1", False),
            ("ulong f(ulong param_1)", "param_1", False),
            ("long f(long param_1)", "param_1", True),
            ("unsigned int f(unsigned int param_1)", "param_1", False),
            ("int32_t f(int32_t param_1)", "param_1", True),
            ("uint32_t f(uint32_t param_1)", "param_1", False),
            ("char f(char param_1)", "param_1", True),
            ("ushort f(ushort param_1)", "param_1", False),
            ("int f(int in_RDI)", "in_RDI", True),
            ("uint f(uint in_RDI)", "in_RDI", False),
            ("ushort f(ushort in_EAX)", "in_EAX", False)]
    bad = []
    for sig, var, want in sigs:
        got = CE._c_signedness(sig + "\n{\n  return " + var + " / 4;\n}", var)
        if got != want:
            bad.append(f"{sig}: want={want} got={got}")
    check(not bad, f"`_c_signedness` {len(sigs)}종 시그니처 전부 정확", "; ".join(bad[:4]))

    # 판단 불가 시 **signed**(보수적) — 오답 통과가 아니라 정직 거부 방향으로
    unknown = CE._c_signedness("f(v)\n{\n  return v / 4;\n}", "v")
    check(unknown is True, "판단 불가 시 signed 기본(보수적 — 거부 방향)")

    # 핵심 정직성: 부호를 **틀리게** 유추해도 차분게이트가 거부해야 해요
    ins_u = ["0:\tMOV EAX,EDI", "2:\tSHR EAX,0x3", "5:\tRET"]     # unsigned x/8
    d_wrong = CE.differential(ins_u, {"kind": "straight", "src": "x / 8", "signed": True})
    d_right = CE.differential(ins_u, {"kind": "straight", "src": "x / 8", "signed": False})
    check(d_wrong["match_pct"] < 100.0 <= d_right["match_pct"],
          f"부호 오분류는 거부({d_wrong['match_pct']}%)·올바르면 통과({d_right['match_pct']}%)",
          f"wrong={d_wrong['match_pct']} right={d_right['match_pct']}")

    # 그리고 실제 파이프라인은 unsigned 함수에 대해 **스스로** 올바른 부호를 골라야 해요
    sy = CE.synth_for("uint g(uint param_1)\n{\n  return param_1 / 8;\n}", ins_u, False)
    check(sy is not None and sy.get("signed") is False
          and CE.differential(ins_u, sy)["match_pct"] == 100.0,
          "실제 파이프라인이 unsigned 를 스스로 unsigned 로 유추 → 100%",
          f"sy={sy}")


def main() -> int:
    print("🩺 구조 감사 게이트 — 결함의 **종류**를 기계적으로 막아요\n")
    for t in (test_single_source_register_model, test_truncation_never_silent,
              test_caps_leave_traces, test_docstring_matches_behavior,
              test_no_foreign_script_contamination, test_two_oracle_paths_agree,
              test_record_only_perfect, test_signedness_inference):
        try:
            t()
        except Exception as exc:                      # noqa: BLE001
            global _FAIL
            _FAIL += 1
            print(f"  ❌ {t.__name__} 예외: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 72)
    if _FAIL:
        print(f"❌ STRUCTURAL AUDIT FAILED — {_PASS} passed / {_FAIL} failed")
        return 1
    print(f"✅ STRUCTURAL AUDIT PASSED — {_PASS} passed / 0 failed")
    print("   이 게이트는 기능이 아니라 **불변식**을 검사해요: 단일 출처·절단 정직성·")
    print("   캡 흔적·문서-코드 행동 일치·문자 오염·두 경로 일관성·기록 정직성.")
    print("   N4 감사에서 손으로 찾던 ①②④⑥ 결함 종류가 이제 자동으로 걸려요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
