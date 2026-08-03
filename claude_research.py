#!/usr/bin/env python3
"""
Claude Research — una llamada a Claude con búsqueda web, devolviendo el texto
JUNTO A las URLs que la herramienta consultó de verdad.

Por qué existe: hasta ahora las fuentes de un veredicto salían de lo que el
modelo escribía en su respuesta, y un modelo puede escribir una URL plausible
igual que escribe una cifra plausible. Aquí las URLs se leen de los bloques
`web_search_tool_result` que devuelve la propia herramienta: son las páginas que
el buscador entregó, no texto generado. Un veredicto sin bloques de búsqueda es
un veredicto sin respaldo, y quien llame decide qué hacer con eso.

Modelo: claude-sonnet-5 con adaptive thinking y effort alto. La tarea es
clasificar en categorías cerradas material que ya trajo el buscador, no razonar
en cadena larga — ahí Sonnet rinde como Opus a la mitad de precio ($3/$15 por
MTok frente a $5/$25). `model=` queda expuesto por si alguna llamada futura
pide un análisis abierto, donde Opus sí se separa.

Notas del contrato de la API que aquí importan:
  - Los errores de las herramientas de servidor NO lanzan excepción: llegan como
    HTTP 200 con un bloque de resultado cuyo `content` es un objeto de error.
  - `stop_reason == "pause_turn"` significa que el bucle de servidor se quedó a
    medias; se reenvía la conversación para que continúe.
  - `stop_reason == "refusal"` llega con 200 y `content` vacío o parcial: hay que
    mirarlo ANTES de leer el contenido.
"""
from __future__ import annotations

import json
import os
from typing import Any

MODEL = 'claude-sonnet-5'
MODEL_ANALISIS_PROFUNDO = 'claude-opus-5'   # para análisis abierto, no clasificación
WEB_SEARCH_TOOL = {'type': 'web_search_20260209', 'name': 'web_search'}
MAX_CONTINUATIONS = 2

# El cliente espera 10 minutos por petición si no se le dice otra cosa, y eso
# tumbó el job de scoring el 3-ago-2026 (8 llamadas × 10 min > los 75 min del
# job). Clasificar con búsqueda web cabe de sobra en 100 s; lo que pase de ahí
# es una llamada atascada, no una que necesite más tiempo.
TIMEOUT_SEG = 100.0

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not os.getenv('ANTHROPIC_API_KEY'):
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(timeout=TIMEOUT_SEG, max_retries=1)
        return _client
    except Exception as e:
        print(f'   ⚠️  Cliente Anthropic no disponible: {e}')
        return None


def _extract(response) -> tuple[str, list[str]]:
    """Texto de la respuesta + URLs que la herramienta devolvió realmente."""
    texto, urls = [], []
    for block in response.content:
        btype = getattr(block, 'type', None)
        if btype == 'text':
            texto.append(block.text)
        elif btype == 'web_search_tool_result':
            # En error, `content` es un objeto ({'error_code': ...}); en éxito,
            # una lista de resultados. Hay que distinguirlo antes de iterar.
            content = getattr(block, 'content', None)
            if isinstance(content, list):
                for r in content:
                    url = getattr(r, 'url', None)
                    if url:
                        urls.append(url)
            else:
                code = getattr(content, 'error_code', 'desconocido')
                print(f'   ⚠️  Búsqueda web falló: {code}')
    return '\n'.join(texto), urls


def ask_with_search(prompt: str, system: str, max_tokens: int = 2000,
                    max_searches: int = 6, model: str = MODEL) -> tuple[str, list[str]]:
    """Pregunta a Claude dejándole buscar. Devuelve (texto, urls consultadas).

    ('', []) si no hay API, si la petición es rechazada por los clasificadores
    o si algo falla: quien llame lo trata como "sin datos", nunca como un sí.
    """
    client = _get_client()
    if client is None:
        return '', []

    tool = dict(WEB_SEARCH_TOOL, max_uses=max_searches)
    messages: list[dict[str, Any]] = [{'role': 'user', 'content': prompt}]

    try:
        for _ in range(MAX_CONTINUATIONS):
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=[tool],
                # medium basta para clasificar en categorías cerradas y recorta
                # mucho el tiempo por llamada — el criterio ya está en el system
                output_config={'effort': 'medium'},
                messages=messages,
            )

            # Los clasificadores pueden declinar: mirar SIEMPRE antes de leer content
            if response.stop_reason == 'refusal':
                print('   ⚠️  Petición rechazada por los clasificadores de seguridad')
                return '', []

            texto, urls = _extract(response)

            # El bucle de herramientas de servidor se quedó a medias: se reenvía
            # tal cual (sin añadir un mensaje de usuario) y el servidor continúa.
            if response.stop_reason == 'pause_turn':
                messages = [
                    {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': response.content},
                ]
                continue

            return texto, urls

        print('   ⚠️  Búsqueda sin terminar tras varias continuaciones')
        return '', []

    except Exception as e:
        print(f'   ⚠️  Claude no disponible ({str(e)[:80]})')
        return '', []


def parse_json(texto: str) -> dict:
    """JSON de la respuesta. {} si no hay nada parseable — nunca a medias."""
    if not texto:
        return {}
    t = texto.strip()
    if '```' in t:
        partes = t.split('```')
        if len(partes) > 1:
            t = partes[1]
            if t.lstrip().lower().startswith('json'):
                t = t.lstrip()[4:]
    ini, fin = t.find('{'), t.rfind('}')
    if ini < 0 or fin <= ini:
        return {}
    try:
        return json.loads(t[ini:fin + 1])
    except ValueError:
        return {}
