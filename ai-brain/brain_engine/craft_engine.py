"""🛠 Stage N — Craft Anything, brain-owned clean-room edition.

영감: storytold/craft-anything (MIT OR Apache-2.0) — "실제 검사 도구로
원본을 분석하고, 나만의 버전을 만들고, 원본과 비교하며 다듬는다".
그 엔진의 빌더는 외부 코딩 에이전트지만, 우리 빌더는 **Ghidra 디컴파일 C
에서 규칙 기반 합성**이고, 우리 비교.oracle은 **원본 바이트를 직접 실행하는
소형 x86-64 부분집합 에뮬레이터**(objdump 텍스트 디코더)예요. 외부 모델
없음, 전부 소유, 불일치면 발명하지 않고 match% 로 보고.

루프: inspect(Ghidra) → build(C 로부터 합성) → compare(에뮬레이터 차분
테스트) → record(vault 노트) → refine(불일치 연산 목록 반환).
"""
from __future__ import annotations

import ast
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from brain_engine import re_analyzer
from brain_engine import x86_cf_emu          # Stage N3: 제어흐름+메모리 oracle
from brain_engine import c_synthesize        # Stage N3: C 부분집합 → 파이썬 합성기

# ── 레지스터 파일: 이름 → (base, shift, width bits) ─────────────────────────
# 별칭/폭 규칙은 **단일 출처**(`x86_cf_emu`)를 그대로 공유해요. 이전에 이 표를
# 복제해서 갖고 있었는데, 그 사본에도 동일한 바이트 레지스터 오투영 결함
# (`_core[0]+"l"` 이 rsi/rdi/rbp/rsp 에 대해 "sl"/"dl"/"bl"/"sl" 을 만들어
# rdx 의 dl·rbx 의 bl 을 덮어씀 → dl→rdi, bl→rbp, 그리고 sil/dil/bpl/spl 누락)
# 이 그대로 들어 있었어요. 즉 **중복이 같은 결함을 두 벌로** 만들었고, 둘 다
# `unsupported` 없이 침묵 오답을 냈어요(직선 경로 oracle 도 오염). N4 감사에서
# 발견하고 표를 하나로 통합해요 — 앞으로 한쪽만 고쳐서 갈라지는 일이 없어요.
_WIDTHS = x86_cf_emu._WIDTHS
_BASES = x86_cf_emu._BASES
_ALIASES = x86_cf_emu._ALIASES


def _reg_info(name: str) -> Optional[Tuple[str, int, int]]:
    """이름 → (base, shift, width bits). `x86_cf_emu.reg_info` 와 단일 출처예요."""
    return x86_cf_emu.reg_info(name)


class _Regs:
    def __init__(self) -> None:
        self.v: Dict[str, int] = {b: 0 for b in _BASES}
        self.out_width = 32

    def get(self, name: str) -> int:
        info = _reg_info(name)
        if not info:
            raise KeyError(name)
        base, shift, wid = info
        return (self.v[base] >> shift) & ((1 << wid) - 1)

    def set(self, name: str, val: int) -> None:
        info = _reg_info(name)
        if not info:
            raise KeyError(name)
        base, shift, wid = info
        val &= (1 << wid) - 1
        if wid == 64:
            self.v[base] = val
        elif wid == 32 and shift == 0:
            self.v[base] = val
        else:
            mask = ((1 << wid) - 1) << shift
            self.v[base] = (self.v[base] & ~mask) | (val << shift)
        if base == "rax" and shift == 0:
            self.out_width = wid


_OPS = {
    "xor": lambda a, b: a ^ b, "or": lambda a, b: a | b, "and": lambda a, b: a & b,
    "add": lambda a, b: a + b, "sub": lambda a, b: a - b,
    "shl": lambda a, b: a << b, "shr": lambda a, b: a >> b,
    "rol": lambda a, b: ((a << b) | (a >> (8 - b))) if b else a,  # width-fixed below
    "ror": lambda a, b: ((a >> b) | (a << (8 - b))) if b else a,
}


