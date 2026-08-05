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


def add_upside_triangulation(df: pd.DataFrame) -> pd.DataFrame:
    """Triangula el upside de analistas con los modelos propios (DCF y P/E).

    Motivación: el score ancla en el target de analistas, pero a veces los
    modelos propios dicen lo contrario (UBER 3-jul-2026: analistas +36%, DCF
    propio -38%, P/E -48%) y nada lo reconciliaba. Columnas nuevas:
      upside_triangulated_pct — mediana de las tres estimaciones disponibles
      upside_divergence_pts   — analistas menos la mediana de DCF/P/E
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
    df['upside_triangulated_pct'] = pd.concat([_an, _dcf, _pe], axis=1).median(axis=1, skipna=True).round(1)
    own = pd.concat([_dcf, _pe], axis=1).median(axis=1, skipna=True)
    # Sin ningún modelo propio válido no hay triangulación: dejarlo en NaN en vez
    # de devolver el upside del analista disfrazado de mediana de tres fuentes.
    df.loc[own.isna(), 'upside_triangulated_pct'] = np.nan
    gap = _an - own
    df['upside_divergence_pts'] = gap.round(1)
    df['upside_divergence'] = np.select([gap >= 40, gap >= 20], ['ALTA', 'MEDIA'], default='')
    df.loc[gap.isna(), 'upside_divergence'] = ''
    n_alta = int((df['upside_divergence'] == 'ALTA').sum())
    if n_alta:
        print(f"   ⚠️  Divergencia ALTA analistas-vs-modelos-propios en {n_alta} tickers")
    return df
