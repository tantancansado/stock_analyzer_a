#!/usr/bin/env python3
"""Peso en cartera de cada idea de Value US y de cada posición del usuario.

El usuario (8-nov-2026): «calcular qué porcentaje de la cartera deberíamos [tener]
para cada recomendación [...] si tiene en esa acción un 15 %, que la IA sea capaz de
decirle "deberías tener un 4 %"». Y «si una es mejor que otra, la app debería
discernir la que es mejor y recomendar una sobre otra».

Lo medido manda en cómo se reparte. Más recorrido según nuestra valoración NO da
más rentabilidad dentro de PRIORIDAD de forma que se repita (ver
value_bands.puede_doblar), así que no se apuesta más a una idea que a otra: cada idea
de PRIORIDAD es una posición completa. Lo que sí se controla es el riesgo:

  1. Volatilidad. Una empresa que se mueve el doble pesa la mitad, para que cada
     posición arriesgue lo mismo. La referencia es la mediana del universo a un año
     (31 % el 8-nov-2026): Coca-Cola, a 19 %, lleva la posición entera; las de
     equipos de chips, a 63-69 %, la mitad o menos.
  2. Ciclo. Dos empresas cuyo precio se mueve casi igual (correlación de un año
     >= 0,7) son la misma apuesta: ASML, Applied, KLA y Lam (0,83-0,91), los
     corredores de seguros (0,72-0,84) o Visa y Mastercard (0,88). Por ciclo, dos
     posiciones como mucho, y van las de mejor nota. Así se decide entre Lam y
     Applied: no por el universo, sino por cuál está más barata.

OBSERVAR no recibe dinero nuevo: medido, ese grupo rinde como el universo.

Para una posición que ya se tiene, el techo es el doble de su peso en PRIORIDAD, o
una posición completa si no es PRIORIDAD. Por encima se recorta hasta el techo, no
hasta el objetivo: entre los dos se deja correr hacia el precio objetivo, que es
cuando vende el usuario. Lo que no es acción (fondos, bonos, opciones) no lleva peso
propio: el fondo es la base de la cartera.

Salida: docs/position_sizing.csv, una fila por empresa de la lista publicada.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from value_bands import motivo_de_venta

DOCS = Path('docs')
LISTA = DOCS / 'value_opportunities_filtered.csv'
SALIDA = DOCS / 'position_sizing.csv'

# 5 % hasta el 11-nov-2026. El usuario lo subió a 10: «si estamos filtrando ya
# bastante no debería ser tan peligroso». En la reconstrucción 2020-26, con un 5 %
# solo había de media un 18 % de la cartera en ideas y la ventaja se diluía (+18 %
# al año contra +14 % del S&P); con un 10 %, +21 % y una caída máxima de -20 % frente
# a -22 %. Es la misma muestra con la que se eligió la regla: el tracker por grupos
# tiene que confirmarlo en febrero de 2027.
POSICION_COMPLETA = 10.0     # % de la cartera
VOL_REFERENCIA = 30.0        # % anual; mediana del universo, 31 el 8-nov-2026
PESO_MINIMO = 1.0            # por debajo no merece la pena una posición
CORRELACION_CICLO = 0.7
MAX_POR_CICLO = 2
SESIONES_MINIMAS = 120       # medio año: con menos, la volatilidad no se conoce


def _fmt(x: float) -> str:
    return f'{x:.1f}'.replace('.', ',').removesuffix(',0')


def _redondear(p: float) -> float:
    """A medio punto: un 3,37 % finge una precisión que nadie tiene."""
    return round(p * 2) / 2


def riesgo(precios: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Volatilidad anual (%) y correlaciones de rentabilidades diarias.

    `precios`: cierres diarios ajustados, una columna por ticker. Un ticker con
    menos de SESIONES_MINIMAS no tiene volatilidad: no se inventa.
    """
    r = np.log(precios.astype(float)).diff()
    validas = r.notna().sum()
    r = r.loc[:, validas >= SESIONES_MINIMAS]
    vol = r.std() * math.sqrt(252) * 100
    return vol, r.corr(min_periods=SESIONES_MINIMAS)


def peso_completo(vol: float | None) -> float | None:
    """Una posición completa para esta volatilidad, o None sin el dato."""
    if vol is None or math.isnan(vol) or vol <= 0:
        return None
    return max(PESO_MINIMO, _redondear(POSICION_COMPLETA * min(1.0, VOL_REFERENCIA / vol)))


def ciclos(corr: pd.DataFrame, tickers: list[str]) -> dict[str, tuple[str, ...]]:
    """Grupos de tickers cuyo precio se mueve casi igual (componentes conexas)."""
    dentro = [t for t in tickers if t in corr.index]
    vecinos = {t: {u for u in dentro if u != t and corr.at[t, u] >= CORRELACION_CICLO} for t in dentro}
    grupo: dict[str, tuple[str, ...]] = {}
    for t in dentro:
        if t in grupo:
            continue
        pila, visto = [t], {t}
        while pila:
            for u in vecinos[pila.pop()] - visto:
                visto.add(u)
                pila.append(u)
        miembros = tuple(sorted(visto))
        for u in miembros:
            grupo[u] = miembros
    return grupo