def _parse_imm(tok: str) -> int:
    tok = tok.strip().replace("$", "")
    if tok.startswith(("0x", "-0x")):
        return int(tok, 16)
    return int(tok)


def emulate(insns: List[str], x: int) -> Tuple[int, int, List[str]]:
    """원본 바이트(objdump 텍스트)를 직선 코드에 대해 실행.

    returns (output, out_width_bits, unsupported_ops).  점프/메모리가
    나오면 unsupported 에 넣고 중단 — 발명하지 않아요.
    """
    regs = _Regs()
    unsupported: List[str] = []
    first_input: Optional[str] = None
    written: set = {"rsp", "rbp"}
    zf = False

    def read(tok: str) -> int:
        nonlocal first_input
        tok = tok.strip()
        if re.fullmatch(r"-?(0x[0-9a-fA-F]+|\d+)", tok):
            return _parse_imm(tok)
        info = _reg_info(tok)
        if info:
            if info[0] not in written and first_input is None:
                first_input = info[0]
                regs.v[info[0]] = x
            return regs.get(tok)
        unsupported.append(tok)
        return 0

    for line in insns:
        line = line.split(";", 1)[0].strip()
        if not line or ":" not in line:
            continue
        body = line.split(":", 1)[1].strip()
        parts = body.split(None, 1)
        mnem = parts[0].lower()
        args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
        if mnem in ("push", "pop", "nop", "leave"):
            continue
        if mnem == "mov" or mnem.startswith("movz") or mnem.startswith("movs"):
            if len(args) == 2 and _reg_info(args[0]) and "[" not in args[1]:
                regs.set(args[0], read(args[1]))
                written.add(_reg_info(args[0])[0])
            else:
                unsupported.append(mnem)
            continue
        if mnem in _OPS:
            if len(args) == 2 and _reg_info(args[0]) and "[" not in args[1]:
                wid = _reg_info(args[0])[2]
                a = read(args[0])
                b = read(args[1])
                if mnem in ("rol", "ror"):
                    b %= wid
                    rot = b % wid
                    val = ((a << rot) | (a >> (wid - rot))) & ((1 << wid) - 1) if mnem == "rol" and rot else \
                          ((a >> rot) | (a << (wid - rot))) & ((1 << wid) - 1) if rot else a
                else:
                    val = _OPS[mnem](a, b)
                regs.set(args[0], val)
                written.add(_reg_info(args[0])[0])
                zf = (regs.get(args[0]) == 0)
            else:
                unsupported.append(mnem)
            continue
        if mnem in ("not", "neg", "inc", "dec"):
            if args and _reg_info(args[0]):
                wid = _reg_info(args[0])[2]
                a = read(args[0])
                val = {"not": ~a, "neg": -a, "inc": a + 1, "dec": a - 1}[mnem]
                regs.set(args[0], val)
                written.add(_reg_info(args[0])[0])
                zf = (regs.get(args[0]) == 0)
            else:
                unsupported.append(mnem)
            continue
        if mnem in ("cmp", "test"):
            if len(args) == 2 and "[" not in args[1]:
                a = read(args[0])
                b = read(args[1])
                zf = ((a - b) & 0xFFFFFFFFFFFFFFFF == 0) if mnem == "cmp" else (a & b == 0)
            else:
                unsupported.append(mnem)
            continue
        if mnem in ("ret", "retq"):
            return regs.get("rax"), regs.out_width, unsupported
        unsupported.append(mnem)
        if mnem.startswith("j"):
            break
    return regs.get("rax"), regs.out_width, unsupported


# ── 빌더: Ghidra 디컴파일 C → 파이썬 함수 ───────────────────────────────────
_IDENT_MAP = re.compile(r"\b(in_[A-Z]{2,3}|param_\d+|undefined\d*\s+param_\d+)\b")


_ABI_PE = ["rcx", "rdx", "r8", "r9"]
_ABI_ELF = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]


