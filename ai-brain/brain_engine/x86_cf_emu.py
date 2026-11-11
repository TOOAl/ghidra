"""🌀 Stage N3 — 제어흐름 + 메모리 x86-64 부분집합 에뮬레이터 (craft oracle 확장).

왜 존재하나
    Stage N 의 `craft_engine.emulate` 은 **직선 스칼라 코드**(점프·메모리 없음)만
    실행해서, 루프/분기/스택 지역변수를 쓰는 함수는 정직하게 skip 했어요(부채④).
    N3 는 이 oracle 을 **제어흐름(PC·조건점프·bounded 루프) + 스택 메모리**까지
    확장해서, 그 함수들의 입출력 ground truth 를 실제로 계산할 수 있게 해요.

정직 원칙 (가장 중요)
    이 에뮬레이터는 craft 의 **oracle**(원본 바이트의 참값)이에요. oracle 이
    틀리면 차분 검증이 오염되므로, 확신 없는 것은 절대 짐작하지 않고
    `unsupported` 에 넣고 **멈춰요**(craft 가 그 함수를 정직 skip). 지원 범위는
    의도적으로 좁고 보수적: CALL(다른 함수)·복잡한 addressing·캡 초과·**RET 없이
    끝나는(잘린) 명령 스트림** → bail.
    검증은 `tools/test_n3_craft.py`(제어흐름·메모리) 와 `tools/test_n4_muldiv.py`
    (곱셈·나눗셈 가족) 가 **gcc 네이티브 실행 ground truth** 와 전수 대조해요.

지원 명령(부분집합): mov/movzx/movsx/movsxd/lea · push/pop · add/sub/and/or/xor/
    shl/shr/sal/sar/rol/ror/not/neg/inc/dec · cmp/test · jmp/jcc · ret/leave · nop
    · **imul**(2-operand) · **N4 곱셈/나눗셈 가족**: 3-operand `imul dst,src,imm`
    (magic reciprocal) · one-op `mul`/`imul`(DX:AX 페어, 8/16/32/64) · `div`/`idiv`
    (몫→AX·나머지→DX, `idiv` 는 0 방향 절삭, 제수 0·몫 오버플로 #DE → bail) ·
    부호확장 `cdq`/`cqo`/`cwd`/`cdqe`/`cwde`/`cbw`.
메모리: `<size> ptr [base + index*scale + disp]` (base/index 는 GPR).
입력: 첫 "쓰기 전 읽힘" GPR(rsp/rbp 제외) = x (Stage N 과 동일 규칙), 또는 명시.
출력: rax(+마지막 rax 쓰기 폭).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ── 레지스터 모델 (craft_engine 과 동일한 별칭/폭 규칙) ──────────────────────
_WIDTHS = {"b": 8, "w": 16, "d": 32, "q": 64}
_BASES = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
          "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
_ALIASES: Dict[str, Tuple[str, int]] = {}
for _i, _b in enumerate(_BASES):
    _ALIASES[_b] = (_b, 64)
    if _i < 8:
        _core = _b[1:]                            # ax bx cx dx si di bp sp
        _ALIASES[_core] = (_b, 16)
        _ALIASES["e" + _core] = (_b, 32)
        if _i < 4:
            _ALIASES[_core[0] + "l"] = (_b, 8)    # al bl cl dl
            _ALIASES[_core[0] + "h"] = (_b, 8)    # ah bh ch dh
        else:
            # sil/dil/bpl/spl — REX 로만 접근되는 저바이트(고바이트는 없어요).
            # ⚠ 결함 수정(N4 감사에서 발견): 이전에 여기서 `_core[0] + "l"` 을
            #   써서 rsi→"sl", rdi→"dl", rbp→"bl", rsp→"sl" 이 만들어졌고, 그것이
            #   rdx 의 "dl"·rbx 의 "bl" 을 **덮어써** dl→rdi, bl→rbp 로 잘못
            #   매핑됐어요. 결과: `MOV BL,imm` 가 프레임 포인터 RBP 를 오염시켜
            #   `[RBP±K]` 가 엉뚱한 주소를 읽고, `MOV DL,imm` 가 입력 RDI 를
            #   오염 — 둘 다 `unsupported` 비어있는 **침묵 오답**이었어요.
            _ALIASES[_core + "l"] = (_b, 8)
    else:
        _ALIASES[_b + "d"] = (_b, 32)
        _ALIASES[_b + "w"] = (_b, 16)
        _ALIASES[_b + "b"] = (_b, 8)

_SIZE_BITS = {"byte": 8, "word": 16, "dword": 32, "qword": 64}


def reg_info(name: str) -> Optional[Tuple[str, int, int]]:
    """name → (base, shift, width_bits). 없으면 None."""
    n = name.strip().lower().rstrip(",")
    hit = _ALIASES.get(n)
    if not hit:
        return None
    base, wid = hit
    if n in ("ah", "bh", "ch", "dh"):
        return base, 8, 8
    return base, 0, wid


def _mask(w: int) -> int:
    return (1 << w) - 1


# 곱셈/나눗셈이 쓰는 누산기 레지스터 쌍 (low, high) — 폭별 DX:AX 페어
_ACC = {8: ("al", "ah"), 16: ("ax", "dx"), 32: ("eax", "edx"), 64: ("rax", "rdx")}


def _ssext(v: int, w: int) -> int:
    """w비트 값을 파이썬 signed 로 부호 확장."""
    v &= _mask(w)
    return v - (1 << w) if (v >> (w - 1)) & 1 else v


def _parse_imm(tok: str) -> int:
    tok = tok.strip().replace("$", "").replace(",", "")
    neg = tok.startswith("-")
    if neg:
        tok = tok[1:]
    if tok.lower().startswith("0x"):
        v = int(tok, 16)
    else:
        v = int(tok)
    return -v if neg else v


# ── 명령 행 파싱 ────────────────────────────────────────────────────────────
def parse_insn(line: str) -> Optional[Tuple[int, str, List[str]]]:
    """'<addr>:\\t<MNEM> <ops>' → (addr, mnem, [op,...]). 실패 시 None."""
    line = line.split(";", 1)[0].strip()
    if ":" not in line:
        return None
    addr_s, body = line.split(":", 1)
    try:
        addr = int(addr_s.strip(), 16)
    except ValueError:
        return None
    body = body.strip()
    if not body:
        return None
    parts = body.split(None, 1)
    mnem = parts[0].lower()
    ops: List[str] = []
    if len(parts) > 1 and parts[1].strip():
        ops = _split_ops(parts[1])
    return addr, mnem, ops


def _split_ops(s: str) -> List[str]:
    """콤마로 분리하되 [] 안의 콤마는 보호(이 부분집합엔 없지만 안전)."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class Operand:
    __slots__ = ("kind", "size", "base", "index", "scale", "disp", "reg", "imm")

    def __init__(self, kind: str) -> None:
        self.kind = kind                      # "reg" | "imm" | "mem"
        self.size = 64
        self.base: Optional[str] = None
        self.index: Optional[str] = None
        self.scale = 1
        self.disp = 0
        self.reg: Optional[str] = None
        self.imm = 0


