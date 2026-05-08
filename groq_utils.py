"""
AI API helpers: Groq (free, with model fallback) + Anthropic Claude (paid).

Groq fallback chain on 429 rate_limit_exceeded:
  1. llama-3.3-70b-versatile    (primary — 100k TPD free)
  2. llama-3.1-8b-instant       (fallback — 500k TPD free, separate quota)
  3. llama-3.1-70b-specdec      (last resort — different quota bucket)

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

PRIMARY_MODEL   = "llama-3.3-70b-versatile"
FALLBACK_MODELS = [
    "llama-3.1-8b-instant",       # 500k TPD — separate quota from 70b
    "llama-3.1-70b-specdec",      # another bucket
]

# Models with separate quota (llama-4-scout family)
SCOUT_PRIMARY  = "meta-llama/llama-4-scout-17b-16e-instruct"
SCOUT_FALLBACK = ["llama-3.1-8b-instant", PRIMARY_MODEL]


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
CLAUDE_SONNET  = "claude-sonnet-4-6"

_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
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
) -> str | None:
    """
    Calls Anthropic Messages API. Returns text content or None on failure.

    messages: list of {"role": "user"|"assistant", "content": "..."}
    system:   optional system prompt (Anthropic separates it from messages)
    """
    client = _get_anthropic_client()
    if client is None:
        return None
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        return resp.content[0].text if resp.content else None
    except Exception as exc:
        logger.warning("claude_chat(%s): %s", model, exc)
        raise