def ident_map(insns: List[str], is_pe: bool) -> Dict[str, str]:
    """C 의 입력 식별자 → 'x' 또는 '0'. 첫 입력 레지스터만이 진짜 x."""
    written = {"rsp", "rbp"}
    order: List[str] = []
    mov_family = {"mov", "movzx", "movsx", "movsxd", "lea"}
    for line in insns:
        body = line.split(":", 1)[-1].strip()
        parts = body.split(None, 1)
        if len(parts) < 2:
            continue
        mnem = parts[0].lower()
        args = [a.strip() for a in parts[1].split(",")]
        read_toks = args[1:] if mnem in mov_family else args
        for tok_group in read_toks:
            for tok in re.split(r"[\[\]+*]", tok_group):
                info = _reg_info(tok)
                if info and info[0] not in written and info[0] not in order:
                    order.append(info[0])
        dst = _reg_info(args[0])
        if dst:
            written.add(dst[0])
    abi = _ABI_PE if is_pe else _ABI_ELF
    m: Dict[str, str] = {}
    primary = order[0] if order else None
    for name in list(_ALIASES):
        base, wid = _ALIASES[name]
        m["in_" + name.upper()] = "x" if base == primary else "0"
    for i, reg in enumerate(abi):
        m[f"param_{i + 1}"] = "x" if reg == primary else "0"
    return m


def _c_to_lambda(dec: str, imap: Optional[Dict[str, str]] = None) -> Optional[str]:
    m = re.search(r"return\s+(.+?)\s*;", dec, re.S)
    if not m:
        return None
    expr = m.group(1).replace("\n", " ")
    expr = re.sub(r"\bundefined\d*\s+", "", expr)
    expr = re.sub(r"\((char|byte|short|ushort|int|uint|long|ulong|undefined[1-8])\)", "", expr)
    expr = re.sub(r"\bunaff_(\w+)", "0", expr)
    imap = imap or {}

    def _sub(mm: re.Match) -> str:
        return imap.get(mm.group(1), "0")

    expr = re.sub(r"\b(in_[A-Z]{2,3}|param_\d+)\b", _sub, expr)
    try:
        ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    return expr


_UNSIGNED_TY = re.compile(
    r"\bunsigned\b|\bundefined\d*\b|\bu(char|short|int|long|int8_t|int16_t|int32_t|int64_t)\b")


def _c_signedness(dec: str, var: str = "param_1") -> bool:
    """디컴파일 C 에서 주 입력 변수의 부호를 유추해요. 판단 불가 시 **signed**(보수적).

    보수적 기본값이 안전한 이유: 실제가 unsigned 인데 signed 로 가정하면 큰 입력에서
    결과가 어긋나 차분게이트가 **정직하게 거부**해요(거짓 100% 기록 불가). 반대로
    signed 를 unsigned 로 오해하면 오답을 통과시킬 수 있으니 그 방향은 절대 기본값
    으로 쓰지 않아요.
    """
    # 변수 **바로 앞**의 타입 토큰 — `uint div8(uint param_1)` 에서 "uint" 만 집어요.
    # 시그니처 앞부분(`uint div8(`)까지 탐욕으로 잡히면 오검출이므로 타입 단어만 허용.
    ty = (r"([A-Za-z_]\w*(?:\s+(?:unsigned|signed|const|short|long|int|char))*"
          r")\s+" + re.escape(var) + r"\b")
    m = re.search(ty, dec)
    if m:
        return not bool(_UNSIGNED_TY.search(m.group(1)))
    # 표현식 안의 캐스트 — `(uint)param_1 / 8`
    m = re.search(r"\(\s*([A-Za-z_]\w*(?:\s+\w+)?)\s*\)\s*" + re.escape(var), dec)
    if m:
        return not bool(_UNSIGNED_TY.search(m.group(1)))
    return True


class _DivZero(ZeroDivisionError):
    """C 의 0 나눔은 UB — **짐작하지 않고** 예외로 올려 차분게이트가 실패로 집계해요."""


