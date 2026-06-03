"""
growders.services.llm
──────────────────────
LLM abstraction layer.

Switch provider with one env var — no code changes in callers.

Implementations:
  MockLLM    — deterministic responses, zero API calls (testing / demo)
  GroqLLM    — Llama 3.1 8B via Groq (free tier, fast)
  OpenAILLM  — GPT-4o-mini (paid, higher quality)
  GeminiLLM  — Google Gemini Flash (alternative)

All providers share the same interface:
    response = await llm.chat(messages, system_prompt)

`messages` is a list of {"role": "user"|"assistant", "content": "..."}
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# ── Response dataclass ────────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    raw: dict = field(default_factory=dict)


# ── Interface ─────────────────────────────────────────────────────────────────

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


# ── Mock (Tier 0 / testing) ───────────────────────────────────────────────────

class MockLLM(LLMProvider):
    """
    Returns predictable responses without any API call.
    Used in tests and for demos when no API key is configured.
    """

    _RESPONSES = {
        "hola": "¡Hola! Soy MarIA, el asistente virtual de este negocio. ¿En qué puedo ayudarte?",
        "horario": "Nuestro horario de atención es de lunes a viernes de 9:00 a 18:00 y sábados de 10:00 a 14:00.",
        "precio": "Para darte información sobre precios necesito saber qué producto o servicio te interesa. ¿Puedes indicarme cuál?",
        "default": "Entendido. ¿Me puedes dar más detalles para poder ayudarte mejor?",
    }

    @property
    def provider_name(self) -> str:
        return "mock"

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        last_user = next(
            (m["content"].lower() for m in reversed(messages) if m["role"] == "user"),
            "",
        )

        response_text = self._RESPONSES["default"]
        for keyword, resp in self._RESPONSES.items():
            if keyword in last_user:
                response_text = resp
                break

        return LLMResponse(
            content=response_text,
            provider="mock",
            model="mock-v1",
            tokens_input=len(last_user.split()),
            tokens_output=len(response_text.split()),
        )


# ── Groq ──────────────────────────────────────────────────────────────────────

class GroqLLM(LLMProvider):
    DEFAULT_MODEL = "llama-3.1-8b-instant"

    def __init__(self):
        from groq import AsyncGroq  # lazy import
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.llm_model or self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "groq"

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        start = time.perf_counter()

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            max_tokens=max_tokens or settings.llm_max_tokens,
            temperature=temperature if temperature is not None else settings.llm_temperature,
        )

        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            provider="groq",
            model=self._model,
            tokens_input=response.usage.prompt_tokens,
            tokens_output=response.usage.completion_tokens,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAILLM(LLMProvider):
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self):
        from openai import AsyncOpenAI  # lazy import
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.llm_model or self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        start = time.perf_counter()

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            max_tokens=max_tokens or settings.llm_max_tokens,
            temperature=temperature if temperature is not None else settings.llm_temperature,
        )

        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            provider="openai",
            model=self._model,
            tokens_input=response.usage.prompt_tokens,
            tokens_output=response.usage.completion_tokens,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


# ── Factory ───────────────────────────────────────────────────────────────────

_llm_instance: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    provider = settings.llm_provider
    logger.info("LLM provider: %s", provider)

    match provider:
        case "groq":
            _llm_instance = GroqLLM()
        case "openai":
            _llm_instance = OpenAILLM()
        case _:
            if provider != "mock":
                logger.warning("Unknown LLM provider '%s', falling back to mock.", provider)
            _llm_instance = MockLLM()

    return _llm_instance
