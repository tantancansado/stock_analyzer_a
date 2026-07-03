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