class _W:
    """폭이 감긴 정수 — C 의 byte/word 산술을 그대로 재현해요.

    ⚠ 감사에서 발견한 결함(수정됨): 이 클래스에 `__mul__`·`__truediv__`·`__mod__` 가
      **없어서**, 디컴파일 C 에 `*`·`/`·`%` 가 조금이라도 있으면 직선 경로 합성이
      모든 벡터에서 `TypeError` → match 0.0% 로 **전부 거부**됐어요. gcc 는 2^n 상수를
      `SHL`/`SHR`/`AND`(전부 `_OPS` 에 있음)로 컴파일하므로 `x*4`·`x/8`·`x%8` 같은
      **아주 흔한** 함수들이 직선 경로에 진입만 하고 하나도 craft 되지 못했어요.
      환각은 아니었지만(0% 는 정직 거부) 침묵의 도달범위 손실이었고, 이제 C truncation
      semantics 로 채워요(부호는 `_c_signedness` 가 디컴파일 C 에서 유추).
    """

    __slots__ = ("v", "w", "s")

    def __init__(self, v: int, w: int, signed: bool = True) -> None:
        self.w = w
        self.s = bool(signed)
        self.v = int(v) & ((1 << w) - 1)

    def _o(self, o: Any) -> int:
        """비트/덧셈/곱셈용 — 폭 안에서 wrap 하므로 부호와 무관하게 raw 값."""
        return o.v if isinstance(o, _W) else int(o)

    def _svof(self, o: Any) -> int:
        """나눗셈/비교용 — `_W` 면 그 자신의 부호 규칙으로 확장, 아니면 정수 그대로."""
        return o._sv() if isinstance(o, _W) else int(o)

    def _sv(self) -> int:
        """부호 확장된 값(C 연산의 실제 피연산자)."""
        if not self.s:
            return self.v
        half = 1 << (self.w - 1)
        return self.v - (1 << self.w) if self.v >= half else self.v

    def _n(self, val: int) -> "_W":
        return _W(val, self.w, self.s)

    def _div(self, a: int, b: int, mod: bool) -> "_W":
        if b == 0:
            raise _DivZero("division by zero (C UB — 짐작하지 않음)")
        if self.s:
            q = abs(a) // abs(b)                     # C truncation toward zero
            if (a < 0) != (b < 0):
                q = -q
            return self._n(a - q * b if mod else q)
        ua, ub = a & ((1 << self.w) - 1), b & ((1 << self.w) - 1)
        q = ua // ub
        return self._n(ua - q * ub if mod else q)

    def __xor__(self, o): return self._n(self.v ^ self._o(o))
    __rxor__ = __xor__
    def __or__(self, o): return self._n(self.v | self._o(o))
    __ror__ = __or__
    def __and__(self, o): return self._n(self.v & self._o(o))
    __rand__ = __and__
    def __add__(self, o): return self._n(self.v + self._o(o))
    __radd__ = __add__
    def __sub__(self, o): return self._n(self.v - self._o(o))
    def __rsub__(self, o): return self._n(self._o(o) - self.v)
    def __mul__(self, o): return self._n(self._sv() * self._o(o))
    __rmul__ = __mul__
    def __lshift__(self, n): return self._n(self.v << int(n))
    def __rshift__(self, n): return self._n(self.v >> int(n))
    def __rlshift__(self, n): return self._n(int(n) << self.v)
    def __rrshift__(self, n): return self._n(int(n) >> self.v)
    def __truediv__(self, o): return self._div(self._sv(), self._svof(o), False)
    def __rtruediv__(self, o): return self._div(self._svof(o), self._sv(), False)
    __floordiv__ = __truediv__
    __rfloordiv__ = __rtruediv__
    def __mod__(self, o): return self._div(self._sv(), self._svof(o), True)
    def __rmod__(self, o): return self._div(self._svof(o), self._sv(), True)
    def __neg__(self): return self._n(-self._sv())
    def __pos__(self): return self._n(self._sv())
    def __invert__(self): return self._n(~self.v)
    def __eq__(self, o): return self._sv() == self._svof(o)
    def __ne__(self, o): return self._sv() != self._svof(o)
    def __lt__(self, o): return self._sv() < self._svof(o)
    def __le__(self, o): return self._sv() <= self._svof(o)
    def __gt__(self, o): return self._sv() > self._svof(o)
    def __ge__(self, o): return self._sv() >= self._svof(o)
    def __bool__(self): return bool(self.v)
    def __hash__(self): return hash((self.v, self.w, self.s))
    def __repr__(self): return f"_W({self.v}, {self.w}, {'s' if self.s else 'u'})"
    def __int__(self): return self.v
    def __index__(self): return self.v


