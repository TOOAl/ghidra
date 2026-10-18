#!/usr/bin/env python3
import json, random, pathlib
ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"
MEM.mkdir(parents=True, exist_ok=True)
templates = [
    ("C2 서버 찾아줘 http://c2.evil.com", ["list_strings","list_functions","get_xrefs"]),
    ("C2 통신 암호화 분석", ["list_strings","search_bytes","get_bytes"]),
    ("C2 http 요청 추적", ["get_xrefs","decompile","list_strings"]),
    ("취약점 버퍼오버플로우 찾아줘", ["search_bytes","decompile","get_bytes"]),
    ("취약점 패치 필요 주소", ["get_bytes","patch_bytes","list_imports"]),
    ("위기 연쇄 파산 예측", ["analyze_sessions","list_functions","get_xrefs"]),
    ("연쇄 위험 네트워크 분석", ["openrig_team","computer_use","live_debug"]),
    ("유동성 동결 레포 위기 분석", ["analyze_sessions","query_database","list_strings"]),
    ("정책 긴축 인플레 금리 예측", ["design_arch","predict_task","train_classifier"]),
    ("AI 버블 캐펙스 과열 분석", ["train_classifier","predict_task","analyze_sessions"]),
    ("자동 프로그램 알고리즘 트레이딩 분석", ["live_debug","search_bytes","get_bytes"]),
    ("여론 투표 침묵층 분석", ["query_database","create_block","search_memory"]),
    ("첩보 경보 비행 테러 예측", ["search_memory","list_js_modules","get_js_source"]),
]
random.seed(42)
sessions=[]
for i in range(100):
    t, tools = random.choice(templates)
    task = f"{t} #{i+1}"
    tool_log=[{"tool":tt,"input":{},"result_preview":"ok"} for tt in tools]
    sessions.append({"task":task,"tool_log":tool_log,"reasoning":{"ok":True},"preset":"mock"})
out=MEM/"session.jsonl"
if out.exists():
    bak=MEM/"session.jsonl.bak"
    try: bak.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    except: pass
out.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in sessions)+"\n", encoding="utf-8")
print(f"✅ 100 sessions {out}")
import sys
sys.path.insert(0,str(ROOT))
from ml.analysis import analyze
from ml.learn import train
print(analyze(100))
print(train())
