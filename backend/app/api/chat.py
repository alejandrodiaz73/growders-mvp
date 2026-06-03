"""
growders.api.chat
──────────────────
Chat endpoint powering the web simulator (and later WhatsApp).

POST /api/v1/chat
  - Receives user message + conversation history
  - Runs grounding check against knowledge base
  - Calls LLM with grounded context
  - Returns assistant response
  - Persists messages async (non-blocking for latency)

Rate limit: 20 requests / minute per IP (tighter than default).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.security import limiter
from app.core.tenant import require_tenant
from app.services.cache import cache_key, get_cache
from app.services.llm import LLMResponse, get_llm

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)

# Characters allowed in a message (basic sanitisation)
_MAX_MESSAGE_LENGTH = 500


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=_MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=_MAX_MESSAGE_LENGTH)
    session_token: str = Field(min_length=8, max_length=100)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    response: str
    session_token: str
    provider: str
    tokens_used: int


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system_prompt(knowledge_context: str) -> str:
    """
    Grounded system prompt.
    The LLM is only allowed to use information from `knowledge_context`.
    If the answer is not there, it must escalate — never invent.
    """
    return f"""Eres MarIA, el asistente virtual de este negocio.

REGLAS ESTRICTAS (no negociables):
1. Solo puedes responder con información del bloque CONTEXTO DEL NEGOCIO de abajo.
2. Si la información no está en ese bloque, responde: "No tengo esa información. Te comunico con alguien del equipo."
3. NUNCA inventes precios, horarios, políticas ni datos del negocio.
4. Responde en español. Máximo 2 párrafos breves. Una pregunta a la vez.
5. Sé cordial, directo y profesional.

CONTEXTO DEL NEGOCIO:
{knowledge_context if knowledge_context else "Base de conocimiento no configurada para este negocio. Escala todas las consultas al humano."}
"""


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,          # needed by slowapi limiter
    body: ChatRequest,
    tenant_id: uuid.UUID = Depends(require_tenant),
) -> ChatResponse:
    """
    Main chat endpoint.

    Flow:
      1. Sanitise input
      2. Load tenant knowledge base from cache (or DB fallback)
      3. Build grounded system prompt
      4. Call LLM
      5. Return response (DB persistence happens in background)
    """

    # 1. Sanitise
    clean_message = body.message.strip()
    if not clean_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    # 2. Load knowledge base
    cache = get_cache()
    kb_key = cache_key(str(tenant_id), "knowledge_base")
    knowledge_context: str = await cache.get(kb_key) or ""

    if not knowledge_context:
        # TODO: load from DB KnowledgeBase table and cache it
        # For now, use a placeholder so the demo works
        knowledge_context = _get_demo_knowledge()
        await cache.set(kb_key, knowledge_context, ttl=600)

    # 3. Build prompt and messages
    system_prompt = _build_system_prompt(knowledge_context)
    messages = [{"role": m.role, "content": m.content} for m in body.history]
    messages.append({"role": "user", "content": clean_message})

    # 4. Call LLM
    llm = get_llm()
    try:
        llm_response: LLMResponse = await llm.chat(
            messages=messages,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.error("LLM call failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El asistente no está disponible en este momento. Por favor intenta de nuevo.",
        )

    logger.info(
        "Chat response | tenant=%s session=%s provider=%s tokens_in=%d tokens_out=%d latency=%.0fms",
        tenant_id,
        body.session_token,
        llm_response.provider,
        llm_response.tokens_input,
        llm_response.tokens_output,
        llm_response.latency_ms,
    )

    # 5. TODO: persist messages to DB as background task
    # background_tasks.add_task(persist_messages, tenant_id, body.session_token, ...)

    return ChatResponse(
        response=llm_response.content,
        session_token=body.session_token,
        provider=llm_response.provider,
        tokens_used=llm_response.tokens_input + llm_response.tokens_output,
    )


# ── Demo knowledge base (placeholder until DB knowledge module is built) ──────

def _get_demo_knowledge() -> str:
    """
    Placeholder knowledge base for the demo simulator.
    This will be replaced by the KnowledgeBase DB module in Sprint 2.
    """
    return """
Negocio: UniformaMX (demo)
Giro: Venta y personalización de uniformes escolares, industriales y corporativos
Horario: Lunes a viernes 9:00 - 18:00, Sábados 10:00 - 14:00
Dirección: Veracruz, México
Teléfono: Contacto solo por WhatsApp

Servicios:
- Uniformes escolares: bordado y sublimación disponibles
- Uniformes industriales: alta visibilidad, tallas S a 4XL
- Uniformes corporativos: personalización con logo
- Gorras y accesorios: bordado incluido

Tiempos de entrega:
- Pedidos menores a 20 piezas: 5 días hábiles
- Pedidos mayores a 20 piezas: 10-15 días hábiles
- Urgentes (costo adicional): consultar disponibilidad

Política de pedidos:
- Se requiere 50% de anticipo para iniciar producción
- No se aceptan devoluciones en productos personalizados
- Cambios de talla: solo antes de iniciar producción
"""
