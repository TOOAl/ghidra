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

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


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

        # Built-in Synapse Graph Memory Synthesizer (works 100% offline even before GGUF download!)
        if not recalled:
            answer = (
                "아직 제 위키 기억 주머니에 이 질문과 연결된 메모가 없어요! "
                "왼쪽 **'밥 주기 (지식·메모 먹이기)'** 칸에 주인님의 생각이나 노트를 던져주시면 즉시 시냅스로 기억할게요."
            )
        else:
            lines = [
                f"🧠 **내 머릿속 위키 그물망에서 관련 기억 카드 {len(recalled)}개**를 찾아 정리했어요 "
                f"*(전체 지식 대비 약 {recall_bundle.get('saved_tokens_pct', 0)}% 읽기 비용 절약!)*:\n"
            ]
            for n in recalled:
                lines.append(f"- **[[{n['title']}]]** *({n['category']})*: {n['summary']}")
            connected = []
            for n in recalled:
                for lk in n["links"]:
                    if lk not in connected and all(r["title"] != lk for r in recalled):
                        connected.append(lk)
            if connected:
                lines.append(f"\n🔗 **함께 이어지는 시냅스 고리**: " + ", ".join(f"`[[{c}]]`" for c in connected[:4]))
            lines.append(
                "\n💡 *참고: 지금 샌드박스에서는 무설치 '시냅스 기억 합성 모드'로 답하고 있어요. "
                "외장하드에 4비트/8비트 GGUF 모델(Gemma 4 E2B 또는 Qwen 0.8B)을 넣으면 같은 기억을 읽고 자유로운 문장 추론까지 수행합니다!*"
            )
            answer = "\n".join(lines)

        return {"answer": answer, "engine": engine}
