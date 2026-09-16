#!/usr/bin/env python3
"""Soportes con FECHA: un nivel no vale lo mismo si es de hace un mes o de hace un año.

Por qué existe
──────────────
El 16-sep-2026, con CBOE a 267, el perfil de volumen de 12 meses señalaba una
zona densa en 247-258 y yo se la di al usuario como sitio para comprar. Estaba
mal, y por un motivo que ningún cálculo del repo miraba: **ese volumen se
negoció entre noviembre de 2025 y enero de 2026**, nueve o diez meses antes. Es
soporte de un rango viejo que el precio abandonó hace tres trimestres.

El soporte que sí había funcionado, y hace tres meses, era 230,87 — el mínimo
del 29 de junio, donde frenó el desplome anterior.

Un nodo de alto volumen dice "aquí se negoció mucho". No dice cuándo, ni si
aguantó cuando se puso a prueba, ni si el precio ha vuelto desde entonces. Esas
tres cosas son la diferencia entre un suelo y una marca en el gráfico, y las
tres se calculan con los mismos datos que ya se descargan.

Qué devuelve
────────────
Niveles ordenados por cercanía al precio, cada uno con:
  · de dónde sale (mínimo pivote / nodo de volumen)
  · cuándo se formó y cuándo se puso a prueba por última vez
  · cuántas veces aguantó y cuántas se rompió — que es la única medida honesta
    de si es un soporte o solo un sitio por donde pasó el precio
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

# Ventana de búsqueda. 2 años: con 1 se pierde el contexto de dónde vino el
# precio, y con 5 se llenan de niveles que ya no significan nada.
VENTANA_SESIONES = 504

# Un pivote es un mínimo rodeado de sesiones más altas a ambos lados.
PIVOTE_HOLGURA = 3

# Dos niveles a menos de esto son el mismo nivel.
AGRUPAR_PCT = 2.0

# A partir de aquí el nivel es «antiguo»: un trimestre sin que el precio lo
# visite. No es un umbral calibrado contra rendimiento — es el plazo a partir
# del cual la composición de quien está dentro ya no se parece.
ANTIGUO_DIAS = 90

# Cuánto tiene que acercarse el precio para considerar que «puso a prueba» el
# nivel, y cuánto tiene que perderlo para considerar que lo rompió.
TOCA_PCT = 1.5
ROMPE_PCT = 2.5


@dataclass
class Soporte:
    nivel: float
    tipo: str                 # 'pivote' | 'volumen'
    distancia_pct: float
    formado: str              # fecha en que aparece por primera vez
    ultima_prueba: str | None
    dias_desde_prueba: int | None
    veces_aguanto: int
    veces_roto: int
    antiguo: bool
    nota: str


def _pivotes(bajos: pd.Series) -> list[tuple[pd.Timestamp, float]]:
    h = PIVOTE_HOLGURA
    out = []
    for i in range(h, len(bajos) - h):
        if bajos.iloc[i] == bajos.iloc[i - h:i + h + 1].min():
            out.append((bajos.index[i], float(bajos.iloc[i])))
    return out


def _nodos_de_volumen(cierres: pd.Series, volumen: pd.Series, n: int = 4) -> list[tuple[pd.Timestamp, float]]:
    """Precios donde más se ha negociado, con la FECHA MEDIA de ese volumen.

    La fecha es la clave y es lo que no se calculaba: un nodo puede ser enorme
    y haberse formado entero hace diez meses.
    """
    if cierres.empty or float(volumen.sum()) <= 0:
        return []
    bordes = np.linspace(float(cierres.min()), float(cierres.max()), 26)
    cesta = np.digitize(cierres.values, bordes)
    df = pd.DataFrame({'cesta': cesta, 'vol': volumen.values, 'precio': cierres.values},
                      index=cierres.index)
    por_cesta = df.groupby('cesta')['vol'].sum().sort_values(ascending=False)
    out = []
    for c in por_cesta.head(n).index:
        trozo = df[df.cesta == c]
        if trozo.empty:
            continue
        # Fecha media PONDERADA POR VOLUMEN: si el 90% se negoció en noviembre,
        # el nodo es de noviembre aunque haya alguna sesión suelta reciente.
        pesos = trozo['vol'].values.astype(float)
        if pesos.sum() <= 0:
            continue
        orden = np.argsort(trozo.index.values)  # posiciones, no fechas
        acum = np.cumsum(pesos[orden]) / pesos.sum()
        # `.index.values` pierde la zona horaria y luego no se puede comparar
        # con el resto de fechas (yfinance las devuelve tz-aware). Se indexa
        # sobre el propio índice para conservarla.
        mediana = trozo.index[orden][np.searchsorted(acum, 0.5)]
        nivel = float(np.average(trozo['precio'].values, weights=pesos))
        out.append((mediana, nivel))
    return out


def _pruebas(hist: pd.DataFrame, nivel: float) -> tuple[list[pd.Timestamp], int, int]:
    """Cada vez que el precio BAJÓ hasta el nivel: ¿aguantó o lo perdió?

    Es la única medida honesta de si algo es un soporte. Un nivel que nunca se
    ha puesto a prueba no es un soporte, es una línea en el gráfico.

    El detalle que casi lo estropea: hay que exigir que el precio venga DE
    ARRIBA. Sin eso, cuando la acción subía y atravesaba el nivel de camino a
    máximos, el toque se contaba como «aguantó» — un breakout al alza sumando
    como soporte defendido. Con CBOE inflaba el marcador de casi todos los
    niveles, porque la acción ha pasado por ahí subiendo varias veces en dos
    años. Es el mismo error de siempre: contar un suceso sin comprobar que es
    el suceso que se cree contar.
    """
    if nivel <= 0:
        return [], 0, 0
    techo_previo = nivel * (1 + TOCA_PCT * 2 / 100)
    cerca = (hist['Low'] <= nivel * (1 + TOCA_PCT / 100)) & (hist['Low'] >= nivel * (1 - ROMPE_PCT / 100))
    roto = hist['Close'] < nivel * (1 - ROMPE_PCT / 100)
    fechas, aguanto, rompio, dentro = [], 0, 0, False
    venia_de_arriba = False
    for f in hist.index:
        cierre = float(hist['Close'].loc[f])
        if not dentro:
            if cerca.loc[f] and venia_de_arriba:
                dentro = True
                fechas.append(f)
            elif cierre > techo_previo:
                venia_de_arriba = True
            elif roto.loc[f]:
                # Perdió el nivel sin que contara como prueba (venía de abajo):
                # hasta que no vuelva a estar claramente por encima, no hay
                # nada que defender.
                venia_de_arriba = False
        else:
            if roto.loc[f]:
                rompio += 1
                dentro = False
                venia_de_arriba = False
            elif cierre > techo_previo:
                aguanto += 1
                dentro = False
                venia_de_arriba = True
    return fechas, aguanto, rompio


def soportes(hist: pd.DataFrame, precio: float | None = None,
             maximo: int = 5) -> list[dict]:
    """Soportes por debajo del precio, con su edad y su historial."""
    if hist is None or hist.empty or len(hist) < 60:
        return []
    h = hist.tail(VENTANA_SESIONES)
    precio = float(h['Close'].iloc[-1]) if precio is None else float(precio)
    if precio <= 0:
        return []
    hoy = h.index[-1]

    candidatos: list[tuple[pd.Timestamp, float, str]] = []
    candidatos += [(f, v, 'pivote') for f, v in _pivotes(h['Low']) if v < precio]
    candidatos += [(f, v, 'volumen') for f, v in _nodos_de_volumen(h['Close'], h['Volume']) if v < precio]
    if not candidatos:
        return []

    # Agrupar los que son el mismo nivel; gana el más reciente como fecha de
    # formación y se queda el tipo del más cercano al precio.
    candidatos.sort(key=lambda c: -c[1])
    grupos: list[list[tuple]] = []
    for c in candidatos:
        if grupos and abs(c[1] / grupos[-1][0][1] - 1) * 100 <= AGRUPAR_PCT:
            grupos[-1].append(c)
        else:
            grupos.append([c])

    out: list[Soporte] = []
    for g in grupos[:maximo]:
        nivel = float(np.mean([x[1] for x in g]))
        formado = min(x[0] for x in g)
        tipos = sorted({x[2] for x in g})
        fechas, aguanto, rompio = _pruebas(h, nivel)
        ultima = max(fechas) if fechas else None
        dias = int((hoy - ultima).days) if ultima is not None else None
        antiguo = dias is None or dias > ANTIGUO_DIAS
        out.append(Soporte(
            nivel=round(nivel, 2),
            tipo='+'.join(tipos),
            distancia_pct=round(100 * (nivel / precio - 1), 1),
            formado=str(formado.date()),
            ultima_prueba=str(ultima.date()) if ultima is not None else None,
            dias_desde_prueba=dias,
            veces_aguanto=aguanto,
            veces_roto=rompio,
            antiguo=bool(antiguo),
            nota=_nota(dias, aguanto, rompio, antiguo),
        ))
    return [asdict(s) for s in out]


def _nota(dias, aguanto, rompio, antiguo) -> str:
    if dias is None:
        return 'el precio no ha vuelto por aquí en la ventana: no es un soporte probado'
    edad = (f'sin visitar desde hace {dias // 30} meses' if antiguo
            else f'puesto a prueba hace {dias} días')
    if aguanto == 0 and rompio == 0:
        return f'{edad}; nunca llegó a resolverse'
    if rompio == 0:
        return f'{edad}; aguantó {aguanto} de {aguanto} veces'
    if aguanto == 0:
        return f'{edad}; se rompió las {rompio} veces que se puso a prueba'
    return f'{edad}; aguantó {aguanto} y se rompió {rompio}'


def frase(lista: list[dict]) -> str:
    """Una línea para la ficha: el soporte vivo más cercano, no el más grande."""
    if not lista:
        return 'sin soportes identificables por debajo'
    vivos = [s for s in lista if not s['antiguo'] and s['veces_aguanto'] > 0]
    s = vivos[0] if vivos else lista[0]
    aviso = '' if s in vivos else ' — pero ninguno está vivo: '
    if aviso:
        return (f'el soporte más cercano está en {s["nivel"]:.2f} ({s["distancia_pct"]:+.1f}%), '
                f'{s["nota"]}')
    return (f'soporte vivo más cercano en {s["nivel"]:.2f} ({s["distancia_pct"]:+.1f}%), '
            f'{s["nota"]}')
