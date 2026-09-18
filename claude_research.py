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
MODEL_HAIKU = 'claude-haiku-4-5'             # clasificación cerrada, sin razonar en cadena
MODEL_ANALISIS_PROFUNDO = 'claude-opus-5'   # para análisis abierto, no clasificación
# `allowed_callers: ['direct']` NO es opcional aquí.
#
# Desde `web_search_20260209` ese campo vale por defecto
# ['code_execution_20260120']: la búsqueda corre dentro de la ejecución de
# código (filtrado dinámico) en vez de llamarse directamente. Y la doc lo dice
# con todas las letras: «Models that don't support programmatic tool calling
# require this setting. Without it, the API returns a 400 error that tells you
# to set it.»
#
# Es lo que rompió el pipeline del 18-sep-2026: 400 invalid_request_error en
# TODAS las llamadas, y GOOG, META, LMT, GGG, SYY, GS y ADSK publicados como
# «SIN_DATOS · 0 fuentes». Nadie se enteró porque `ask_with_search` devuelve
# vacío ante cualquier excepción y quien llama lo trata como «este ticker no
# tiene datos» — el mismo resultado que si la empresa no tuviera noticias.
#
# Y aunque no diera 400, seguiría sin funcionar: con filtrado dinámico los
# resultados llegan ANIDADOS dentro de los bloques de la ejecución de código,
# y `_extract` solo mira los de primer nivel. De ahí el «0 fuentes».
WEB_SEARCH_TOOL = {'type': 'web_search_20260209', 'name': 'web_search',
                   'allowed_callers': ['direct']}

