"""
brain/listener.py — 귀 1개 (우선순위 3)
사람 말(회의록·트윗·여론)에서 감성 점수 1개 추출 → 11차원 특징으로
"""
import re, json, pathlib
POS = ["좋다","지지","찬성","긍정","희망","상승"]
NEG = ["나쁘다","반대","부정","불안","하락","위기","공포"]

def listen(text: str) -> dict:
    if not text:
        return {"ok": False, "reason": "텍스트 없음"}
    p = sum(1 for w in POS if w in text)
    n = sum(1 for w in NEG if w in text)
    score = round((p - n) / max(1, p+n), 2)  # -1~+1
    label = "긍정" if score>0.3 else "부정" if score<-0.3 else "중립"
    # hindsight 저장 (사람 말을 들은 기록)
    try:
        h = pathlib.Path(__file__).parent.parent / "memory" / "hindsight.jsonl"
        h.parent.mkdir(exist_ok=True)
        rec = {"task": text[:20], "hindsight": f"귀 감성 {score} {label}"}
        with open(h, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
    except: pass
    return {"ok": True, "score": score, "label": label, "insight": f"사람 말 감성 {score} {label} → 11차원 특징"}

if __name__ == "__main__":
    print(listen("좋다 찬성 희망"))
    print(listen("위기 공포 하락"))
