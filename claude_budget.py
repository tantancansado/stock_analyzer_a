#!/usr/bin/env python3
"""
Tope de gasto de Claude — un techo real, no una estimación.

El 10-ago-2026 el saldo de la API se agotó: $5 que antes duraban un mes se
gastaron en días. Causa: entre el 3 y el 5-ago se añadieron tres pasos que usan
Claude CON BÚSQUEDA WEB (why_cheap, narrativa de commodities, catalizador de
rebotes). Los resultados de búsqueda se inyectan en el contexto (~5k tokens por
búsqueda) y, con MAX_CONTINUATIONS=2, se reenvían enteros en la segunda llamada
— se paga dos veces por ticker. Estimado: ~$42/mes.

Ajustar parámetros reduce el gasto pero no lo ACOTA: basta un día con más
candidatos, o una búsqueda que devuelva páginas largas, para desbordarlo. Esto
sí lo acota: cada llamada se registra con su coste real (tokens de la respuesta
+ búsquedas efectuadas) y, alcanzado el tope del mes, las siguientes se
rechazan. Los consumidores tratan el rechazo como "sin datos", que es el
comportamiento que ya tienen cuando la API falla (fail-open, no rompen).

El contador vive en docs/.claude_budget.json (mismo patrón que el watchdog) y
se reinicia solo al cambiar de mes.

Uso:
    from claude_budget import hay_presupuesto, registrar_uso, resumen

    if not hay_presupuesto():
        return None          # el consumidor lo trata como "sin datos"
    resp = ...llamada...
    registrar_uso(resp, modelo='claude-sonnet-5')
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Sin punto delante A PROPÓSITO: `git add docs/*.json` de los workflows no
# expande ficheros ocultos en bash, así que como dotfile el contador nunca se
# commiteaba, cada run de CI partía de cero y el tope no acotaba nada.
ESTADO = Path(__file__).parent / 'docs' / 'claude_budget.json'

# Tope mensual en dólares. Lo fija el usuario, no es una optimización: no
# tocarlo sin pedírselo.
#   10-ago-2026: 10$, hasta comprobar si las recomendaciones compensan.
#   15-sep-2026: 20$. El gasto real iba a ~19,7$/mes y el tope se agotaba el
#     día 15 — con el gate fail-closed eso deja media Value US colgando de la
#     caché de veredictos. El usuario lo dio por aceptable: «20 dólares al mes
#     puede ser aceptable, el objetivo es optimizarlo sin perder calidad».
TOPE_USD = float(os.getenv('CLAUDE_BUDGET_USD', '20.0'))

# Reserva para que el último día del mes no se quede sin briefing: por debajo
# de este margen solo pasan las llamadas marcadas como esenciales.
RESERVA_USD = 1.0

# Precios por millón de tokens (Anthropic, consultados 10-ago-2026).
# Sonnet 5 tiene precio introductorio hasta el 31-ago-2026: 2/10 en vez de 3/15.
# Se usa el precio ALTO a propósito — es mejor cortar antes de tiempo que
# después, y el introductorio caduca solo.
PRECIOS = {
    'claude-sonnet-5': (3.0, 15.0),
    'claude-opus-5':   (5.0, 25.0),
    'claude-haiku-4-5': (1.0, 5.0),
}
PRECIO_BUSQUEDA_USD = 0.01   # $10 por 1000 búsquedas web


def _mes_actual() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


def _leer() -> dict:
    if not ESTADO.exists():
        return {'mes': _mes_actual(), 'gastado_usd': 0.0, 'llamadas': 0, 'busquedas': 0}
    try:
        d = json.loads(ESTADO.read_text())
    except Exception:
        return {'mes': _mes_actual(), 'gastado_usd': 0.0, 'llamadas': 0, 'busquedas': 0}
    # Cambio de mes: el contador se reinicia solo.
    if d.get('mes') != _mes_actual():
        return {'mes': _mes_actual(), 'gastado_usd': 0.0, 'llamadas': 0, 'busquedas': 0,
                'mes_anterior': {'mes': d.get('mes'), 'gastado_usd': d.get('gastado_usd')}}
    return d


def _escribir(d: dict) -> None:
    try:
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(d, indent=2))
    except Exception:
        pass   # no poder escribir el contador nunca debe tumbar el pipeline


def gastado_este_mes() -> float:
    """Gasto del mes, a prueba de que alguien ponga el contador a cero.

    Se devuelve el MAYOR entre `gastado_usd` y `techo_mes`, que solo sube. El
    25-ago-2026 un commit reinicializó el fichero a mitad de mes y borró $9.02:
    el tope volvió a creer que quedaba presupuesto entero y el gasto real de
    agosto ($29.52 en la consola) nunca cuadró con lo registrado ($7.30).
    """
    d = _leer()
    return max(float(d.get('gastado_usd', 0.0) or 0.0),
               float(d.get('techo_mes', 0.0) or 0.0))


def hay_presupuesto(coste_estimado: float = 0.0, esencial: bool = False) -> bool:
    """¿Cabe una llamada más este mes?

    `esencial=True` para lo que no debe caerse aunque quede poco (el briefing
    diario). Lo no esencial se corta antes, dejando RESERVA_USD de colchón.
    """
    gastado = gastado_este_mes()
    techo = TOPE_USD if esencial else max(TOPE_USD - RESERVA_USD, 0.0)
    return (gastado + coste_estimado) < techo


# La Batch API cobra al 50%: «All usage is charged at 50% of the standard API
# prices… applies to input tokens, output tokens, and any special tokens».
# No menciona las peticiones de búsqueda web, que se cobran por petición y no
# por token, así que aquí el descuento se aplica SOLO a los tokens y la
# búsqueda se cuenta entera. Si resultara que también va rebajada, el contador
# va por encima del gasto real — que es el lado seguro para un tope.
DESCUENTO_LOTE = 0.5


def coste_de(respuesta, modelo: str, descuento: float = 1.0) -> float:
    """Coste real de una respuesta de la API, leído de su `usage`.

    `descuento` multiplica el precio de los tokens: 1.0 síncrono,
    DESCUENTO_LOTE para lo que vaya por la Batch API.
    """
    p_in, p_out = PRECIOS.get(modelo, PRECIOS['claude-sonnet-5'])
    u = getattr(respuesta, 'usage', None)
    if u is None:
        return 0.0
    # Las tres partidas de entrada son SEPARADAS y cada una tiene su precio
    # (no se solapan: total = input + cache_read + cache_creation).
    #
    #   input_tokens                  1x
    #   cache_creation_input_tokens   1,25x con TTL de 5 min, 2x con el de 1 h
    #   cache_read_input_tokens       0,1x
    #
    # Antes se sumaba `cache_read` al precio COMPLETO —diez veces de más— y
    # `cache_creation` no se contaba en absoluto. Hoy los dos valen 0 porque
    # el repo no manda `cache_control`, así que no explica ningún descuadre;
    # se arregla ahora porque el día que alguien active la caché para ahorrar,
    # el contador empezaría a mentir sin que nada lo avise.
    #
    # Se usa 1,25 para la creación: es el TTL por defecto. Si la API devuelve
    # el desglose por TTL, se cobra el de una hora al doble, que es lo que
    # vale.
    base = getattr(u, 'input_tokens', 0) or 0
    lectura = getattr(u, 'cache_read_input_tokens', 0) or 0
    creacion = getattr(u, 'cache_creation_input_tokens', 0) or 0
    desglose = getattr(u, 'cache_creation', None)
    if desglose is not None:
        c5 = getattr(desglose, 'ephemeral_5m_input_tokens', 0) or 0
        c1h = getattr(desglose, 'ephemeral_1h_input_tokens', 0) or 0
        if c5 or c1h:
            creacion_ponderada = c5 * 1.25 + c1h * 2.0
        else:
            creacion_ponderada = creacion * 1.25
    else:
        creacion_ponderada = creacion * 1.25
    tin = base + lectura * 0.1 + creacion_ponderada
    tout = getattr(u, 'output_tokens', 0) or 0
    # Las búsquedas web se cobran aparte de los tokens
    busq = 0
    stu = getattr(u, 'server_tool_use', None)
    if stu is not None:
        busq = getattr(stu, 'web_search_requests', 0) or 0
    return (tin / 1e6 * p_in + tout / 1e6 * p_out) * descuento + busq * PRECIO_BUSQUEDA_USD


def _quien_llama() -> str:
    """Script del repo que originó la llamada, subiendo por la pila.

    Se deduce en vez de pasarse como argumento porque hay 13 sitios que llaman
    y un parámetro nuevo se olvida justo en el que más gasta. Sin esto, el
    contador dice "$8 este mes" y no de qué, que es lo único accionable:
    saber que el postmortem se lleva la mitad vale más que el total.
    """
    import inspect
    propios = {'claude_budget.py', 'groq_utils.py', 'claude_research.py'}
    try:
        for fr in inspect.stack()[1:]:
            nombre = os.path.basename(fr.filename)
            if nombre.endswith('.py') and nombre not in propios:
                return nombre[:-3]
    except Exception:
        pass
    return 'desconocido'


def registrar_uso(respuesta, modelo: str, descuento: float = 1.0) -> float:
    """Suma al contador del mes lo que ha costado esta llamada. Devuelve el coste."""
    c = coste_de(respuesta, modelo, descuento)
    d = _leer()
    por_script = d.setdefault('por_script', {})
    quien = _quien_llama()
    prev = por_script.get(quien) or {'usd': 0.0, 'llamadas': 0}
    por_script[quien] = {'usd': round(prev['usd'] + c, 6), 'llamadas': prev['llamadas'] + 1}
    # El total del mes NO puede bajar. El 25-ago-2026 un commit reinicializó
    # este fichero a mitad de mes y borró $9.02 acumulados: el tope volvió a
    # creerse que quedaba presupuesto entero, y el gasto real de agosto ($29.52
    # en la consola de Anthropic) nunca cuadró con lo registrado ($7.30).
    # `techo_mes` sobrevive a que alguien ponga `gastado_usd` a cero, y
    # `hay_presupuesto` lee el mayor de los dos.
    d['gastado_usd'] = round(float(d.get('gastado_usd', 0.0)) + c, 6)
    d['techo_mes'] = round(max(float(d.get('techo_mes', 0.0)), d['gastado_usd']), 6)
    d['llamadas'] = int(d.get('llamadas', 0)) + 1
    if descuento != 1.0:
        d['llamadas_lote'] = int(d.get('llamadas_lote', 0)) + 1
        d['ahorro_lote_usd'] = round(
            float(d.get('ahorro_lote_usd', 0.0))
            + (coste_de(respuesta, modelo) - c), 6)
    u = getattr(respuesta, 'usage', None)
    stu = getattr(u, 'server_tool_use', None) if u is not None else None
    if stu is not None:
        d['busquedas'] = int(d.get('busquedas', 0)) + (getattr(stu, 'web_search_requests', 0) or 0)
    d['ultima_llamada'] = datetime.now(timezone.utc).isoformat()
    # Una llamada que cobra es la prueba de que hay saldo otra vez. Sin esto el
    # aviso de "sin saldo" se queda pegado para siempre y miente en cuanto el
    # usuario recarga — y un aviso que miente se aprende a ignorar.
    d.pop('sin_credito', None)
    d.pop('sin_credito_desde', None)
    d.pop('sin_credito_mensaje', None)
    _escribir(d)
    return c


def registrar_fallo_credito(mensaje: str) -> None:
    """Marca que la API rechazó por saldo/facturación, no por otra cosa.

    Sin esto el fallo es mudo: los clientes capturan la excepción y devuelven
    vacío, el pipeline sigue con `continue-on-error` y la app publica listas sin
    why_cheap con la misma cara de siempre. El usuario se entera semanas después.
    """
    d = _leer()
    d['sin_credito'] = True
    d['sin_credito_desde'] = d.get('sin_credito_desde') or datetime.now(timezone.utc).isoformat()
    d['sin_credito_mensaje'] = str(mensaje)[:200]
    _escribir(d)


def es_error_de_credito(exc: Exception) -> bool:
    """¿Este fallo es de saldo, o es otra cosa (red, rate limit, 500)?"""
    m = str(exc).lower()
    return any(s in m for s in (
        'credit balance', 'insufficient', 'billing', 'quota',
        'payment', 'plans & billing', 'too low',
    ))


def estado_alerta() -> dict:
    """Lo que necesita saber quien avise al usuario (briefing, watchdog)."""
    d = _leer()
    g = float(d.get('gastado_usd', 0.0))
    return {
        'gastado_usd': round(g, 2),
        'tope_usd': TOPE_USD,
        'pct': round(100 * g / TOPE_USD, 0) if TOPE_USD else 0,
        'tope_alcanzado': not hay_presupuesto(esencial=True),
        'sin_credito': bool(d.get('sin_credito')),
        'sin_credito_desde': d.get('sin_credito_desde'),
        'llamadas': d.get('llamadas', 0),
    }


def linea_para_briefing() -> str | None:
    """Una línea para el mensaje diario. None si no hay nada que contar.

    Solo habla cuando importa — el usuario odia el ruido: sin saldo, tope
    alcanzado, o por encima del 80%. En uso normal no dice nada.
    """
    e = estado_alerta()
    if e['sin_credito']:
        desde = (e['sin_credito_desde'] or '')[:10]
        return (f"🔴 <b>Claude sin saldo</b> desde {desde} — el análisis de por qué "
                f"cae cada valor está DESACTIVADO hasta que recargues")
    if e['tope_alcanzado']:
        return (f"🟠 <b>Tope de Claude alcanzado</b> (${e['gastado_usd']:.2f} de "
                f"${e['tope_usd']:.0f} este mes) — why_cheap pausado hasta el día 1")
    if e['pct'] >= 80:
        # Con el mayor gastador: "vas al 86%" no se puede accionar, "vas al 86%
        # y se lo lleva why_cheap" sí — dice qué recortar o si compensa subir
        # el tope. La decisión de subirlo es del usuario, no una optimización.
        top = _mayor_gastador()
        extra = f" · lo que más gasta: {top}" if top else ''
        return (f"🟡 Claude: ${e['gastado_usd']:.2f} de ${e['tope_usd']:.0f} "
                f"({e['pct']:.0f}%){extra}")
    return None


def _mayor_gastador() -> str | None:
    por = _leer().get('por_script') or {}
    if not por:
        return None
    nombre, v = max(por.items(), key=lambda kv: kv[1]['usd'])
    return f"{nombre} (${v['usd']:.2f})"


def resumen() -> str:
    d = _leer()
    g = float(d.get('gastado_usd', 0.0))
    pct = 100 * g / TOPE_USD if TOPE_USD else 0
    return (f"Claude {d.get('mes')}: ${g:.2f} de ${TOPE_USD:.2f} ({pct:.0f}%) · "
            f"{d.get('llamadas', 0)} llamadas · {d.get('busquedas', 0)} búsquedas")


def desglose() -> str:
    """Quién se gasta el presupuesto, de mayor a menor. Para decidir con datos
    qué recortar en vez de a ojo."""
    d = _leer()
    por = d.get('por_script') or {}
    if not por:
        return '  (sin llamadas registradas este mes)'
    filas = sorted(por.items(), key=lambda kv: -kv[1]['usd'])
    total = sum(v['usd'] for _, v in filas) or 1.0
    out = []
    for nombre, v in filas:
        proy = v['usd'] / max(int(d.get('dia_del_mes') or _hoy_dia()), 1) * 30
        out.append(f"  {nombre:32s} ${v['usd']:6.2f}  {100*v['usd']/total:4.0f}%  "
                   f"{v['llamadas']:4d} llam  →${proy:5.2f}/mes")
    return '\n'.join(out)


def _hoy_dia() -> int:
    return datetime.now(timezone.utc).day


if __name__ == '__main__':
    print(resumen())
    print(desglose())
