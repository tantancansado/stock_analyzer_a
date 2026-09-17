#!/usr/bin/env python3
"""
Upside Triangulation — compara el upside de analistas contra los modelos
propios (DCF y P/E). Función pura, sin dependencias del resto del pipeline.

Vivía dentro de super_score_integrator.py. Se extrae aquí el 5-ago-2026 porque
european_value_scanner.py también la necesita y no debe arrastrar todo el
integrator (market_regime_detector, moving_average_filter, ai_pick_verifier...)
solo para reusar una función de treinta líneas. super_score_integrator.py la
sigue exponiendo con el mismo nombre — reexportada, no duplicada — para no
romper nada que ya la importe de ahí.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Un upside de modelo propio fuera de ±200% es un dato roto (divisa sin
# convertir en ADR), no una valoración: se descarta al triangular.
MODEL_UPSIDE_SANE_MAX = 200.0

# Dos modelos del MISMO signo pero muy separados siguen siendo una valoración
# floja. Estaba en 45 (el percentil 75 de |DCF − P/E| entre las que coinciden
# en signo) y se baja a 20 el 17-sep-2026, porque con 45 la etiqueta mentía:
#
#   NYT   DCF  -8,3%  ·  P/E -53,0%  ·  44,7 pts  ->  decía COHERENTES
#   CBOE  DCF  +1,8%  ·  P/E +42,2%  ·  40,4 pts  ->  decía COHERENTES
#   MCO   DCF +35,7%  ·  P/E  +1,1%  ·  34,6 pts  ->  decía COHERENTES
#
# Decirle al usuario que sus dos modelos «coinciden» cuando difieren en 45
# puntos de upside es peor que no decirle nada. Coincidir en el signo no es
# coincidir: con 20 puntos de diferencia ya son dos respuestas distintas.
DISPERSION_ALTA_PTS = 20.0


def add_upside_triangulation(df: pd.DataFrame) -> pd.DataFrame:
    """Triangula el upside de analistas con los modelos propios (DCF y P/E).

    Motivación: el score ancla en el target de analistas, pero a veces los
    modelos propios dicen lo contrario (UBER 3-jul-2026: analistas +36%, DCF
    propio -38%, P/E -48%) y nada lo reconciliaba. Columnas nuevas:
      upside_triangulated_pct — mediana de las tres estimaciones disponibles
      upside_divergence_pts   — analistas menos la mediana de DCF/P/E
      modelos_dispersion_pts  — |DCF − P/E|: cuánto se separan ENTRE ELLOS
      modelos_acuerdo         — CONTRADICEN / DISPERSOS / COHERENTES
      upside_divergence       — ALTA (>=40pts) / MEDIA (>=20) / '' — cuánto
                                se separa el sell-side de tus propios modelos

    Alimenta la penalización de credibilidad del value_score, así que debe
    calcularse ANTES de puntuar (antes solo era informativo y se computaba al
    final: la bandera existía en el CSV y no la miraba nadie).
    """
    if 'analyst_upside_pct' not in df.columns:
        return df
    _an = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
    _dcf = (pd.to_numeric(df['target_price_dcf_upside_pct'], errors='coerce')
            if 'target_price_dcf_upside_pct' in df.columns
            else pd.Series(np.nan, index=df.index))
    _pe = (pd.to_numeric(df['target_price_pe_upside_pct'], errors='coerce')
           if 'target_price_pe_upside_pct' in df.columns
           else pd.Series(np.nan, index=df.index))

    # Los ADR no patrocinados mezclan divisas y escupen valoraciones imposibles
    # (ATLKY DCF +570%, ASAZY +1082% el 31-jul-2026 — SEK contra USD). Si UNO de
    # los dos modelos delira, el otro viene del mismo precio contaminado: se
    # invalidan los dos para ese ticker y se queda sin veredicto de credibilidad,
    # en vez de penalizarlo con el modelo roto que sobrevivió al rango.
    _broken = ((_dcf.abs() > MODEL_UPSIDE_SANE_MAX) | (_pe.abs() > MODEL_UPSIDE_SANE_MAX)).fillna(False)
    if _broken.any():
        _bt = df.loc[_broken, 'ticker'].tolist() if 'ticker' in df.columns else []
        print(f"   ⚠️  Modelos propios fuera de rango (divisa rota?) — sin triangular: {_bt[:12]}")
    _dcf = _dcf.where(~_broken)
    _pe  = _pe.where(~_broken)
    # ── ¿Se ponen de acuerdo los modelos ENTRE ELLOS? ────────────────────────
    # La divergencia de abajo solo mira analista-contra-modelos. El desacuerdo
    # de los modelos entre sí no lo miraba nadie, y es la mitad del universo:
    # medido sobre las 63 filas con ambos modelos el 16-sep-2026, la mediana de
    # |DCF − P/E| es de 38,8 puntos de upside, y en el 32% de los casos uno dice
    # BARATA y el otro CARA.
    #
    # Ahí la "triangulación" es una ficción. Cuando el analista cae entre los
    # dos modelos —que es lo que pasa cuando se contradicen— la mediana de tres
    # ES el analista: ocurría en 14 de esas 20 filas. La columna se llama
    # `upside_triangulated_pct` y en esos casos no aporta ni un dato más que
    # `analyst_upside_pct`. EQIX: DCF +54,3% y P/E −55,1%, triangulado 22,5 =
    # el analista clavado.
    #
    # El corte no es un umbral inventado: es el signo. No existe un valor
    # verdadero entre "un 50% barata" y "un 45% cara" — son dos respuestas a la
    # misma pregunta, no dos medidas del mismo número. La línea de abajo ya
    # aplicaba exactamente este razonamiento al caso de CERO modelos válidos;
    # dos modelos que se contradicen son, para esto, lo mismo.
    _disp = (_dcf - _pe).abs()
    df['modelos_dispersion_pts'] = _disp.round(1)
    _contradicen = (np.sign(_dcf) != np.sign(_pe)) & _dcf.notna() & _pe.notna()
    _dispersos = (~_contradicen) & (_disp > DISPERSION_ALTA_PTS)
    df['modelos_acuerdo'] = np.select(
        [_contradicen, _dispersos, _dcf.notna() & _pe.notna()],
        ['CONTRADICEN', 'DISPERSOS', 'COHERENTES'], default='')

    df['upside_triangulated_pct'] = pd.concat([_an, _dcf, _pe], axis=1).median(axis=1, skipna=True).round(1)
    own = pd.concat([_dcf, _pe], axis=1).median(axis=1, skipna=True)
    # Si se contradicen en el signo, su mediana no estima nada: se anula igual
    # que cuando no hay ningún modelo válido.
    own = own.where(~_contradicen)
    # Sin ningún modelo propio válido no hay triangulación: dejarlo en NaN en vez
    # de devolver el upside del analista disfrazado de mediana de tres fuentes.
    df.loc[own.isna(), 'upside_triangulated_pct'] = np.nan

    # La DIVERGENCIA no se pierde aunque no haya triangulación. Antes sí: con
    # `own` en NaN el gap salía NaN y la bandera se quedaba vacía, así que el
    # usuario no veía ni el número consolidado NI el aviso de que su analista
    # y sus modelos dicen cosas distintas. Doble silencio sobre el mismo
    # problema, y en 24 de los 43 picks publicados el 17-sep-2026.
    #
    # Cuando los modelos se contradicen se mide contra el MÁS PRUDENTE de los
    # dos: si uno dice +50% y el otro -45%, lo que hay que contrastar con el
    # +26% del analista es el -45%, no una media que no significa nada.
    _prudente = pd.concat([_dcf, _pe], axis=1).min(axis=1, skipna=True)
    _referencia = own.fillna(_prudente)
    gap = _an - _referencia
    df['upside_divergence_pts'] = gap.round(1)
    df['upside_divergence'] = np.select([gap >= 40, gap >= 20], ['ALTA', 'MEDIA'], default='')
    df.loc[gap.isna(), 'upside_divergence'] = ''
    n_alta = int((df['upside_divergence'] == 'ALTA').sum())
    if n_alta:
        print(f"   ⚠️  Divergencia ALTA analistas-vs-modelos-propios en {n_alta} tickers")
    return df
