"""🌀 Stage N3 — Ghidra 디컴파일 C 부분집합 → 파이썬 함수 합성기.

왜 존재하나
    Stage N 의 `craft_engine._c_to_lambda` 는 C 의 **단일 반환식**(`return <expr>;`)
    만 파이썬 람다로 만들 수 있었어요. 그래서 루프·분기·스택 지역변수를 쓰는
    함수는 합성 자체가 불가 → 정직 skip 했죠(부채④).

    N3 는 디컴파일 C 의 **작은 부분집합**(선언·대입·for·while·if/else·return·
    산술/논리/비트/비교 연산·캐스트)을 **폭·부호 인식 파이썬 함수**로 옮기는 규칙
    기반 합성기를 추가해요. 외부 모델 없이 결정론적·무료로 동작하고, 파싱할 수
    없는 형태는 절대 짐작하지 않고 `None`(→ 정직 skip) 을 돌려줘요.

정직 원칙
    이 합성기는 craft 의 **build**(clean-room 제작) 단계예요. 제작 결과가 원본과
    같은지는 `craft_engine` 가 **차분 검증**(원본 바이트 실행 oracle vs 합성 함수)
    으로 확인하고, 100% 일치만 vault 에 기록해요. 합성기가 잘못 만들어도 차분
    검증이 잡아내므로 **환각 기록은 구조적으로 불가능**해요. SLM 브리지가 online
    일 때는 LLM 합성을 추가 시도할 수 있고(역시 차분 검증 통과분만 기록),
    offline(dormant) 일 때는 이 규칙 기반 합성이 grounded 폴백이 돼요.
"""
from __future__ import annotations

import ast
import re
from typing import Dict, List, Optional, Tuple

# C 타입 → 비트 폭 / 부호
_TYPE_WIDTH = {
    "char": 8, "byte": 8, "undefined1": 8, "bool": 8,
    "short": 16, "ushort": 16, "undefined2": 16, "word": 16,
    "int": 32, "uint": 32, "undefined4": 32, "dword": 32,
    # Ghidra x86-64(LP64) 렌더에서 `long`/`ulong` 은 8 바이트(64비트)다.
    # (32비트로 두면 64비트 곱셈 반환을 잘못 잘라 차분 게이트가 거부한다.)
    "long": 64, "ulong": 64,
    "undefined8": 64, "qword": 64, "longlong": 64, "ulonglong": 64,
    "size_t": 64, "pointer": 64,
}
_UNSIGNED_TYPES = {"byte", "undefined1", "bool", "ushort", "word", "undefined2",
                   "uint", "undefined4", "dword", "ulong", "ulonglong", "undefined8",
                   "qword", "size_t", "pointer"}
_CAST_RE = re.compile(
    r"\(\s*(?:unsigned\s+|signed\s+)?(?:const\s+)?"
    r"(byte|char|short|ushort|int|uint|long|ulong|longlong|ulonglong|"
    r"undefined\d*|dword|qword|word|size_t|void)\s*\)")

_LOOP_GUARD = 2_000_000        # 합성 루프의 안전 캡(진짜 무한루프만 차단)
_IDENT = re.compile(r"[A-Za-z_]\w*")


class _DivModToHelper(ast.NodeTransformer):
    """C 정수 `a/b`·`a%b`(0 절삭, 피제수 부호) 를 런타임 헬퍼 호출로 치환.

    파이썬 `//`·`%` 는 음수에서 C 와 결과가 달라서(바닥 나눗셈) 그대로 두면
    환각이 된다. 제수가 0 이 아닌 상수일 때만 변환(비트폭 추정이 안전);
    그 외엔 그대로 두고 상위의 안전 검증이 거부하게 한다.
    """

    def visit_BinOp(self, node):  # noqa: N802
        self.generic_visit(node)
        if not isinstance(node.op, (ast.Div, ast.Mod)):
            return node
        fname = "_tdiv" if isinstance(node.op, ast.Div) else "_tmod"
        return ast.Call(func=ast.Name(id=fname, ctx=ast.Load()),
                        args=[node.left, node.right], keywords=[])


def _mask(w: int) -> int:
    return (1 << w) - 1


def _wrap(v: int, w: int, signed: bool) -> int:
    """C 대입 semantics: 폭 w 로 자르고, signed 면 두's complement 부호 복원."""
    v &= _mask(w)
    if signed and v >= (1 << (w - 1)):
        v -= (1 << w)
    return v


