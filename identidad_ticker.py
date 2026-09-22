#!/usr/bin/env python3
"""¿El dato que traigo es de la empresa que creo?

Por qué existe
──────────────
El 17-sep-2026, cruzando las fuentes del MISMO ticker, salieron tres registros
completos, plausibles y de otra compañía:

    AI.PA    debería ser L'Air Liquide  →  TIKR traía C3.ai, Inc.
    BRK-B    Berkshire Hathaway         →  Direxion Daily BRKB Bull 2X ETF
    MMC      Marsh & McLennan           →  MM Conferences S.A. (Polonia, 8,90 PLN)

El resolvedor se queda con lo que se parece: `AI.PA` pierde el sufijo y encuentra
`AI`, `BRK-B` engancha un ETF apalancado que sigue a BRKB, `MMC` cae en una
polaca. Y nada lo delata: el registro está entero, los números son razonables, y
una valoración construida sobre ellos sale bien formada.

Es el fallo más difícil de ver de todos los de este repo. Los demás dejan un
hueco —un `None`, una lista vacía, un cero—; este deja un dato lleno y correcto,
solo que de otra empresa.

Tres comprobaciones, todas por cruce y ninguna por confianza:

  1. La divisa tiene que cuadrar con el mercado del sufijo. `.PA` es EUR: si
     vuelve USD, no es esa acción.
  2. El nombre de la empresa tiene que coincidir entre fuentes.
  3. El precio también, salvo el factor 100 de las bolsas que cotizan en
     subunidad (Londres en peniques).
"""
from __future__ import annotations

import re
import unicodedata

# Sufijo de yfinance → divisa de cotización. Espejo de
# `frontend/src/lib/moneda.ts`; hay un test que impide que se separen.
# Londres cotiza en PENIQUES (GBp), no en libras — por eso va aparte.
DIVISA_POR_SUFIJO: dict[str, str] = {
    'L': 'GBp', 'IL': 'USD',
    'PA': 'EUR', 'DE': 'EUR', 'F': 'EUR', 'AS': 'EUR', 'BR': 'EUR', 'MC': 'EUR',
    'MI': 'EUR', 'LS': 'EUR', 'VI': 'EUR', 'IR': 'EUR', 'HE': 'EUR',
    'SW': 'CHF', 'S': 'CHF',
    'ST': 'SEK', 'OL': 'NOK', 'CO': 'DKK',
    'T': 'JPY',
    'TO': 'CAD', 'V': 'CAD',
    'AX': 'AUD', 'NZ': 'NZD',
    'HK': 'HKD', 'SI': 'SGD',
}

# Divisas que se cotizan en subunidad: el precio viene ×100 respecto a la mayor.
SUBUNIDAD = {'GBp': 'GBP'}


def divisa_esperada(ticker: str) -> str | None:
    """Divisa en la que debería cotizar, o None si no se puede saber."""
    t = str(ticker or '').strip().upper()
    punto = t.rfind('.')
    if punto <= 0:
        # Sin sufijo: bolsa estadounidense. Los ADR (terminan en Y) también
        # cotizan en dólares aunque la empresa sea de fuera.
        return 'USD'
    return DIVISA_POR_SUFIJO.get(t[punto + 1:])


def _normalizar(nombre: str) -> str:
    """Nombre comparable: sin acentos, sin formas jurídicas, sin puntuación."""
    s = unicodedata.normalize('NFKD', str(nombre or '')).encode('ascii', 'ignore').decode()
    s = s.lower().strip()
    # Elisión francesa al principio: «L'Air Liquide» y «Air Liquide» son la
    # misma empresa, pero el `l'` pegado hacía que ni una empezara por la otra.
    # Dos formas: con apóstrofo pegado («l'air liquide») o como palabra suelta
    # («the coca-cola company»). No se quita una «l» inicial sin apóstrofo
    # —«Linde» no es «inde»— y no hace falta: sobre los 137 tickers reales, el
    # único nombre que difiere entre fuentes por este motivo es AI.PA, que es
    # precisamente el caso que hay que cazar.
    s = re.sub(r"^(?:[ld]\s*['’]\s*|(?:el|la|le|los|las|the)\s+)", '', s)
    s = re.sub(r"\b(inc|corp|corporation|company|co|plc|sa|s\.a|ag|nv|n\.v|se|ltd|limited"
               r"|group|holdings?|the|klasse|class [ab])\b", ' ', s)
    return re.sub(r'[^a-z0-9]+', '', s)


