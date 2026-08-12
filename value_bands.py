"""Banda canónica de analyst_upside_pct para señales VALUE — única fuente.

Calibrada con señales reales (86 clean-period + 55 del tier ≥30%):
  [10, 25)  → +4.73% / 83% win   (zona dorada)
  [25, 30)  → transición (n pequeño, sin evidencia clara)
  >= 30     → 0% win / -8.28% avg (value trap: si el gap con el target es
              enorme, el precio se desplomó por algo que el modelo no ve)

Antes cada consumidor tenía su propia banda (integrator ≥30 reject,
portfolio_tracker 10-45, conviction_filter 10-55) y el mismo ticker podía
ser trampa en un módulo y pick en otro. Cualquier cambio de banda se hace
AQUÍ y en ningún otro sitio.
"""

# Por debajo: upside demasiado justo para compensar el riesgo de la posición
UPSIDE_MIN = 10.0

# Fin de la zona dorada [10, 25): el bonus de score solo premia esta banda
UPSIDE_GOLDEN_MAX = 25.0

# Hard reject: >= 30% es señal de trampa, no de oportunidad
UPSIDE_HARD_REJECT = 30.0

# Score mínimo para seguir en la lista VALUE. Vive aquí por el mismo motivo que
# las bandas de upside: el integrator lo aplicaba al ordenar y
# apply_oe_ai_adjustment bajaba scores DESPUÉS sin re-filtrar, así que el CSV
# publicado del 31-jul-2026 llevaba 15 tickers por debajo del propio corte.
VALUE_SCORE_MIN = 30.0


def solo_politica_vigente(df, columna: str = 'analyst_upside_pct'):
    """Quita del histórico las señales que el sistema YA NO emitiría.

    Medir "desde el periodo limpio" no basta: en abril-2026 todavía se emitían
    señales con upside >= UPSIDE_HARD_REJECT, que hoy el integrator rechaza de
    plano (value_score = 0). Eran 59 de las 120 limpias y las peores con
    diferencia — 1,7% de acierto a 30d y -8,28% de media — así que mezclarlas
    describe una política MUERTA y hunde el resultado del sistema actual:

        a 30d   con ellas 21,0% / -4,68%   ·   sin ellas 48,8% / +0,51%
        a 90d   con ellas 33,7% / -2,68%   ·   sin ellas 66,7% / +3,46%

    Vive aquí, junto a las bandas, porque el fallo fue tenerlo duplicado: el
    tracker y signal_postmortem filtraban cada uno por su cuenta y solo por
    fecha, y publicaban cifras que se contradecían entre sí (35,6% contra 61,5%
    de acierto a 90d, detectado por coherence_check el 12-ago-2026).

    Al añadir un filtro duro nuevo al integrator, añadirlo TAMBIÉN aquí.
    """
    import pandas as pd
    if df is None or len(df) == 0 or columna not in df.columns:
        return df
    up = pd.to_numeric(df[columna], errors='coerce')
    # NaN se conserva: "sin dato de upside" no es lo mismo que "upside alto",
    # y descartarlo sesgaría la muestra hacia las que sí tienen cobertura.
    return df[~(up >= UPSIDE_HARD_REJECT)]
