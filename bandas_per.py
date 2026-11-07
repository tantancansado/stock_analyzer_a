#!/usr/bin/env python3
"""La historia del PER de cada empresa y las revisiones del consenso, desde TIKR.

TIKR no nos da la serie del múltiplo, pero sí el BPA normalizado de cada año
(hasta 27), sin extraordinarios. Con el precio mensual se reconstruye el PER sin
mirar al futuro: el BPA de un año solo cuenta 60 días después de su cierre.

Se guarda la media y la desviación del logaritmo del PER en sus 10 años
anteriores, y `aplicar` calcula la desviación con el precio del día. Así, si un
día falla la descarga de precios, las bandas de ayer siguen valiendo.

Medido (2005-2025, 124 empresas): la desviación sola predice poco y en 2011-15
salió al revés, pero con las ventas creciendo al 10 % o más es lo mejor que se ha
encontrado. Ver value_bands.nota_value.

De aquí sale también el objetivo por P/E de `fundamental_scores.csv`: mediana de 10
años × BPA normalizado. El de yfinance usa beneficio contable, que descartaba a INTU,
FICO o BSX con múltiplos de 54-64x cuando normalizados son 29-43x, y daba a MKC un
BPA del doble del real. Con TIKR, la puerta en 2026 rinde +1,8 a 90 días contra el
universo; con yfinance, -0,4. Reescribirlo en el CSV hace que todo el que lo lea
(lista, avisos de venta, ficha) vea el mismo número. Donde TIKR no llega, se queda
el de yfinance.

También lleva el historial del BPA a 12 meses de cada foto semanal de TIKR, que
es lo que permite medir revisiones de verdad: `analyst_revision_momentum` es
crecimiento esperado por recomendación, y no compara con ninguna fecha anterior.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from value_bands import PER_ANCLA_MAX, PER_ANCLA_MIN, UPSIDE_PE_ABSURDO

DOCS = Path('docs')
TIKR = DOCS / 'tikr_earnings_data.json'
FUND = DOCS / 'fundamental_scores.csv'
SALIDA = DOCS / 'bandas_per.json'
CONSENSO = DOCS / 'tikr_consenso.json'

PER_MIN, PER_MAX = 4.0, 80.0     # fuera de aquí el múltiplo sale de un BPA deprimido
MESES_HISTORIA = 120
MESES_MINIMOS = 60
DIAS_HASTA_CONOCERLO = 60
# Acciones implícitas (beneficio/BPA) que saltan de un año a otro: la serie cambia
# de base y lo anterior no es comparable. CTAS 2005 valía 1,11 con 0,37 en 2010.
SALTO_ACCIONES = (0.6, 1.6)
AJUSTE_ANIOS_TENDENCIA = 6
REVISION_MAXIMA = 0.5            # más que esto es un cambio de base, no una revisión
VENTANAS_REVISION = {'revision_4s_pct': 28, 'revision_13s_pct': 91}
TOLERANCIA_DIAS = 10


def cierre_conocido(anio: int, mes: int) -> pd.Timestamp:
    """Cuándo se conoce el BPA de un año de TIKR. Su etiqueta 2025 es enero de 2026 en
    WMT, pero febrero de 2025 en STZ y mayo de 2025 en ORCL: solo los cierres de enero
    son del año siguiente (validado contra el cierre real de 128 empresas, 7-nov-2026)."""
    return pd.Timestamp(anio if mes >= 2 else anio + 1, mes, 28) + pd.Timedelta(days=DIAS_HASTA_CONOCERLO)


def serie_bpa(td: dict, mes: int, hoy: pd.Timestamp) -> dict[int, float]:
    """BPA normalizado por año, sin lo anterior a una rotura de base.

    Un año ya cerrado pero que TIKR aún lleva en `forward` también cuenta: con
    solo `historico_norm`, MSFT seguía en el BPA de junio de 2025 en noviembre de
    2026 y parecía un 20 % más cara de lo que está.
    """
    est = td.get('analyst_estimates') or {}
    hist = est.get('historico_norm') or {}
    bpa = {int(y): float(v['eps_norm']) for y, v in hist.items() if v.get('eps_norm') is not None}
    neto = {int(y): v.get('net_income_norm') for y, v in hist.items()}
    for y, v in (est.get('forward') or {}).items():
        y = int(y)
        if y not in bpa and v.get('eps_norm') is not None and cierre_conocido(y, mes) <= hoy:
            bpa[y] = float(v['eps_norm'])
            neto[y] = v.get('net_income_norm')
    anios = sorted(bpa)
    inicio = anios[0] if anios else None
    for a, b in zip(anios, anios[1:]):
        if bpa[a] > 0 and bpa[b] > 0 and (neto.get(a) or 0) > 0 and (neto.get(b) or 0) > 0:
            salto = (neto[b] / bpa[b]) / (neto[a] / bpa[a])
            if not SALTO_ACCIONES[0] < salto < SALTO_ACCIONES[1]:
                inicio = b
    return {y: bpa[y] for y in anios if y >= inicio} if anios else {}


def ventas_anuales(td: dict, mes: int, hoy: pd.Timestamp) -> dict:
    """Crecimiento de las ventas del último año cerrado. {} si no se puede.

    Es un cociente de la misma empresa en la misma divisa: vale también para los
    ADR, donde el BPA de TIKR no tiene base fija.
    """
    rv = ((td.get('financials_history') or {}).get('metrics') or {}).get('total_revenue') or {}
    serie = {int(y): float(v) for y, v in rv.items() if v is not None}
    anios = [y for y in sorted(serie) if cierre_conocido(y, mes) <= hoy]
    if len(anios) < 2 or anios[-1] - anios[-2] != 1 or serie[anios[-2]] <= 0:
        return {}
    return {'ventas_anual_pct': round((serie[anios[-1]] / serie[anios[-2]] - 1) * 100, 1), 'ventas_anual_anio': anios[-1]}


def bandas_de_ticker(td: dict, cierres: pd.Series, mes: int, hoy: pd.Timestamp) -> dict:
    """{bpa, bpa_anio, mu, sd, mediana, meses, tendencia_pct}, o {motivo} si no se puede."""
    bpa = serie_bpa(td, mes, hoy)
    if not bpa:
        return {'motivo': 'TIKR no tiene su BPA histórico'}
    conocidos = sorted((cierre_conocido(y, mes), y) for y in bpa)
    if conocidos[0][0] > hoy:
        return {'motivo': 'sin ningún año cerrado'}

    pasados = []
    for f, precio in cierres.dropna().items():
        if f >= hoy.replace(day=1):
            continue
        y = [a for c, a in conocidos if c <= f]
        if y and bpa[y[-1]] > 0:
            per = float(precio) / bpa[y[-1]]
            if PER_MIN < per < PER_MAX:
                pasados.append(math.log(per))
    ultimos = pasados[-MESES_HISTORIA:]
    actual = [a for c, a in conocidos if c <= hoy][-1]
    if bpa[actual] <= 0:
        return {'motivo': f'BPA de {actual} negativo'}
    if len(ultimos) < MESES_MINIMOS:
        return {'motivo': f'solo {len(ultimos)} meses de PER utilizable'}

    previos = [bpa[a] for a in sorted(bpa) if a < actual and bpa[a] > 0][-AJUSTE_ANIOS_TENDENCIA:]
    tendencia = None
    if len(previos) >= 4:
        pendiente, corte = np.polyfit(np.arange(len(previos)), np.log(previos), 1)
        tendencia = round((math.exp(math.log(bpa[actual]) - (corte + pendiente * len(previos))) - 1) * 100, 1)
    return {'bpa': round(bpa[actual], 4), 'bpa_anio': actual, 'mu': round(float(np.mean(ultimos)), 5),
            'sd': round(float(np.std(ultimos, ddof=1)), 5), 'mediana': round(math.exp(float(np.median(ultimos))), 2),
            'meses': len(ultimos), 'tendencia_pct': tendencia}


def revisiones(historial: dict[str, float], hoy: pd.Timestamp) -> dict[str, float | None]:
    """Cuánto ha cambiado el BPA a 12 meses en 4 y 13 semanas. None si no se sabe."""
    salida: dict[str, float | None] = {k: None for k in VENTANAS_REVISION}
    if not historial:
        return salida
    puntos = sorted((pd.Timestamp(f), float(v)) for f, v in historial.items() if v is not None)
    if not puntos:
        return salida
    ultima_f, ultimo = puntos[-1]
    for clave, dias in VENTANAS_REVISION.items():
        objetivo = ultima_f - pd.Timedelta(days=dias)
        cerca = [p for p in puntos if abs((p[0] - objetivo).days) <= TOLERANCIA_DIAS]
        if not cerca:
            continue
        base = min(cerca, key=lambda p: abs((p[0] - objetivo).days))[1]
        if base <= 0:
            continue
        cambio = ultimo / base - 1
        if abs(cambio) <= REVISION_MAXIMA:
            salida[clave] = round(cambio * 100, 1)
    return salida


def _leer(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text())
    except (OSError, ValueError):
        return {}


COLUMNAS = ('per_norm', 'per_mediana_10a', 'per_z', 'precio_per_menos_1s', 'precio_per_media',
            'bpa_sobre_tendencia_pct', 'per_sin_dato_motivo', 'ventas_anual_pct', 'ventas_anual_anio',
            'revision_4s_pct', 'revision_13s_pct')


def aplicar(df: pd.DataFrame, bandas: dict | None = None, consenso: dict | None = None) -> pd.DataFrame:
    """Añade a cada fila su PER contra su historia, al precio del día, y las revisiones."""
    bandas = (_leer(SALIDA) if bandas is None else bandas).get('bandas') or {}
    consenso = (_leer(CONSENSO) if consenso is None else consenso).get('bpa_ntm') or {}
    hoy = pd.Timestamp(date.today())
    filas = []
    for _, r in df.iterrows():
        t = str(r.get('ticker') or '').upper()
        b = bandas.get(t) or {}
        o: dict = {c: None for c in COLUMNAS}
        o.update(revisiones(consenso.get(t) or {}, hoy))
        o['ventas_anual_pct'], o['ventas_anual_anio'] = b.get('ventas_anual_pct'), b.get('ventas_anual_anio')
        precio = pd.to_numeric(r.get('current_price'), errors='coerce')
        if 'mu' not in b:
            o['per_sin_dato_motivo'] = b.get('motivo') or 'sin bandas de PER'
        elif pd.isna(precio) or precio <= 0:
            o['per_sin_dato_motivo'] = 'sin precio'
        else:
            per = float(precio) / b['bpa']
            o.update(per_norm=round(per, 1), per_mediana_10a=b.get('mediana'),
                     per_z=round((math.log(per) - b['mu']) / b['sd'], 2),
                     precio_per_menos_1s=round(b['bpa'] * math.exp(b['mu'] - b['sd']), 2),
                     precio_per_media=round(b['bpa'] * b['mediana'], 2) if b.get('mediana') else None,
                     bpa_sobre_tendencia_pct=b.get('tendencia_pct'))
        filas.append(o)
    extra = pd.DataFrame(filas, index=df.index, columns=list(COLUMNAS))
    return pd.concat([df.drop(columns=[c for c in COLUMNAS if c in df.columns]), extra], axis=1)


COLUMNAS_PE = ('target_price_pe', 'target_price_pe_upside_pct', 'pe_ancla', 'pe_ancla_n', 'pe_ancla_dispersion',
               'pe_ancla_fragil', 'pe_ancla_excluidos', 'pe_sin_ancla_motivo', 'pe_eps_usado', 'pe_eps_motivo')


def reescribir_objetivo_pe(fund: pd.DataFrame, bandas: dict) -> tuple[pd.DataFrame, int]:
    """Pone en la tabla el objetivo por P/E de TIKR donde lo hay. Devuelve (tabla, cuántos)."""
    salida = fund.copy()
    for c in COLUMNAS_PE:
        if c not in salida.columns:
            salida[c] = None
        salida[c] = salida[c].astype(object)
    n = 0
    for i, r in salida.iterrows():
        b = bandas.get(str(r.get('ticker') or '').upper()) or {}
        precio = pd.to_numeric(r.get('current_price'), errors='coerce')
        mediana = b.get('mediana')
        if not mediana or pd.isna(precio) or precio <= 0:
            continue
        if not PER_ANCLA_MIN <= mediana <= PER_ANCLA_MAX:
            continue    # múltiplo de burbuja: tampoco ancla aquí. Queda lo que hubiera
        objetivo = round(b['bpa'] * mediana, 2)
        subida = round((objetivo / float(precio) - 1) * 100, 1)
        if abs(subida) > UPSIDE_PE_ABSURDO:
            continue
        for c, v in (('target_price_pe', objetivo), ('target_price_pe_upside_pct', subida),
                     ('pe_ancla', 'múltiplo propio normalizado (TIKR)'), ('pe_ancla_n', b.get('meses')),
                     ('pe_ancla_dispersion', None), ('pe_ancla_fragil', False), ('pe_ancla_excluidos', None),
                     ('pe_sin_ancla_motivo', None), ('pe_eps_usado', f"normalizado {b.get('bpa_anio')} (TIKR)"),
                     ('pe_eps_motivo', None)):
            salida.at[i, c] = v
        n += 1
    return salida, n


def anotar_consenso(tikr: dict, consenso: dict) -> dict:
    """Añade la foto de TIKR al historial si es nueva. Se escribe una vez por foto."""
    fecha = str(tikr.get('generated_at') or '')[:10]
    historial = consenso.setdefault('bpa_ntm', {})
    if not fecha:
        return consenso
    for t, x in (tikr.get('data') or {}).items():
        v = (x.get('ntm') or {}).get('ntm_eps')
        v = pd.to_numeric(v, errors='coerce')
        if not pd.isna(v):
            historial.setdefault(str(t).upper(), {})[fecha] = round(float(v), 4)
    return consenso


def _mes_fiscal(v) -> int:
    # Sin el dato se asume diciembre: el BPA se da por conocido más tarde de lo
    # real, así que como mucho se usa uno viejo, nunca uno del futuro.
    v = pd.to_numeric(v, errors='coerce')
    return int(v) if not pd.isna(v) and 1 <= v <= 12 else 12


def _calcular(datos: dict, fund: pd.DataFrame, hoy: pd.Timestamp) -> dict | None:
    """Las bandas de hoy, o None si no se pudieron calcular (se usan las de ayer)."""
    fund = fund.drop_duplicates('ticker').set_index('ticker')
    salida: dict[str, dict] = {}
    aptos = []
    for t in fund.index:
        if t not in datos:
            salida[t] = {'motivo': 'fuera de TIKR'}
            continue
        mes = _mes_fiscal(fund.at[t, 'mes_cierre_fiscal']) if 'mes_cierre_fiscal' in fund.columns else 12
        salida[t] = ventas_anuales(datos[t], mes, hoy)
        if fund.at[t, 'price_currency'] == fund.at[t, 'financial_currency']:
            aptos.append(t)
        else:
            # El BPA de TIKR no tiene base fija cuando precio y cuentas van en
            # divisas distintas (ver tikr-bases-por-campo): no se inventa un PER.
            salida[t]['motivo'] = 'cotiza y presenta cuentas en divisas distintas'

    import yfinance as yf
    try:
        crudo = yf.download(aptos, period='15y', interval='1mo', auto_adjust=False,
                            group_by='ticker', threads=True, progress=False)
    except Exception as e:
        print(f'  ⚠️ No se pudieron bajar los precios ({e})')
        return None
    if crudo is None or crudo.empty:
        print('  ⚠️ Descarga de precios vacía')
        return None

    for t in aptos:
        mes = _mes_fiscal(fund.at[t, 'mes_cierre_fiscal']) if 'mes_cierre_fiscal' in fund.columns else 12
        try:
            cierres = (crudo[t]['Close'] if len(aptos) > 1 else crudo['Close']).copy()
            cierres.index = pd.to_datetime(cierres.index).tz_localize(None)
        except Exception:
            salida[t]['motivo'] = 'sin precios históricos'
            continue
        salida[t].update(bandas_de_ticker(datos[t], cierres, mes, hoy))

    con = sum('mu' in v for v in salida.values())
    if con < len(aptos) / 2:
        print(f'  ⚠️ Solo {con} de {len(aptos)} con bandas: algo falla')
        return None
    print(f'  {con} empresas con bandas de {len(fund)} · {len(aptos) - con} sin historia suficiente')
    return salida


def main() -> None:
    print('[Bandas de PER] Historia del múltiplo desde TIKR')
    tikr = _leer(TIKR)
    datos = tikr.get('data') or {}
    hoy = pd.Timestamp(date.today())
    bandas = None
    if not FUND.exists():
        print('  ⚠️ Sin fundamental_scores.csv: nada que hacer')
        return
    fund = pd.read_csv(FUND, low_memory=False)
    if datos:
        CONSENSO.write_text(json.dumps(anotar_consenso(tikr, _leer(CONSENSO)), indent=0, sort_keys=True))
        bandas = _calcular(datos, fund, hoy)
    if bandas is not None:
        SALIDA.write_text(json.dumps({'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                                      'bandas': bandas}, ensure_ascii=False, indent=0, sort_keys=True))
    else:
        print('  ⚠️ Se conservan las bandas anteriores')
        bandas = _leer(SALIDA).get('bandas') or {}
    fund, n = reescribir_objetivo_pe(fund, bandas)
    fund.to_csv(FUND, index=False)
    print(f'  Objetivo por P/E con BPA normalizado de TIKR en {n} de {len(fund)}')


if __name__ == '__main__':
    main()