def _concat22(a: Any, b: Any) -> int:
    av = int(a) if not isinstance(a, _W) else a.v
    bv = int(b) if not isinstance(b, _W) else b.v
    return ((av & 0xFFFF) << 16) | (bv & 0xFFFF)


_HELPERS = {"bswap16": lambda v: (((int(v) & 0xFF) << 8) | ((int(v) >> 8) & 0xFF)) & 0xFFFF,
            "CONCAT22": _concat22}


def build_python(expr: str, width: int, signed: bool = True) -> Any:
    """직선경로 합성식을 실행 가능 함수로 만들어요.

    `signed` 는 C 타입의 부호 — `/`·`%` 의 truncation 방향을 정해요. 디컴파일 C 에서
    `_c_signedness` 가 유추하고, 유추 불가 시 True(보수적: 오답이면 차분이 거부).
    """
    code = compile(expr, "<craft>", "eval")

    def fn(x: int) -> int:
        val = eval(code, {"__builtins__": {}},                        # noqa: S307
                   dict(_HELPERS, x=_W(x, width, signed)))
        return int(val)
    return fn


def input_width(insns: List[str]) -> int:
    """첫 '쓰기 전 읽힘' 레지스터의 폭 = 입력 폭 (에뮬레이터와 같은 규칙)."""
    written = {"rsp", "rbp"}
    for line in insns:
        body = line.split(":", 1)[-1].strip()
        parts = body.split(None, 1)
        if len(parts) < 2:
            continue
        for tok in re.split(r"[,\[\]+*]", parts[1]):
            info = _reg_info(tok)
            if info and info[0] not in written:
                return info[2]
        dst = _reg_info(parts[1].split(",")[0])
        if dst:
            written.add(dst[0])
    return 32


# ── craft 루프 ──────────────────────────────────────────────────────────────
# Stage N3: 직선 스칼라(경로1) + 제어흐름·메모리(경로2) 를 하나의 정직 게이트로.
#   경로1 oracle = emulate (직선·레지스터),  build = _c_to_lambda + build_python
#   경로2 oracle = x86_cf_emu.run (PC·flags·스택메모리·bounded 루프, 네이티브 검증됨),
#          build = c_synthesize (규칙 기반) [+ SLM 브리지 online 시 LLM 합성]
# 두 경로 모두 **차분 검증**(oracle vs 합성, 100% 일치만 기록) 으로 환각을 차단해요.

_MIN_CF_COMPARABLE = 32          # 제어흐름 함수: oracle 이 완주한 벡터 최소 증거


def synth_for(dec: str, insns: List[str], is_pe: bool,
              slm: Optional[Any] = None) -> Optional[Dict[str, str]]:
    """함수 하나에 대한 합성 시도. {"kind","src"[,"via"]} 또는 None(정직 skip).

    직선 스칼라로 표현되고 oracle 이 완주하면 경로1, 아니면 제어흐름 경로2.
    경로2 는 규칙 기반 합성 우선, 실패 시 SLM 브리지(online) 시도, dormant 면
    규칙 기반이 grounded 폴백(SLM 은 코드 발명 거부).
    """
    imap = ident_map(insns, is_pe)
    expr = _c_to_lambda(dec, imap)
    if expr is not None:
        try:
            _o0, _owid, uns0 = emulate(insns, 0)
        except Exception:  # noqa: BLE001
            uns0 = ["exc"]
        if not uns0:
            # 직선경로는 C 표현식을 **그대로** 실행하므로 `/`·`%`·`*` 의 부호 규칙이
            # 결과에 영향을 줘요. 디컴파일 C 의 타입에서 유추해 함께 넘겨요.
            xvars = [k for k, v in imap.items() if v == "x"]
            signed = True
            for vn in xvars or ["param_1"]:
                if re.search(re.escape(vn) + r"\b", dec):
                    signed = _c_signedness(dec, vn)
                    break
            return {"kind": "straight", "src": expr, "via": "rule", "signed": signed}
    src = c_synthesize.synthesize(dec, imap)
    via = "rule"
    if src is None and slm is not None:
        try:
            res = slm.synthesize_python(dec)
        except Exception:  # noqa: BLE001
            res = None
        if res and res.get("source"):
            src = res["source"]
            via = "slm:" + str((res.get("engine") or {}).get("engine_id", "?"))
    if src is not None:
        return {"kind": "cf", "src": src, "via": via}
    return None


