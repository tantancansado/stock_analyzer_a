"""Ningún aviso sale con números que se contradigan entre sí.

Por qué existe
──────────────
El 16-sep-2026 llegó por Telegram:

    🔬 CBOE [CURADO] $270.44
       Target $308.62 · Stop $253.49 · R:R 1.1

Los tres números eran correctos por separado y el conjunto era falso: ese 1,1
se calcula contra `bounce_target` (289,37), no contra el objetivo que se
anunciaba. Con el target del mensaje el R:R real era 2,25.

Veintiún scripts de este repo mandan a Telegram y ninguno comprobaba el mensaje
antes de enviarlo. `setup_coherente` existía, pero valida el dict DENTRO del
detector: entre ese punto y el envío hay un armado de mensaje que puede
—y pudo— romper la correspondencia.

Esto se ejecuta justo antes de enviar. Un aviso con precios es una propuesta de
operación: si sus números no cuadran entre ellos, no sale. Mejor no avisar que
avisar mal — es la misma regla que el gate de VALUE.

Qué comprueba
─────────────
  - que haya precio, y que sea un número positivo
  - objetivo POR ENCIMA del precio y stop POR DEBAJO
  - que el R:R anunciado sea el que sale de (objetivo-precio)/(precio-stop)
  - que el precio no esté rancio respecto al de mercado, si se le pasa

Lo que NO comprueba es si la idea es buena. Eso es de los filtros; esto solo
verifica que el mensaje no se contradiga.
"""
from __future__ import annotations

# Tolerancia del R:R anunciado. Los avisos lo redondean a un decimal, así que
# 1,64 se enseña como «1.6»: el margen cubre el redondeo, no un descuadre.
TOLERANCIA_RR = 0.12

# Cuánto puede alejarse el precio del aviso del precio real antes de considerarlo
# rancio. Un 3% cubre el movimiento normal entre el scan y el envío.
TOLERANCIA_PRECIO_PCT = 3.0


def _num(v):
    try:
        f = float(v)
        return None if f != f else f          # NaN fuera
    except (TypeError, ValueError):
        return None


def revisar(aviso: dict, precio_real: float | None = None) -> list[str]:
    """Problemas encontrados. Lista vacía = el aviso es coherente.

    `aviso` usa las claves del mensaje: ticker, price, target, stop, rr.
    """
    fallos: list[str] = []
    t = str(aviso.get('ticker') or '?')

    precio = _num(aviso.get('price'))
    if precio is None or precio <= 0:
        return [f'{t}: sin precio válido ({aviso.get("price")!r})']

    objetivo = _num(aviso.get('target'))
    stop = _num(aviso.get('stop'))
    rr = _num(aviso.get('rr'))

    if objetivo is not None and objetivo <= precio:
        fallos.append(f'{t}: objetivo {objetivo} no está por encima del precio {precio} '
                      f'(pediría comprar caro para vender barato)')
    if stop is not None and stop >= precio:
        fallos.append(f'{t}: stop {stop} no está por debajo del precio {precio}')

    # El corazón del asunto: que el R:R anunciado sea el del objetivo anunciado.
    if rr is not None and objetivo is not None and stop is not None:
        riesgo = precio - stop
        if riesgo > 0:
            calculado = (objetivo - precio) / riesgo
            if abs(calculado - rr) > TOLERANCIA_RR:
                fallos.append(
                    f'{t}: el R:R anunciado ({rr:.2f}) no corresponde a su objetivo '
                    f'({objetivo}) — con ese objetivo y ese stop sale {calculado:.2f}')

    if precio_real is not None:
        pr = _num(precio_real)
        if pr and pr > 0:
            desvio = abs(precio / pr - 1) * 100
            if desvio > TOLERANCIA_PRECIO_PCT:
                fallos.append(f'{t}: el precio del aviso ({precio}) se desvía un '
                              f'{desvio:.1f}% del de mercado ({pr})')
    return fallos


def filtrar(avisos: list[dict], precios_reales: dict | None = None) -> tuple[list[dict], list[str]]:
    """Deja pasar los coherentes. Devuelve (los que salen, los problemas)."""
    ok, problemas = [], []
    for a in avisos:
        fallos = revisar(a, (precios_reales or {}).get(str(a.get('ticker', '')).upper()))
        if fallos:
            problemas.extend(fallos)
            continue
        ok.append(a)
    return ok, problemas