# Haiku 4.5 no soporta `output_config.effort` — confirmado el 8-sep-2026
# contra la doc oficial, no adivinado. Mandarlo sería el mismo 400 que ya
# rompió groq_utils.py dos veces (temperature, luego thinking: adaptive),
# pero aquí el fallo sería mucho más silencioso: `ask_with_search` trata
# CUALQUIER excepción como "sin datos" (fail-open), así que el síntoma no
# sería "VALUE publica 0 filas" sino "why_cheap/bounce_catalyst siempre
# salen SIN_DATOS" sin ningún aviso en el log.
_SIN_EFFORT = ('haiku-4-5',)
# 1, no 2. Una continuación reenvía el contexto ENTERO — incluidos los
# resultados de búsqueda, que son ~5k tokens por búsqueda — así que la segunda
# llamada duplica el coste de entrada del ticker. Solo aporta cuando el bucle
# de herramientas del servidor se queda a medias (`pause_turn`), que es raro;
# cuando pasa, se pierde esa respuesta y el consumidor lo trata como "sin
# datos", igual que cualquier otro fallo. Pagar el doble en todas las llamadas
# para salvar unas pocas no compensa con un tope de $10/mes.
MAX_CONTINUATIONS = 1

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
                    max_searches: int = 2, model: str = MODEL,
                    effort: str = 'medium') -> tuple[str, list[str]]:
    """Pregunta a Claude dejándole buscar. Devuelve (texto, urls consultadas).

    ('', []) si no hay API, si la petición es rechazada por los clasificadores
    o si algo falla: quien llame lo trata como "sin datos", nunca como un sí.

    `max_searches` no escala lineal en coste: la herramienta de búsqueda del
    servidor puede encadenar varias rondas DENTRO de una sola llamada, y cada
    ronda reenvía el contexto de las anteriores, así que el coste de entrada
    crece con el CUADRADO del número de búsquedas. El defecto es 2 y NO se
    sube sin medir: estaba en 6, que son 21 unidades de contexto frente a las
    3 de dos búsquedas — siete veces más caro para quien no pase el parámetro.

    Con datos de producción (sep-2026), tres búsquedas arrastraban 172k-263k
    tokens de ENTRADA por llamada y salían a $0.21-$0.31 CADA UNA, incluso en
    Haiku. Ahí está el gasto de este repo, no en la elección de modelo.

    Lo que sigue es la nota original sobre el mismo efecto: con resultados de
    ~5k tokens cada uno, el coste de entrada crece con el cuadrado del número de
    búsquedas, no con el número. Medido el 25-ago-2026: why_cheap_analyzer
    llamaba con el valor por defecto (6) y salía a $0.33/llamada, el 44% del
    gasto mensual con solo 12 llamadas. Bajar a 3 no ahorra la mitad, ahorra
    bastante más — para clasificar "por qué cayó" con 2-3 fuentes buenas suele
    bastar.
    """
    client = _get_client()
    if client is None:
        return '', []

    # Tope de gasto: esta es la vía cara de la app (los resultados de búsqueda
    # se inyectan en el contexto y las continuaciones los reenvían enteros).
    # Agotado el presupuesto del mes se devuelve vacío, que quien llama ya
    # trata como "sin datos" — el mismo camino que cuando la API falla.
    from claude_budget import hay_presupuesto, registrar_uso, resumen
    if not hay_presupuesto(coste_estimado=0.15):
        print(f'   💸 Sin presupuesto Claude este mes — se omite la búsqueda. {resumen()}')
        return '', []

    tool = dict(WEB_SEARCH_TOOL, max_uses=max_searches)
    messages: list[dict[str, Any]] = [{'role': 'user', 'content': prompt}]

    kwargs: dict[str, Any] = {
        'model': model,
        'max_tokens': max_tokens,
        'system': system,
        'tools': [tool],
    }
    if not any(m in model.lower() for m in _SIN_EFFORT):
        # medium basta para clasificar en categorías cerradas y recorta mucho
        # el tiempo por llamada — el criterio ya está en el system. `effort`
        # es parametrizable porque hay llamadas (why_cheap) que ni siquiera
        # necesitan medium: solo sintetizan 2-3 fuentes en una etiqueta
        # cerrada, no comparan ni razonan en cadena. Ver _SIN_EFFORT: en
        # Haiku 4.5 no se manda en absoluto.
        kwargs['output_config'] = {'effort': effort}

    try:
        for _ in range(MAX_CONTINUATIONS):
            response = client.messages.create(messages=messages, **kwargs)

            registrar_uso(response, model)

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
        # Distinguir "sin saldo" del resto: un fallo de red se reintenta solo
        # mañana, uno de facturación no se arregla solo y hay que avisar.
        from claude_budget import es_error_de_credito, registrar_fallo_credito
        if es_error_de_credito(e):
            registrar_fallo_credito(str(e))
            print(f'   🔴 CLAUDE SIN SALDO — se avisará en el briefing ({str(e)[:80]})')
        else:
            # El mensaje iba cortado a 80 caracteres, y un 400 de la API gasta
            # los primeros ochenta en la envoltura: el log del 18-sep-2026
            # repetía 164 veces «Error code: 400 - {'type': 'error', 'error':
            # {'type': 'invalid_request_error', ')» y se cortaba justo antes
            # del motivo. Un error truncado donde empieza lo útil cuesta un
            # día entero de diagnóstico.
            print(f'   ⚠️  Claude no disponible ({_resumen_error(e)})')
            _anotar_fallo(e)
        return '', []


# Un 400 no es «este ticker no tiene datos»: es que la petición está mal
# formada, y entonces falla PARA TODOS. `ask_with_search` devuelve '' ante
# cualquier excepción y quien llama lo trata como «sin datos», así que una
# configuración rota se publica como 164 tickers sin información y el
# pipeline termina en verde. Pasó el 18-sep-2026 con GOOG, META, LMT, GGG,
# SYY, GS, ADSK… y los rebotes se enviaron por Telegram igualmente.
_FALLOS: dict[str, int] = {}
_AVISADO: set[str] = set()
FALLOS_PARA_SOSPECHAR = 5


def _resumen_error(e: Exception) -> str:
    """El tipo del error y el motivo, sin la envoltura que se come el log."""
    texto = str(e)
    import re
    motivo = re.search(r"'message':\s*'([^']{0,200})", texto)
    tipo = re.search(r"'type':\s*'([a-z_]+_error)'", texto)
    partes = [p for p in (tipo.group(1) if tipo else None,
                          motivo.group(1) if motivo else None) if p]
    return ' · '.join(partes) if partes else texto[:200]


