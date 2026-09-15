"""Batch API de Anthropic: lo mismo, a mitad de precio.

Por qué existe
──────────────
El gasto iba a ~19,7$/mes con un tope de 10$, y el tope se agotaba el día 15.
Con el gate fail-closed eso deja media Value US colgando de la caché de
veredictos. La Batch API cobra el 50% de todo por procesar en diferido, y —esto
es lo que la hace aceptable aquí— NO cambia el resultado: mismo modelo, mismos
parámetros y el mismo bucle agéntico de servidor, herramientas incluidas.
La documentación es explícita: «All server tools (web search, web fetch, code
execution, MCP connectors, advisor, and tool search) work in batch requests. The
batch worker runs the same server-side agentic loop as the synchronous Messages
API.» Lo único no soportado es `stream`, el modo rápido y `max_tokens: 0`, que
aquí no se usan.

Lo que se paga a cambio es latencia: la mayoría terminan en menos de una hora,
el máximo son 24 y lo que expire no se factura.

Cómo no romper el pipeline
──────────────────────────
El pipeline es secuencial: el gate alimenta a entry_exit, a thesis_generator y
al resto del mismo run. Un lote que tarde más que la ventana lo dejaría sin
datos, y eso sería cambiar dinero por fiabilidad — mal negocio en una app cuyo
problema histórico son los fallos silenciosos.

Así que esto NO es "batch o nada": se envía el lote, se espera hasta
`espera_max_s`, y todo lo que no haya llegado (o haya fallado, o haya expirado)
se pide en síncrono antes de devolver. El peor caso es pagar el precio de
siempre; el caso normal es pagar la mitad. Nunca es quedarse sin respuesta.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Cuánto esperar al lote antes de tirar de síncrono. El pipeline nocturno tiene
# margen de sobra —el paso de scoring ya dura ~57 min— pero no infinito.
ESPERA_MAX_S = 45 * 60
# Sondeo con espera creciente: los lotes pequeños suelen estar en minutos y no
# tiene sentido preguntar cada 5 segundos durante tres cuartos de hora.
SONDEO_INICIAL_S = 10
SONDEO_MAX_S = 60


# El `custom_id` que acepta la API es `^[a-zA-Z0-9_-]{1,64}$`: sin puntos. Y
# aquí los ids son tickers, que los llevan en cuanto salen de EEUU —SAP.DE,
# NGAS.L, 0700.HK—. Un solo id con punto hace que la API rechace el LOTE
# ENTERO; el respaldo lo salvaría, pero se perdería el ahorro sin que nadie se
# entere de por qué. Así que se manda un id saneado y se traduce de vuelta.
_ID_VALIDO = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _id_para_la_api(ident: str, usados: dict[str, str]) -> str:
    """Id que la API acepta, único dentro del lote.

    La unicidad se comprueba TAMBIÉN para los ids que ya son válidos: 'SAP.DE'
    se convierte en 'SAP-DE', y si el lote llevara además un 'SAP-DE' literal
    los dos acabarían apuntando al mismo sitio y uno se comería la respuesta
    del otro. Es rebuscado, pero el precio de cubrirlo es una línea y el de no
    cubrirlo es un veredicto asignado al ticker equivocado.
    """
    base = ident if _ID_VALIDO.fullmatch(ident) else (
        re.sub(r'[^a-zA-Z0-9_-]', '-', ident)[:60] or 'x')
    candidato, n = base, 1
    while candidato in usados:
        n += 1
        candidato = f'{base[:57]}-{n}'
    return candidato


class Peticion:
    """Una llamada del lote. `id` vuelve en el resultado para reemparejarla."""

    __slots__ = ('id', 'messages', 'system', 'max_tokens', 'extra')

    def __init__(self, id: str, messages: list[dict], system: str | None = None,
                 max_tokens: int = 800, **extra: Any) -> None:
        self.id = id
        self.messages = messages
        self.system = system
        self.max_tokens = max_tokens
        self.extra = extra


def _cuerpo(p: Peticion, model: str, sin_sampling: bool, sin_control: bool,
            temperature: float) -> dict:
    """Mismo armado de parámetros que `claude_chat`, para que el lote no sea
    una segunda forma de llamar que se desincronice de la primera."""
    cuerpo: dict[str, Any] = {
        'model': model,
        'max_tokens': p.max_tokens,
        'messages': p.messages,
    }
    if sin_sampling:
        cuerpo['thinking'] = {'type': 'adaptive'}
    elif not sin_control:
        cuerpo['temperature'] = temperature
    if p.system:
        cuerpo['system'] = p.system
    cuerpo.update(p.extra)
    return cuerpo


def _texto_de(mensaje) -> str | None:
    """El bloque de texto. Con adaptive thinking los de pensamiento van primero,
    así que no vale `content[0]` — el mismo cuidado que en `claude_chat`."""
    contenido = getattr(mensaje, 'content', None) or []
    return next((b.text for b in contenido if getattr(b, 'type', None) == 'text'), None)


def claude_lote(
    peticiones: list[Peticion],
    model: str,
    *,
    temperature: float = 0.3,
    espera_max_s: int = ESPERA_MAX_S,
    respaldo: Callable[[Peticion], Any] | None = None,
    extraer: Callable[[Any], Any] | None = None,
    esencial: bool = False,
) -> dict[str, Any]:
    """Resuelve todas las peticiones y devuelve {id: resultado}.

    Lo que se pueda, por lote (mitad de precio). Lo que no llegue a tiempo o
    falle, por `respaldo` (síncrono, precio entero). Nunca devuelve menos ids
    de los que se le pasaron.

    `extraer` convierte el mensaje de la API en lo que quiera quien llama; por
    defecto, su texto. Devolver None desde ahí manda esa petición al respaldo —
    que es como la búsqueda web trata un `pause_turn`: el turno se quedó a
    medias y quien sabe continuarlo es el camino síncrono.
    """
    extraer = extraer or _texto_de
    from groq_utils import _get_anthropic_client, _SIN_SAMPLING, _SIN_CONTROL_MUESTREO
    from claude_budget import hay_presupuesto, registrar_uso, resumen, DESCUENTO_LOTE

    salida: dict[str, str | None] = {p.id: None for p in peticiones}
    if not peticiones:
        return salida

    pendientes = {p.id: p for p in peticiones}

    def _resolver_pendientes(motivo: str) -> None:
        if not pendientes:
            return
        logger.warning('claude_lote: %d pendientes por %s — se piden en síncrono',
                       len(pendientes), motivo)
        for pid, p in list(pendientes.items()):
            salida[pid] = respaldo(p) if respaldo else None
            pendientes.pop(pid, None)

    cliente = _get_anthropic_client()
    if cliente is None:
        _resolver_pendientes('sin cliente de Anthropic')
        return salida

    # El tope se comprueba una vez para todo el lote: 485 comprobaciones
    # individuales contra el mismo fichero no aportan nada y lo martillean.
    if not hay_presupuesto(coste_estimado=0.05 * len(peticiones), esencial=esencial):
        logger.warning('claude_lote: sin presupuesto este mes. %s', resumen())
        return salida        # sin respaldo: el síncrono también lo rechazaría

    modelo = model.lower()
    sin_sampling = any(m in modelo for m in _SIN_SAMPLING)
    sin_control = any(m in modelo for m in _SIN_CONTROL_MUESTREO)

    # id de la API -> id de quien llama
    de_la_api: dict[str, str] = {}
    for p in peticiones:
        de_la_api[_id_para_la_api(p.id, de_la_api)] = p.id
    hacia_la_api = {v: k for k, v in de_la_api.items()}

    try:
        lote = cliente.messages.batches.create(requests=[
            {'custom_id': hacia_la_api[p.id],
             'params': _cuerpo(p, model, sin_sampling, sin_control, temperature)}
            for p in peticiones
        ])
    except Exception as exc:
        logger.error('claude_lote: no se pudo crear el lote (%s)', exc)
        _resolver_pendientes('fallo al crear el lote')
        return salida

    logger.info('claude_lote: %d peticiones enviadas (lote %s)', len(peticiones), lote.id)

    # ── Sondeo ────────────────────────────────────────────────────────────
    limite = time.monotonic() + espera_max_s
    espera = SONDEO_INICIAL_S
    estado = lote
    while time.monotonic() < limite:
        time.sleep(min(espera, max(0, limite - time.monotonic())))
        espera = min(espera * 2, SONDEO_MAX_S)
        try:
            estado = cliente.messages.batches.retrieve(lote.id)
        except Exception as exc:
            logger.warning('claude_lote: sondeo fallido (%s)', exc)
            continue
        if getattr(estado, 'processing_status', None) == 'ended':
            break
    else:
        logger.warning('claude_lote: %s no terminó en %d min', lote.id, espera_max_s // 60)

    if getattr(estado, 'processing_status', None) != 'ended':
        try:
            cliente.messages.batches.cancel(lote.id)   # no seguir pagando por algo que ya no se espera
        except Exception:
            pass
        _resolver_pendientes('el lote no terminó a tiempo')
        return salida

    # ── Recogida ──────────────────────────────────────────────────────────
    try:
        for r in cliente.messages.batches.results(lote.id):
            pid = de_la_api.get(getattr(r, 'custom_id', None))
            if pid not in pendientes:
                continue
            res = getattr(r, 'result', None)
            if getattr(res, 'type', None) != 'succeeded':
                # errored / canceled / expired: lo coge el respaldo. Los
                # expirados no se facturan.
                logger.warning('claude_lote: %s -> %s', pid, getattr(res, 'type', '?'))
                continue
            mensaje = getattr(res, 'message', None)
            # El uso se registra ANTES de mirar si sirve: la llamada se cobró
            # igual. No hacerlo fue lo que ocultó el bug de max_tokens=300 en
            # el gate durante tres días.
            registrar_uso(mensaje, model, descuento=DESCUENTO_LOTE)
            valor = extraer(mensaje)
            if valor is None:
                continue          # al respaldo
            salida[pid] = valor
            pendientes.pop(pid, None)
    except Exception as exc:
        logger.error('claude_lote: no se pudieron leer los resultados (%s)', exc)

    _resolver_pendientes('no llegaron en el lote')
    return salida
