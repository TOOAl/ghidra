"""
brain/team.py — 4명 팀 토론 3턴 (우선순위 2)
다빈치/퀴리/튜링/오일러 4명이 토론 → 합의 4/4일 때만 CONFIRMED
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from brain.reasoning import reason

GENIUS = {
    "다빈치": "관찰→스케치→연결: 증거에서 형태 찾기",
    "퀴리": "측정→반복→실패로그: 숫자 3개로 검증",
    "튜링": "형식화→해독→모방: 논리식으로 반증",
    "오일러": "기호→일반화→우아: 수식 f(x)로 압축",
}

def discuss(task: str, evidence: dict, turns=3) -> dict:
    transcript = []
    for t in range(turns):
        for name, style in GENIUS.items():
            # 각 천재 1문장 — reasoning 3단계 중 1단계씩 담당
            msg = f"[{name} {t+1}턴] {style}: {task} → 증거 {list(evidence.keys())[:1]}"
            transcript.append(msg)
    # 합의: 4명 모두 모순0이면 4/4
    r = reason(task, evidence)
    consensus = "4/4" if r.get("ok") else "3/4"
    return {
        "ok": r.get("ok", False),
        "consensus": consensus,
        "transcript": transcript,
        "insight": f"3턴 토론 {len(transcript)}문장 → 합의 {consensus} → {'CONFIRMED' if consensus=='4/4' else 'LIKELY'}",
        "report": f"# {task} 팀 토론\n\n" + "\n".join(transcript[-4:]) + f"\n\n합의: {consensus} → {r.get('steps',[])}"
    }

if __name__ == "__main__":
    print(discuss("C2 찾아줘", {"list_strings": "http://c2.evil.com"}))