def mismo_nombre(a: str, b: str) -> bool:
    """¿Son la misma empresa? Tolerante con la forma jurídica, no con el nombre.

    «Berkshire Hathaway Inc.» y «Berkshire Hathaway» sí. «Berkshire Hathaway» y
    «Direxion Daily BRKB Bull 2X ETF» no, aunque una siga a la otra.
    """
    na, nb = _normalizar(a), _normalizar(b)
    if not na or not nb:
        return True          # sin nombre en una fuente no se puede desmentir
    return na.startswith(nb) or nb.startswith(na)


def _factor_unidad(precio_a: float, precio_b: float) -> bool:
    """¿La diferencia es solo peniques contra libras?"""
    if precio_a <= 0 or precio_b <= 0:
        return False
    r = max(precio_a, precio_b) / min(precio_a, precio_b)
    return 95 < r < 105


def revisar(ticker: str, fuentes: list[dict]) -> list[str]:
    """Problemas de identidad de un ticker. Lista vacía = las fuentes concuerdan.

    `fuentes`: [{'fuente': str, 'nombre': str|None, 'precio': float|None,
                 'divisa': str|None}, ...]
    """
    fallos: list[str] = []
    t = str(ticker).upper()

    esperada = divisa_esperada(t)
    for f in fuentes:
        d = (f.get('divisa') or '').strip()
        if not d or not esperada:
            continue
        # GBp y GBP son el mismo mercado en distinta unidad: no es otra empresa.
        if d == esperada or (esperada in SUBUNIDAD and d == SUBUNIDAD[esperada]):
            continue
        fallos.append(f"{t}: {f['fuente']} lo da en {d} y {t.split('.')[-1] if '.' in t else 'US'} "
                      f"cotiza en {esperada} — no es esa acción")

    nombres = [(f['fuente'], f['nombre']) for f in fuentes if f.get('nombre')]
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            if not mismo_nombre(nombres[i][1], nombres[j][1]):
                fallos.append(f"{t}: {nombres[i][0]} dice «{nombres[i][1]}» y "
                              f"{nombres[j][0]} dice «{nombres[j][1]}» — no es la misma empresa")

    # El precio solo prueba identidad cuando no hay nombre con el que
    # compararla. Si las dos fuentes dicen que es la misma empresa, un precio
    # distinto no dice «otra compañía», dice «fechas distintas»: TIKR se
    # refresca los domingos y el resto del pipeline a diario, así que a
    # mitad de semana hay días de desfase y cualquier valor movido pasa del
    # 10%. META saltó el 22-sep-2026 con un 11% teniendo el mismo nombre en
    # ambas fuentes, y eso tumbó el pipeline entero. Un desfase se vigila con
    # la frescura, no acusando a la acción de ser otra.
    nombres_concuerdan = bool(nombres) and all(
        mismo_nombre(nombres[i][1], nombres[j][1])
        for i in range(len(nombres)) for j in range(i + 1, len(nombres)))
    # Con el nombre confirmado hace falta un disparate para hablar de otra
    # acción: el doble de precio ya no es volatilidad de unos días.
    tolerancia = 2.0 if nombres_concuerdan else 1.10

    precios = [(f['fuente'], float(f['precio'])) for f in fuentes
               if f.get('precio') and float(f['precio']) > 0]
    for i in range(len(precios)):
        for j in range(i + 1, len(precios)):
            a, b = precios[i][1], precios[j][1]
            if max(a, b) / min(a, b) <= tolerancia or _factor_unidad(a, b):
                continue
            fallos.append(f"{t}: {precios[i][0]}={a:.2f} y {precios[j][0]}={b:.2f} "
                          f"({100 * (max(a, b) / min(a, b) - 1):.0f}% de diferencia)")
    return fallos