def differential(insns: List[str], synth: Dict[str, str]) -> Dict[str, Any]:
    """oracle(원본 바이트 실행) vs 합성 함수 차분 검증 → 일치율/벡터/불일치."""
    kind = synth["kind"]
    if kind == "straight":
        built = build_python(synth["src"], input_width(insns),
                             bool(synth.get("signed", True)))
        _o0, owid, _u0 = emulate(insns, 0)
        mask = (1 << owid) - 1
        if owid <= 8:
            vectors: List[int] = list(range(256))       # 바이트 함수 전수 검증
        else:
            rnd = random.Random(42)
            vectors = [rnd.randrange(1, 1 << min(owid, 32)) for _ in range(1024)]
        bad: List[int] = []
        comp = 0
        for v in vectors:
            comp += 1
            try:
                o, _, uns = emulate(insns, v)
                b = built(v) & mask
            except Exception:  # noqa: BLE001
                bad.append(v)
                continue
            if uns or (o & mask) != b:
                bad.append(v)
        match = 100.0 * (comp - len(bad)) / comp if comp else 0.0
        return {"kind": kind, "match_pct": round(match, 2), "vectors": comp,
                "mismatches": bad[:5], "out_width": owid, "exhaustive": owid <= 8}
    # 경로2: 제어흐름+메모리 — 루프 완주 가능한 bounded 벡터로 차분 검증
    built_fn = c_synthesize.build_func(synth["src"])
    vectors = list(range(-128, 257))                    # 음수·0·양수(루프/분기 포괄)
    comp = 0
    matches = 0
    bad = []
    owid = 32
    owid_set = False
    for v in vectors:
        try:
            o, w, uns = x86_cf_emu.run(insns, v)
        except Exception:  # noqa: BLE001
            continue
        if uns:
            continue                                    # oracle 이 이 입력에서 미완주 → 비교 불가
        if not owid_set:
            owid = w
            owid_set = True
        mask = (1 << owid) - 1
        comp += 1
        try:
            b = built_fn(v) & mask
        except Exception:  # noqa: BLE001
            bad.append(v)
            continue
        if (o & mask) == b:
            matches += 1
        else:
            bad.append(v)
    match = 100.0 * matches / comp if comp else 0.0
    return {"kind": "cf", "match_pct": round(match, 2), "vectors": comp,
            "mismatches": bad[:5], "out_width": owid, "exhaustive": False}


