"""Horizontes de medición de señales.

Esta app no va del corto plazo. El usuario compra empresas y vende a precio
objetivo por valoración, no a fecha, así que medir una señal VALUE a 7 o 14
días responde a una pregunta que nadie se hace.

Y los datos lo confirman. Medido sobre el tracker completo (sep-2026), el
edge del sistema es una función del plazo y NO EXISTE a corto:

    horizonte    n      aciertos    1/2 Kelly
       7d      1692      29.2%        0.0%
      14d      1644      30.4%        0.0%
      30d      1557      45.9%        0.0%
      90d      1511      55.1%       12.3%
     180d       844      70.7%       25.6%

Un win rate del 29% a 7 días no dice que el sistema falle: dice que a 7 días
todavía no ha pasado nada. Enseñarlo como "win rate" invita a concluir lo
contrario.

La excepción son las estrategias que SÍ son de corto plazo por diseño —
rebotes técnicos y setups de entrada—, donde 30 días es el horizonte natural
y 90 sería igual de equivocado en el otro sentido.
"""

# Horizonte principal para todo lo que no sea corto plazo por diseño.
PRINCIPAL = '90d'

# El secundario da la lectura a plazo completo. Tiene menos muestra (844 vs
# 1511) porque una señal necesita 180 días cerrados para entrar.
SECUNDARIO = '180d'

LARGOS = (PRINCIPAL, SECUNDARIO)

# Estrategias de corto plazo por diseño: un rebote técnico se resuelve o
# fracasa en semanas, y medirlo a 90 días mezcla el rebote con lo que venga
# después.
ESTRATEGIAS_CORTO_PLAZO = frozenset({'MEAN_REVERSION', 'BOUNCE_BROAD', 'ENTRY_SETUP'})

CORTO_PRINCIPAL = '30d'
CORTO_SECUNDARIO = '14d'
CORTOS = (CORTO_PRINCIPAL, CORTO_SECUNDARIO)


def es_corto_plazo(estrategia) -> bool:
    """¿Esta estrategia se mide a semanas en vez de a meses?"""
    return str(estrategia or '').strip().upper() in ESTRATEGIAS_CORTO_PLAZO


def horizontes_de(estrategia=None) -> tuple[str, str]:
    """(principal, secundario) para una estrategia. Sin argumento, los largos."""
    return CORTOS if es_corto_plazo(estrategia) else LARGOS


def etiqueta(horizonte: str) -> str:
    """'90d' -> '90 días'. Para no escribir el sufijo a mano en cada sitio."""
    h = str(horizonte or '').strip()
    return f"{h[:-1]} días" if h.endswith('d') and h[:-1].isdigit() else h