def parse_operand(op: str) -> Optional[Operand]:
    op = op.strip()
    if not op:
        return None
    if "[" in op:
        o = Operand("mem")
        m = re.match(r"(byte|word|dword|qword)\s+ptr\s+", op, re.I)
        if m:
            o.size = _SIZE_BITS[m.group(1).lower()]
            op = op[m.end():]
        if "[" not in op or "]" not in op:
            return None
        inner = op[op.index("[") + 1:op.rindex("]")].strip()
        # 부호 보존 토큰화: '-' 를 '+-' 로 바꿔 '+' 로 가른 뒤 각 항의 부호 처리
        norm = re.sub(r"\s+", "", inner).replace("-", "+-")
        for term in [t for t in norm.split("+") if t]:
            if "*" in term:
                reg_s, sc_s = term.split("*", 1)
                ri = reg_info(reg_s)
                if not ri:
                    return None
                o.index = ri[0]
                o.scale = _parse_imm(sc_s)
            elif reg_info(term):
                ri = reg_info(term)
                if o.base is None:
                    o.base = ri[0]
                    # base 의 폭(64)을 메모리 피연산자 기본 폭으로(아직 size 없음)
                else:
                    o.index = ri[0]
            else:
                try:
                    o.disp += _parse_imm(term)
                except ValueError:
                    return None
        if o.base is None and o.index is None:
            return None                        # 절대주소 [0x..] 는 이 부분집합 밖
        return o
    ri = reg_info(op)
    if ri:
        o = Operand("reg")
        o.reg = op.strip().lower()
        o.size = ri[2]
        return o
    # 즉시값
    try:
        o = Operand("imm")
        o.imm = _parse_imm(op)
        o.size = 64
        return o
    except ValueError:
        return None