def craft_function(f: Dict[str, Any], is_pe: bool,
                   slm: Optional[Any] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """함수 facts 하나 → (검증 entry, None) 또는 (None, skip 사유)."""
    name = f.get("name", "?")
    dec = (f.get("decompile") or "").strip()
    raw_ins = f.get("insns") or []
    insns = raw_ins.splitlines() if isinstance(raw_ins, str) else [i for i in raw_ins if str(i).strip()]
    if not dec or not insns:
        return None, "디컴파일/명령 없음"
    synth = synth_for(dec, insns, is_pe, slm)
    if synth is None:
        return None, "합성 불가(직선·제어흐름 모두 정직 거부)"
    try:
        diff = differential(insns, synth)
    except Exception as exc:  # noqa: BLE001
        return None, f"차분검증 예외 {type(exc).__name__}"
    if synth["kind"] == "cf" and diff["vectors"] < _MIN_CF_COMPARABLE:
        return None, f"제어흐름 비교가능 벡터 부족({diff['vectors']}<{_MIN_CF_COMPARABLE})"
    entry = {"name": name, "kind": synth["kind"], "via": synth.get("via", "rule"),
             "expr": synth["src"], "out_width": diff["out_width"],
             "vectors": diff["vectors"], "match_pct": diff["match_pct"],
             "exhaustive": diff["exhaustive"], "mismatches": diff["mismatches"]}
    return entry, None


def craft(binary: Path, cap: int = 200, slm: Optional[Any] = None) -> Dict[str, Any]:
    """원본 바이너리에서 clean-room 복제 가능 함수를 골라 차분 검증.

    직선 스칼라 변환(Stage N) + 루프/분기/스택메모리 함수(Stage N3) 모두
    `craft_function` 한 경로로 처리하고, 100% 일치만 crafted 에 들어가요.
    """
    facts = re_analyzer.analyze(Path(binary), backend="auto", cap=cap)
    report: Dict[str, Any] = {"binary": Path(binary).name, "backend": facts["backend"],
                              "crafted": [], "skipped": []}
    is_pe = Path(binary).read_bytes()[:2] == b"MZ"
    for f in facts["functions"]:
        entry, why = craft_function(f, is_pe, slm)
        if entry is None:
            report["skipped"].append({"name": f.get("name", "?"), "why": why})
        else:
            report["crafted"].append(entry)
    report["all_verified"] = bool(report["crafted"]) and all(
        c["match_pct"] == 100.0 for c in report["crafted"])
    return report


# ── 기록: 검증된 craft 를 vault 노트로 ──────────────────────────────────────
def record(report: Dict[str, Any], vault_dir: Path) -> List[Path]:
    out: List[Path] = []
    d = Path(vault_dir) / "30_Ghidra"
    d.mkdir(parents=True, exist_ok=True)
    for c in report.get("crafted", []):
        if c["match_pct"] != 100.0:
            continue  # 미검증은 기록하지 않아요 — 발명 금지
        safe = re.sub(r"[^\w가-힝.-]", "_", f"{report['binary']}-{c['name']}")[:80]
        p = d / f"craft-{safe}.md"
        kind = c.get("kind", "straight")
        if kind == "cf":
            code_block = c["expr"]                       # 'def fn(x): ...' 전체 소스
            class_txt = "제어흐름 함수(루프/분기/스택 메모리)"
            oracle_txt = "제어흐름+메모리 x86-64 부분집합 에뮬레이터(네이티브 실행과 대조 검증됨)"
            build_txt = ("규칙 기반 C→파이썬 합성" if str(c.get("via", "rule")).startswith("rule")
                         else f"SLM 브리지 합성({c.get('via')}) + 차분 검증")
        else:
            code_block = f"lambda x: {c['expr']}"
            class_txt = "직선 스칼라 변환"
            oracle_txt = "직선 스칼라 x86-64 부분집합 에뮬레이터"
            build_txt = "규칙 기반 C 반환식 파싱"
        body = f"""---
title: "🛠 craft — {report['binary']}:{c['name']}"
category: "역공학·자가복제"
tags: [machine-output, crafted, clean-room, {report['backend']}]
kind: "code"
created: ""
---

# 🛠 craft — {report['binary']}:{c['name']}

## 💡 핵심 요약
원본 바이트를 직접 실행한 에뮬레이터와 차분 테스트 **{c['match_pct']}%**
({c['vectors']}개 벡터{', 전수 검증' if c['exhaustive'] else ''}) 를 통과한 자가 복제 {class_txt}이에요.

## 🔩 합성된 변환 (Ghidra 디컴파일 C 로부터)
```python
{code_block}
```

## 🧭 출처와 방법
영감: storytold/craft-anything (MIT OR Apache-2.0) — 검사→제작→비교 루프.
검사=Ghidra(PyGhidra) · 제작={build_txt} · 비교={oracle_txt}.
불일치였다면(100% 미만) 이 노트는 존재하지 않아요 — 발명 금지, 증거만 기록.
"""
        p.write_text(body, encoding="utf-8")
        out.append(p)
    return out
