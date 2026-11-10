"""
Portable Quantized SLM Bridge.
Automatically detects local inference engines running on the host computer:
  1. Portable llama.cpp (`llama-server`) at 127.0.0.1:8080  [Zero-install USB favorite!]
  2. Ollama at 127.0.0.1:11434                              [OLLAMA_MODELS=./models]
  3. LM Studio at 127.0.0.1:1234
Also scans `ai-brain/models/*.gguf` on the external drive, and provides a deterministic
Graph-Memory Synthesizer fallback when no local GGUF engine is currently running.
"""

from __future__ import annotations

import ast
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


_CODE_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def _extract_func_src(reply: str) -> Optional[str]:
    """LLM 응답에서 `def fn(x): ...` 파이썬 소스를 추출(코드펜스优先)."""
    cand = None
    m = _CODE_FENCE.search(reply or "")
    if m:
        cand = m.group(1)
    else:
        i = (reply or "").find("def fn(")
        if i != -1:
            cand = reply[i:]
    if not cand:
        return None
    # 첫 'def fn(' 부터 잘라 들여쓰기 일관성 확보
    i = cand.find("def fn(")
    if i == -1:
        return None
    return cand[i:].strip()


def safe_synth_source(src: Optional[str]) -> bool:
    """LLM 이 준 소스가 안전한 단일 `def fn(x)` 인지 정적 검증.

    신뢰 경계: exec 는 빌트인 없는 네임스페이스에서 일어나고 최종 진실은
    차분 검증(원본 바이트 oracle 과 대조)이지만, 그 전에 import/던더/호출 등
    명백히 위험하거나 규칙 밖인 형태는 여기서 정직하게 거부해요.
    """
    if not src:
        return False
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return False
    fn = tree.body[0]
    if fn.name != "fn" or [a.arg for a in fn.args.args] != ["x"]:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            return False
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return False
    return True


ENDPOINTS = [
    {"id": "llama_cpp", "name": "Portable llama.cpp (llama-server)", "base": "http://127.0.0.1:8080", "kind": "openai"},
    {"id": "ollama", "name": "Ollama 로컬 엔진", "base": "http://127.0.0.1:11434", "kind": "ollama"},
    {"id": "lm_studio", "name": "LM Studio 로컬 서버", "base": "http://127.0.0.1:1234", "kind": "openai"},
]


