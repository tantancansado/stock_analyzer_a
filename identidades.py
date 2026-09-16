#!/usr/bin/env python3
"""Identidades que TIENEN que cumplirse. Si no, hay un bug arriba.

Por qué existe
──────────────
Todos los fallos de datos encontrados el 16-sep-2026 tienen la misma forma:
**dos números correctos por separado que juntos mienten.** Ni uno solo dio
error, ni uno solo dejó un hueco visible.

    el R:R de un rebote        contra un objetivo distinto del publicado
    la zona de entrada         por encima del precio al que cotiza
    `fcf_per_share`            en libras contra un precio en peniques
    `priceclose` de TIKR       que era el tipo de cambio, no un precio
    `avg_move_pct`             que era la sorpresa de BPA, no el movimiento
    `upside_triangulated_pct`  que era el número del analista
    250 millones de acciones   por defecto, para 54 empresas distintas

Y el patrón de por qué sobrevivieron: **nada falla cuando el dato está mal**.
La página se pinta igual, el CSV tiene sus filas, el aviso sale bien formado.

Una identidad es una relación que se cumple por definición: el upside ES
(objetivo − precio) / precio. No es una heurística ni un umbral calibrado — o
cuadra o hay un bug. Es la comprobación más barata que existe y la única que no
necesita saber nada del negocio.

Lo que NO es
────────────
No juzga si el dato es bueno, ni si el pick es buena idea. Solo comprueba que el
CSV no se contradiga a sí mismo. Un dato coherente puede ser perfectamente
falso; uno incoherente es seguro que está mal en alguna parte.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Margen para redondeos y para el desfase normal entre el momento en que se
# captura el precio y el momento en que se calcula un derivado. Por debajo de
# esto no se avisa: un aviso que salta todos los días deja de leerse.
TOLERANCIA_PCT = 2.0

# A partir de aquí ya no es desfase, es otra cosa. Un factor de 100 (peniques),
# un tipo de cambio, un recuento de acciones equivocado.
TOLERANCIA_GRAVE_PCT = 20.0


@dataclass
class Incumplimiento:
    fichero: str
    identidad: str
    filas: int
    total: int
    peor_pct: float
    ejemplos: list[str]
    grave: bool

    def __str__(self) -> str:
        marca = '🛑' if self.grave else '⚠️ '
        return (f'{marca} {self.fichero}: {self.identidad} — {self.filas}/{self.total} filas, '
                f'peor desvío {self.peor_pct:.0f}% ({", ".join(self.ejemplos[:5])})')


def _num(d: pd.DataFrame, c: str) -> pd.Series:
    if c not in d.columns:
        return pd.Series(np.nan, index=d.index, dtype=float)
    return pd.to_numeric(d[c], errors='coerce')


def _comparar(d, fichero, nombre, calculado, publicado, tol=TOLERANCIA_PCT) -> Incumplimiento | None:
    vale = calculado.notna() & publicado.notna()
    if not vale.any():
        return None
    # Referencia con suelo: un publicado de 0,01 haría que cualquier diferencia
    # fuera un 10.000% y llenaría el informe de ruido.
    ref = publicado.abs().clip(lower=1.0)
    desv = (calculado - publicado).abs() / ref * 100
    mal = vale & (desv > tol)
    if not mal.any():
        return None
    tickers = d.loc[mal, 'ticker'].astype(str).tolist() if 'ticker' in d.columns else []
    peor = float(desv[mal].max())
    return Incumplimiento(fichero, nombre, int(mal.sum()), int(vale.sum()),
                          peor, tickers, peor > TOLERANCIA_GRAVE_PCT)


def revisar(d: pd.DataFrame, fichero: str = '') -> list[Incumplimiento]:
    """Identidades sobre un CSV de oportunidades. Lista vacía = cuadra todo."""
    if d is None or d.empty:
        return []
    p = _num(d, 'current_price')
    fuera: list[Incumplimiento | None] = []

    # ── Upsides: cada uno ES su objetivo contra el precio ────────────────────
    for obj, pct, nombre in (
        ('target_price_analyst', 'analyst_upside_pct',      'upside analista'),
        ('target_price_dcf',     'target_price_dcf_upside_pct', 'upside DCF'),
        ('target_price_pe',      'target_price_pe_upside_pct',  'upside P/E'),
    ):
        fuera.append(_comparar(d, fichero, f'{nombre} = (objetivo − precio) / precio',
                               (_num(d, obj) / p - 1) * 100, _num(d, pct)))

    # ── Distancia al máximo de 52 semanas ───────────────────────────────────
    fuera.append(_comparar(d, fichero, 'distancia al máximo 52s',
                           (p / _num(d, 'fifty_two_week_high') - 1) * 100,
                           _num(d, 'proximity_to_52w_high')))

    # ── FCF por acción contra su yield. El que destapó los peniques ─────────
    fuera.append(_comparar(d, fichero, 'FCF yield = FCF por acción / precio',
                           _num(d, 'fcf_per_share') / p * 100, _num(d, 'fcf_yield_pct'), 5.0))

    # ── Dividendo por acción contra su yield ────────────────────────────────
    fuera.append(_comparar(d, fichero, 'dividendo yield = dividendo / precio',
                           _num(d, 'dividend_rate') / p * 100, _num(d, 'dividend_yield_pct'), 5.0))

    # ── Capitalización = precio × acciones ──────────────────────────────────
    acc = _num(d, 'shares_outstanding')
    if acc.notna().any():
        fuera.append(_comparar(d, fichero, 'capitalización = precio × acciones',
                               p * acc, _num(d, 'market_cap'), 5.0))

    return [f for f in fuera if f is not None]


def revisar_operacion(d: pd.DataFrame, fichero: str = '',
                      col_entrada: str = 'entry_price') -> list[Incumplimiento]:
    """Identidades de una ficha operativa: entrada, stop, salida y su R:R.

    Es la forma exacta del fallo de los rebotes: `risk_reward` calculado contra
    un objetivo que no era el que se publicaba. Cero de doce fichas cuadraban y
    nadie se enteró porque los dos números eran correctos por separado.
    """
    if d is None or d.empty:
        return []
    ent = _num(d, col_entrada)
    if not ent.notna().any():
        ent = _num(d, 'current_price')
    stop, sal = _num(d, 'stop_loss'), _num(d, 'exit_price')
    if not sal.notna().any():
        sal = _num(d, 'target')
    # `rr_operativo` primero: es el que se calcula CON esta entrada, este stop
    # y esta salida. `risk_reward_ratio` es `analyst_upside_pct / 8` y no
    # describe esta ficha — se mira solo si no hay nada mejor, para que un CSV
    # antiguo siga dando señal.
    for col in ('rr_operativo', 'risk_reward', 'risk_reward_ratio'):
        if col in d.columns and _num(d, col).notna().any():
            rr = _num(d, col)
            break
    else:
        rr = pd.Series(np.nan, index=d.index, dtype=float)

    fuera = []
    riesgo = (ent - stop).where(ent > stop)
    i = _comparar(d, fichero, 'R:R = (salida − entrada) / (entrada − stop)',
                  (sal - ent) / riesgo, rr, 10.0)
    if i:
        fuera.append(i)

    # Órdenes imposibles: no es una identidad, es aritmética.
    for nombre, mal in (
        ('stop por encima de la entrada', (stop >= ent) & stop.notna() & ent.notna()),
        ('salida por debajo de la entrada', (sal <= ent) & sal.notna() & ent.notna()),
    ):
        if mal.any():
            t = d.loc[mal, 'ticker'].astype(str).tolist() if 'ticker' in d.columns else []
            fuera.append(Incumplimiento(fichero, nombre, int(mal.sum()), len(d), 100.0, t, True))
    return fuera
