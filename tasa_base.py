#!/usr/bin/env python3
"""¿Qué hizo ESTE valor las otras veces que estuvo ASÍ?

Por qué existe
──────────────
La app calcula ESTADOS y nunca DESENLACES. Todo lo que publica es de dos tipos:

  · una regla escrita a mano — «bajo la MA200 → ESPERAR» (19 de esas solo en
    `technical_filter`);
  · una estadística agrupada — «ESPERAR rinde −10% de alfa», medida mezclando
    todos los tickers.

Falta la pregunta del medio, que es la que el usuario acaba haciendo a mano:
*este valor, en este estado, las veces anteriores, ¿qué hizo?*

El 16-sep-2026, con CBOE, la diferencia entre las dos respuestas era toda:

    lo que decía la app   «ESPERAR — en caída, espera a que haga suelo»
    lo que decían los datos  las 5 veces anteriores o paró en 3 días (3 de 5,
                             ≤3% más abajo) o se fue un 13-19% abajo. Ni una
                             sola se quedó a medias.

Con la primera frase pones la orden de compra un 5% abajo. Con la segunda te
das cuenta de que ese 5% es justo el hueco entre los dos desenlaces, o sea el
único sitio donde no va a pasar nada.

El único mecanismo del repo para esto era `macro_stress/scoring/
historical_analogues.py`, un stub vacío que espera «a acumular 5 años de
historial de señales». Ese es el error de fondo: espera a tener historia PROPIA
cuando la del mercado ya está ahí. No hacen falta cinco años de señales para
saber qué hizo CBOE las cinco veces anteriores — son diez años de precios que
ya se descargan.

Lo que NO hace
──────────────
No predice. Una tasa base no dice adónde va: dice cómo se ha repartido esto
otras veces. Y con n pequeño ni eso — por eso `muestra_suficiente` y `n` van
siempre delante, y la frase los nombra. Media app se ha equivocado por publicar
un porcentaje sin su n.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Mismos cortes que `mean_reversion_detector` (RSI) y `technical_filter`
# (MA200 y su pendiente a 4 semanas). No se define aquí un tercer criterio:
# tener la misma idea escrita en tres sitios es el fallo que más veces ha
# aparecido en este repo.
# Dos tramos, no tres. `mean_reversion_detector` separa EXTREMO (<20) de ALTO
# (<25) para PUNTUAR un setup, y ahí tiene sentido. Para agrupar episodios no:
# una sobreventa a RSI 18 y otra a RSI 23 son el mismo fenómeno, y partirlas
# deja cohortes de dos o tres casos. Con CBOE la diferencia era n=4 contra n=5,
# y a esas alturas cada caso vale un 20% de la muestra.
RSI_SOBREVENDIDO = 25.0
PENDIENTE_MA200_SESIONES = 21

# Separación mínima entre episodios para no contar la misma caída tres veces.
SEPARACION_MINIMA_SESIONES = 60

# Horizonte de medida. 45 sesiones ≈ un trimestre bursátil: suficiente para que
# un rebote técnico se resuelva y corto para que siga siendo la misma historia.
HORIZONTE_SESIONES = 45

# Por debajo de esto, la tasa base no se usa para decidir — se publica con el
# aviso puesto. No es un umbral estadístico fino: es el punto en que el
# intervalo de confianza ocupa medio rango y el número deja de informar.
MUESTRA_MINIMA = 5

# Umbrales de «cayó bastante más» sobre los que se reparte la muestra.
CORTES_CAIDA = (-4.0, -8.0)

# Esperanza mínima para que un setup con muestra suficiente se publique. Una
# operación cuya esperanza medida es negativa no es una oportunidad: es pagar
# por participar. El listón no es cero porque cero no cubre comisión ni
# horquilla — con 0,25% de coste de ida y vuelta, un setup de +0,39% (el de
# Starbucks del 17-sep-2026) devuelve +0,14% por operación, que no compensa ni
# el riesgo ni la atención.
ESPERANZA_MINIMA_PCT = 0.5


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    sube = d.clip(lower=0).rolling(n).mean()
    baja = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + sube / baja.replace(0, np.nan))


def _tier_rsi(v: float) -> str:
    return 'SOBREVENDIDO' if v < RSI_SOBREVENDIDO else 'NORMAL'


def describir_estado(close: pd.Series, i: int | None = None) -> dict | None:
    """Estado técnico en la sesión `i` (por defecto, la última).

    Tres banderas, las mismas que ya usa el resto del sistema: en qué tramo de
    RSI está, si cotiza sobre o bajo su MA200, y si esa MA200 sube o baja.
    """
    i = len(close) - 1 if i is None else i
    if i < 200 + PENDIENTE_MA200_SESIONES:
        return None
    ma200 = close.rolling(200).mean()
    hoy, antes = ma200.iloc[i], ma200.iloc[i - PENDIENTE_MA200_SESIONES]
    if hoy != hoy or antes != antes:
        return None
    rsi = _rsi(close).iloc[i]
    if rsi != rsi:
        # Sin RSI no hay estado. Antes devolvía el tramo 'SIN_RSI' y con él se
        # formaban cohortes de episodios agrupados por un hueco — la misma
        # regla de siempre: si el dato falla, no hay número.
        return None
    return {
        'tier_rsi':   _tier_rsi(float(rsi)),
        'sobre_ma200': bool(close.iloc[i] > hoy),
        'ma200_sube':  bool(hoy > antes),
    }


def _frase_estado(e: dict) -> str:
    rsi = {'SOBREVENDIDO': 'sobrevendido (RSI<25)',
           'NORMAL': 'RSI normal'}[e['tier_rsi']]
    ma = 'sobre su MA200' if e['sobre_ma200'] else 'bajo su MA200'
    pend = 'que sube' if e['ma200_sube'] else 'que baja'
    return f'{rsi}, {ma} {pend}'


def tasa_base(close: pd.Series, horizonte: int = HORIZONTE_SESIONES) -> dict:
    """Episodios análogos al estado de hoy y qué pasó en cada uno.

    `close` debe traer varios años: con un año no hay episodios que contar.
    """
    vacio = {'n': 0, 'muestra_suficiente': False, 'episodios': [],
             'estado': None, 'frase': 'sin histórico suficiente para comparar'}
    if close is None or len(close) < 200 + PENDIENTE_MA200_SESIONES + horizonte:
        return vacio

    hoy = describir_estado(close)
    if hoy is None:
        return vacio

    episodios = []
    for i in _indices_analogos(close, hoy, horizonte):
        p0 = float(close.iloc[i])
        futuro = close.iloc[i + 1: i + 1 + horizonte]
        if p0 <= 0 or futuro.empty:
            continue
        episodios.append({
            'fecha': str(close.index[i].date()) if hasattr(close.index[i], 'date') else str(close.index[i]),
            'precio': round(p0, 2),
            'caida_extra_pct': round(100 * (float(futuro.min()) / p0 - 1), 1),
            'minimo': round(float(futuro.min()), 2),
            'retorno_pct': round(100 * (float(futuro.iloc[-1]) / p0 - 1), 1),
        })

    n = len(episodios)
    out = {
        'estado': hoy,
        'estado_frase': _frase_estado(hoy),
        'horizonte_sesiones': horizonte,
        'n': n,
        'muestra_suficiente': n >= MUESTRA_MINIMA,
        'episodios': episodios,
    }
    if not n:
        out['frase'] = (f'nunca había estado así ({_frase_estado(hoy)}) '
                        f'en el histórico disponible')
        return out

    caidas = np.array([e['caida_extra_pct'] for e in episodios])
    rets = np.array([e['retorno_pct'] for e in episodios])
    out.update({
        'caida_extra_mediana_pct': round(float(np.median(caidas)), 1),
        'caida_extra_peor_pct':    round(float(caidas.min()), 1),
        'retorno_mediano_pct':     round(float(np.median(rets)), 1),
        'pct_arriba_al_horizonte': round(100 * float((rets > 0).mean())),
        'reparto_caida': {f'{int(c)}%': round(100 * float((caidas <= c).mean()))
                          for c in CORTES_CAIDA},
        'bimodal': _es_bimodal(caidas),
    })
    out['frase'] = _frase(out)
    return out



def _indices_analogos(close: pd.Series, estado: dict,
                      horizonte: int = HORIZONTE_SESIONES) -> list[int]:
    """Posiciones del histórico en que el valor estuvo en `estado`.

    Separadas por `SEPARACION_MINIMA_SESIONES` para no contar la misma caída
    tres veces, y con `horizonte` sesiones por delante para poder medir el
    desenlace.
    """
    out, ultimo = [], -10 ** 9
    for i in range(200 + PENDIENTE_MA200_SESIONES, len(close) - horizonte - 1):
        if i - ultimo <= SEPARACION_MINIMA_SESIONES:
            continue
        if describir_estado(close, i) != estado:
            continue
        out.append(i)
        ultimo = i
    return out


def _pct(v, signo: int) -> float | None:
    try:
        return round(signo * abs(float(v)), 2)
    except (TypeError, ValueError):
        return None


def simular_operacion(hist: pd.DataFrame, objetivo_pct: float, stop_pct: float,
                      horizonte: int = HORIZONTE_SESIONES,
                      cohorte=None, nombre_cohorte: str | None = None) -> dict:
    """Qué habría pasado con ESTE stop y ESTE objetivo en los episodios análogos.

    `tasa_base` mide dónde está el precio AL FINAL del horizonte. Una operación
    con stop no llega al final: la cierra lo primero que toca. Y no es un
    matiz — es la diferencia entre ganar y perder:

        Starbucks, 17-sep-2026, 9 episodios con su estado de hoy
          · a 45 sesiones estaba en positivo el 89%
          · con el stop del setup (-2,5%), el objetivo (+4%) llegaba antes
            solo en el 44%, porque lo típico es caer otro 4% primero
          · esperanza real de la operación: +0,69%

    Publicar el 89% al lado de ese setup es enseñar un número cierto que
    responde a otra pregunta. Esta función responde a la que importa.

    `hist` necesita High y Low: un stop salta con el mínimo del día, no con el
    cierre. Con solo cierres se subestiman los stops y todo parece mejor.

    `cohorte` permite definir QUÉ episodios son comparables. Por defecto se usa
    el estado de `describir_estado` (tramo de RSI14, posición y pendiente de la
    MA200), que sirve para una tesis de valoración pero NO para un setup de
    pánico: el 18-sep-2026, de los 25 episodios que se midieron para GS, solo
    DOS tenían el RSI2 por debajo de 15 que define el setup. Se estaba midiendo
    «comprar GS un día normal sobre su MA200», no «comprar tras un desplome», y
    con eso el filtro puede descartar setups buenos.

    Quien conoce los criterios del setup los pasa aquí como función
    `(hist, i) -> bool`.

    Devuelve n, aciertos, stops, esperanza_pct y los días hasta el objetivo.
    """
    # Un único juego de claves pase lo que pase: quien consuma esto no debe
    # tener que comprobar si la clave existe según por qué camino salió.
    def _vacio(motivo: str) -> dict:
        return {'n': 0, 'aciertos': 0, 'stops': 0, 'ni_stop_ni_objetivo': 0,
                'muestra_suficiente': False,
                'objetivo_pct': _pct(objetivo_pct, signo=1),
                'stop_pct': _pct(stop_pct, signo=-1),
                'esperanza_pct': None, 'pct_acierto': None,
                'dias_mediana_al_objetivo': None,
                'horizonte_sesiones': horizonte, 'estado_frase': None,
                'frase': motivo}

    if hist is None or len(hist) < 200 + PENDIENTE_MA200_SESIONES + horizonte:
        return _vacio('sin histórico suficiente para simular')
    for col in ('Close', 'High', 'Low'):
        if col not in hist.columns:
            return _vacio(f'falta la columna {col}: sin máximos y mínimos no se '
                          f'sabe si el stop saltó intradía')
    if objetivo_pct is None or stop_pct is None:
        return _vacio('sin objetivo o sin stop no hay operación que simular')

    obj = abs(float(objetivo_pct)) / 100.0
    stop = -abs(float(stop_pct)) / 100.0
    close, high, low = hist['Close'], hist['High'], hist['Low']

    if cohorte is None:
        hoy = describir_estado(close)
        if hoy is None:
            return _vacio('no se puede describir el estado de hoy')
        indices = _indices_analogos(close, hoy, horizonte)
        etiqueta = _frase_estado(hoy)
    else:
        indices, ultimo = [], -10 ** 9
        for i in range(200 + PENDIENTE_MA200_SESIONES, len(close) - horizonte - 1):
            if i - ultimo <= SEPARACION_MINIMA_SESIONES:
                continue
            try:
                if not cohorte(hist, i):
                    continue
            except Exception:
                continue
            indices.append(i)
            ultimo = i
        etiqueta = nombre_cohorte or 'cohorte propia del setup'

    aciertos = stops = ninguno = 0
    dias = []
    for i in indices:
        p0 = float(close.iloc[i])
        if p0 <= 0:
            continue
        t_stop = t_obj = None
        for j in range(i + 1, min(i + 1 + horizonte, len(close))):
            if t_stop is None and float(low.iloc[j]) / p0 - 1 <= stop:
                t_stop = j
            if t_obj is None and float(high.iloc[j]) / p0 - 1 >= obj:
                t_obj = j
            if t_stop is not None and t_obj is not None:
                break
        if t_stop is not None and (t_obj is None or t_stop < t_obj):
            stops += 1
        elif t_obj is not None:
            aciertos += 1
            dias.append(t_obj - i)
        else:
            ninguno += 1

    n = aciertos + stops + ninguno
    if not n:
        return {**_vacio(f'nunca había estado así ({etiqueta})'), 'estado_frase': etiqueta}

    # Lo que ni toca stop ni objetivo se cierra al final del horizonte; se
    # cuenta como cero, que es conservador respecto a medir su retorno real.
    esperanza = (aciertos * obj + stops * stop) / n * 100
    out = {
        'n': n, 'aciertos': aciertos, 'stops': stops, 'ni_stop_ni_objetivo': ninguno,
        'muestra_suficiente': n >= MUESTRA_MINIMA,
        'objetivo_pct': round(obj * 100, 2), 'stop_pct': round(stop * 100, 2),
        'esperanza_pct': round(esperanza, 2),
        'pct_acierto': round(100 * aciertos / n),
        'dias_mediana_al_objetivo': int(np.median(dias)) if dias else None,
        'horizonte_sesiones': horizonte,
        'estado_frase': etiqueta,
    }
    out['frase'] = _frase_operacion(out)
    return out


def _frase_operacion(o: dict) -> str:
    aviso = '' if o['muestra_suficiente'] else f" (solo {o['n']} casos, no decide nada)"
    dias = (f", y cuando llegó tardó {o['dias_mediana_al_objetivo']} sesiones de mediana"
            if o.get('dias_mediana_al_objetivo') is not None else '')
    return (f"en los {o['n']} episodios iguales, el objetivo (+{o['objetivo_pct']:.1f}%) "
            f"llegó antes que el stop ({o['stop_pct']:.1f}%) {o['aciertos']} veces "
            f"y el stop saltó primero {o['stops']}{dias}. Esperanza "
            f"{o['esperanza_pct']:+.2f}% por operación{aviso}.")


def _es_bimodal(caidas: np.ndarray) -> bool:
    """¿Se parte la muestra en dos grupos con un hueco en medio?

    Importa más que la mediana: si no hay casos intermedios, poner una orden a
    medio camino es ponerla donde históricamente no pasa nada. Con CBOE los
    cinco episodios daban −18,9 / −12,7 / −3,0 / −1,1 / +3,0: dos grupos y un
    hueco de nueve puntos en medio, justo donde yo había propuesto comprar.

    El detalle que casi lo estropea: un único caso extremo —marzo de 2020 está
    en casi todas las muestras— abre un hueco enorme sin que haya dos grupos.
    Eso es una cola gorda, no una bimodalidad, y con el criterio ingenuo («el
    mayor hueco es grande») la bandera saltaba en 12 de 13 tickers, o sea no
    decía nada. Por eso se exige que AMBOS lados pesen: mínimo dos casos y un
    cuarto de la muestra cada uno.

    No es una prueba estadística. Es un detector de «aquí falta el medio», que
    es lo único que hace falta saber para no poner la orden justo ahí.
    """
    n = len(caidas)
    if n < 4:
        return False
    o = np.sort(caidas)
    minimo_lado = max(2, int(np.ceil(n * 0.25)))
    mejor = None
    for k in range(minimo_lado, n - minimo_lado + 1):
        hueco = float(o[k] - o[k - 1])
        if mejor is None or hueco > mejor[0]:
            mejor = (hueco, k)
    if mejor is None:
        return False
    hueco, k = mejor
    if hueco < 5.0:
        return False
    # El hueco tiene que ser grande CONTRA la dispersión dentro de cada grupo,
    # no en términos absolutos: 5 puntos separan mucho si los grupos son
    # compactos y nada si ya venían desperdigados.
    dentro = np.concatenate([np.diff(o[:k]), np.diff(o[k:])])
    media_dentro = float(np.mean(dentro)) if len(dentro) else 0.0
    return media_dentro <= 0 or hueco >= 2 * media_dentro


def _frase(t: dict) -> str:
    """Una línea que se pueda imprimir tal cual en la app o en Telegram."""
    n = t['n']
    veces = 'la vez anterior' if n == 1 else f'las {n} veces anteriores'
    if t['bimodal']:
        cuerpo = (f'o paró casi donde estaba o se desplomó hasta '
                  f'{t["caida_extra_peor_pct"]:.0f}% — sin término medio')
    else:
        cuerpo = (f'cayó otro {abs(t["caida_extra_mediana_pct"]):.0f}% de mediana '
                  f'(peor caso {t["caida_extra_peor_pct"]:.0f}%)')
    # El plazo en meses, no en sesiones: «a 252 sesiones» no se lee, y el plazo
    # es la mitad del mensaje — YUM pasa del 73% de episodios en positivo a
    # cuatro meses al 93% a un año.
    hz = t["horizonte_sesiones"]
    plazo = ('al año' if 240 <= hz <= 264 else
             f'a {hz // 21} meses' if hz >= 42 else
             f'a {hz} sesiones')
    cola = (f'; {plazo} el {t["pct_arriba_al_horizonte"]}% '
            f'estaba en positivo (mediana {t["retorno_mediano_pct"]:+.0f}%)')
    aviso = '' if t['muestra_suficiente'] else f' ⚠ solo {n} casos, no decide nada'
    return f'{veces} ({t["estado_frase"]}) {cuerpo}{cola}.{aviso}'
