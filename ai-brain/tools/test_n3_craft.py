#!/usr/bin/env python3
"""🌀 Stage N3 기계 증명 — 제어흐름·메모리 craft(루프/분기/스택) 정직 게이트.

자가완결·멱등: 임시 디렉터리만 쓰고(라이브 state/vault 불변), 외부 모델·네트워크·
컴파일러 없이 **ฝัง된 실제 픽스처**(Ghidra analyzeHeadless insn + gcc 네이티브 실행
ground truth)만으로 검증 → 언제 어디서나 재현 가능. 어떤 검사든 실패하면 exit 1.

커버:
  1) oracle 정확성 — 제어흐름+메모리 에뮬레이터 == 네이티브 실행 (전수, 미지원 0)
  2) 합성 정확성 — 규칙 기반 C→파이썬 합성 == 네이티브 실행 (전수)
  3) 차분 게이트 — craft_function: oracle vs 합성 100% (루프/분기/메모리/lea/rotate)
  4) 정직(미지원) — CALL 등 → oracle bail → craft 는 거짓 100% 기록 안 함
  5) 정직(훼손) — 잘못된 합성 → 차분 검증 <100% → record 차단(발명 금지)
  6) SLM grounded 폴백 — dormant SLM 은 코드 발명 거부(source=None)
  7) 안전 합성 검증 — import/던더/비함수/시그니처 불일치 소스 거부
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent
sys.path.insert(0, str(BRAIN))

from brain_engine import x86_cf_emu as EMU       # noqa: E402
from brain_engine import c_synthesize as SYN     # noqa: E402
from brain_engine import craft_engine as CE      # noqa: E402
from brain_engine import slm_bridge as SLM       # noqa: E402

SPECIMEN_C = r"""/* N3 픽스처 출처 — 이 C 를 컴파일/실행해 ground truth 와 insn 을 채집했음.
   재현: gcc -O0 -c n3.c && gcc -O2 -c sl.c  →  네이티브 실행(ground truth)
        + Ghidra analyzeHeadless(pyghidra) 으로 insn 채집.  아래 픽스처는 그 산출물. */
