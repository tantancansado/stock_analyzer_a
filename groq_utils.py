"""
AI API helpers: Groq (free, with model fallback) + Anthropic Claude (paid).

Groq fallback chain on 429 rate_limit_exceeded:
  1. openai/gpt-oss-120b   (primary)
  2. openai/gpt-oss-20b    (fallback — separate quota)

31-ago-2026: la cadena entera apuntaba a modelos ya retirados por Groq —
llama-3.3-70b-versatile y llama-3.1-8b-instant murieron el 16-ago-2026,
meta-llama/llama-4-scout-17b-16e-instruct el 17-jul-2026, y el "último
recurso" llama-3.1-70b-specdec llevaba MUERTO DESDE ENERO DE 2025 (su propio
reemplazo recomendado, llama-3.3-70b-specdec, también está deprecado desde
abr-2025 — una cadena de reemplazos apuntando unos a otros, todos muertos).
Se vio en el log del pipeline del 27-ago-2026: "404 model_not_found" para
varios tickers EU/asiáticos. Reemplazo verificado contra
console.groq.com/docs/deprecations, no adivinado — se quita el tercer nivel
de fallback en vez de perseguir otro reemplazo de un reemplazo ya muerto.

Claude usage by task:
  - thesis_generator: Haiku 4.5  (~$5.5/mes for ~40k output tokens/day)
  - cerebro exits + daily_plan:  Sonnet 4.6 (~$1.5/mes for ~1.5k output tokens/day)
"""
from __future__ import annotations
import os
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

PRIMARY_MODEL   = "openai/gpt-oss-120b"
FALLBACK_MODELS = [
    "openai/gpt-oss-20b",         # separate quota bucket del primario
]

# Modelo con cupo separado del primario, para diversificar cuando el
# primario está agotado — no puede ser el mismo que PRIMARY_MODEL o pierde
# el sentido de tener un segundo nivel.
SCOUT_PRIMARY  = "qwen/qwen3.6-27b"
SCOUT_FALLBACK = ["openai/gpt-oss-20b", PRIMARY_MODEL]


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc)
    return "rate_limit_exceeded" in msg or "429" in msg


def groq_chat(
    client,
    messages: list[dict],
    model: str = PRIMARY_MODEL,
    max_tokens: int = 500,
    temperature: float = 0.3,
    response_format: dict | None = None,
    fallback_chain: list[str] | None = None,
) -> Any:
    """
    Calls client.chat.completions.create with automatic model fallback on 429.

    Returns the raw response object (same as the Groq SDK).
    Raises the last exception if all models are exhausted.
    """
    if fallback_chain is None:
        fallback_chain = FALLBACK_MODELS if model == PRIMARY_MODEL else SCOUT_FALLBACK

    models_to_try = [model] + [m for m in fallback_chain if m != model]

    last_exc: Exception | None = None
    for attempt, m in enumerate(models_to_try):
        try:
            kwargs: dict[str, Any] = dict(
                model=m,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if response_format:
                kwargs["response_format"] = response_format
            resp = client.chat.completions.create(**kwargs)
            if attempt > 0:
                logger.warning("groq_chat: used fallback model %s (primary %s exhausted)", m, model)
                print(f"  ⚡ Groq fallback: {model} → {m}")
            return resp
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc):
                print(f"  ⚠️  {m} rate-limited — {'trying next model' if attempt + 1 < len(models_to_try) else 'all models exhausted'}")
                time.sleep(1)
                continue
            raise  # non-rate-limit error → propagate immediately

    raise last_exc  # type: ignore[misc]


# ── Anthropic Claude helpers ──────────────────────────────────────────────────

CLAUDE_HAIKU   = "claude-haiku-4-5"
CLAUDE_SONNET  = "claude-sonnet-5"
CLAUDE_OPUS    = "claude-opus-5"