# ── 조건점프 테이블 ─────────────────────────────────────────────────────────
def _jcc_take(mnem: str, ZF: int, SF: int, OF: int, CF: int) -> Optional[bool]:
    t = {
        "jmp": True,
        "je": ZF == 1, "jz": ZF == 1,
        "jne": ZF == 0, "jnz": ZF == 0,
        "js": SF == 1, "jns": SF == 0,
        "jg": ZF == 0 and SF == OF, "jnle": ZF == 0 and SF == OF,
        "jge": SF == OF, "jnl": SF == OF,
        "jl": SF != OF, "jnge": SF != OF,
        "jle": ZF == 1 or SF != OF, "jng": ZF == 1 or SF != OF,
        "ja": CF == 0 and ZF == 0, "jnbe": CF == 0 and ZF == 0,
        "jae": CF == 0, "jnb": CF == 0, "jnc": CF == 0,
        "jb": CF == 1, "jnae": CF == 1, "jc": CF == 1,
        "jbe": CF == 1 or ZF == 1, "jna": CF == 1 or ZF == 1,
    }
    return t.get(mnem)


# ── 입력 레지스터 사전 탐지 (craft_engine.ident_map 과 동일 알고리즘) ────────
def _detect_input_reg(parsed: List[Tuple[int, str, List[str]]]) -> Optional[str]:
    """첫 '쓰기 전 읽힘' GPR(rsp/rbp 제외) = 함수 입력 레지스터.

    LEA/메모리 피연산자의 base/index 도 읽힘으로 counted — 이게 핵심. 게으른
    주입(read 시점)은 effective-address 경유 읽힘을 놓치므로, 실행 전에 미리
    결정해서 레지스터를 초기화해요.
    """
    written = {"rsp", "rbp"}
    order: List[str] = []
    mov_family = {"mov", "movzx", "movsx", "movsxd", "lea"}
    for _addr, mnem, ops in parsed:
        if not ops:
            continue
        read_toks = ops[1:] if mnem in mov_family else ops
        for tok_group in read_toks:
            for tok in re.split(r"[\[\]+*]", tok_group):
                info = reg_info(tok)
                if info and info[0] not in written and info[0] not in order:
                    order.append(info[0])
        dst = reg_info(ops[0])
        if dst:
            written.add(dst[0])
    return order[0] if order else None


