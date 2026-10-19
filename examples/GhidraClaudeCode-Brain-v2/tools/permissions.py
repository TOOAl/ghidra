"""
tools/permissions.py — Claude Code 권한 4단계 중 최소 2단계만 구현

deny → allow → classifier → ask 중
v2 Phase 1은 deny(차단) + allow(자동 승인)만으로 80% 커버.
classifier/ask는 Phase 3에서 MCP와 함께 추가.
"""
BLOCKED = ["rm -rf /", ":(){", "mkfs", "shutdown", "reboot", "dd if=", "> /dev/sda"]

# 자동 승인 — 읽기 전용이면서 안전한 명령
ALLOWED_PREFIXES = [
    "ls", "cat", "head", "tail", "grep", "find", "wc", "echo",
    "git status", "git diff", "git log", "git branch",
    "python -m py_compile", "python verify",
]

def check(cmd: str) -> dict:
    """
    반환: {"ok": bool, "reason": str, "auto": bool}
    - ok=False → 즉시 차단
    - auto=True → 승인 없이 실행
    - auto=False → 사용자 확인 필요 (v2에서는 일단 허용으로 처리, Phase3에서 ask)
    """
    if not cmd or not cmd.strip():
        return {"ok": False, "reason": "명령어 없음", "auto": False}
    c = cmd.strip()
    for b in BLOCKED:
        if b in c:
            return {"ok": False, "reason": f"차단된 패턴: {b}", "auto": False}
    for p in ALLOWED_PREFIXES:
        if c.startswith(p):
            return {"ok": True, "reason": f"자동 승인: {p}", "auto": True}
    # 읽기 전용 도구는 항상 ok
    # 나머지는 허용하되 auto=False로 표시 (Phase3에서 ask 다이얼로그)
    return {"ok": True, "reason": "허용 (사용자 확인 권장)", "auto": False}