# Estos modelos rechazan temperature/top_p/top_k con un 400 y usan adaptive
# thinking. No basta con mirar si pone "opus": Sonnet 5 también los rechaza, y
# daily_briefing.py lo usa — mandarle temperature habría hecho que el briefing
# fallara en su primer envío sin que nadie supiera por qué.
#
# 'haiku-4-5' añadido el 31-ago-2026: ai_pick_verifier.py (paso CRÍTICO del
# pipeline, dentro de super_score_integrator) llama a Haiku con temperature y
# fallaba SIEMPRE con "Messages.create() got an unexpected keyword argument
# 'temperature'" — visto en el log del 27-ago. No tumbaba el job (el propio
# ai_pick_verifier trata la ausencia de respuesta como "sin veredicto", fail-
# open) pero el verificador llevaba días sin verificar nada.
_SIN_SAMPLING = ('opus-5', 'opus-4-8', 'opus-4-7', 'sonnet-5', 'fable-5', 'mythos-5', 'haiku-4-5')

# Sin timeout el cliente espera 10 minutos por petición, y claude_chat corre
# dentro de pasos críticos del pipeline (ai_pick_verifier). Ver el incidente
# del 3-ago-2026: 75 min de job agotados por llamadas sin acotar.
_TIMEOUT_SEG = 120.0

_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Único camino de claude_chat que devolvía None sin dejar rastro. El
        # 27-ago-2026 esto pasó (probablemente) en el paso de AI Quality
        # Filter mientras OTRO paso del mismo job, segundos antes, sí tenía
        # la clave — 65 picks VALUE excluidos en cascada sin ninguna pista en
        # el log de por qué. Con esta línea, la próxima vez se ve al momento.
        logger.warning("ANTHROPIC_API_KEY no está en el entorno — Claude no disponible este proceso")
        return None
    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(
            api_key=api_key, timeout=_TIMEOUT_SEG, max_retries=1)
        return _anthropic_client
    except ImportError:
        logger.warning("anthropic package not installed — Claude unavailable")
        return None
    except Exception as exc:
        logger.warning("Failed to init Anthropic client: %s", exc)
        return None


def claude_chat(
    messages: list[dict],
    model: str = CLAUDE_HAIKU,
    max_tokens: int = 800,
    temperature: float = 0.3,
    system: str | None = None,
    esencial: bool = False,
) -> str | None:
    """
    Calls Anthropic Messages API. Returns text content or None on failure.

    messages: list of {"role": "user"|"assistant", "content": "..."}
    system:   optional system prompt (Anthropic separates it from messages)

    Los modelos de _SIN_SAMPLING rechazan `temperature` con un 400 y usan
    adaptive thinking; el resto (Haiku, Sonnet 4.6 y anteriores) siguen
    aceptándola. Se decide por lista explícita y no por "¿pone opus?", porque
    Sonnet 5 también la rechaza.
    """
    client = _get_anthropic_client()
    if client is None:
        return None
    # Tope de gasto mensual. `esencial` deja pasar el briefing diario aunque
    # quede poco margen: es el único mensaje del día y perderlo se nota.
    from claude_budget import hay_presupuesto, registrar_uso, resumen
    if not hay_presupuesto(coste_estimado=0.05, esencial=esencial):
        logger.warning("claude_chat: sin presupuesto este mes. %s", resumen())
        return None
    modelo = model.lower()
    sin_sampling = any(m in modelo for m in _SIN_SAMPLING)
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if sin_sampling:
            kwargs["thinking"] = {"type": "adaptive"}
        else:
            kwargs["temperature"] = temperature
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        registrar_uso(resp, model)
        # Con adaptive thinking los bloques de pensamiento van primero: se
        # coge el de texto, no content[0].
        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
        return text
    except Exception as exc:
        # Devuelve None, no propaga: quien llama (ai_pick_verifier, cerebro,
        # daily_briefing) trata la ausencia de respuesta como "sin veredicto" y
        # sigue. Propagar aquí haría que una caída de la API tumbase el paso
        # crítico del pipeline, que es justo lo que pasó el 3-ago-2026.
        from claude_budget import es_error_de_credito, registrar_fallo_credito
        if es_error_de_credito(exc):
            registrar_fallo_credito(str(exc))
            logger.error("claude_chat(%s): SIN SALDO — %s", model, exc)
        else:
            logger.warning("claude_chat(%s): %s", model, exc)
        return None