# ── 괄호/중괄호 매칭 ────────────────────────────────────────────────────────
def _match(s: str, i: int, open_ch: str, close_ch: str) -> int:
    if i >= len(s) or s[i] != open_ch:
        return -1
    depth = 0
    j = i
    while j < len(s):
        if s[j] == open_ch:
            depth += 1
        elif s[j] == close_ch:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def _split_top(s: str, sep: str = ";") -> List[str]:
    out, dp, db, dk, cur = [], 0, 0, 0, ""
    for ch in s:
        if ch == "(":
            dp += 1
        elif ch == ")":
            dp -= 1
        elif ch == "[":
            dk += 1
        elif ch == "]":
            dk -= 1
        elif ch == "{":
            db += 1
        elif ch == "}":
            db -= 1
        if ch == sep and dp == 0 and db == 0 and dk == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


# ── 표현식 번역 ─────────────────────────────────────────────────────────────
def xlate_expr(expr: str, imap: Dict[str, str]) -> Optional[str]:
    """C 표현식 → 파이썬 표현식. 미지원 구성이면 None(정직 거부)."""
    e = expr.strip()
    if not e:
        return None
    # 미지원 구성(포인터 역참조 `*p`·주소연산 `&x`·함수호출 `f()`·구조체 `a.b`·
    # 배열 `a[i]`) 은 텍스트로 짐작해 거부하지 않고, 아래 ast.parse + 노드 워크가
    # 정확히 걸러내요: 단항 `*p`/`&x` 는 eval 모드에서 SyntaxError, `a.b`→Attribute,
    # `f()`→Call, `a[i]`→Subscript, `*a`→Starred 는 노드 워크가 거부. 이진 `a*b`/
    # `a&b` 는 유효한 파이썬 식이라 통과(곱셈·비트AND — 정확히 원하는 동작).
    prev = None
    while prev != e:                             # 중첩 캐스트 제거
        prev = e
        e = _CAST_RE.sub("", e)
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    # C 정수 리터럴 접미어(U/L/UL/LL …) 제거 — Ghidra 가 `1U` `0xffU` 등으로 출력
    e = re.sub(r"\b(0[xX][0-9a-fA-F]+|\d+)[uUlL]+\b", r"\1", e)
    e = _IDENT.sub(lambda m: ("and" if m.group(0) == "and" else
                              "or" if m.group(0) == "or" else
                              "not" if m.group(0) == "not" else
                              imap.get(m.group(0), m.group(0))), e)
    e = re.sub(r"\s+", " ", e).strip()
    try:
        tree = ast.parse(e, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Subscript, ast.Starred)):
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, (float, complex, bytes, str)):
            return None                          # 부동소수/문자열 상수 → 이 부분집합 밖
    # C 정수 나눗셈/나머지는 0 절삭·피제수 부호 — 파이썬 `//`·`%` 와 음수에서
    # 달라서 충실 헬퍼 호출(_tdiv/_tmod)으로 AST 치환 후 unparse.
    try:
        tree = _DivModToHelper().visit(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except Exception:  # noqa: BLE001
        return None


# ── 선언/시그니처 파싱 ──────────────────────────────────────────────────────
_DECL_RE = re.compile(
    r"^\s*(?:unsigned\s+|signed\s+|const\s+)*([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*$")


def _decl_type_width(stmt: str) -> Optional[Tuple[str, str, int]]:
    """'int local_10' → ('local_10','int',32). 선언 아니면 None."""
    m = _DECL_RE.match(stmt.strip().rstrip(";").strip())
    if not m:
        return None
    typ, var = m.group(1).lower(), m.group(2)
    if typ not in _TYPE_WIDTH:
        return None
    return var, typ, _TYPE_WIDTH[typ]


def _sig_info(dec: str) -> Tuple[int, bool, Dict[str, Tuple[int, bool]]]:
    """시그니처 → (ret_width, ret_signed, {param_idx: (width, signed)})."""
    # 반환타입은 함수명 '바로 앞' 토큰:  `<ret_type> <name>(<params>) {`
    m = re.search(r"\b([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{", dec, re.S)
    ret_w, ret_s = 32, True
    pw: Dict[str, Tuple[int, bool]] = {}
    if m:
        rt = m.group(1).lower()
        ret_w = _TYPE_WIDTH.get(rt, 32)
        ret_s = rt not in _UNSIGNED_TYPES
        for i, p in enumerate([q.strip() for q in m.group(3).split(",") if q.strip()]):
            for t in p.replace("*", " ").split():
                if t.lower() in _TYPE_WIDTH:
                    pw[f"param_{i+1}"] = (_TYPE_WIDTH[t.lower()],
                                          t.lower() not in _UNSIGNED_TYPES)
                    break
    return ret_w, ret_s, pw


# ── 본문 번역 (재귀 하강) ───────────────────────────────────────────────────
class _Synth:
    def __init__(self, imap: Dict[str, str], widths: Dict[str, int],
                 signed: Dict[str, bool], ret_w: int, ret_s: bool) -> None:
        self.imap = imap
        self.widths = dict(widths)        # 파이썬 변수명 → bits
        self.signed = dict(signed)        # 파이썬 변수명 → 부호
        self.ret_w = ret_w
        self.ret_s = ret_s
        self.lines: List[str] = []
        self.guard = 0

    def _emit(self, indent: int, line: str) -> None:
        self.lines.append("    " * indent + line)

    def _pyname(self, ident: str) -> str:
        return self.imap.get(ident, ident)

    def _wrapexpr(self, pyvar: str, rhs_py: str) -> str:
        w = self.widths.get(pyvar, self.ret_w)
        s = self.signed.get(pyvar, self.ret_s)
        m = _mask(w)
        if s:
            half = 1 << (w - 1)
            return f"_w(({rhs_py}) & {m}, {half}, {1 << w})"
        return f"(({rhs_py}) & {m})"

    def _store(self, pyvar: str, rhs_py: str, indent: int) -> None:
        if pyvar not in self.widths:
            self.widths[pyvar] = self.ret_w
            self.signed[pyvar] = self.ret_s
        self._emit(indent, f"{pyvar} = {self._wrapexpr(pyvar, rhs_py)}")

    # ── 블록 ──
    def parse_block(self, body: str, indent: int) -> bool:
        body = body.strip()
        if body.startswith("{"):
            end = _match(body, 0, "{", "}")
            if end == -1:
                return False
            body = body[1:end - 1]
        pos, n = 0, len(body)
        while pos < n:
            while pos < n and body[pos] in " \t\r\n":
                pos += 1
            if pos >= n:
                break
            rest = body[pos:]
            kw = re.match(r"(for|while|if)\b", rest)
            if kw:
                consumed = self._control(rest, indent)
                if consumed < 0:
                    return False
                pos += consumed
                continue
            semi = self._find_semi(body, pos)
            if semi == -1:
                return False
            stmt = body[pos:semi].strip()
            pos = semi + 1
            if stmt and not self._simple_stmt(stmt, indent):
                return False
        return True

    def _find_semi(self, s: str, start: int) -> int:
        dp = db = dk = 0
        i = start
        while i < len(s):
            c = s[i]
            if c == "(":
                dp += 1
            elif c == ")":
                dp -= 1
            elif c == "[":
                dk += 1
            elif c == "]":
                dk -= 1
            elif c == "{":
                db += 1
            elif c == "}":
                db -= 1
            elif c == ";" and dp == 0 and db == 0 and dk == 0:
                return i
            i += 1
        return -1

    def _control(self, rest: str, indent: int) -> int:
        kw = re.match(r"(for|while|if)\s*\(", rest)
        if not kw:
            return -1
        head_start = rest.index("(", kw.end() - 1)
        head_end = _match(rest, head_start, "(", ")")
        if head_end == -1:
            return -1
        header = rest[head_start + 1:head_end - 1]
        after = rest[head_end:].lstrip()
        if after.startswith("{"):
            b_end = _match(after, 0, "{", "}")
            if b_end == -1:
                return -1
            block_body, tail = after[1:b_end - 1], after[b_end:]
        else:
            semi = self._find_semi(after, 0)
            if semi == -1:
                return -1
            block_body, tail = after[:semi], after[semi:]
        kind = kw.group(1)
        if kind in ("for", "while"):
            if not self._loop(kind, header, block_body, indent):
                return -1
        else:
            ok, tail = self._if_else(header, block_body, tail, indent)
            if not ok:
                return -1
        return head_end + (len(rest[head_end:]) - len(tail))

    def _loop(self, kind: str, header: str, block_body: str, indent: int) -> bool:
        incr_s = ""
        if kind == "for":
            parts = _split_top(header, ";")
            if len(parts) != 3:
                return False
            init_s, cond_s, incr_s = (p.strip() for p in parts)
            if init_s and not self._simple_stmt(init_s, indent):
                return False
        else:
            cond_s = header.strip()
        cond_py = xlate_expr(cond_s, self.imap)
        if cond_py is None:
            return False
        self.guard += 1
        g = f"_g{self.guard}"
        self._emit(indent, f"{g} = 0")
        self._emit(indent, f"while ({cond_py}) and {g} < {_LOOP_GUARD}:")
        self._emit(indent + 1, f"{g} += 1")
        if not self.parse_block(block_body, indent + 1):
            return False
        if incr_s and not self._simple_stmt(incr_s, indent + 1):
            return False
        return True

    def _if_else(self, header: str, block_body: str, tail: str,
                 indent: int) -> Tuple[bool, str]:
        cond_py = xlate_expr(header, self.imap)
        if cond_py is None:
            return False, tail
        self._emit(indent, f"if {cond_py}:")
        if not self.parse_block(block_body, indent + 1):
            return False, tail
        rest = tail.lstrip()
        if re.match(r"else\b", rest):
            after_else = rest[len("else"):].lstrip()
            if re.match(r"if\s*\(", after_else):
                consumed = self._control(after_else, indent)
                if consumed < 0:
                    return False, tail
                total = (len(tail) - len(rest)) + (len(rest) - len(after_else)) + consumed
                return True, tail[total:]
            if after_else.startswith("{"):
                e_end = _match(after_else, 0, "{", "}")
                if e_end == -1:
                    return False, tail
                else_body, else_tail = after_else[1:e_end - 1], after_else[e_end:]
            else:
                semi = self._find_semi(after_else, 0)
                if semi == -1:
                    return False, tail
                else_body, else_tail = after_else[:semi], after_else[semi:]
            self._emit(indent, "else:")
            if not self.parse_block(else_body, indent + 1):
                return False, tail
            total = len(tail) - len(else_tail)
            return True, tail[total:]
        return True, tail

    def _simple_stmt(self, stmt: str, indent: int) -> bool:
        stmt = stmt.strip().rstrip(";").strip()
        if not stmt:
            return True
        if stmt.startswith("return"):
            py = xlate_expr(stmt[len("return"):].strip(), self.imap)
            if py is None:
                return False
            # 반환은 rax 의 raw 비트(부호 없음 마스크) — oracle 과 동일 기준
            self._emit(indent, f"return ({py}) & {_mask(self.ret_w)}")
            return True
        head = stmt.split("=", 1)[0]
        d = _decl_type_width(head)
        if d:                                   # 선언 (초기화 동반 가능)
            var, typ, w = d
            pyvar = self._pyname(var)
            self.widths[pyvar] = w
            self.signed[pyvar] = typ not in _UNSIGNED_TYPES
            if "=" in stmt:
                rhs = xlate_expr(stmt.split("=", 1)[1], self.imap)
                if rhs is None:
                    return False
                self._store(pyvar, rhs, indent)
            else:
                self._emit(indent, f"{pyvar} = 0")
            return True
        if "=" in stmt and not re.match(r"(==|!=|<=|>=)", stmt):
            lhs, rhs = stmt.split("=", 1)
            lhs_py = lhs.strip()
            if not _IDENT.fullmatch(lhs_py):
                return False
            rhs_py = xlate_expr(rhs, self.imap)
            if rhs_py is None:
                return False
            self._store(self._pyname(lhs_py), rhs_py, indent)
            return True
        return False                            # '++', '--', 복합대입 등 → 거부


# 합성된 함수가 사용하는 런타임 헬퍼 (부호 wrap)
def _tdiv(a: int, b: int) -> int:
    """C 정수 나눗셈: 0 방향으로 절삭(파이썬 `//` 의 바닥 나눗셈과 다름)."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _tmod(a: int, b: int) -> int:
    """C 정수 나머지: 부호는 피제수(a)를 따름(파이썬 `%` 와 다름)."""
    return a - _tdiv(a, b) * b


_SYNTH_HELPERS = {
    "_w": lambda v, half, full: v - full if v >= half else v,
    "_tdiv": _tdiv,
    "_tmod": _tmod,
}


def synthesize(dec: str, imap: Optional[Dict[str, str]] = None) -> Optional[str]:
    """디컴파일 C → 'def fn(x): ...' 소스. 불가 시 None(정직 skip)."""
    imap = imap or {}
    dec = dec.strip()
    if not dec:
        return None
    b0 = dec.find("{")
    if b0 == -1:
        return None
    b1 = _match(dec, b0, "{", "}")
    if b1 == -1:
        return None
    body = dec[b0 + 1:b1 - 1]
    ret_w, ret_s, pw = _sig_info(dec)
    in_w, in_s = pw.get("param_1", (ret_w, ret_s))

    widths = {"x": in_w}
    signed = {"x": in_s}
    syn = _Synth(imap, widths, signed, ret_w, ret_s)
    if not syn.parse_block(body, 1):
        return None
    if not any(ln.strip().startswith("return") for ln in syn.lines):
        return None                              # 반환 경로 없음 → 거부

    lines = ["def fn(x):"]
    if in_s:
        half = 1 << (in_w - 1)
        lines.append(f"    x = _w((x) & {_mask(in_w)}, {half}, {1 << in_w})")
    else:
        lines.append(f"    x = (x) & {_mask(in_w)}")
    lines.extend(syn.lines)
    lines.append("    return 0")                 # 안전 기본 반환(도달 불가 정상)
    src = "\n".join(lines)
    try:
        ast.parse(src)
    except SyntaxError:
        return None
    return src


def build_func(src: str):
    """합성 소스 → 호출 가능한 fn(x). 제한 네임스페이스(빌트인 없음)."""
    ns: Dict[str, object] = {"__builtins__": {}}
    ns.update(_SYNTH_HELPERS)
    exec(compile(src, "<c_synth>", "exec"), ns)  # noqa: S102 — 차분 검증이 신뢰 게이트
    return ns["fn"]