def _lista(nombres) -> str:
    nombres = list(nombres)
    return nombres[0] if len(nombres) == 1 else ', '.join(nombres[:-1]) + ' y ' + nombres[-1]


def pesos_de_ideas(lista: pd.DataFrame, vol: pd.Series, corr: pd.DataFrame) -> pd.DataFrame:
    """Peso objetivo de cada idea de la lista publicada, con su motivo."""
    df = lista.copy()
    df['value_score'] = pd.to_numeric(df.get('value_score'), errors='coerce')
    df = df.sort_values('value_score', ascending=False)
    prioridad = df.loc[df['value_grupo'].astype(str) == 'PRIORIDAD', 'ticker'].tolist()
    grupo = ciclos(corr, prioridad)
    ocupados: dict[tuple[str, ...], list[str]] = {}
    filas = []
    for _, r in df.iterrows():
        t, g = r['ticker'], str(r.get('value_grupo') or '')
        v = vol.get(t)
        completo = peso_completo(v)
        fila = {'ticker': t, 'value_grupo': g, 'volatilidad_pct': round(float(v), 1) if completo else None,
                'peso_completo_pct': completo, 'peso_objetivo_pct': 0.0, 'ciclo': '', 'peso_motivo': ''}
        if g != 'PRIORIDAD':
            fila['peso_motivo'] = 'Observar: sin dinero nuevo hasta que sea Prioridad.'
        elif completo is None:
            fila['peso_objetivo_pct'] = None
            fila['peso_motivo'] = 'Sin un año de precios no se conoce su riesgo: no se dimensiona.'
        else:
            miembros = grupo.get(t, (t,))
            otros = [u for u in miembros if u != t]
            if otros:
                fila['ciclo'] = ' '.join(miembros)
            delante = ocupados.setdefault(miembros, [])
            if len(delante) >= MAX_POR_CICLO:
                fila['peso_motivo'] = (f'Se mueve igual que {_lista(delante)}, que están más baratas: '
                                       f'como mucho {MAX_POR_CICLO} del mismo ciclo.')
            else:
                delante.append(t)
                fila['peso_objetivo_pct'] = completo
                partes = [f'Posición completa ({POSICION_COMPLETA:.0f} %)' if completo >= POSICION_COMPLETA
                          else f'Se mueve un {v:.0f} % al año, más que la media ({VOL_REFERENCIA:.0f} %): '
                               f'{_fmt(completo)} % en vez de {POSICION_COMPLETA:.0f}']
                if otros:
                    partes.append(f'comparte ciclo con {_lista(otros)}')
                fila['peso_motivo'] = '; '.join(partes) + '.'
        filas.append(fila)
    return pd.DataFrame(filas)


def motivos_de_venta(docs: Path = DOCS) -> dict[str, str]:
    """{ticker: motivo} de lo que fue Prioridad; '' si se mantiene (value_bands.motivo_de_venta).

    Solo lo que el tracker registró en PRIORIDAD (desde el 9-nov-2026): lo comprado
    por otra razón sigue vendiéndose al objetivo (portfolio_price_alerts). Sin el
    estado del integrador o sin el tracker no se decide nada.
    """
    try:
        tracker = pd.read_csv(docs / 'portfolio_tracker' / 'recommendations.csv',
                              usecols=['ticker', 'value_grupo'], low_memory=False)
        estado = pd.read_csv(docs / 'value_estado.csv')
    except (OSError, ValueError):
        return {}
    fue = set(tracker.loc[tracker['value_grupo'] == 'PRIORIDAD', 'ticker'].astype(str).str.upper())
    try:
        cache = json.loads((docs / 'why_cheap_cache.json').read_text())
    except (OSError, ValueError):
        cache = {}
    veredictos = {str(t).upper(): str((e or {}).get('veredicto') or '') for t, e in cache.items()}
    estado = estado[estado['ticker'].astype(str).str.upper().isin(fue)]
    return dict(zip(estado['ticker'].astype(str).str.upper(), motivo_de_venta(estado, veredictos)))


