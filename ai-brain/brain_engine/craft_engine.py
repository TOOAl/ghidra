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

# ── 레지스터 파일: 이름 → (base, shift, width bits) ─────────────────────────
_WIDTHS = {"b": 8, "w": 16, "d": 32, "q": 64}
_BASES = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
          "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]


_ALIASES: Dict[str, Tuple[str, int]] = {}
for _i, _b in enumerate(_BASES):
    _ALIASES[_b] = (_b, 64)
    if _i < 8:
        _core = _b[1:]
        _ALIASES[_core] = (_b, 16)
        _ALIASES["e" + _core] = (_b, 32)
        _ALIASES[_core[0] + "l"] = (_b, 8)
        if _i < 4:
            _ALIASES[_core[0] + "h"] = (_b, 8)
    else:
        _ALIASES[_b + "d"] = (_b, 32)
        _ALIASES[_b + "w"] = (_b, 16)
        _ALIASES[_b + "b"] = (_b, 8)


def _reg_info(name: str) -> Optional[Tuple[str, int, int]]:
    n = name.strip().lower()
    hit = _ALIASES.get(n)
    if not hit:
        return None
    base, wid = hit
    if n in ("ah", "bh", "ch", "dh"):
        return base, 8, 8
    return base, 0, wid


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


class _W:
    """폭이 감긴 정수 — C 의 byte/word 산술을 그대로 재현해요."""

    __slots__ = ("v", "w")

    def __init__(self, v: int, w: int) -> None:
        self.w = w
        self.v = int(v) & ((1 << w) - 1)

    def _o(self, o: Any) -> int:
        return o.v if isinstance(o, _W) else int(o)

    def __xor__(self, o): return _W(self.v ^ self._o(o), self.w)
    __rxor__ = __xor__
    def __or__(self, o): return _W(self.v | self._o(o), self.w)
    __ror__ = __or__
    def __and__(self, o): return _W(self.v & self._o(o), self.w)
    __rand__ = __and__
    def __add__(self, o): return _W(self.v + self._o(o), self.w)
    __radd__ = __add__
    def __sub__(self, o): return _W(self.v - self._o(o), self.w)
    def __rsub__(self, o): return _W(self._o(o) - self.v, self.w)
    def __lshift__(self, n): return _W(self.v << int(n), self.w)
    def __rshift__(self, n): return _W(self.v >> int(n), self.w)
    def __int__(self): return self.v
    def __index__(self): return self.v


def _concat22(a: Any, b: Any) -> int:
    av = int(a) if not isinstance(a, _W) else a.v
    bv = int(b) if not isinstance(b, _W) else b.v
    return ((av & 0xFFFF) << 16) | (bv & 0xFFFF)


_HELPERS = {"bswap16": lambda v: (((int(v) & 0xFF) << 8) | ((int(v) >> 8) & 0xFF)) & 0xFFFF,
            "CONCAT22": _concat22}


def build_python(expr: str, width: int) -> Any:
    code = compile(expr, "<craft>", "eval")

    def fn(x: int) -> int:
        val = eval(code, {"__builtins__": {}}, dict(_HELPERS, x=_W(x, width)))  # noqa: S307
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
def craft(binary: Path, cap: int = 200) -> Dict[str, Any]:
    """원본 바이너리에서 직선 스칼라 변환을 골라 clean-room 복제 + 차분 검증."""
    facts = re_analyzer.analyze(Path(binary), backend="auto", cap=cap)
    report: Dict[str, Any] = {"binary": Path(binary).name, "backend": facts["backend"],
                              "crafted": [], "skipped": []}
    for f in facts["functions"]:
        dec = (f.get("decompile") or "").strip()
        raw_ins = f.get("insns") or []
        if isinstance(raw_ins, str):
            raw_ins = raw_ins.splitlines()
        insns = [i for i in raw_ins if str(i).strip()]
        if not dec or not insns:
            report["skipped"].append({"name": f["name"], "why": "디컴파일/명령 없음"})
            continue
        is_pe = Path(binary).read_bytes()[:2] == b"MZ"
        expr = _c_to_lambda(dec, ident_map(insns, is_pe))
        if expr is None:
            report["skipped"].append({"name": f["name"], "why": "C 반환식 파싱 불가"})
            continue
        try:
            o0, owid, uns0 = emulate(insns, 0)
        except Exception as exc:  # noqa: BLE001
            report["skipped"].append({"name": f["name"], "why": f"에뮬 예외 {exc}"})
            continue
        if uns0:
            report["skipped"].append({"name": f["name"],
                                      "why": f"지원 밖 연산 {uns0[:3]}"})
            continue
        built = build_python(expr, input_width(insns))
        mask = (1 << owid) - 1
        if owid <= 8:
            vectors = list(range(256))          # 바이트 함수는 전수 검증
        else:
            rnd = random.Random(42)
            vectors = [rnd.randrange(1, 1 << min(owid, 32)) for _ in range(1024)]
        bad: List[int] = []
        for v in vectors:
            try:
                o, _, uns = emulate(insns, v)
                b = built(v) & mask
            except Exception:  # noqa: BLE001
                bad.append(v)
                continue
            if uns or (o & mask) != b:
                bad.append(v)
        match = 100.0 * (len(vectors) - len(bad)) / len(vectors)
        entry = {"name": f["name"], "expr": expr, "out_width": owid,
                 "vectors": len(vectors), "match_pct": round(match, 2),
                 "exhaustive": owid <= 8, "mismatches": bad[:5]}
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
({c['vectors']}개 벡터{', 전수 검증' if c['exhaustive'] else ''}) 를 통과한 자가 복제 변환이에요.

## 🔩 합성된 변환 (Ghidra 디컴파일 C 로부터)
```python
lambda x: {c['expr']}
```

## 🧭 출처와 방법
영감: storytold/craft-anything (MIT OR Apache-2.0) — 검사→제작→비교 루프.
우리 판은 외부 모델 없이: 검사=Ghidra(PyGhidra) · 제작=규칙 기반 C 파싱 ·
비교=원본 바이트 실행 소형 에뮬레이터. 불일치였다면 이 노트는 없었어요.
"""
        p.write_text(body, encoding="utf-8")
        out.append(p)
    return out