def _anotar_fallo(e: Exception) -> None:
    """Cuenta los fallos por tipo y grita cuando dejan de ser puntuales."""
    clave = _resumen_error(e)[:120]
    _FALLOS[clave] = _FALLOS.get(clave, 0) + 1
    n = _FALLOS[clave]
    if n >= FALLOS_PARA_SOSPECHAR and clave not in _AVISADO:
        _AVISADO.add(clave)
        print(f'\n   🔴 {n} llamadas seguidas fallando con el MISMO error: '
              f'{clave}\n      Esto no es «sin datos» de un ticker, es la '
              f'petición mal formada. Todo lo que dependa de Claude va a '
              f'salir vacío en esta ejecución.\n')


def fallos_sistematicos() -> dict[str, int]:
    """Errores que se han repetido lo bastante como para no ser casualidad."""
    return {k: v for k, v in _FALLOS.items() if v >= FALLOS_PARA_SOSPECHAR}


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


def ask_with_search_lote(
    prompts: dict[str, str], system: str, max_tokens: int = 2000,
    max_searches: int = 2, model: str = MODEL, effort: str = 'medium',
    espera_max_s: int | None = None,
) -> dict[str, tuple[str, list[str]]]:
    """`ask_with_search` para varias preguntas a la vez, por la Batch API.

    Devuelve {id: (texto, urls)}, con una entrada por cada id que entró.

    Esta es la vía CARA de la app: con búsqueda, cada llamada arrastra 172k-263k
    tokens de entrada y sale a $0,21-$0,31. Diecisiete llamadas al mes son el
    46% de la factura. La Batch API las cobra a la mitad sin cambiar nada del
    resultado — mismo modelo, mismos parámetros y el mismo bucle agéntico de
    servidor, herramientas incluidas.

    Lo que NO se da por hecho es que el lote siempre llegue: lo que falle, lo
    que expire o lo que vuelva a medias se resuelve por el camino síncrono de
    siempre. La comprobación veta pero no autoriza, así que quedarse sin
    respuesta nunca deja pasar un setup malo — pero sí dejaría pasar uno que
    debería vetarse, y eso no se cambia por ahorrar.
    """
    from claude_lote import Peticion, claude_lote, ESPERA_MAX_S

    vacios: dict[str, tuple[str, list[str]]] = {k: ('', []) for k in prompts}
    if not prompts:
        return vacios

    tool = dict(WEB_SEARCH_TOOL, max_uses=max_searches)
    extra: dict[str, Any] = {'tools': [tool]}
    if not any(m in model.lower() for m in _SIN_EFFORT):
        extra['output_config'] = {'effort': effort}

    def _extraer(mensaje):
        """None manda esta petición al respaldo síncrono.

        El bucle de herramientas del servidor da MÁS vueltas en lote que en
        síncrono —no hay conexión abierta que mantener— pero aun así puede
        volver con `pause_turn`, y entonces el turno no ha terminado. Quien
        sabe continuarlo es `ask_with_search`, que ya trae ese bucle.
        """
        if getattr(mensaje, 'stop_reason', None) in ('pause_turn', 'refusal'):
            return None
        texto, urls = _extract(mensaje)
        return (texto, urls) if texto else None

    def _respaldo(p: Peticion) -> tuple[str, list[str]]:
        return ask_with_search(prompts[p.id], system=system, max_tokens=max_tokens,
                               max_searches=max_searches, model=model, effort=effort)

    peticiones = [
        Peticion(pid, [{'role': 'user', 'content': texto}],
                 system=system, max_tokens=max_tokens, **extra)
        for pid, texto in prompts.items()
    ]
    res = claude_lote(peticiones, model=model,
                      espera_max_s=espera_max_s or ESPERA_MAX_S,
                      respaldo=_respaldo, extraer=_extraer)
    return {pid: (res.get(pid) or ('', [])) for pid in prompts}