def peso_de_posicion(peso_actual: float, grupo: str, vol: float | None, venta: str = '') -> dict:
    """Qué peso debería tener una posición que ya se tiene, y qué hacer.

    `grupo`: PRIORIDAD / OBSERVAR / '' (fuera de la lista o fuera del universo).
    `venta`: el motivo de `motivos_de_venta` si fue Prioridad y ya no lo es.
    Devuelve {objetivo, techo, accion, motivo}; accion es AÑADIR, MANTENER, REDUCIR o VENDER.
    """
    if venta:
        return {'objetivo': 0.0, 'techo': 0.0, 'accion': 'VENDER',
                'motivo': f'Fue Prioridad y ya no lo es: {venta}. Toca vender.'}
    completo = peso_completo(vol)
    if completo is None:
        return {'objetivo': None, 'techo': None, 'accion': 'MANTENER',
                'motivo': 'Sin un año de precios no se conoce su riesgo: sin peso calculado.'}
    if grupo == 'PRIORIDAD':
        objetivo, techo = completo, completo * 2
        if peso_actual > techo:
            return {'objetivo': objetivo, 'techo': techo, 'accion': 'REDUCIR',
                    'motivo': f'Pesa un {_fmt(peso_actual)} %, más del doble de una posición completa para su riesgo '
                              f'({_fmt(objetivo)} %): recorta hasta {_fmt(techo)} %.'}
        if peso_actual < objetivo - 0.5:
            return {'objetivo': objetivo, 'techo': techo, 'accion': 'AÑADIR',
                    'motivo': f'Es Prioridad y pesa un {_fmt(peso_actual)} %: puedes subir hasta {_fmt(objetivo)} %.'}
        return {'objetivo': objetivo, 'techo': techo, 'accion': 'MANTENER',
                'motivo': f'Bien de peso: entre {_fmt(objetivo)} y {_fmt(techo)} % se deja correr hasta el objetivo.'}
    techo = completo
    porque = 'está en Observar' if grupo == 'OBSERVAR' else 'no está en la lista de Value'
    if peso_actual > techo:
        return {'objetivo': None, 'techo': techo, 'accion': 'REDUCIR',
                'motivo': f'Pesa un {_fmt(peso_actual)} % y {porque}: más de una posición completa para su riesgo. '
                          f'Recorta hasta {_fmt(techo)} %.'}
    return {'objetivo': None, 'techo': techo, 'accion': 'MANTENER',
            'motivo': f'No añadas: {porque}. Techo {_fmt(techo)} %.'}


def aviso_de_ciclos(pesos: dict[str, float], corr: pd.DataFrame, vol: pd.Series) -> list[str]:
    """Posiciones que son la misma apuesta y, juntas, pesan más de dos completas.

    «Completa» según su riesgo: dos de equipos de chips (4,5 % cada una) son un 9 %,
    no un 20 %. Sin volatilidad de ninguna no se dice nada: no se inventa el tope.
    """
    avisos = []
    vistos = set()
    for miembros in ciclos(corr, list(pesos)).values():
        if len(miembros) < 2 or miembros in vistos:
            continue
        vistos.add(miembros)
        completas = [c for c in (peso_completo(vol.get(t)) for t in miembros) if c is not None]
        if not completas:
            continue
        tope = MAX_POR_CICLO * max(completas)
        total = sum(pesos[t] for t in miembros)
        if total > tope:
            sobran = (f' Quédate con las {MAX_POR_CICLO} más baratas.' if len(miembros) > MAX_POR_CICLO else '')
            avisos.append(f'{_lista(miembros)} se mueven casi igual: juntas pesan un {_fmt(total)} % y, como una '
                          f'sola apuesta, no deberían pasar del {_fmt(tope)} %.{sobran}')
    return avisos


def precios_diarios(tickers: list[str]) -> pd.DataFrame:
    import yfinance as yf
    crudo = yf.download(tickers, period='1y', interval='1d', auto_adjust=True, progress=False, threads=True)
    cierres = crudo['Close'] if isinstance(crudo.columns, pd.MultiIndex) else crudo[['Close']].set_axis(tickers, axis=1)
    return cierres.dropna(how='all')


def main() -> None:
    if not LISTA.exists():
        print(f'❌ No está {LISTA}: nada que dimensionar')
        raise SystemExit(1)
    lista = pd.read_csv(LISTA)
    if lista.empty or 'value_grupo' not in lista.columns:
        print('❌ Lista sin grupos de Value: se mantiene el CSV anterior')
        raise SystemExit(1)
    tickers = lista['ticker'].astype(str).tolist()
    try:
        precios = precios_diarios(tickers)
    except Exception as e:
        print(f'❌ No se pudieron bajar los precios ({e}): se mantiene el CSV anterior')
        raise SystemExit(1)
    vol, corr = riesgo(precios)
    if vol.empty:
        print('❌ Ningún ticker con un año de precios: se mantiene el CSV anterior')
        raise SystemExit(1)
    salida = pesos_de_ideas(lista, vol, corr)
    salida.to_csv(SALIDA, index=False)
    con = salida[salida['peso_objetivo_pct'] > 0]
    print(f'💾 {SALIDA}: {len(con)} ideas con peso, {con["peso_objetivo_pct"].sum():.1f} % entre todas')
    for _, r in con.iterrows():
        print(f"   {r['ticker']:6} {r['peso_objetivo_pct']:4.1f} %  {r['peso_motivo']}")


if __name__ == '__main__':
    main()
