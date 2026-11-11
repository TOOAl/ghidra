#!/usr/bin/env python3
"""🌀 Stage N3 — SLM online 합성경로 기계증명 (mock 로컬 LLM).

dormant SLM 브리지의 **online 분기**를 mock 로컬 LLM(OpenAI 호환, 127.0.0.1:8080)
으로 띄워 기계 증명해요. 핵심 주장: SLM 이 환각( 그럴듯하지만 틀린 코드)을 돌려줘도
**차분 검증 게이트**(원본 바이트 oracle vs 합성)가 잡아내 vault 기록을 차단한다.

자가완결·멱등: mock 서버는 테스트 프로세스 안 daemon 스레드(127.0.0.1 전용, 외부
네트워크 0), 임시 디렉터리만 사용, 끝나면 shutdown. 어떤 검사든 실패하면 exit 1.

커버:
  1) online 탐지 — mock 엔진 감지(detect_active_engine online=True, llama_cpp)
  2) 올바른 합성 — LLM 이 정확한 fn 주면 차분 검증 100% (기록 가능)
  3) 환각 거부 ★ — plausible 하지만 틀린 fn → 정적검증은 통과하나 차분 <100% → record 0건
  4) 안전 거부 — LLM 출력에 import/던더 → safe_synth_source 정적 거부(source=None)
  5) 통합 라우팅 — 규칙 기반이 정직 실패(do-while)하는 실함수 dw 에서 synth_for 가
     SLM 을 상담 → 올바르면 100%, 환각이면 <100%; SLM 없으면 정직 skip. + dw oracle==native
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent
sys.path.insert(0, str(BRAIN))

from brain_engine import craft_engine as CE       # noqa: E402
from brain_engine import c_synthesize as SYN      # noqa: E402
from brain_engine import x86_cf_emu as EMU        # noqa: E402
from brain_engine import slm_bridge as SLM        # noqa: E402

# 실제 채집 픽스처: xorv(직선) + dw(do-while, 규칙기반 불가) — Ghidra insn·C·네이티브 정답
_FIXTURE = json.loads(r"""{"xorv":{"dec":"uint xorv(uint param_1)\n\n{\n  return param_1 ^ 0x5a;\n}","insns":["00100000:\tMOV EAX,EDI","00100002:\tXOR EAX,0x5a","00100005:\tRET"]},"dw":{"dec":"int dw(int param_1)\n\n{\n  int local_10;\n  int local_c;\n  \n  local_c = 0;\n  local_10 = 0;\n  do {\n    local_c = local_c + local_10;\n    local_10 = local_10 + 1;\n  } while (local_10 < param_1);\n  return local_c;\n}","insns":["0010003d:\tPUSH RBP","0010003e:\tMOV RBP,RSP","00100041:\tMOV dword ptr [RBP + -0x14],EDI","00100044:\tMOV dword ptr [RBP + -0x4],0x0","0010004b:\tMOV dword ptr [RBP + -0x8],0x0","00100052:\tMOV EAX,dword ptr [RBP + -0x8]","00100055:\tADD dword ptr [RBP + -0x4],EAX","00100058:\tADD dword ptr [RBP + -0x8],0x1","0010005c:\tMOV EAX,dword ptr [RBP + -0x8]","0010005f:\tCMP EAX,dword ptr [RBP + -0x14]","00100062:\tJL 0x00100052","00100064:\tMOV EAX,dword ptr [RBP + -0x4]","00100067:\tPOP RBP","00100068:\tRET"],"ground":{"-40":0,"-39":0,"-38":0,"-37":0,"-36":0,"-35":0,"-34":0,"-33":0,"-32":0,"-31":0,"-30":0,"-29":0,"-28":0,"-27":0,"-26":0,"-25":0,"-24":0,"-23":0,"-22":0,"-21":0,"-20":0,"-19":0,"-18":0,"-17":0,"-16":0,"-15":0,"-14":0,"-13":0,"-12":0,"-11":0,"-10":0,"-9":0,"-8":0,"-7":0,"-6":0,"-5":0,"-4":0,"-3":0,"-2":0,"-1":0,"0":0,"1":0,"2":1,"3":3,"4":6,"5":10,"6":15,"7":21,"8":28,"9":36,"10":45,"11":55,"12":66,"13":78,"14":91,"15":105,"16":120,"17":136,"18":153,"19":171,"20":190,"21":210,"22":231,"23":253,"24":276,"25":300,"26":325,"27":351,"28":378,"29":406,"30":435,"31":465,"32":496,"33":528,"34":561,"35":595,"36":630,"37":666,"38":703,"39":741,"40":780,"41":820,"42":861,"43":903,"44":946,"45":990,"46":1035,"47":1081,"48":1128,"49":1176,"50":1225,"51":1275,"52":1326,"53":1378,"54":1431,"55":1485,"56":1540,"57":1596,"58":1653,"59":1711,"60":1770,"61":1830,"62":1891,"63":1953,"64":2016,"65":2080,"66":2145,"67":2211,"68":2278,"69":2346,"70":2415,"71":2485,"72":2556,"73":2628,"74":2701,"75":2775,"76":2850,"77":2926,"78":3003,"79":3081,"80":3160}}}""")
XORV = _FIXTURE["xorv"]
DW = _FIXTURE["dw"]

PASS = FAIL = 0


def check(cond: bool, label: str, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))


# ── mock 로컬 LLM (OpenAI 호환, 127.0.0.1 전용) ─────────────────────────────
class _MockHandler(BaseHTTPRequestHandler):
    RESPONSE = ""                                  # 시나리오별로 테스트가 설정

    def log_message(self, *a):                     # 요청 로그 침묵
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):                              # noqa: N802
        if self.path.startswith("/v1/models"):
            self._send({"object": "list", "data": [{"id": "mock-slm", "object": "model"}]})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):                             # noqa: N802
        n = int(self.headers.get("Content-Length", "0") or 0)
        self.rfile.read(n)                         # payload 소비(canned 응답)
        if self.path.startswith("/v1/chat/completions"):
            self._send({"choices": [{"message": {"role": "assistant",
                                                 "content": _MockHandler.RESPONSE}}]})
        else:
            self._send({"error": "not found"}, 404)


def _start_mock():
    srv = ThreadingHTTPServer(("127.0.0.1", 8080), _MockHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)                                # ready 대기
    return srv


def _fence(code: str) -> str:
    return "Sure, here is the clean-room function:\n```python\n" + code + "\n```"


CORRECT_XORV = _fence("def fn(x):\n    return (x ^ 0x5a)")
HALLUC_XORV = _fence("def fn(x):\n    return (x ^ 0x5a) + 7")     # 그럴듯하지만 틀림
UNSAFE_XORV = _fence("def fn(x):\n    import os\n    return x")   # 본문 내 import
CORRECT_DW = _fence(
    "def fn(x):\n"
    "    local_c = 0\n"
    "    local_10 = 0\n"
    "    _g = 0\n"
    "    while True:\n"
    "        _g += 1\n"
    "        if _g > 10000000:\n"
    "            break\n"
    "        local_c = (local_c + local_10) & 4294967295\n"
    "        local_10 = local_10 + 1\n"
    "        if not (local_10 < x):\n"
    "            break\n"
    "    return local_c & 4294967295")
HALLUC_DW = _fence(                                                # do-while→while 오역(범위 off)
    "def fn(x):\n"
    "    s = 0\n"
    "    i = 1\n"
    "    _g = 0\n"
    "    while (i <= x) and _g < 10000000:\n"
    "        _g += 1\n"
    "        s = (s + i) & 4294967295\n"
    "        i = i + 1\n"
    "    return s & 4294967295")


def _diff_pct(insns, src):
    d = CE.differential(insns, {"kind": "cf", "src": src})
    return d["match_pct"], d["vectors"]


def main() -> int:
    global FAIL
    print("🌀 Stage N3 — SLM online 합성경로 기계증명 (mock 로컬 LLM 127.0.0.1:8080)\n")
    srv = _start_mock()
    d = Path(tempfile.mkdtemp(prefix="slm_online_"))
    try:
        br = SLM.PortableSLMBridge(d / "models")

        print("[1] online 탐지")
        eng = br.detect_active_engine()
        check(eng.get("online") is True and eng.get("engine_id") == "llama_cpp",
              "mock 엔진 online 감지(llama_cpp)", str(eng.get("engine_id")))

        print("\n[2] 올바른 합성 → 차분 게이트 통과")
        _MockHandler.RESPONSE = CORRECT_XORV
        r = br.synthesize_python(XORV["dec"])
        check(r.get("source") is not None and r.get("via") == "llm",
              "LLM 응답에서 def fn(x) 추출(via=llm)", str(r.get("via")))
        pct, vec = _diff_pct(XORV["insns"], r["source"])
        check(pct == 100.0, f"올바른 합성 → 차분 100% ({vec}벡터)", f"match={pct}")

        print("\n[3] ★ 환각 → 차분 게이트 거부 (이 테스트의 핵심)")
        _MockHandler.RESPONSE = HALLUC_XORV
        r = br.synthesize_python(XORV["dec"])
        check(r.get("source") is not None,
              "환각은 '유효 파이썬'이라 정적 안전검증은 통과(=차분 게이트가 유일한 방어)",
              str(r.get("via")))
        pct, vec = _diff_pct(XORV["insns"], r["source"])
        check(pct < 100.0, f"★환각(xor+7) → 차분 검증이 잡아냄 match={pct}%<100%", f"match={pct}")
        rep = {"binary": "mock", "backend": "mock-slm", "skipped": [],
               "crafted": [{"name": "xorv", "kind": "cf", "expr": r["source"],
                            "match_pct": pct, "vectors": vec, "exhaustive": False,
                            "out_width": 32, "mismatches": [1]}]}
        written = CE.record(rep, d)
        check(len(written) == 0, "★환각 → vault 기록 0건(발명 금지, 구조적 차단)", f"{len(written)}건")

        print("\n[4] unsafe LLM 출력 → 정적 거부")
        _MockHandler.RESPONSE = UNSAFE_XORV
        r = br.synthesize_python(XORV["dec"])
        check(r.get("source") is None and r.get("via") == "llm-rejected",
              "본문 import → safe_synth_source 거부(source=None)", str(r.get("via")))

        print("\n[5] 통합 라우팅 — 규칙 기반 정직 실패(dw do-while)에서 SLM 상담")
        rb = SYN.synthesize(DW["dec"], CE.ident_map(DW["insns"], False))
        check(rb is None, "dw(do-while) → 규칙 기반 합성 정직 실패(None)", "규칙기반이 처리해버림")
        gok = gtot = 0
        for xs, exp in DW["ground"].items():
            o, w, uns = EMU.run(DW["insns"], int(xs))
            gtot += 1
            if not uns and (o & ((1 << w) - 1)) == (exp & 0xFFFFFFFF):
                gok += 1
        check(gok == gtot, f"dw oracle==native {gok}/{gtot} (차분 검증의 oracle 신뢰성)", "불일치")
        _MockHandler.RESPONSE = CORRECT_DW
        syn = CE.synth_for(DW["dec"], DW["insns"], False, slm=br)
        check(syn is not None and str(syn.get("via", "")).startswith("slm:"),
              f"synth_for 가 SLM 상담(via={syn.get('via') if syn else None})", "라우팅 실패")
        if syn:
            pct, vec = _diff_pct(DW["insns"], syn["src"])
            check(pct == 100.0, f"SLM 올바른 dw 합성 → 차분 100% ({vec}벡터) = 규칙기반이 못 하던 것", f"match={pct}")
        _MockHandler.RESPONSE = HALLUC_DW
        syn2 = CE.synth_for(DW["dec"], DW["insns"], False, slm=br)
        if syn2:
            pct2, _v2 = _diff_pct(DW["insns"], syn2["src"])
            check(pct2 < 100.0, f"★SLM 환각 dw(do-while 오역) → 차분 거부 match={pct2}%<100%", f"match={pct2}")
        syn3 = CE.synth_for(DW["dec"], DW["insns"], False, slm=None)
        check(syn3 is None, "SLM 없으면 dw 정직 skip(규칙기반 grounded 폴백은 발명 안 함)", "무언가 반환")
    except Exception:  # noqa: BLE001
        FAIL += 1
        print("  ❌ 예외:\n" + traceback.format_exc())
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(d, ignore_errors=True)
    print(f"\n{'✅ N3 SLM ONLINE PASSED' if FAIL == 0 else '❌ FAILED'} — {PASS} passed / {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