# ── 본 에뮬레이터 ───────────────────────────────────────────────────────────
def run(insns: List[str], x: int, input_reg: Optional[str] = None,
        max_steps: int = 200_000) -> Tuple[int, int, List[str]]:
    """원본 바이트(Ghidra/objdump 텍스트)를 제어흐름+메모리 포함 실행.

    returns (rax_out, out_width_bits, unsupported).  unsupported 가 비어있지
    않으면 oracle 이 이 함수를 완주하지 못한 것 → craft 가 정직 skip 해야 해요.
    """
    parsed: List[Tuple[int, str, List[str]]] = []
    for ln in insns:
        p = parse_insn(str(ln))
        if p is not None:
            parsed.append(p)
    if not parsed:
        return 0, 32, ["parse:none"]
    addr2pc: Dict[int, int] = {a: i for i, (a, _, _) in enumerate(parsed)}

    regs: Dict[str, int] = {b: 0 for b in _BASES}
    out_width = 32
    mem: Dict[int, int] = {}                    # byte_addr → 0..255
    regs["rsp"] = 0x7FFF0000
    ZF = SF = OF = CF = 0
    unsupported: List[str] = []
    # 입력 레지스터를 실행 전에 미리 결정·초기화 (LEA/메모리 경유 읽힘도 정확히)
    in_base = reg_info(input_reg)[0] if input_reg else _detect_input_reg(parsed)  # type: ignore
    if in_base and in_base not in ("rsp", "rbp"):
        regs[in_base] = x & _mask(64)

    def rget(name: str) -> int:
        info = reg_info(name)
        base, shift, wid = info              # type: ignore
        return (regs[base] >> shift) & _mask(wid)

    def rset(name: str, val: int) -> None:
        nonlocal out_width
        info = reg_info(name)
        base, shift, wid = info              # type: ignore
        val &= _mask(wid)
        if wid == 64:
            regs[base] = val
        elif wid == 32 and shift == 0:
            regs[base] = val                 # 32비트 쓰기는 상위 zero(AMD64)
        else:
            m = _mask(wid) << shift
            regs[base] = (regs[base] & ~m) | (val << shift)
        if base == "rax" and shift == 0:
            out_width = wid

    def r64(name: str) -> int:
        info = reg_info(name)
        return regs[info[0]] & _mask(64)     # type: ignore

    def mem_read(addr: int, size: int) -> int:
        v = 0
        for i in range(size // 8):
            v |= mem.get(addr + i, 0) << (8 * i)
        return v & _mask(size)

    def mem_write(addr: int, size: int, val: int) -> None:
        val &= _mask(size)
        for i in range(size // 8):
            mem[addr + i] = (val >> (8 * i)) & 0xFF

    def eff(o: Operand) -> int:
        a = r64(o.base) if o.base else 0
        if o.index:
            a += r64(o.index) * o.scale
        return (a + o.disp) & _mask(64)

    def read_op(o: Operand) -> Tuple[int, int]:
        """피연산자 값 + 폭(bits)."""
        if o.kind == "imm":
            return o.imm, o.size
        if o.kind == "reg":
            info = reg_info(o.reg)
            return rget(o.reg), info[2]       # type: ignore
        # mem
        sz = o.size if o.size in (8, 16, 32, 64) else 64
        return mem_read(eff(o), sz), sz

    def write_op(o: Operand, val: int, width: int) -> None:
        if o.kind == "reg":
            rset(o.reg, val)
        elif o.kind == "mem":
            sz = width if width in (8, 16, 32, 64) else (o.size or 64)
            mem_write(eff(o), sz, val)
        # imm dst 는 불법 → 무시( caller 가 unsupported 처리 )

    def setflags_sub(a: int, b: int, w: int, res: int) -> None:
        nonlocal ZF, SF, OF, CF
        m = _mask(w)
        a &= m; b &= m; res &= m
        ZF = 1 if res == 0 else 0
        SF = (res >> (w - 1)) & 1
        CF = 1 if a < b else 0                        # unsigned borrow
        sa = (a >> (w - 1)) & 1; sb = (b >> (w - 1)) & 1
        OF = 1 if (sa != sb and SF != sa) else 0

    def setflags_add(a: int, b: int, w: int, res: int) -> None:
        nonlocal ZF, SF, OF, CF
        m = _mask(w)
        full = (a & m) + (b & m)
        CF = 1 if full > m else 0
        res &= m
        ZF = 1 if res == 0 else 0
        SF = (res >> (w - 1)) & 1
        sa = ((a & m) >> (w - 1)) & 1; sb = ((b & m) >> (w - 1)) & 1
        OF = 1 if (sa == sb and SF != sa) else 0

    def setflags_logic(res: int, w: int) -> None:
        nonlocal ZF, SF, OF, CF
        res &= _mask(w)
        ZF = 1 if res == 0 else 0
        SF = (res >> (w - 1)) & 1
        CF = 0; OF = 0

    pc = 0
    steps = 0
    ARITH = {"add", "sub", "and", "or", "xor", "adc", "sbb"}
    SHIFT = {"shl", "sal", "shr", "sar", "rol", "ror"}
    while pc < len(parsed):
        steps += 1
        if steps > max_steps:
            unsupported.append("step_cap")            # 무한루프 등 → 정직 bail
            break
        addr, mnem, ops = parsed[pc]
        nxt = pc + 1
        try:
            if mnem in ("nop", "endbr64", "endbr32"):
                pc = nxt; continue
            if mnem == "push":
                if len(ops) != 1:
                    unsupported.append(mnem); break
                o = parse_operand(ops[0])
                if not o or o.kind == "mem":
                    unsupported.append("push:" + ops[0]); break
                v, _ = read_op(o)
                regs["rsp"] = (regs["rsp"] - 8) & _mask(64)
                mem_write(regs["rsp"], 64, v)
                pc = nxt; continue
            if mnem == "pop":
                if len(ops) != 1:
                    unsupported.append(mnem); break
                o = parse_operand(ops[0])
                if not o or o.kind != "reg":
                    unsupported.append("pop:" + ops[0]); break
                v = mem_read(regs["rsp"], 64)
                regs["rsp"] = (regs["rsp"] + 8) & _mask(64)
                rset(ops[0], v)
                pc = nxt; continue
            if mnem == "leave":
                regs["rsp"] = regs["rbp"]
                regs["rbp"] = mem_read(regs["rsp"], 64)
                regs["rsp"] = (regs["rsp"] + 8) & _mask(64)
                pc = nxt; continue
            if mnem in ("ret", "retq"):
                return rget("rax"), out_width, unsupported
            if mnem == "mov" or mnem.startswith("movz") or mnem.startswith("movs") \
                    or mnem in ("movzx", "movsx", "movsxd"):
                if len(ops) != 2:
                    unsupported.append(mnem); break
                d = parse_operand(ops[0]); s = parse_operand(ops[1])
                if not d or not s or d.kind == "imm":
                    unsupported.append(mnem + ":bad"); break
                v, sw = read_op(s)
                dw = d.size if d.kind == "mem" else reg_info(d.reg)[2]  # type: ignore
                if mnem in ("movzx",):
                    v &= _mask(sw); dw = max(dw, sw)
                elif mnem in ("movsx", "movsxd"):
                    if (v >> (sw - 1)) & 1:
                        v |= ~_mask(sw)
                    v &= _mask(max(dw, 64))
                write_op(d, v, dw)
                pc = nxt; continue
            if mnem == "lea":
                if len(ops) != 2:
                    unsupported.append(mnem); break
                d = parse_operand(ops[0]); s = parse_operand(ops[1])
                if not d or d.kind != "reg" or not s or s.kind != "mem":
                    unsupported.append("lea:bad"); break
                write_op(d, eff(s), reg_info(d.reg)[2])              # type: ignore
                pc = nxt; continue
            # ── N4: 부호확장 + 곱셈/나눗셈 가족 (DX:AX 페어, 3-op imul, div/idiv) ──
            if mnem in ("cdq", "cqo", "cwd", "cdqe", "cwde", "cbw"):
                if mnem == "cdq":     rset("edx", _mask(32) if (rget("eax") >> 31) & 1 else 0)
                elif mnem == "cqo":   rset("rdx", _mask(64) if (rget("rax") >> 63) & 1 else 0)
                elif mnem == "cwd":   rset("dx", _mask(16) if (rget("ax") >> 15) & 1 else 0)
                elif mnem == "cdqe":  rset("rax", _ssext(rget("eax"), 32))
                elif mnem == "cwde":  rset("eax", _ssext(rget("ax"), 16))
                elif mnem == "cbw":   rset("ax", _ssext(rget("al"), 8))
                pc = nxt; continue
            if mnem in ("mul", "div", "idiv") or (mnem == "imul" and len(ops) in (1, 3)):
                if not ops:
                    unsupported.append(mnem + ":ops"); break
                if mnem == "imul" and len(ops) == 3:
                    d = parse_operand(ops[0]); s = parse_operand(ops[1])
                    if not d or d.kind != "reg" or not s:
                        unsupported.append("imul3:bad"); break
                    sv, _sw = read_op(s)
                    dwi = reg_info(d.reg)[2]                      # type: ignore
                    rset(d.reg, (sv * _parse_imm(ops[2])) & _mask(dwi))
                    pc = nxt; continue
                s = parse_operand(ops[0])
                if not s or s.kind == "imm":
                    unsupported.append(mnem + ":src"); break
                sv, w = read_op(s)
                if w not in (8, 16, 32, 64):
                    unsupported.append(mnem + ":w"); break
                lo, hi = _ACC[w]
                if mnem in ("mul", "imul"):
                    av = rget(lo)
                    if mnem == "imul":
                        prod = (_ssext(av, w) * _ssext(sv, w)) & _mask(2 * w)
                    else:
                        prod = (av * sv) & _mask(2 * w)
                    rset(lo, prod & _mask(w))
                    rset(hi, (prod >> w) & _mask(w))
                    pc = nxt; continue
                lowv = rget(lo); highv = rget(hi)
                dividend = (highv << w) | lowv                    # 2w 비트 (unsigned)
                if mnem == "idiv":
                    D = _ssext(dividend, 2 * w); dvs = _ssext(sv, w)
                else:
                    D = dividend; dvs = sv
                if dvs == 0:
                    unsupported.append(mnem + ":div0"); break      # #DE → 정직 bail
                if mnem == "idiv":
                    q = abs(D) // abs(dvs)
                    q = q if (D < 0) == (dvs < 0) else -q          # 0 절삭
                    r = D - q * dvs
                    if q >= (1 << (w - 1)) or q < -(1 << (w - 1)):
                        unsupported.append(mnem + ":of"); break    # #DE 오버플로
                else:
                    q = D // dvs; r = D % dvs
                    if q >= (1 << w):
                        unsupported.append(mnem + ":of"); break
                rset(lo, q & _mask(w))
                rset(hi, r & _mask(w))
                pc = nxt; continue
            if mnem in ARITH or mnem in SHIFT or mnem in ("not", "neg", "inc", "dec", "imul"):
                if not ops:
                    unsupported.append(mnem); break
                d = parse_operand(ops[0])
                if not d or d.kind == "imm":
                    unsupported.append(mnem + ":dst"); break
                a, dw = read_op(d)
                if mnem in ("not", "neg", "inc", "dec"):
                    res = {"not": ~a, "neg": -a, "inc": a + 1, "dec": a - 1}[mnem] & _mask(dw)
                    if mnem == "neg":
                        setflags_sub(0, a, dw, res); CF = 1 if (a & _mask(dw)) != 0 else 0
                    elif mnem in ("inc", "dec"):
                        cf_save = CF
                        setflags_add(a, 1 if mnem == "inc" else -1, dw, res); CF = cf_save
                    else:
                        setflags_logic(res, dw); CF = 0; OF = 0
                    write_op(d, res, dw)
                    pc = nxt; continue
                if len(ops) != 2:
                    unsupported.append(mnem + ":ops"); break
                s = parse_operand(ops[1])
                if not s:
                    unsupported.append(mnem + ":src"); break
                b, _bw = read_op(s)
                m = _mask(dw)
                if mnem in ("add", "adc"):
                    res = (a + b + (CF if mnem == "adc" else 0)) & m; setflags_add(a, b, dw, res)
                elif mnem in ("sub", "sbb"):
                    bb = b + (CF if mnem == "sbb" else 0)
                    res = (a - bb) & m; setflags_sub(a, bb, dw, res)
                elif mnem == "and":
                    res = (a & b) & m; setflags_logic(res, dw)
                elif mnem == "or":
                    res = (a | b) & m; setflags_logic(res, dw)
                elif mnem == "xor":
                    res = (a ^ b) & m; setflags_logic(res, dw)
                elif mnem == "imul":
                    res = (a * b) & m
                    ZF = SF = 0; CF = OF = 0
                elif mnem in ("shl", "sal"):
                    sh = b & 63; res = (a << sh) & m
                    setflags_logic(res, dw)
                elif mnem == "shr":
                    sh = b & 63; res = ((a & m) >> sh); setflags_logic(res, dw)
                elif mnem == "sar":
                    sh = b & 63; sa = a if not ((a >> (dw - 1)) & 1) else (a | ~m)
                    res = (sa >> sh) & m; setflags_logic(res, dw)
                elif mnem in ("rol", "ror"):
                    sh = b % dw if dw else 0
                    if mnem == "rol":
                        res = ((a << sh) | (a >> (dw - sh))) & m if sh else a & m
                    else:
                        res = ((a >> sh) | (a << (dw - sh))) & m if sh else a & m
                    setflags_logic(res, dw)
                else:
                    unsupported.append(mnem); break
                write_op(d, res, dw)
                pc = nxt; continue
            if mnem in ("cmp", "test"):
                if len(ops) != 2:
                    unsupported.append(mnem); break
                aop = parse_operand(ops[0]); bop = parse_operand(ops[1])
                if not aop or not bop:
                    unsupported.append(mnem + ":bad"); break
                a, w = read_op(aop)
                b, _ = read_op(bop)
                if mnem == "cmp":
                    setflags_sub(a, b, w, (a - b) & _mask(w))
                else:
                    setflags_logic(a & b, w)
                pc = nxt; continue
            if mnem.startswith("j"):
                if len(ops) != 1:
                    unsupported.append(mnem); break
                take = _jcc_take(mnem, ZF, SF, OF, CF)
                if take is None:
                    unsupported.append(mnem); break
                if take:
                    tgt = parse_operand(ops[0])
                    ta: Optional[int] = None
                    if tgt and tgt.kind == "imm":
                        ta = tgt.imm & _mask(64)
                    elif re.fullmatch(r"0x[0-9a-fA-F]+", ops[0].strip()):
                        ta = int(ops[0].strip(), 16)
                    if ta is None or ta not in addr2pc:
                        unsupported.append("jtarget:" + ops[0]); break
                    pc = addr2pc[ta]; continue
                pc = nxt; continue
            if mnem in ("call", "jmpq", "callq"):
                unsupported.append(mnem)          # 다른 함수 호출 → 정직 bail
                break
            unsupported.append(mnem)
            break
        except Exception as exc:                  # noqa: BLE001 — 예측 못 한 형태는 bail
            unsupported.append(f"{mnem}:{type(exc).__name__}")
            break
    # 여기에 도달했다는 것은 RET 을 만나지 못하고 명령 스트림이 끝났다는 뜻이에요.
    # 즉 채집이 잘린 것(함수 본문이 채집 캡 초과, 또는 꼬리 점프) — 이때 RAX 는
    # 참값이라는 보장이 전혀 없어요. 침묵 완주 주장 대신 **정직하게 bail** 해요.
    # (불명확한 명령·step_cap·jtarget 등으로 break 한 경우는 unsupported 가 이미
    #  비어있지 않으므로 이 표식이 중복 붙지 않아요.)
    if not unsupported:
        unsupported.append("trunc:no-ret")
    return rget("rax"), out_width, unsupported