/* -O0 : 루프/분기/스택메모리 */
int sum_to(int n){ int s=0; for(int i=1;i<=n;i++) s+=i; return s; }
int classify(int x){ if(x>10) return x*2; else if(x>0) return x+5; else return 0-x; }
int with_local(int x){ int t=x^0x5A; t=t+3; return t&0xFF; }
/* -O2 : 직선/lea/rotate/부분레지스터 */
int xorv(int x){ return x ^ 0x5A; }
int rotl(int x){ return (x<<3)|(x>>29); }
int mix(int x){ return ((x+1)^0xFF)-7; }"""

# 실제 채집 픽스처: 함수별 Ghidra insn + 디컴파일 C, 그리고 gcc 네이티브 실행 정답
# ⚠ classify 복구 기록(N4 감사): 최초 채집본은 `ghidra_facts_pyghidra.py` 의 함수별
#   insn 캡이 16 이어서 classify 가 정확히 16번째 명령(`POP RBP`)에서 **잘려** 있었어요
#   (마지막 `RET` 누락). 캡을 64 로 올린 뒤, 누락된 1개를 **독립 검증**으로 복구했어요:
#   SPECIMEN_C 를 gcc -O0 로 다시 컴파일하고 objdump 로 대조 → 주소 0x2e..0x55 가
#   픽스처와 명령·주소 모두 완전 일치, 그리고 `56: ret` 이 존재함을 확인. 즉 지어낸
#   값이 아니라 재현 가능한 증거로 확정한 1 명령이에요. oracle 이 이제 RET 없는
#   스트림을 `trunc:no-ret` 로 정직 bail 하므로, 잘린 픽스처는 조용히 통과할 수 없어요.
_FIXTURE = json.loads(r"""{"functions":{"sum_to":{"insns":["00100000:\tPUSH RBP","00100001:\tMOV RBP,RSP","00100004:\tMOV dword ptr [RBP + -0x14],EDI","00100007:\tMOV dword ptr [RBP + -0x4],0x0","0010000e:\tMOV dword ptr [RBP + -0x8],0x1","00100015:\tJMP 0x00100021","00100017:\tMOV EAX,dword ptr [RBP + -0x8]","0010001a:\tADD dword ptr [RBP + -0x4],EAX","0010001d:\tADD dword ptr [RBP + -0x8],0x1","00100021:\tMOV EAX,dword ptr [RBP + -0x8]","00100024:\tCMP EAX,dword ptr [RBP + -0x14]","00100027:\tJLE 0x00100017","00100029:\tMOV EAX,dword ptr [RBP + -0x4]","0010002c:\tPOP RBP","0010002d:\tRET"],"dec":"int sum_to(int param_1)\n\n{\n  int local_10;\n  int local_c;\n  \n  local_c = 0;\n  for (local_10 = 1; local_10 <= param_1; local_10 = local_10 + 1) {\n    local_c = local_c + local_10;\n  }\n  return local_c;\n}"},"classify":{"insns":["0010002e:\tPUSH RBP","0010002f:\tMOV RBP,RSP","00100032:\tMOV dword ptr [RBP + -0x4],EDI","00100035:\tCMP dword ptr [RBP + -0x4],0xa","00100039:\tJLE 0x00100042","0010003b:\tMOV EAX,dword ptr [RBP + -0x4]","0010003e:\tADD EAX,EAX","00100040:\tJMP 0x00100055","00100042:\tCMP dword ptr [RBP + -0x4],0x0","00100046:\tJLE 0x00100050","00100048:\tMOV EAX,dword ptr [RBP + -0x4]","0010004b:\tADD EAX,0x5","0010004e:\tJMP 0x00100055","00100050:\tMOV EAX,dword ptr [RBP + -0x4]","00100053:\tNEG EAX","00100055:\tPOP RBP","00100056:\tRET"],"dec":"int classify(int param_1)\n\n{\n  if (param_1 < 0xb) {\n    if (param_1 < 1) {\n      param_1 = -param_1;\n    }\n    else {\n      param_1 = param_1 + 5;\n    }\n  }\n  else {\n    param_1 = param_1 * 2;\n  }\n  return param_1;\n}"},"with_local":{"insns":["00100057:\tPUSH RBP","00100058:\tMOV RBP,RSP","0010005b:\tMOV dword ptr [RBP + -0x14],EDI","0010005e:\tMOV EAX,dword ptr [RBP + -0x14]","00100061:\tXOR EAX,0x5a","00100064:\tMOV dword ptr [RBP + -0x4],EAX","00100067:\tADD dword ptr [RBP + -0x4],0x3","0010006b:\tMOV EAX,dword ptr [RBP + -0x4]","0010006e:\tMOVZX EAX,AL","00100071:\tPOP RBP","00100072:\tRET"],"dec":"char with_local(byte param_1)\n\n{\n  return (param_1 ^ 0x5a) + 3;\n}"},"xorv":{"insns":["00100000:\tMOV EAX,EDI","00100002:\tXOR EAX,0x5a","00100005:\tRET"],"dec":"uint xorv(uint param_1)\n\n{\n  return param_1 ^ 0x5a;\n}"},"rotl":{"insns":["00100010:\tLEA EAX,[RDI*0x8]","00100017:\tSAR EDI,0x1d","0010001a:\tOR EAX,EDI","0010001c:\tRET"],"dec":"uint rotl(int param_1)\n\n{\n  return param_1 * 8 | param_1 >> 0x1d;\n}"},"mix":{"insns":["00100020:\tLEA EAX,[RDI + 0x1]","00100023:\tXOR AL,0xff","00100025:\tSUB EAX,0x7","00100028:\tRET"],"dec":"int mix(int param_1)\n\n{\n  return (param_1 + 1U ^ 0xff) - 7;\n}"}},"ground":{"-30":{"sum_to":0,"classify":30,"with_local":187,"xorv":4294967224,"rotl":4294967295,"mix":4294967061},"-29":{"sum_to":0,"classify":29,"with_local":188,"xorv":4294967225,"rotl":4294967295,"mix":4294967060},"-28":{"sum_to":0,"classify":28,"with_local":193,"xorv":4294967230,"rotl":4294967295,"mix":4294967059},"-27":{"sum_to":0,"classify":27,"with_local":194,"xorv":4294967231,"rotl":4294967295,"mix":4294967058},"-26":{"sum_to":0,"classify":26,"with_local":191,"xorv":4294967228,"rotl":4294967295,"mix":4294967057},"-25":{"sum_to":0,"classify":25,"with_local":192,"xorv":4294967229,"rotl":4294967295,"mix":4294967056},"-24":{"sum_to":0,"classify":24,"with_local":181,"xorv":4294967218,"rotl":4294967295,"mix":4294967055},"-23":{"sum_to":0,"classify":23,"with_local":182,"xorv":4294967219,"rotl":4294967295,"mix":4294967054},"-22":{"sum_to":0,"classify":22,"with_local":179,"xorv":4294967216,"rotl":4294967295,"mix":4294967053},"-21":{"sum_to":0,"classify":21,"with_local":180,"xorv":4294967217,"rotl":4294967295,"mix":4294967052},"-20":{"sum_to":0,"classify":20,"with_local":185,"xorv":4294967222,"rotl":4294967295,"mix":4294967051},"-19":{"sum_to":0,"classify":19,"with_local":186,"xorv":4294967223,"rotl":4294967295,"mix":4294967050},"-18":{"sum_to":0,"classify":18,"with_local":183,"xorv":4294967220,"rotl":4294967295,"mix":4294967049},"-17":{"sum_to":0,"classify":17,"with_local":184,"xorv":4294967221,"rotl":4294967295,"mix":4294967048},"-16":{"sum_to":0,"classify":16,"with_local":173,"xorv":4294967210,"rotl":4294967295,"mix":4294967047},"-15":{"sum_to":0,"classify":15,"with_local":174,"xorv":4294967211,"rotl":4294967295,"mix":4294967046},"-14":{"sum_to":0,"classify":14,"with_local":171,"xorv":4294967208,"rotl":4294967295,"mix":4294967045},"-13":{"sum_to":0,"classify":13,"with_local":172,"xorv":4294967209,"rotl":4294967295,"mix":4294967044},"-12":{"sum_to":0,"classify":12,"with_local":177,"xorv":4294967214,"rotl":4294967295,"mix":4294967043},"-11":{"sum_to":0,"classify":11,"with_local":178,"xorv":4294967215,"rotl":4294967295,"mix":4294967042},"-10":{"sum_to":0,"classify":10,"with_local":175,"xorv":4294967212,"rotl":4294967295,"mix":4294967041},"-9":{"sum_to":0,"classify":9,"with_local":176,"xorv":4294967213,"rotl":4294967295,"mix":4294967040},"-8":{"sum_to":0,"classify":8,"with_local":165,"xorv":4294967202,"rotl":4294967295,"mix":4294967039},"-7":{"sum_to":0,"classify":7,"with_local":166,"xorv":4294967203,"rotl":4294967295,"mix":4294967038},"-6":{"sum_to":0,"classify":6,"with_local":163,"xorv":4294967200,"rotl":4294967295,"mix":4294967037},"-5":{"sum_to":0,"classify":5,"with_local":164,"xorv":4294967201,"rotl":4294967295,"mix":4294967036},"-4":{"sum_to":0,"classify":4,"with_local":169,"xorv":4294967206,"rotl":4294967295,"mix":4294967035},"-3":{"sum_to":0,"classify":3,"with_local":170,"xorv":4294967207,"rotl":4294967295,"mix":4294967034},"-2":{"sum_to":0,"classify":2,"with_local":167,"xorv":4294967204,"rotl":4294967295,"mix":4294967033},"-1":{"sum_to":0,"classify":1,"with_local":168,"xorv":4294967205,"rotl":4294967295,"mix":248},"0":{"sum_to":0,"classify":0,"with_local":93,"xorv":90,"rotl":0,"mix":247},"1":{"sum_to":1,"classify":6,"with_local":94,"xorv":91,"rotl":8,"mix":246},"2":{"sum_to":3,"classify":7,"with_local":91,"xorv":88,"rotl":16,"mix":245},"3":{"sum_to":6,"classify":8,"with_local":92,"xorv":89,"rotl":24,"mix":244},"4":{"sum_to":10,"classify":9,"with_local":97,"xorv":94,"rotl":32,"mix":243},"5":{"sum_to":15,"classify":10,"with_local":98,"xorv":95,"rotl":40,"mix":242},"6":{"sum_to":21,"classify":11,"with_local":95,"xorv":92,"rotl":48,"mix":241},"7":{"sum_to":28,"classify":12,"with_local":96,"xorv":93,"rotl":56,"mix":240},"8":{"sum_to":36,"classify":13,"with_local":85,"xorv":82,"rotl":64,"mix":239},"9":{"sum_to":45,"classify":14,"with_local":86,"xorv":83,"rotl":72,"mix":238},"10":{"sum_to":55,"classify":15,"with_local":83,"xorv":80,"rotl":80,"mix":237},"11":{"sum_to":66,"classify":22,"with_local":84,"xorv":81,"rotl":88,"mix":236},"12":{"sum_to":78,"classify":24,"with_local":89,"xorv":86,"rotl":96,"mix":235},"13":{"sum_to":91,"classify":26,"with_local":90,"xorv":87,"rotl":104,"mix":234},"14":{"sum_to":105,"classify":28,"with_local":87,"xorv":84,"rotl":112,"mix":233},"15":{"sum_to":120,"classify":30,"with_local":88,"xorv":85,"rotl":120,"mix":232},"16":{"sum_to":136,"classify":32,"with_local":77,"xorv":74,"rotl":128,"mix":231},"17":{"sum_to":153,"classify":34,"with_local":78,"xorv":75,"rotl":136,"mix":230},"18":{"sum_to":171,"classify":36,"with_local":75,"xorv":72,"rotl":144,"mix":229},"19":{"sum_to":190,"classify":38,"with_local":76,"xorv":73,"rotl":152,"mix":228},"20":{"sum_to":210,"classify":40,"with_local":81,"xorv":78,"rotl":160,"mix":227},"21":{"sum_to":231,"classify":42,"with_local":82,"xorv":79,"rotl":168,"mix":226},"22":{"sum_to":253,"classify":44,"with_local":79,"xorv":76,"rotl":176,"mix":225},"23":{"sum_to":276,"classify":46,"with_local":80,"xorv":77,"rotl":184,"mix":224},"24":{"sum_to":300,"classify":48,"with_local":69,"xorv":66,"rotl":192,"mix":223},"25":{"sum_to":325,"classify":50,"with_local":70,"xorv":67,"rotl":200,"mix":222},"26":{"sum_to":351,"classify":52,"with_local":67,"xorv":64,"rotl":208,"mix":221},"27":{"sum_to":378,"classify":54,"with_local":68,"xorv":65,"rotl":216,"mix":220},"28":{"sum_to":406,"classify":56,"with_local":73,"xorv":70,"rotl":224,"mix":219},"29":{"sum_to":435,"classify":58,"with_local":74,"xorv":71,"rotl":232,"mix":218},"30":{"sum_to":465,"classify":60,"with_local":71,"xorv":68,"rotl":240,"mix":217},"31":{"sum_to":496,"classify":62,"with_local":72,"xorv":69,"rotl":248,"mix":216},"32":{"sum_to":528,"classify":64,"with_local":125,"xorv":122,"rotl":256,"mix":215},"33":{"sum_to":561,"classify":66,"with_local":126,"xorv":123,"rotl":264,"mix":214},"34":{"sum_to":595,"classify":68,"with_local":123,"xorv":120,"rotl":272,"mix":213},"35":{"sum_to":630,"classify":70,"with_local":124,"xorv":121,"rotl":280,"mix":212},"36":{"sum_to":666,"classify":72,"with_local":129,"xorv":126,"rotl":288,"mix":211},"37":{"sum_to":703,"classify":74,"with_local":130,"xorv":127,"rotl":296,"mix":210},"38":{"sum_to":741,"classify":76,"with_local":127,"xorv":124,"rotl":304,"mix":209},"39":{"sum_to":780,"classify":78,"with_local":128,"xorv":125,"rotl":312,"mix":208},"40":{"sum_to":820,"classify":80,"with_local":117,"xorv":114,"rotl":320,"mix":207},"41":{"sum_to":861,"classify":82,"with_local":118,"xorv":115,"rotl":328,"mix":206},"42":{"sum_to":903,"classify":84,"with_local":115,"xorv":112,"rotl":336,"mix":205},"43":{"sum_to":946,"classify":86,"with_local":116,"xorv":113,"rotl":344,"mix":204},"44":{"sum_to":990,"classify":88,"with_local":121,"xorv":118,"rotl":352,"mix":203},"45":{"sum_to":1035,"classify":90,"with_local":122,"xorv":119,"rotl":360,"mix":202},"46":{"sum_to":1081,"classify":92,"with_local":119,"xorv":116,"rotl":368,"mix":201},"47":{"sum_to":1128,"classify":94,"with_local":120,"xorv":117,"rotl":376,"mix":200},"48":{"sum_to":1176,"classify":96,"with_local":109,"xorv":106,"rotl":384,"mix":199},"49":{"sum_to":1225,"classify":98,"with_local":110,"xorv":107,"rotl":392,"mix":198},"50":{"sum_to":1275,"classify":100,"with_local":107,"xorv":104,"rotl":400,"mix":197},"51":{"sum_to":1326,"classify":102,"with_local":108,"xorv":105,"rotl":408,"mix":196},"52":{"sum_to":1378,"classify":104,"with_local":113,"xorv":110,"rotl":416,"mix":195},"53":{"sum_to":1431,"classify":106,"with_local":114,"xorv":111,"rotl":424,"mix":194},"54":{"sum_to":1485,"classify":108,"with_local":111,"xorv":108,"rotl":432,"mix":193},"55":{"sum_to":1540,"classify":110,"with_local":112,"xorv":109,"rotl":440,"mix":192},"56":{"sum_to":1596,"classify":112,"with_local":101,"xorv":98,"rotl":448,"mix":191},"57":{"sum_to":1653,"classify":114,"with_local":102,"xorv":99,"rotl":456,"mix":190},"58":{"sum_to":1711,"classify":116,"with_local":99,"xorv":96,"rotl":464,"mix":189},"59":{"sum_to":1770,"classify":118,"with_local":100,"xorv":97,"rotl":472,"mix":188},"60":{"sum_to":1830,"classify":120,"with_local":105,"xorv":102,"rotl":480,"mix":187}}}""")
FUNCS = _FIXTURE["functions"]
GROUND = _FIXTURE["ground"]
XS = sorted(int(k) for k in GROUND)

PASS = FAIL = 0


def check(cond: bool, label: str, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))


def _exp(name: str, x: int) -> int:
    v = GROUND[str(x)].get(name)
    if v is None:
        return 0
    return v & 0xFF if name == "with_local" else v & 0xFFFFFFFF


def test_oracle_vs_native() -> None:
    print("\n[1] oracle(제어흐름+메모리 에뮬레이터) vs 네이티브 실행 ground truth")
    for name, fx in FUNCS.items():
        bad = uns = n = 0
        for x in XS:
            if GROUND[str(x)].get(name) is None:
                continue
            n += 1
            o, w, u = EMU.run(fx["insns"], x)
            if u:
                uns += 1
                continue
            if (o & ((1 << w) - 1) & (0xFF if name == "with_local" else 0xFFFFFFFF)) != _exp(name, x):
                bad += 1
        check(bad == 0 and uns == 0, f"{name}: oracle==native ({n} 입력)", f"bad={bad} uns={uns}")


def test_synth_vs_native() -> None:
    print("\n[2] 규칙 기반 합성(C→파이썬) vs 네이티브 실행 ground truth")
    for name, fx in FUNCS.items():
        src = SYN.synthesize(fx["dec"], CE.ident_map(fx["insns"], False))
        if src is None:
            check(False, f"{name}: 합성 가능", "synthesize→None")
            continue
        fn = SYN.build_func(src)
        bad = n = 0
        for x in XS:
            if GROUND[str(x)].get(name) is None:
                continue
            n += 1
            try:
                got = fn(x) & 0xFFFFFFFF
            except Exception:  # noqa: BLE001
                bad += 1
                continue
            if got != _exp(name, x):
                bad += 1
        check(bad == 0, f"{name}: synth==native ({n} 입력)", f"bad={bad}")


def test_craft_differential() -> None:
    print("\n[3] craft 차분 게이트 — oracle vs 합성 100% 일치")
    for name, fx in FUNCS.items():
        f = {"name": name, "decompile": fx["dec"], "insns": fx["insns"]}
        entry, why = CE.craft_function(f, False)
        ok = entry is not None and entry["match_pct"] == 100.0 and not entry["mismatches"]
        check(ok, f"{name}: craft 100% (kind={entry['kind'] if entry else '—'})",
              why or (f"match={entry['match_pct']} mm={entry['mismatches']}" if entry else ""))


def test_honesty_unsupported() -> None:
    print("\n[4] 정직 — 미지원 구성(CALL) → oracle bail → 거짓 100% 기록 안 함")
    call_insns = ["00100000:\tPUSH RBP", "00100001:\tMOV RBP,RSP",
                  "00100004:\tCALL 0x00200000", "00100009:\tPOP RBP", "0010000a:\tRET"]
    _o, _w, u = EMU.run(call_insns, 1)
    check(bool(u), "CALL → oracle unsupported(정직 bail)", f"uns={u}")
    f = {"name": "f", "decompile": "int f(int param_1)\n\n{\n  return g(param_1);\n}",
         "insns": call_insns}
    entry, _why = CE.craft_function(f, False)
    check(entry is None or entry["match_pct"] != 100.0,
          "CALL 함수 → 100% 기록 안 됨", f"entry={entry}")


def test_honesty_corrupt() -> None:
    print("\n[5] 정직 — 잘못된 합성 → 차분 검증이 잡아내 record 차단")
    fx = FUNCS["sum_to"]
    wrong = {"kind": "cf", "src": "def fn(x):\n    return (x * 2) & 4294967295"}
    diff = CE.differential(fx["insns"], wrong)
    check(diff["match_pct"] < 100.0, "sum_to≠x*2 → match<100%", f"match={diff['match_pct']}")
    rep = {"binary": "x", "backend": "t", "skipped": [],
           "crafted": [{"name": "sum_to", "kind": "cf", "expr": wrong["src"],
                        "match_pct": diff["match_pct"], "vectors": diff["vectors"],
                        "exhaustive": False, "out_width": 32, "mismatches": diff["mismatches"]}]}
    d = Path(tempfile.mkdtemp(prefix="rec_"))
    try:
        written = CE.record(rep, d)
        check(len(written) == 0, "match<100% → vault 기록 0건(발명 금지)", f"{len(written)}건")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_slm_grounded_fallback() -> None:
    print("\n[6] SLM grounded 폴백 — dormant → 코드 발명 거부")
    d = Path(tempfile.mkdtemp(prefix="slm_"))
    try:
        br = SLM.PortableSLMBridge(d / "models")
        eng = br.detect_active_engine()
        res = br.synthesize_python("int f(int param_1)\n\n{\n  return param_1 ^ 0x5a;\n}")
        if not eng.get("online"):
            check(res.get("source") is None and res.get("via") == "grounded-fallback",
                  "offline SLM → source=None(환각 거부, 규칙 기반 폴백)", str(res.get("via")))
        else:
            check("source" in res, f"online SLM({eng.get('engine_id')}) — 합성 경로 활성")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_safe_synth_source() -> None:
    print("\n[7] 안전 합성 소스 정적 검증")
    check(SLM.safe_synth_source("def fn(x):\n    return x ^ 0x5a"), "정상 def fn(x) 허용")
    check(not SLM.safe_synth_source("import os\ndef fn(x):\n    return x"), "import 거부")
    check(not SLM.safe_synth_source("def fn(x):\n    return x.__class__"), "던더 접근 거부")
    check(not SLM.safe_synth_source("def g(x):\n    return x"), "fn 아닌 함수 거부")
    check(not SLM.safe_synth_source("def fn(x, y):\n    return x"), "시그니처 불일치 거부")
    check(not SLM.safe_synth_source("def fn(x): return (("), "구문 오류 거부")


def main() -> int:
    global FAIL
    print("🌀 Stage N3 기계 증명 — 제어흐름·메모리 craft 정직 게이트\n")
    print(f"픽스처: {len(FUNCS)} 함수 · {len(XS)} 입력 · 출처=실제 Ghidra insn + gcc 네이티브 실행")
    for t in (test_oracle_vs_native, test_synth_vs_native, test_craft_differential,
              test_honesty_unsupported, test_honesty_corrupt, test_slm_grounded_fallback,
              test_safe_synth_source):
        try:
            t()
        except Exception:  # noqa: BLE001
            FAIL += 1
            print("  ❌ 예외:\n" + traceback.format_exc())
    print(f"\n{'✅ N3 CRAFT PASSED' if FAIL == 0 else '❌ FAILED'} — {PASS} passed / {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
