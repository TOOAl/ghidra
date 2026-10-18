"""
brain/model_adapter.py — 모든 LLM을 하나의 인터페이스로

미래에 어떤 모델이 나와도 여기만 바꾸면 됨.
OpenAI 호환 API를 표준으로 사용 (Ollama, OpenRouter, Groq, OpenAI 모두 지원)
Anthropic은 내부적으로 변환.
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelConfig:
    provider: str       # ollama | openrouter | groq | openai | anthropic
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 8192

    def resolved_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.getenv(self.api_key_env, "")
        # Ollama는 키 불필요
        if self.provider == "ollama":
            return "ollama"
        return ""

class ModelAdapter:
    """
    사용법:
        adapter = ModelAdapter(ModelConfig(provider="ollama", model="qwen3:14b"))
        resp = adapter.chat(
            system="너는 리버싱 전문가야",
            messages=[{"role": "user", "content": "main 함수 분석해줘"}],
            tools=GHIDRA_TOOLS
        )
        # resp = {"text": "...", "tool_calls": [{"name": "decompile", "input": {...}}]}
    """
    def __init__(self, config: ModelConfig):
        self.config = config
        self._client = None

    @classmethod
    def from_yaml(cls, path: str = "config/models.yaml", preset: Optional[str] = None):
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        if preset:
            cfg = data["presets"][preset]
        else:
            cfg = data["default"]
        return cls(ModelConfig(**cfg))

    def _get_openai_client(self):
        # 지연 import — openai 패키지 없으면 에러 메시지
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install openai 필요 (Ollama/OpenRouter/Groq 모두 이 패키지로 호출)")
        return OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.resolved_api_key()
        )

    def chat(self, system: str, messages: list, tools: list = None) -> dict:
        """
        모든 provider를 OpenAI Chat Completions 형태로 통일.
        반환: {"text": str, "tool_calls": [{"id": str, "name": str, "input": dict}]}
        """
        if self.config.provider == "anthropic":
            return self._chat_anthropic(system, messages, tools)
        else:
            return self._chat_openai_compatible(system, messages, tools)

    def _chat_openai_compatible(self, system: str, messages: list, tools: list = None) -> dict:
        client = self._get_openai_client()
        # system을 messages 맨 앞에 추가 (OpenAI 방식)
        openai_messages = [{"role": "system", "content": system}] + messages

        kwargs = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"]
            }} for t in tools]
            kwargs["tool_choice"] = "auto"

        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        result = {"text": msg.content or "", "tool_calls": []}
        if msg.tool_calls:
            for tc in msg.tool_calls:
                import json
                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments or "{}")
                })
        return result

    def _chat_anthropic(self, system: str, messages: list, tools: list = None) -> dict:
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic 필요")
        client = anthropic.Anthropic(api_key=self.config.resolved_api_key())
        # Anthropic은 system 분리
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)
        result = {"text": "", "tool_calls": []}
        for block in resp.content:
            if block.type == "text":
                result["text"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
        return result

    def list_free_models(self) -> list:
        """OpenRouter 무료 모델 목록 (참고용)"""
        return [
            "qwen/qwen3-32b:free",
            "deepseek/deepseek-r1:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-nemo:free",
        ]
