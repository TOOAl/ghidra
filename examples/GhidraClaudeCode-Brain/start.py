#!/usr/bin/env python3
"""
start.py — 원클릭 실행기 (Windows/Mac/Linux 공통)
.env에 키를 넣어두면 PowerShell 환경변수 설정 없이 바로 8090에 연결된다.

사용법:
  copy .env.example .env   # 한 번만, 키 붙여넣기
  python start.py           # 끝 — 브라우저가 http://127.0.0.1:8090 자동으로 뜬다
  python start.py --preset openrouter_qwen3_free --task "C2 찾아줘"
"""
import os, sys, subprocess, pathlib, webbrowser, time, json, argparse

ROOT = pathlib.Path(__file__).parent
ENV_FILE = ROOT / ".env"

def load_dotenv():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k,v=line.split("=",1)
            k=k.strip(); v=v.strip().strip('"').strip("'")
            if k and v and "여기에" not in v:
                os.environ[k]=v
        print(f"[start] .env 로드: {ENV_FILE}")
    else:
        print(f"[start] .env 없음 — .env.example을 .env로 복사 후 키를 넣으면 자동 적용")

def ensure_deps():
    try:
        import openai, yaml, requests
        print(f"[start] 의존성 OK (openai {openai.__version__})")
        return True
    except ImportError as e:
        print(f"[start] 의존성 설치 중... ({e})")
        # pyyaml은 휠 실패 시 건너뛰고 openai+requests만 설치
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "-q"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "requests", "-q"])
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "pyyaml", "-q"])
            except: 
                print("[start] pyyaml 휠 없음 — 없이 진행 (UI는 모형 배지로 동작)")
            return True
        except Exception as e2:
            print(f"[start] pip 설치 실패: {e2}\n  → 수동: pip install openai requests")
            return False

def check_status():
    try:
        import requests
        r=requests.get("http://127.0.0.1:8090/api/status", timeout=2)
        j=r.json()
        llm=j.get("llm",{})
        print(f"[start] 서버 OK — default:{j.get('default')} presets:{len(j.get('presets',[]))} | LLM {llm.get('mode')} — {llm.get('detail')}")
        return j
    except Exception as e:
        print(f"[start] 서버 아직 안 켜짐: {e}")
        return None

def api_set_preset(preset):
    try:
        import requests
        r=requests.post("http://127.0.0.1:8090/api/set_model", json={"preset": preset}, timeout=5)
        print(f"[start] 모델 교체: {preset} → {r.json()}")
    except Exception as e:
        print(f"[start] 모델 교체 실패: {e}")

def api_run(task, binary, preset):
    import requests
    r=requests.post("http://127.0.0.1:8090/api/run", json={"task":task, "binary":binary, "preset":preset}, timeout=60)
    j=r.json()
    print("\n"+"="*60+"\n[결과] "+task+"\n"+"="*60)
    print(j.get("report","")[:3000])
    if j.get("llm"):
        print(f"\n[LLM] {j['llm']}")
    return j

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Ghidra Brain 원클릭 실행기")
    ap.add_argument("--preset", help="모델 프리셋 (예: openrouter_qwen3_free)")
    ap.add_argument("--task", help="바로 실행할 작업 (예: 'C2 찾아줘')")
    ap.add_argument("--binary", default="/bin/ls", help="바이너리 경로")
    ap.add_argument("--no-browser", action="store_true", help="브라우저 자동 열기 안 함")
    ap.add_argument("--sync", action="store_true", help="git pull 먼저 실행 (Arena 최신 가져오기)")
    args=ap.parse_args()

    load_dotenv()
    if args.sync:
        try:
            subprocess.call(["git","pull","origin","arena/61934e9d-ghidra"], cwd=str(ROOT.parent.parent))
        except: pass
    ensure_deps()

    # 서버가 이미 켜져있으면 재사용, 아니면 새로 켜기
    st=check_status()
    proc=None
    if not st:
        print("[start] 서버 시작: python ui/server.py → http://127.0.0.1:8090")
        proc=subprocess.Popen([sys.executable, "ui/server.py"], cwd=str(ROOT))
        time.sleep(1.5)
        check_status()
        if not args.no_browser:
            try: webbrowser.open("http://127.0.0.1:8090")
            except: pass
        print("[start] 서버 PID", proc.pid, "— 종료하려면 Ctrl+C")
    else:
        print("[start] 기존 서버 재사용 — 브라우저에서 http://127.0.0.1:8090 열려있음")
        if not args.no_browser:
            try: webbrowser.open("http://127.0.0.1:8090")
            except: pass

    if args.preset:
        time.sleep(0.5)
        api_set_preset(args.preset)
        check_status()
    if args.task:
        api_run(args.task, args.binary, args.preset or "")
    if proc:
        try: proc.wait()
        except KeyboardInterrupt: proc.terminate(); print("\n[start] 서버 종료")