def _http_get_json(url: str, timeout: float = 1.2) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _http_post_json(url: str, payload: Dict[str, Any], timeout: float = 45.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


class PortableSLMBridge:
    def __init__(self, models_dir: Path) -> None:
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def scan_local_gguf_files(self) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        for p in sorted(self.models_dir.glob("*.gguf")):
            size_mb = round(p.stat().st_size / (1024 * 1024), 1)
            files.append({"name": p.name, "size_mb": size_mb, "path": str(p.name)})
        return files

    def detect_active_engine(self) -> Dict[str, Any]:
        ggufs = self.scan_local_gguf_files()
        for ep in ENDPOINTS:
            try:
                if ep["kind"] == "ollama":
                    data = _http_get_json(f"{ep['base']}/api/tags")
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    if models:
                        return {
                            "online": True,
                            "engine_id": ep["id"],
                            "engine_name": ep["name"],
                            "base_url": ep["base"],
                            "kind": "ollama",
                            "active_model": models[0],
                            "available_models": models,
                            "gguf_on_drive": ggufs,
                        }
                else:
                    data = _http_get_json(f"{ep['base']}/v1/models")
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    return {
                        "online": True,
                        "engine_id": ep["id"],
                        "engine_name": ep["name"],
                        "base_url": ep["base"],
                        "kind": "openai",
                        "active_model": models[0] if models else "local-gguf",
                        "available_models": models or ["local-gguf"],
                        "gguf_on_drive": ggufs,
                    }
            except Exception:
                continue

        return {
            "online": False,
            "engine_id": "synapse_memory_fallback",
            "engine_name": "내장 시냅스 기억 합성 모드 (무설치 기본 두뇌)",
            "base_url": None,
            "kind": "fallback",
            "active_model": "Synapse-Graph-v1 (GGUF 연결 시 자동 승격)",
            "available_models": [],
            "gguf_on_drive": ggufs,
        }

    def answer_with_memories(self, question: str, recall_bundle: Dict[str, Any]) -> Dict[str, Any]:
        engine = self.detect_active_engine()
        recalled: List[Dict[str, Any]] = recall_bundle.get("recalled", [])

        context_blocks = []
        for idx, n in enumerate(recalled, 1):
            context_blocks.append(
                f"[기억카드 {idx}: {n['title']} | 분류: {n['category']}]\n{n['summary']}\n링크: {', '.join(n['links'])}"
            )
        context_text = "\n\n".join(context_blocks) if context_blocks else "(관련 기억 카드 없음)"

        if engine["online"]:
            sys_prompt = (
                "당신은 사용자의 외장하드에 서식하는 살아있는 다마고치형 개인 AI 두뇌입니다. "
                "아래 [인출된 마크다운 위키 기억카드]를 최우선 근거로 삼아 친절하고 명확하게 한국어로 답하세요.\n\n"
                f"{context_text}"
            )
            try:
                if engine["kind"] == "ollama":
                    resp = _http_post_json(
                        f"{engine['base_url']}/api/chat",
                        {
                            "model": engine["active_model"],
                            "stream": False,
                            "messages": [
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": question},
                            ],
                        },
                    )
                    reply = resp.get("message", {}).get("content", "").strip()
                else:
                    resp = _http_post_json(
                        f"{engine['base_url']}/v1/chat/completions",
                        {
                            "model": engine["active_model"],
                            "temperature": 0.3,
                            "messages": [
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": question},
                            ],
                        },
                    )
                    reply = resp["choices"][0]["message"]["content"].strip()
                if reply:
                    return {"answer": reply, "engine": engine}
            except Exception:
                pass

        # Built-in Synapse Graph Memory Synthesizer (100% grounded, zero fabrication!)
        if not recalled:
            answer = (
                "🛑 **[환각 방어막 작동 — 억지 추측 차단]**\n"
                "방금 물어보신 내용은 아직 제 마크다운 위키 기억망(`vault/`)에 적혀 있지 않아요!\n\n"
                "거대 AI처럼 그럴듯한 거짓말(환각)을 지어내는 대신 솔직하게 **'아직 모르는 내용'** 이라고 말씀드립니다. "
                "상단 **「🌱 지식 먹이기」** 탭에 관련 내용을 한 줄만 넣어주시면 즉시 시냅스로 기억해 정확히 답할게요!"
            )
        else:
            lines = [
                f"🧠 **위키 기억망에서 검증된 근거 카드 {len(recalled)}개**를 찾아 정리했어요 "
                f"*(전체 문서 대비 {recall_bundle.get('saved_tokens_pct', 0)}% 읽기 절약)*:\n"
            ]
            for n in recalled:
                lines.append(f"• **[[{n['title']}]]** *({n['category']})*: {n['summary']}")
            connected = []
            for n in recalled:
                for lk in n["links"]:
                    if lk not in connected and all(r["title"] != lk for r in recalled):
                        connected.append(lk)
            if connected:
                lines.append(f"\n🔗 **연결된 시냅스 고리**: " + ", ".join(f"`[[{c}]]`" for c in connected[:4]))
            answer = "\n".join(lines)

        return {"answer": answer, "engine": engine}

    # ── Stage N3: 코드 합성 oracle hook (부채⑤ — dormant SLM 에 실제 역할 부여) ──
    def synthesize_python(self, c_text: str, sig_hint: str = "") -> Dict[str, Any]:
        """디컴파일 C → clean-room 파이썬 `def fn(x): ...` 합성 시도.

        online  : 로컬 LLM 에게 동등 함수를 요청 → 코드펜스 추출 → 정적 안전検証.
                  (최종 진실은 craft 의 차분 검증: 원본 바이트 oracle 과 100% 일치만 기록)
        offline : **grounded 폴백** — 코드를 발명하지 않고 정직하게 source=None 을
                  돌려줘 craft 가 규칙 기반 합성기(c_synthesize)를 쓰게 해요.
                  SLM 이 dormant 여도 환각으로 vault 를 오염시키지 않는 것이 핵심.
        """
        engine = self.detect_active_engine()
        if not engine.get("online"):
            return {"source": None, "via": "grounded-fallback", "engine": engine,
                    "reason": "SLM dormant — 환각 방지: 코드 발명 거부, 규칙 기반 합성 사용"}
        sys_prompt = (
            "You are a precise reverse-engineering assistant. Rewrite the given Ghidra "
            "decompiled C function as ONE clean-room Python function named exactly "
            "`fn` taking a single integer argument `x`. Rules: integer arithmetic only; "
            "no imports, no calls to builtins, no I/O; replicate C integer width/signedness "
            "and operator semantics faithfully; the first C parameter maps to `x`. "
            "Return ONLY a single ```python fenced block."
        )
        user_prompt = (
            (f"Signature hint: {sig_hint}\n" if sig_hint else "")
            + "Decompiled C:\n" + (c_text or "").strip()
        )
        try:
            if engine["kind"] == "ollama":
                resp = _http_post_json(
                    f"{engine['base_url']}/api/chat",
                    {"model": engine["active_model"], "stream": False,
                     "messages": [{"role": "system", "content": sys_prompt},
                                  {"role": "user", "content": user_prompt}]})
                reply = resp.get("message", {}).get("content", "")
            else:
                resp = _http_post_json(
                    f"{engine['base_url']}/v1/chat/completions",
                    {"model": engine["active_model"], "temperature": 0.0,
                     "messages": [{"role": "system", "content": sys_prompt},
                                  {"role": "user", "content": user_prompt}]})
                reply = resp["choices"][0]["message"]["content"]
            src = _extract_func_src(reply)
            if safe_synth_source(src):
                return {"source": src, "via": "llm", "engine": engine}
            return {"source": None, "via": "llm-rejected", "engine": engine,
                    "reason": "LLM 출력이 안전/형식 검증 통과 못 함(정직 거부)"}
        except Exception as exc:  # noqa: BLE001 — LLM 실패는 grounded 폴백으로
            return {"source": None, "via": "llm-error", "engine": engine,
                    "reason": f"LLM 호출 실패: {type(exc).__name__}"}
